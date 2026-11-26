"""Produção: atribuição, ações do parceiro, etiqueta, ganhos e cancelamento.

Toda ação vale para o pedido inteiro (RN-PAR-01) e passa pela máquina de estados do job, com
evento. O status do pedido para o cliente é derivado dos jobs (RN-PAR-03).

`orders.services` é importado dentro das funções: ele importa `shipping`, que importa este
módulo para a origem do frete.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, Max, OuterRef, QuerySet, Subquery, Sum
from django.utils import timezone

from audit.services import record_event
from common.alerts import alert
from common.dates import add_business_days
from common.exceptions import Conflict, GuardFailed, ResourceNotFound
from common.fsm import apply_transition
from fulfillment.fsm import JOB_FSM
from fulfillment.models import (
    Partner,
    PartnerEntry,
    PartnerMember,
    PartnerOrderGroup,
    PartnerPayout,
    PartnerRate,
    ProductionFile,
    ProductionIssue,
    ProductionJob,
    ProductionPhoto,
    Shipment,
)
from media import services as media
from media.models import Asset, AssetDownload
from notifications.services import send_email

JobStatus = ProductionJob.Status
_GROUP_STATUS = {
    PartnerOrderGroup.TO_PRINT: JobStatus.ASSIGNED,
    PartnerOrderGroup.IN_PRODUCTION: JobStatus.IN_PRODUCTION,
    PartnerOrderGroup.AWAITING_LABEL: JobStatus.READY_TO_SHIP,
    PartnerOrderGroup.TO_POST: JobStatus.READY_TO_SHIP,
    PartnerOrderGroup.POSTED: JobStatus.SHIPPED,
    PartnerOrderGroup.CANCELLED: JobStatus.CANCELLED,
}
ISSUE_MAX_CHARS = 2000
REFUSE_MAX_CHARS = 500


def origin_postal_code() -> str:
    partner = Partner.objects.filter(is_internal=True).first()
    return partner.origin_postal_code if partner else settings.INTERNAL_PARTNER_POSTAL_CODE


# --- Acesso ---


def partner_for(user) -> Partner | None:
    """Parceiro ativo do usuário. Conferido a cada requisição (RF-PAR-04)."""
    if user is None or not getattr(user, "is_authenticated", False) or not user.is_active:
        return None
    member = (
        PartnerMember.objects.select_related("partner")
        .filter(user=user, partner__status=Partner.Status.ACTIVE)
        .first()
    )
    return member.partner if member else None


def _member_emails(partner: Partner) -> list[str]:
    return list(
        partner.members.filter(user__is_active=True, user__anonymized_at__isnull=True).values_list(
            "user__email", flat=True
        )
    )


def _notify_partner(partner: Partner, *, subject: str, template: str, context: dict) -> None:
    """Envia depois do commit, para nunca avisar de algo que foi desfeito."""

    def send():
        for email in _member_emails(partner):
            send_email(to=email, subject=subject, template=template, context=context)

    transaction.on_commit(send)


def _order_url(order) -> str:
    return f"{settings.PARTNERS_APP_URL}/impressoes/{order.globalid}"


# --- Jobs ---


def create_jobs_for_order(order) -> None:
    """Uma tarefa por item, sem parceiro. Idempotente: pagamento tardio não duplica."""
    paid_on = timezone.localdate(order.paid_at) if order.paid_at else timezone.localdate()
    post_by = add_business_days(paid_on, settings.BUSINESS["PRODUCTION_DAYS"])
    for item in order.items.all():
        ProductionJob.objects.get_or_create(order_item=item, defaults={"post_by": post_by})


def _active_jobs(order, *, partner: Partner | None = None) -> list[ProductionJob]:
    jobs = ProductionJob.objects.filter(order_item__order=order).exclude(status=JobStatus.CANCELLED)
    if partner is not None:
        jobs = jobs.filter(partner=partner)
    return list(jobs.select_related("order_item").order_by("order_item__created_at"))


def _transition_jobs(jobs, *, event: str, actor=None, payload=None, effects=None) -> None:
    for job in jobs:
        apply_transition(
            instance=job,
            fsm=JOB_FSM,
            event=event,
            actor=actor,
            payload=payload,
            effects=(lambda job=job: effects(job)) if effects else None,
        )


def _require_jobs(order, *, partner: Partner, status: str) -> list[ProductionJob]:
    jobs = _active_jobs(order, partner=partner)
    if not jobs:
        raise ResourceNotFound("Pedido não encontrado.")
    if any(job.status != status for job in jobs):
        raise Conflict("Este pedido não está nesta etapa.", code="illegal_transition")
    return jobs


def latest_file(job: ProductionJob) -> ProductionFile | None:
    return job.files.order_by("-version").first()


def add_production_file(*, job: ProductionJob, data: bytes, actor=None) -> ProductionFile:
    """Sobe o 3MF do item. A nova versão substitui a anterior para o parceiro."""
    if not data:
        raise GuardFailed("Envie o arquivo 3MF.", code="production_file_invalid")
    if len(data) > settings.BUSINESS["PRODUCTION_FILE_MAX_BYTES"]:
        raise GuardFailed("O arquivo é grande demais.", code="production_file_too_large")
    # 3MF é um ZIP: começa com a assinatura "PK".
    if not data.startswith(b"PK"):
        raise GuardFailed("O arquivo não é um 3MF válido.", code="production_file_invalid")
    with transaction.atomic():
        current = job.files.aggregate(v=Max("version"))["v"] or 0
        asset = media.store(data=data, kind=Asset.Kind.PRODUCTION, mime="model/3mf")
        file = ProductionFile.objects.create(job=job, version=current + 1, asset=asset)
        record_event(
            instance=job.order_item.order,
            event="production_file_added",
            actor=actor,
            payload={"item_id": str(job.order_item.globalid), "version": file.version},
        )
    return file


def assign_order(*, order, partner: Partner, actor=None) -> None:
    """A equipe atribui o pedido inteiro. O ganho de cada item é congelado aqui (RN-PAR-06)."""
    if partner.status != Partner.Status.ACTIVE:
        raise GuardFailed("Este parceiro está inativo.", code="partner_inactive")
    with transaction.atomic():
        jobs = _active_jobs(order)
        if not jobs:
            raise GuardFailed("Este pedido não tem itens a produzir.", code="no_jobs")
        payouts = {}
        for job in jobs:
            item = job.order_item
            rate = PartnerRate.objects.filter(category=item.category, size_id=item.size_id).first()
            if rate is None:
                raise GuardFailed(
                    f"Falta o valor do parceiro para {item.category} em {item.size_label}.",
                    code="partner_rate_missing",
                )
            payouts[job.pk] = rate.amount_cents * item.quantity
        now = timezone.now()

        def set_partner(job):
            ProductionJob.objects.filter(pk=job.pk).update(
                partner=partner, assigned_at=now, payout_cents=payouts[job.pk]
            )

        _transition_jobs(
            jobs,
            event="assign",
            actor=actor,
            payload={"partner_id": str(partner.globalid)},
            effects=set_partner,
        )
    _notify_partner(
        partner,
        subject=f"Nova impressão para você: pedido {order.number}",
        template="partner_order_assigned",
        context={
            "number": order.number,
            "pieces": sum(job.order_item.quantity for job in jobs),
            "post_by": jobs[0].post_by,
            "order_url": _order_url(order),
        },
    )


def attach_label(*, order, pdf: bytes, carrier: str, tracking_code: str, actor=None) -> Shipment:
    """A equipe anexa a etiqueta comprada fora do sistema. Pode substituir antes da postagem."""
    if not pdf.startswith(b"%PDF"):
        raise GuardFailed("Envie a etiqueta em PDF.", code="label_invalid")
    if len(pdf) > settings.BUSINESS["PARTNER_LABEL_MAX_BYTES"]:
        raise GuardFailed("A etiqueta é grande demais.", code="label_too_large")
    carrier, tracking_code = carrier.strip(), tracking_code.strip()
    if not carrier or not tracking_code:
        raise GuardFailed("Informe a transportadora e o rastreio.", code="label_invalid")
    with transaction.atomic():
        jobs = _active_jobs(order)
        if not jobs or any(job.status != JobStatus.READY_TO_SHIP for job in jobs):
            raise Conflict("O pedido ainda não está pronto para envio.", code="illegal_transition")
        partner = jobs[0].partner
        asset = media.store(data=pdf, kind=Asset.Kind.PRODUCTION, mime="application/pdf")
        shipment = order.shipments.filter(shipped_at__isnull=True).first()
        replaced = shipment is not None
        if shipment is None:
            shipment = Shipment(order=order)
        shipment.partner = partner
        shipment.carrier = carrier
        shipment.tracking_code = tracking_code
        shipment.label = asset
        shipment.save()
        record_event(
            instance=order,
            event="label_replaced" if replaced else "label_attached",
            actor=actor,
            payload={"carrier": carrier},
        )
    _notify_partner(
        partner,
        subject=f"Etiqueta pronta: pedido {order.number}",
        template="partner_label_ready",
        context={"number": order.number, "order_url": _order_url(order)},
    )
    return shipment


def open_shipment(order) -> Shipment | None:
    return order.shipments.filter(shipped_at__isnull=True, label__isnull=False).first()


# --- Ações do parceiro ---


def refuse_order(*, order, partner: Partner, user, reason: str) -> None:
    reason = reason.strip()
    if not reason:
        raise GuardFailed("Conte o motivo da recusa.", code="reason_required")
    with transaction.atomic():
        jobs = _require_jobs(order, partner=partner, status=JobStatus.ASSIGNED)

        def clear_partner(job):
            ProductionJob.objects.filter(pk=job.pk).update(
                partner=None, assigned_at=None, payout_cents=None
            )

        _transition_jobs(
            jobs,
            event="refuse",
            actor=user,
            payload={"partner_id": str(partner.globalid), "reason": reason[:REFUSE_MAX_CHARS]},
            effects=clear_partner,
        )
    alert("partner_refused_order", order_id=str(order.globalid))


def start_order(*, order, partner: Partner, user) -> None:
    from orders.models import Order
    from orders.services import transition_order

    with transaction.atomic():
        jobs = _require_jobs(order, partner=partner, status=JobStatus.ASSIGNED)
        if any(latest_file(job) is None for job in jobs):
            raise GuardFailed(
                "O arquivo de impressão ainda não chegou. Aguarde a EuMini.",
                code="production_file_missing",
            )
        _transition_jobs(jobs, event="start", actor=user)
        order.refresh_from_db()
        if order.status == Order.Status.PAID:
            transition_order(order=order, event="start_production", actor=user)


def _store_partner_photo(raw: bytes) -> Asset:
    prepared = media.prepare_photo(raw)
    return media.store(
        data=prepared.original, kind=Asset.Kind.PARTNER_PHOTO, mime=prepared.original_mime
    )


def mark_ready(*, order, partner: Partner, user, photos: list[bytes]) -> None:
    limit = settings.BUSINESS["PARTNER_READY_PHOTOS_MAX"]
    if not photos:
        raise GuardFailed("Envie pelo menos uma foto das peças prontas.", code="photo_required")
    if len(photos) > limit:
        raise GuardFailed(f"Envie no máximo {limit} fotos.", code="too_many_photos")
    # Confere a etapa antes de gravar as fotos, para não guardar arquivo à toa.
    _require_jobs(order, partner=partner, status=JobStatus.IN_PRODUCTION)
    assets = [_store_partner_photo(raw) for raw in photos]
    with transaction.atomic():
        jobs = _require_jobs(order, partner=partner, status=JobStatus.IN_PRODUCTION)
        for asset in assets:
            ProductionPhoto.objects.create(order=order, partner=partner, asset=asset)
        _transition_jobs(jobs, event="mark_ready", actor=user)
    alert("partner_order_ready", order_id=str(order.globalid))


def post_order(*, order, partner: Partner, user) -> None:
    """O parceiro postou. O pedido vira Enviado e os ganhos entram no extrato."""
    from orders.services import transition_order

    with transaction.atomic():
        jobs = _require_jobs(order, partner=partner, status=JobStatus.READY_TO_SHIP)
        shipment = open_shipment(order)
        if shipment is None:
            raise GuardFailed("A etiqueta ainda não chegou.", code="label_missing")
        shipment.shipped_at = timezone.now()
        shipment.save(update_fields=["shipped_at", "updated_at"])

        def add_earning(job):
            PartnerEntry.objects.create(
                partner=partner,
                kind=PartnerEntry.Kind.EARNING,
                job=job,
                amount_cents=job.payout_cents or 0,
            )

        _transition_jobs(jobs, event="post", actor=user, effects=add_earning)
        order.refresh_from_db()
        transition_order(order=order, event="ship", actor=user)


def report_issue(*, order, partner: Partner, user, text: str, photo: bytes | None):
    text = text.strip()
    if not text:
        raise GuardFailed("Conte o que aconteceu.", code="text_required")
    if len(text) > ISSUE_MAX_CHARS:
        raise GuardFailed(f"Use até {ISSUE_MAX_CHARS} caracteres.", code="text_too_long")
    jobs = _active_jobs(order, partner=partner)
    if not jobs or all(job.status == JobStatus.SHIPPED for job in jobs):
        raise ResourceNotFound("Pedido não encontrado.")
    asset = _store_partner_photo(photo) if photo else None
    with transaction.atomic():
        issue = ProductionIssue.objects.create(order=order, partner=partner, text=text, photo=asset)
        record_event(instance=order, event="issue_reported", actor=user)
    alert("partner_issue_reported", order_id=str(order.globalid))
    return issue


def cancel_jobs_for_order(order) -> None:
    """Reembolso: cancela o que não foi postado e avisa o parceiro (RN-PAR-05)."""
    jobs = [job for job in _active_jobs(order) if job.status != JobStatus.SHIPPED]
    partners = {job.partner for job in jobs if job.partner is not None}
    _transition_jobs(jobs, event="cancel")
    for partner in partners:
        _notify_partner(
            partner,
            subject=f"Pedido {order.number} cancelado: não imprima nem poste",
            template="partner_order_cancelled",
            context={"number": order.number, "order_url": _order_url(order)},
        )


# --- Leitura pelo parceiro ---


def _has_open_label():
    return Exists(
        Shipment.objects.filter(order=OuterRef("pk"), shipped_at__isnull=True, label__isnull=False)
    )


def partner_orders(partner: Partner, group: str | None = None) -> QuerySet:
    from orders.models import Order

    jobs = ProductionJob.objects.filter(order_item__order=OuterRef("pk"), partner=partner)
    orders = Order.objects.filter(Exists(jobs))
    if group:
        status = _GROUP_STATUS[group]
        orders = orders.filter(Exists(jobs.filter(status=status)))
        if group == PartnerOrderGroup.AWAITING_LABEL:
            orders = orders.filter(~_has_open_label())
        elif group == PartnerOrderGroup.TO_POST:
            orders = orders.filter(_has_open_label())
    return orders


def with_post_by(orders: QuerySet) -> QuerySet:
    """Anota o prazo de postagem, igual em todos os itens do pedido."""
    jobs = ProductionJob.objects.filter(order_item__order=OuterRef("pk")).values("post_by")
    return orders.annotate(post_by_date=Subquery(jobs[:1]))


def get_partner_order(*, partner: Partner, order_id):
    order = partner_orders(partner).filter(globalid=order_id).first()
    if order is None:
        raise ResourceNotFound("Pedido não encontrado.")
    return order


def partner_jobs(order, partner: Partner) -> list[ProductionJob]:
    return list(
        ProductionJob.objects.filter(order_item__order=order, partner=partner)
        .select_related("order_item__version__asset")
        .order_by("order_item__created_at")
    )


def group_of(jobs: list[ProductionJob], *, has_label: bool) -> str:
    if not jobs or any(job.status == JobStatus.CANCELLED for job in jobs):
        return PartnerOrderGroup.CANCELLED
    status = jobs[0].status
    if status == JobStatus.READY_TO_SHIP:
        return PartnerOrderGroup.TO_POST if has_label else PartnerOrderGroup.AWAITING_LABEL
    for group, group_status in _GROUP_STATUS.items():
        if group_status == status:
            return group
    return PartnerOrderGroup.CANCELLED


def group_counts(partner: Partner) -> dict[str, int]:
    counts = {group: partner_orders(partner, group).count() for group in PartnerOrderGroup.values}
    active = (JobStatus.ASSIGNED, JobStatus.IN_PRODUCTION, JobStatus.READY_TO_SHIP)
    counts["overdue"] = (
        partner_orders(partner)
        .filter(
            Exists(
                ProductionJob.objects.filter(
                    order_item__order=OuterRef("pk"),
                    partner=partner,
                    status__in=active,
                    post_by__lt=timezone.localdate(),
                )
            )
        )
        .count()
    )
    return counts


@dataclass(frozen=True)
class Download:
    url: str
    filename: str


def _download(*, asset: Asset | None, user, context: str, filename: str) -> Download:
    if asset is None or asset.purged_at is not None:
        raise ResourceNotFound("Arquivo indisponível.")
    AssetDownload.objects.create(asset=asset, user=user, context=context)
    return Download(url=media.signed_url(asset, filename=filename), filename=filename)


def download_item_file(*, order, partner: Partner, user, item_id, file: str) -> Download:
    jobs = [job for job in partner_jobs(order, partner) if job.status != JobStatus.CANCELLED]
    for index, job in enumerate(jobs, start=1):
        if str(job.order_item.globalid) != str(item_id):
            continue
        if file == "3mf":
            production = latest_file(job)
            asset = production.asset if production else None
            filename = f"{order.number}-item{index}-v{production.version if production else 0}.3mf"
        else:
            asset = job.order_item.version.asset
            filename = f"{order.number}-item{index}.{media.extension_of(asset)}"
        return _download(
            asset=asset, user=user, context=f"partner_order:{order.globalid}", filename=filename
        )
    raise ResourceNotFound("Item não encontrado.")


def download_label(*, order, partner: Partner, user) -> Download:
    if not partner_jobs(order, partner):
        raise ResourceNotFound("Pedido não encontrado.")
    shipment = (
        order.shipments.filter(partner=partner, label__isnull=False).order_by("-created_at").first()
    )
    return _download(
        asset=shipment.label if shipment else None,
        user=user,
        context=f"partner_order:{order.globalid}",
        filename=f"{order.number}-etiqueta.pdf",
    )


# --- Ganhos ---


@dataclass(frozen=True)
class Balance:
    to_receive_cents: int
    paid_cents: int


def partner_balance(partner: Partner) -> Balance:
    to_receive = partner.entries.filter(payout__isnull=True).aggregate(s=Sum("amount_cents"))["s"]
    paid = partner.payouts.aggregate(s=Sum("amount_cents"))["s"]
    return Balance(to_receive_cents=to_receive or 0, paid_cents=paid or 0)


def partner_entries(partner: Partner) -> QuerySet:
    return partner.entries.select_related("job__order_item__order", "payout")


def partner_payouts(partner: Partner) -> QuerySet:
    return PartnerPayout.objects.filter(partner=partner).order_by("-paid_on", "-created_at")


def is_overdue(post_by, *, today=None) -> bool:
    return post_by is not None and post_by < (today or timezone.localdate())


def due_soon(post_by, *, today=None) -> bool:
    if post_by is None:
        return False
    today = today or timezone.localdate()
    return 0 <= (post_by - today).days <= settings.BUSINESS["PARTNER_DUE_SOON_DAYS"]


def issues_for(order, partner: Partner) -> QuerySet:
    return ProductionIssue.objects.filter(order=order, partner=partner)


def photos_for(order, partner: Partner) -> QuerySet:
    return ProductionPhoto.objects.filter(order=order, partner=partner).select_related("asset")
