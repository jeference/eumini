"""Operações da equipe sobre a produção: retirar e reatribuir pedidos, entrega, problemas,
parceiros, tarifas, repasses e ajustes.

Chamadas pelo app Staff. Toda ação grava `DomainEvent` com quem fez. Atribuir, subir o 3MF e
anexar a etiqueta ficam em `fulfillment.services`, junto do fluxo do parceiro.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from audit.services import record_event
from common.exceptions import Conflict, GuardFailed, ResourceNotFound
from fulfillment import services
from fulfillment.invites import invite_partner_member
from fulfillment.models import (
    Partner,
    PartnerEntry,
    PartnerMember,
    PartnerPayout,
    PartnerRate,
    ProductionIssue,
    ProductionJob,
)
from media import services as media
from media.models import Asset

JobStatus = ProductionJob.Status
ACTIVE_STATUSES = (JobStatus.ASSIGNED, JobStatus.IN_PRODUCTION, JobStatus.READY_TO_SHIP)
REASON_MAX_CHARS = 500
NOTE_MAX_CHARS = 1000


def _brl(cents: int) -> str:
    from orders.services import brl

    return brl(cents)


def _required(text: str, *, code: str, message: str, limit: int) -> str:
    text = (text or "").strip()
    if not text:
        raise GuardFailed(message, code=code)
    if len(text) > limit:
        raise GuardFailed(f"Use até {limit} caracteres.", code="text_too_long")
    return text


# --- Pedidos ---


def unassign_order(*, order, actor, reason: str) -> Partner:
    """Retira o pedido do parceiro antes da postagem. A etiqueta em aberto é descartada,
    porque saiu do CEP dele. O status do pedido para o cliente não muda."""
    reason = _required(
        reason, code="reason_required", message="Conte o motivo.", limit=REASON_MAX_CHARS
    )
    with transaction.atomic():
        jobs = services._active_jobs(order)
        if not jobs or any(job.status not in ACTIVE_STATUSES for job in jobs):
            raise Conflict("Este pedido não está com um parceiro.", code="illegal_transition")
        partner = jobs[0].partner

        def clear_partner(job):
            ProductionJob.objects.filter(pk=job.pk).update(
                partner=None, assigned_at=None, payout_cents=None
            )

        services._transition_jobs(
            jobs,
            event="unassign",
            actor=actor,
            payload={"partner_id": str(partner.globalid), "reason": reason},
            effects=clear_partner,
        )
        order.shipments.filter(shipped_at__isnull=True).delete()
    services._notify_partner(
        partner,
        subject=f"O pedido {order.number} saiu da sua fila",
        template="partner_order_removed",
        context={"number": order.number},
    )
    return partner


def reassign_order(*, order, partner: Partner, actor, reason: str = "") -> None:
    """Atribui o pedido, tirando antes do parceiro atual, se houver."""
    with transaction.atomic():
        jobs = services._active_jobs(order)
        if jobs and jobs[0].status != JobStatus.UNASSIGNED:
            if jobs[0].partner_id == partner.pk:
                raise GuardFailed("O pedido já está com este parceiro.", code="same_partner")
            unassign_order(order=order, actor=actor, reason=reason or "Reatribuído pela equipe.")
        services.assign_order(order=order, partner=partner, actor=actor)


def mark_delivered(*, order, actor) -> None:
    from orders.models import Order
    from orders.services import transition_order

    with transaction.atomic():
        order.refresh_from_db()
        if order.status != Order.Status.SHIPPED:
            raise Conflict("O pedido ainda não foi enviado.", code="illegal_transition")
        shipment = order.shipments.filter(shipped_at__isnull=False).order_by("-created_at").first()
        if shipment is not None:
            shipment.delivered_at = timezone.now()
            shipment.save(update_fields=["delivered_at", "updated_at"])
        transition_order(order=order, event="deliver", actor=actor)


def resolve_issue(*, issue: ProductionIssue, actor, note: str) -> ProductionIssue:
    if issue.resolved_at is not None:
        raise Conflict("Este problema já foi resolvido.", code="already_resolved")
    note = _required(
        note, code="note_required", message="Conte como foi resolvido.", limit=NOTE_MAX_CHARS
    )
    issue.resolved_at = timezone.now()
    issue.resolution_note = note
    issue.save(update_fields=["resolved_at", "resolution_note", "updated_at"])
    record_event(instance=issue.order, event="issue_resolved", actor=actor)
    return issue


def download_item_file(*, order, item_id, file: str, user) -> services.Download:
    """Imagem comprada, foto original do cliente ou o 3MF atual de um item, com registro."""
    jobs = list(
        ProductionJob.objects.filter(order_item__order=order)
        .select_related("order_item__version__asset", "order_item__creation__input")
        .order_by("order_item__created_at")
    )
    for index, job in enumerate(jobs, start=1):
        item = job.order_item
        if str(item.globalid) != str(item_id):
            continue
        if file == "3mf":
            production = services.latest_file(job)
            asset = production.asset if production else None
            version = production.version if production else 0
            filename = f"{order.number}-item{index}-v{version}.3mf"
        elif file == "photo":
            source = item.creation.input
            asset = source.original_photo or source.photo
            filename = f"{order.number}-item{index}-foto.{media.extension_of(asset)}"
        else:
            asset = item.version.asset
            filename = f"{order.number}-item{index}.{media.extension_of(asset)}"
        return services._download(
            asset=asset, user=user, context=f"staff_order:{order.globalid}", filename=filename
        )
    raise ResourceNotFound("Item não encontrado.")


def download_label(*, order, user) -> services.Download:
    shipment = order.shipments.filter(label__isnull=False).order_by("-created_at").first()
    return services._download(
        asset=shipment.label if shipment else None,
        user=user,
        context=f"staff_order:{order.globalid}",
        filename=f"{order.number}-etiqueta.pdf",
    )


# --- Parceiros ---


def _clean_partner_fields(*, name: str, origin_postal_code: str, pix_key: str) -> dict:
    from shipping.services import normalize_postal_code

    name = _required(name, code="name_required", message="Informe o nome.", limit=120)
    return {
        "name": name,
        "origin_postal_code": normalize_postal_code(origin_postal_code),
        "pix_key": (pix_key or "").strip()[:140],
    }


def create_partner(*, name: str, email: str, origin_postal_code: str, pix_key: str = "", actor):
    fields = _clean_partner_fields(
        name=name, origin_postal_code=origin_postal_code, pix_key=pix_key
    )
    email = email.strip().lower()
    if PartnerMember.objects.filter(user__email=email).exists():
        raise GuardFailed("Este e-mail já é de outro parceiro.", code="email_in_use")
    with transaction.atomic():
        partner = Partner.objects.create(**fields)
        invite_partner_member(partner=partner, email=email)
        record_event(instance=partner, event="partner_created", actor=actor)
    return partner


def update_partner(*, partner: Partner, actor, **values) -> Partner:
    fields = _clean_partner_fields(
        name=values.get("name", partner.name),
        origin_postal_code=values.get("origin_postal_code", partner.origin_postal_code),
        pix_key=values.get("pix_key", partner.pix_key),
    )
    for key, value in fields.items():
        setattr(partner, key, value)
    partner.save(update_fields=[*fields, "updated_at"])
    record_event(instance=partner, event="partner_updated", actor=actor)
    return partner


def partner_login_email(partner: Partner) -> str:
    member = partner.members.select_related("user").order_by("created_at").first()
    return member.user.email if member else ""


def resend_invite(*, partner: Partner, actor) -> None:
    email = partner_login_email(partner)
    if not email:
        raise GuardFailed("Este parceiro não tem login.", code="no_member")
    invite_partner_member(partner=partner, email=email)
    record_event(instance=partner, event="partner_invited", actor=actor)


def has_active_orders(partner: Partner) -> bool:
    return partner.jobs.filter(status__in=ACTIVE_STATUSES).exists()


def set_partner_status(*, partner: Partner, active: bool, actor) -> Partner:
    status = Partner.Status.ACTIVE if active else Partner.Status.INACTIVE
    if not active and has_active_orders(partner):
        raise GuardFailed(
            "Retire ou finalize os pedidos ativos deste parceiro antes de desativar.",
            code="partner_has_active_orders",
        )
    partner.status = status
    partner.save(update_fields=["status", "updated_at"])
    record_event(
        instance=partner,
        event="partner_reactivated" if active else "partner_deactivated",
        actor=actor,
    )
    return partner


# --- Tarifas ---


@dataclass(frozen=True)
class RateRow:
    category: str
    size_id: int
    size_globalid: str
    size_label: str
    sort_order: int
    price_cents: int
    amount_cents: int | None


def rate_table() -> list[RateRow]:
    """Uma linha por combinação vendida, com o valor do parceiro ou vazio."""
    from catalog.models import ProductPrice

    rates = {(rate.category, rate.size_id): rate.amount_cents for rate in PartnerRate.objects.all()}
    rows = []
    for price in ProductPrice.objects.filter(is_active=True).select_related("size"):
        rows.append(
            RateRow(
                category=price.category,
                size_id=price.size_id,
                size_globalid=str(price.size.globalid),
                size_label=price.size.label,
                sort_order=price.size.sort_order,
                price_cents=price.price_cents,
                amount_cents=rates.get((price.category, price.size_id)),
            )
        )
    return sorted(rows, key=lambda row: (row.category, row.sort_order))


def set_rates(*, rows: list[dict], actor) -> list[RateRow]:
    """Grava a tabela inteira. Valor vazio remove a tarifa. Vale só para novas atribuições."""
    table = {(row.category, row.size_globalid): row for row in rate_table()}
    with transaction.atomic():
        for row in rows:
            key = (row["category"], str(row["size_id"]))
            current = table.get(key)
            if current is None:
                raise GuardFailed("Combinação que não é vendida.", code="rate_not_sold")
            amount = row.get("amount_cents")
            if amount is None:
                PartnerRate.objects.filter(
                    category=current.category, size_id=current.size_id
                ).delete()
                continue
            if amount <= 0:
                raise GuardFailed("O valor precisa ser maior que zero.", code="rate_invalid")
            rate, _ = PartnerRate.objects.update_or_create(
                category=current.category,
                size_id=current.size_id,
                defaults={"amount_cents": amount},
            )
            record_event(
                instance=rate, event="rate_set", actor=actor, payload={"amount_cents": amount}
            )
    return rate_table()


# --- Repasses e ajustes ---


def _store_receipt(raw: bytes) -> Asset:
    if raw.startswith(b"%PDF"):
        if len(raw) > settings.BUSINESS["PARTNER_LABEL_MAX_BYTES"]:
            raise GuardFailed("O comprovante é grande demais.", code="receipt_too_large")
        return media.store(data=raw, kind=Asset.Kind.RECEIPT, mime="application/pdf")
    prepared = media.prepare_photo(raw)
    return media.store(data=prepared.original, kind=Asset.Kind.RECEIPT, mime=prepared.original_mime)


def record_payout(
    *,
    partner: Partner,
    entry_ids: list,
    paid_on,
    amount_cents: int,
    receipt: bytes | None,
    note: str,
    actor,
) -> PartnerPayout:
    """Registra o PIX feito fora do sistema e quita os lançamentos escolhidos (RN-PAR-07)."""
    if amount_cents <= 0:
        raise GuardFailed("O repasse precisa ter valor.", code="payout_invalid")
    asset = _store_receipt(receipt) if receipt else None
    ids = {str(entry_id) for entry_id in entry_ids}
    with transaction.atomic():
        entries = list(
            PartnerEntry.objects.select_for_update().filter(
                partner=partner, globalid__in=ids, payout__isnull=True
            )
        )
        if not ids or len(entries) != len(ids):
            raise GuardFailed(
                "Escolha lançamentos em aberto deste parceiro.", code="payout_entries_invalid"
            )
        total = sum(entry.amount_cents for entry in entries)
        if total != amount_cents:
            raise GuardFailed(
                f"A soma dos lançamentos é {_brl(total)}, diferente do repasse.",
                code="payout_mismatch",
            )
        payout = PartnerPayout.objects.create(
            partner=partner,
            paid_on=paid_on,
            amount_cents=amount_cents,
            receipt=asset,
            note=(note or "").strip()[:NOTE_MAX_CHARS],
        )
        PartnerEntry.objects.filter(pk__in=[entry.pk for entry in entries]).update(payout=payout)
        record_event(
            instance=payout,
            event="payout_recorded",
            actor=actor,
            payload={"amount_cents": amount_cents, "entries": len(entries)},
        )
    services._notify_partner(
        partner,
        subject=f"Repasse de {_brl(amount_cents)} feito pela EuMini",
        template="partner_payout_paid",
        context={
            "amount": _brl(amount_cents),
            "paid_on": paid_on,
            "entries": len(entries),
            "earnings_url": f"{settings.PARTNERS_APP_URL}/ganhos",
        },
    )
    return payout


def add_adjustment(*, partner: Partner, amount_cents: int, note: str, actor) -> PartnerEntry:
    if amount_cents == 0:
        raise GuardFailed("O ajuste precisa ter valor.", code="adjustment_invalid")
    note = _required(
        note, code="note_required", message="Conte o motivo do ajuste.", limit=NOTE_MAX_CHARS
    )
    with transaction.atomic():
        entry = PartnerEntry.objects.create(
            partner=partner, kind=PartnerEntry.Kind.ADJUSTMENT, amount_cents=amount_cents, note=note
        )
        record_event(
            instance=partner,
            event="adjustment_added",
            actor=actor,
            payload={"amount_cents": amount_cents},
        )
    return entry


def open_balance(partner: Partner) -> int:
    total = partner.entries.filter(payout__isnull=True).aggregate(s=Sum("amount_cents"))["s"]
    return total or 0


def get_partner(partner_id) -> Partner:
    partner = Partner.objects.filter(globalid=partner_id).first()
    if partner is None:
        raise ResourceNotFound("Parceiro não encontrado.")
    return partner
