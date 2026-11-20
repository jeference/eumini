"""Worker de geração: consome `ProviderTask` com `FOR UPDATE SKIP LOCKED`.

Cada tarefa é pega com uma concessão de tempo (`locked_until`). Se o processo morrer, a
concessão vence e outro worker assume.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import requests
import structlog
from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone

from catalog.categories import Category
from common.alerts import alert
from common.exceptions import QuotaExceeded, ServiceBusy
from common.fsm import apply_transition
from creations import quota, services
from creations.fsm import CREATION_FSM
from creations.models import Classification, Creation, ImageVersion, ProviderTask
from integrations.ports import (
    ContentRefused,
    GeneratedImage,
    ImageGenerationPort,
    ProviderPermanentError,
    ProviderTemporaryError,
    get_image_classification_port,
    get_image_generation_port,
)
from media import services as media
from media.models import Asset

_REFUSED_MESSAGE = (
    "Não conseguimos gerar essa imagem porque ela esbarrou nas regras de conteúdo. Personagens "
    "e marcas conhecidos, nudez e violência costumam ser recusados. Tente descrever de outro jeito."
)
_FAILED_MESSAGE = "Não conseguimos gerar agora. Tente de novo."
_CLASSIFY_FAILED_MESSAGE = "Não conseguimos ler a foto agora. Tente de novo."
_TIMEOUT_MESSAGE = "A geração demorou demais. Tente de novo."

log = structlog.get_logger(__name__)


def claim_task() -> ProviderTask | None:
    """Pega a próxima tarefa livre: na fila, ou com a concessão vencida."""
    now = timezone.now()
    lease = timedelta(seconds=settings.BUSINESS["TASK_LEASE_SECONDS"])
    with transaction.atomic():
        task = (
            ProviderTask.objects.select_for_update(skip_locked=True)
            .filter(
                Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now),
                Q(locked_until__isnull=True) | Q(locked_until__lte=now),
                status__in=(ProviderTask.Status.QUEUED, ProviderTask.Status.RUNNING),
            )
            .order_by("next_attempt_at", "created_at")
            .first()
        )
        if task is None:
            return None
        task.locked_until = now + lease
        task.started_at = task.started_at or now
        if task.status == ProviderTask.Status.QUEUED:
            task.status = ProviderTask.Status.RUNNING
        task.save(update_fields=["locked_until", "started_at", "status", "updated_at"])
    return task


def run_task(task: ProviderTask) -> None:
    structlog.contextvars.bind_contextvars(task_id=str(task.globalid), kind=task.kind)
    try:
        if task.kind == ProviderTask.Kind.CLASSIFY:
            _run_classify(task)
        else:
            _run_image(task)
    except ContentRefused as exc:
        _fail(task, code="content_refused", message=_REFUSED_MESSAGE, detail=str(exc))
    except (ProviderTemporaryError, requests.RequestException) as exc:
        _retry_or_fail(task, code="provider_unavailable", message=_FAILED_MESSAGE, detail=str(exc))
    except ProviderPermanentError as exc:
        _fail(task, code="provider_error", message=_FAILED_MESSAGE, detail=str(exc))
    except Exception as exc:
        log.exception("task_crashed")
        alert("generation_task_crashed", task_id=str(task.globalid), error=str(exc)[:200])
        _fail(task, code="internal_error", message=_FAILED_MESSAGE, detail=str(exc))
    finally:
        structlog.contextvars.unbind_contextvars("task_id", "kind")


def _is_cancelled(task: ProviderTask) -> bool:
    return (
        ProviderTask.objects.filter(pk=task.pk).values_list("status", flat=True).first()
        == ProviderTask.Status.CANCELLED
    )


def _record_cost(task: ProviderTask, cost: float | None) -> None:
    if cost is not None:
        task.cost_usd = Decimal(str(cost))


def _generate(
    task: ProviderTask, port: ImageGenerationPort, *, image: bytes, models: tuple[str, ...]
) -> GeneratedImage:
    """Tenta cada modelo em ordem. Qualquer falha passa para o próximo; sem próximo, relança."""
    size = settings.BUSINESS["IMAGE_SIZE"]
    for index, model in enumerate(models):
        task.model_name = model
        task.save(update_fields=["model_name", "updated_at"])
        try:
            return port.edit(image=image, prompt=task.rendered_prompt, size=size, model=model)
        except (
            ContentRefused,
            ProviderTemporaryError,
            ProviderPermanentError,
            requests.RequestException,
        ) as exc:
            if index == len(models) - 1:
                raise
            log.warning("image_model_failed", model=model, error=str(exc)[:200])


def _run_image(task: ProviderTask) -> None:
    port = get_image_generation_port()
    task.provider = port.provider
    task.attempts += 1
    task.save(update_fields=["provider", "attempts", "updated_at"])

    creation = task.creation
    if task.kind == ProviderTask.Kind.GENERATE:
        source_asset = creation.input.photo
        models = port.models
    else:
        # A edição fica no modelo que gerou a imagem de origem.
        source_asset = task.source_version.asset
        models = (task.source_version.task.model_name,)
    result = _generate(task, port, image=media.read(source_asset), models=models)

    _record_cost(task, result.cost_usd)
    if _is_cancelled(task):
        # O provedor já cobrou: guarda o custo e descarta o resultado (RN-08).
        ProviderTask.objects.filter(pk=task.pk).update(cost_usd=task.cost_usd)
        return

    asset = media.store(data=result.data, kind=Asset.Kind.IMAGE, mime="image/png")
    origin = {
        ProviderTask.Kind.GENERATE: ImageVersion.Origin.PHOTO,
        ProviderTask.Kind.EDIT: ImageVersion.Origin.EDIT,
    }[task.kind]

    # A imagem fica guardada; a criação só fica pronta depois que a versão é classificada.
    # Se a classificação falhar, só ela se repete, sem gerar a imagem de novo.
    with transaction.atomic():
        locked = Creation.objects.select_for_update().get(pk=creation.pk)
        number = locked.versions.count() + 1
        version = ImageVersion.objects.create(
            creation=locked,
            parent=task.source_version,
            number=number,
            origin=origin,
            instruction=task.instruction,
            asset=asset,
            task=task,
        )
        _succeed(task)
        services.enqueue_version_classification(version)


def _run_classify(task: ProviderTask) -> None:
    """Classifica a foto (antes de gerar) ou uma versão gerada (RN-33, RN-34)."""
    port = get_image_classification_port()
    task.provider = port.provider
    task.attempts += 1
    task.save(update_fields=["provider", "attempts", "updated_at"])

    creation = task.creation
    version = task.source_version
    image = media.read(version.asset if version else creation.input.photo)
    result = port.classify(image=image, target="version" if version else "photo")
    _record_cost(task, result.cost_usd)
    task.model_name = result.model
    accepted = result.result in Category.values
    # Quem pediu (RN-36): a leitura da foto tem reserva própria; a da versão herda a da tarefa
    # que gerou a imagem.
    owner_task = version.task if version is not None and version.task else task
    reservation = getattr(owner_task, "quota_reservation", None)
    ip_hash = reservation.ip_hash if reservation else ""

    with transaction.atomic():
        Classification.objects.create(
            creation=creation,
            version=version,
            task=task,
            requested_category=creation.requested_category,
            result=result.result,
            decision=(
                Classification.Decision.ACCEPTED if accepted else Classification.Decision.REJECTED
            ),
            confidence=result.confidence,
            probabilities=result.probabilities,
            character_probability=result.character_probability,
            model_name=result.model[:64],
            question_set_version=result.question_set_version[:16],
            ip_hash=ip_hash,
        )
        _succeed(task)
        locked = Creation.objects.select_for_update().get(pk=creation.pk)
        if version is None:
            _apply_photo_result(locked, result.result, accepted=accepted, ip_hash=ip_hash)
        else:
            _apply_version_result(locked, version, result.result, accepted=accepted)


def _apply_photo_result(creation: Creation, result: str, *, accepted: bool, ip_hash: str) -> None:
    if not accepted:
        creation.rejection_reason = result
        creation.save(update_fields=["rejection_reason", "updated_at"])
        apply_transition(
            instance=creation, fsm=CREATION_FSM, event="photo_rejected", payload={"reason": result}
        )
        return
    creation.category = result
    creation.save(update_fields=["category", "updated_at"])
    try:
        # Savepoint: se a cota acabou entre o envio e a leitura da foto, nada da geração fica.
        with transaction.atomic():
            services.enqueue_image(
                actor=services.actor_of(creation), ip_hash=ip_hash, creation=creation
            )
    except (QuotaExceeded, ServiceBusy) as exc:
        creation.last_error_code = exc.code[:32]
        creation.last_error_message = exc.detail[:255]
        creation.save(update_fields=["last_error_code", "last_error_message", "updated_at"])
        apply_transition(
            instance=creation, fsm=CREATION_FSM, event="image_failed", payload={"code": exc.code}
        )
        return
    apply_transition(
        instance=creation, fsm=CREATION_FSM, event="photo_accepted", payload={"category": result}
    )


def _apply_version_result(
    creation: Creation, version: ImageVersion, result: str, *, accepted: bool
) -> None:
    if accepted:
        version.category = result
    else:
        version.rejection_reason = result
    version.save(update_fields=["category", "rejection_reason", "updated_at"])
    # A primeira imagem abre a compra; as edições só ganham categoria e preço.
    if version.origin == ImageVersion.Origin.PHOTO and creation.current_version_id is None:
        creation.current_version = version
        creation.save(update_fields=["current_version", "updated_at"])
        apply_transition(instance=creation, fsm=CREATION_FSM, event="image_ready")


def _succeed(task: ProviderTask) -> None:
    task.status = ProviderTask.Status.SUCCEEDED
    task.finished_at = timezone.now()
    task.locked_until = None
    task.save(
        update_fields=[
            "status",
            "finished_at",
            "locked_until",
            "cost_usd",
            "provider",
            "model_name",
            "attempts",
            "updated_at",
        ]
    )
    quota.consume(task)


def _retry_or_fail(task: ProviderTask, *, code: str, message: str, detail: str = "") -> None:
    if task.attempts >= settings.BUSINESS["TASK_MAX_ATTEMPTS"]:
        _fail(task, code=code, message=message, detail=detail)
        return
    if _is_cancelled(task):
        return
    delay = 2**task.attempts
    task.status = ProviderTask.Status.QUEUED
    task.next_attempt_at = timezone.now() + timedelta(seconds=delay)
    task.locked_until = None
    task.error_code = code
    task.error_message = detail[:500]
    task.save(
        update_fields=[
            "status",
            "next_attempt_at",
            "locked_until",
            "error_code",
            "error_message",
            "updated_at",
        ]
    )
    log.info("task_retry_scheduled", code=code, delay=delay)


def _fail(task: ProviderTask, *, code: str, message: str, detail: str = "") -> None:
    if _is_cancelled(task):
        return
    task.status = ProviderTask.Status.FAILED
    task.finished_at = timezone.now()
    task.locked_until = None
    task.error_code = code
    task.error_message = (detail or message)[:500]
    with transaction.atomic():
        task.save(
            update_fields=[
                "status",
                "finished_at",
                "locked_until",
                "error_code",
                "error_message",
                "attempts",
                "provider",
                "model_name",
                "updated_at",
            ]
        )
        quota.release(task)
        # Edições e suas versões não mudam o status da criação: a versão fica sem categoria.
        if task.kind == ProviderTask.Kind.EDIT:
            return
        source = task.source_version
        if source is not None and source.origin == ImageVersion.Origin.EDIT:
            return
        reading_photo = task.kind == ProviderTask.Kind.CLASSIFY and source is None
        if reading_photo:
            code = "classification_failed" if code != "timeout" else code
            message = _CLASSIFY_FAILED_MESSAGE
        creation = Creation.objects.select_for_update().get(pk=task.creation_id)
        creation.last_error_code = code
        creation.last_error_message = message
        creation.save(update_fields=["last_error_code", "last_error_message", "updated_at"])
        apply_transition(
            instance=creation,
            fsm=CREATION_FSM,
            event="classification_failed" if reading_photo else "image_failed",
            payload={"code": code},
        )


def run_once() -> bool:
    task = claim_task()
    if task is None:
        return False
    run_task(task)
    return True


def reconcile_stuck_tasks() -> int:
    """Tarefas sem progresso muito além do limite: encerra e devolve a cota."""
    limit = settings.BUSINESS["TASK_TIMEOUT_SECONDS"] * 2
    cutoff = timezone.now() - timedelta(seconds=limit)
    stuck = ProviderTask.objects.filter(
        status=ProviderTask.Status.RUNNING,
        started_at__lt=cutoff,
    ).filter(Q(locked_until__isnull=True) | Q(locked_until__lte=timezone.now()))
    count = 0
    for task in stuck:
        _fail(task, code="timeout", message=_TIMEOUT_MESSAGE)
        count += 1
    if count:
        alert("generation_tasks_stuck", count=count)
    return count


def close_connections() -> None:
    close_old_connections()
