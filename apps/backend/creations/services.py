"""Criações: ações do cliente. A API só cria tarefas; quem as executa é o worker."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from catalog import prompts
from catalog.categories import GROUP_REASONS, Category
from catalog.themes import Theme
from common.exceptions import GuardFailed, ResourceNotFound
from common.fsm import apply_transition
from creations import quota
from creations.fsm import CREATION_FSM, TASK_ACTIVE
from creations.models import (
    Creation,
    CreationInput,
    ImageVersion,
    ProviderTask,
    WaitlistEntry,
)
from media import services as media
from media.models import Asset


def creations_for(actor):
    return Creation.objects.filter(actor.owner_filter(), deleted_at__isnull=True)


def get_creation(actor, creation_id) -> Creation:
    creation = (
        creations_for(actor)
        .select_related("input", "input__photo", "current_version")
        .filter(globalid=creation_id)
        .first()
    )
    if creation is None:
        raise ResourceNotFound("Criação não encontrada.")
    return creation


def get_creation_for_response(creation: Creation) -> Creation:
    """Recarrega com o que o serializer usa, depois de uma ação."""
    return (
        Creation.objects.select_related("input", "input__photo", "current_version")
        .prefetch_related("versions__asset", "versions__parent")
        .get(pk=creation.pk)
    )


def _new_task(*, actor, ip_hash: str, creation: Creation, kind: str, **fields) -> ProviderTask:
    quota_kind = quota.reserve(actor=actor, ip_hash=ip_hash, task_kind=kind)
    task = ProviderTask.objects.create(
        creation=creation,
        kind=kind,
        prompt_version=prompts.PROMPT_VERSION,
        next_attempt_at=timezone.now(),
        **fields,
    )
    quota.attach(actor=actor, ip_hash=ip_hash, kind=quota_kind, task=task)
    return task


def start_creation(
    *,
    actor,
    ip_hash: str,
    requested_category: str,
    photo_bytes: bytes,
    theme: str = "",
    request_id: str = "",
) -> Creation:
    """Guarda a foto e pede a classificação. A imagem só é gerada se a foto for aceita (RN-33)."""
    if requested_category not in Category.values:
        raise GuardFailed("Categoria inválida.", code="invalid_category")
    if theme and theme not in Theme.values:
        raise GuardFailed("Tema inválido.", code="invalid_theme")
    prepared = media.prepare_photo(photo_bytes)
    original_photo = media.store(
        data=prepared.original, kind=Asset.Kind.ORIGINAL, mime=prepared.original_mime
    )
    photo = media.store(data=prepared.normalized, kind=Asset.Kind.PHOTO, mime="image/png")

    with transaction.atomic():
        # Só confere a cota de imagem, sem reservar: quem esgotou não gasta a classificação.
        quota.reserve(actor=actor, ip_hash=ip_hash, task_kind=ProviderTask.Kind.GENERATE)
        creation = Creation.objects.create(
            requested_category=requested_category, **actor.owner_fields()
        )
        CreationInput.objects.create(
            creation=creation,
            theme=theme,
            photo=photo,
            original_photo=original_photo,
            terms_version=settings.BUSINESS["TERMS_VERSION"],
        )
        _enqueue_photo_classification(actor=actor, ip_hash=ip_hash, creation=creation)
        _record_started(creation, actor, request_id)
    return creation


def _record_started(creation: Creation, actor, request_id: str) -> None:
    from audit.services import record_event

    record_event(
        instance=creation,
        event="created",
        to_state=creation.status,
        actor=actor,
        request_id=request_id,
    )


def _enqueue_photo_classification(*, actor, ip_hash: str, creation: Creation) -> ProviderTask:
    return _new_task(
        actor=actor, ip_hash=ip_hash, creation=creation, kind=ProviderTask.Kind.CLASSIFY
    )


def enqueue_image(*, actor, ip_hash: str, creation: Creation) -> ProviderTask:
    """Gera a imagem na categoria detectada. Reserva a cota de imagem (levanta QuotaExceeded)."""
    return _new_task(
        actor=actor,
        ip_hash=ip_hash,
        creation=creation,
        kind=ProviderTask.Kind.GENERATE,
        rendered_prompt=prompts.photo_prompt(
            category=creation.category, theme=creation.input.theme
        ),
    )


def enqueue_version_classification(version: ImageVersion) -> ProviderTask:
    """Classifica uma versão gerada (RN-34). Não usa cota do cliente; o custo entra no teto."""
    return ProviderTask.objects.create(
        creation=version.creation,
        kind=ProviderTask.Kind.CLASSIFY,
        source_version=version,
        next_attempt_at=timezone.now(),
    )


def actor_of(creation: Creation):
    """O dono da criação, para o worker reservar cota em nome dele."""
    from common.actor import Actor

    if creation.user_id is not None:
        return Actor(user=creation.user)
    return Actor(visitor=creation.visitor)


def retry(*, actor, ip_hash: str, creation: Creation, request_id: str = "") -> Creation:
    """Tenta de novo a etapa que falhou: a leitura da foto, a leitura da imagem ou a imagem.

    Uma nova reserva de cota quando a etapa usa cota: a anterior foi devolvida.
    """
    unclassified = (
        creation.versions.filter(category="", rejection_reason="").order_by("number").first()
        if creation.category and creation.current_version_id is None
        else None
    )

    def effects():
        creation.last_error_code = ""
        creation.last_error_message = ""
        creation.save(update_fields=["last_error_code", "last_error_message", "updated_at"])
        if not creation.category:
            _enqueue_photo_classification(actor=actor, ip_hash=ip_hash, creation=creation)
        elif unclassified is not None:
            enqueue_version_classification(unclassified)
        else:
            enqueue_image(actor=actor, ip_hash=ip_hash, creation=creation)

    apply_transition(
        instance=creation,
        fsm=CREATION_FSM,
        event="retry" if creation.category else "retry_classification",
        actor=actor,
        effects=effects,
        request_id=request_id,
    )
    creation.refresh_from_db()
    return creation


def request_edit(
    *, actor, ip_hash: str, creation: Creation, instruction: str, version_id
) -> ProviderTask:
    instruction = instruction.strip()
    if not instruction:
        raise GuardFailed("Descreva o ajuste.", code="empty_instruction")
    if len(instruction) > settings.BUSINESS["EDIT_MAX_CHARS"]:
        raise GuardFailed("Instrução longa demais.", code="instruction_too_long")
    if creation.status != Creation.Status.READY:
        raise GuardFailed("Esta criação não pode ser editada agora.", code="not_editable")
    version = creation.versions.filter(globalid=version_id).first()
    if version is None:
        raise ResourceNotFound("Versão não encontrada.")
    with transaction.atomic():
        return _new_task(
            actor=actor,
            ip_hash=ip_hash,
            creation=creation,
            kind=ProviderTask.Kind.EDIT,
            source_version=version,
            instruction=instruction,
            rendered_prompt=prompts.edit_prompt(instruction=instruction),
        )


def cancel_edit(*, creation: Creation, task_id) -> ProviderTask:
    """Oculta o resultado. Se o provedor já recebeu a tarefa, o custo fica registrado (RN-08)."""
    with transaction.atomic():
        task = (
            creation.tasks.select_for_update()
            .filter(globalid=task_id, kind=ProviderTask.Kind.EDIT)
            .first()
        )
        if task is None:
            raise ResourceNotFound("Edição não encontrada.")
        if task.status not in TASK_ACTIVE:
            return task
        already_sent = task.status != ProviderTask.Status.QUEUED
        task.status = ProviderTask.Status.CANCELLED
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "finished_at", "updated_at"])
        if already_sent:
            quota.consume(task)
        else:
            quota.release(task)
    return task


def apply_version(*, actor, creation: Creation, version_id, request_id: str = "") -> Creation:
    """Concluir a edição: a versão escolhida vira a atual. Itens no carrinho mantêm a sua."""
    from audit.services import record_event

    version = creation.versions.filter(globalid=version_id).first()
    if version is None:
        raise ResourceNotFound("Versão não encontrada.")
    if creation.status != Creation.Status.READY:
        raise GuardFailed("Esta criação não pode ser alterada agora.", code="not_editable")
    if creation.current_version_id == version.pk:
        return creation

    with transaction.atomic():
        creation.current_version = version
        creation.save(update_fields=["current_version", "updated_at"])
        record_event(
            instance=creation,
            event="version_applied",
            actor=actor,
            request_id=request_id,
            payload={"version": version.number},
        )
    creation.refresh_from_db()
    return creation


def join_waitlist(*, actor, creation: Creation, email: str) -> WaitlistEntry:
    """Lista de espera de quem foi recusado por ter gente ou pets demais na foto (RN-37).

    Enviar o e-mail no formulário, que diz para que ele serve, é o consentimento.
    """
    if (
        creation.status != Creation.Status.REJECTED
        or creation.rejection_reason not in GROUP_REASONS
    ):
        raise GuardFailed(
            "A lista de espera é só para fotos com mais pessoas ou pets.", code="not_waitlistable"
        )
    classification = (
        creation.classifications.filter(version__isnull=True).order_by("-created_at").first()
    )
    entry, _ = WaitlistEntry.objects.get_or_create(
        email=email.strip().lower(),
        reason=creation.rejection_reason,
        defaults={
            "classification": classification,
            "consent_version": settings.BUSINESS["WAITLIST_CONSENT_VERSION"],
            "consented_at": timezone.now(),
            **actor.owner_fields(),
        },
    )
    return entry


def delete_creation(*, actor, creation: Creation, request_id: str = "") -> None:
    from audit.services import record_event

    creation.deleted_at = timezone.now()
    creation.save(update_fields=["deleted_at", "updated_at"])
    record_event(instance=creation, event="deleted", actor=actor, request_id=request_id)


def delete_all_for_user(user) -> None:
    now = timezone.now()
    for creation in Creation.objects.filter(user=user, deleted_at__isnull=True):
        creation.deleted_at = now
        creation.save(update_fields=["deleted_at", "updated_at"])


def transfer_visitor_creations(*, visitor, user) -> int:
    return Creation.objects.filter(visitor=visitor, user__isnull=True).update(user=user)


def purge_expired_assets() -> dict:
    """Aplica a retenção. Arquivos ligados a um pedido nunca são apagados (RN-28)."""
    from accounts.models import Visitor
    from orders.models import OrderItem

    now = timezone.now()
    business = settings.BUSINESS
    purged = {"photos": 0, "generated": 0, "visitors": 0}
    with_order = OrderItem.objects.values("creation_id")

    photo_cutoff = now - timedelta(days=business["PHOTO_RETENTION_DAYS"])
    photos = CreationInput.objects.filter(
        photo__isnull=False, photo__purged_at__isnull=True, creation__created_at__lt=photo_cutoff
    ).exclude(creation_id__in=with_order)
    for source in photos.select_related("photo", "original_photo"):
        media.purge(source.photo)
        if source.original_photo is not None:
            media.purge(source.original_photo)
        purged["photos"] += 1

    deleted_cutoff = now - timedelta(days=business["DELETED_CREATION_PURGE_DAYS"])
    deleted = Creation.objects.filter(deleted_at__lt=deleted_cutoff).exclude(pk__in=with_order)
    for creation in deleted.prefetch_related("versions__asset"):
        assets = [v.asset for v in creation.versions.all()]
        source = getattr(creation, "input", None)
        if source is not None:
            assets.append(source.photo)
            if source.original_photo is not None:
                assets.append(source.original_photo)
        for asset in assets:
            if asset.purged_at is None:
                media.purge(asset)
                purged["generated"] += 1

    visitor_cutoff = now - timedelta(days=business["VISITOR_RETENTION_DAYS"])
    inactive = Visitor.objects.filter(last_seen_at__lt=visitor_cutoff)
    purged["visitors"] = inactive.count()
    # Sem dono, a criação some do produto: entra na retenção de excluídas.
    Creation.objects.filter(
        visitor__in=inactive, user__isnull=True, deleted_at__isnull=True
    ).update(deleted_at=now)
    inactive.delete()
    return purged
