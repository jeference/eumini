"""Consultas do app Staff: fila do dia, lista de pedidos e histórico.

Só leitura. As ações ficam em `fulfillment.services` e `fulfillment.operations`.
"""

from __future__ import annotations

from datetime import date

from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from audit.models import DomainEvent
from common.exceptions import ResourceNotFound
from fulfillment.models import ProductionFile, ProductionIssue, ProductionJob, Shipment
from orders.models import Order

JobStatus = ProductionJob.Status
# Pedidos ainda a produzir: os que não foram postados nem cancelados.
_OPEN_JOB_STATUSES = (
    JobStatus.UNASSIGNED,
    JobStatus.ASSIGNED,
    JobStatus.IN_PRODUCTION,
    JobStatus.READY_TO_SHIP,
)
QUEUES = ("to_assign", "missing_file", "awaiting_label", "overdue", "issues")


def _jobs():
    return ProductionJob.objects.filter(order_item__order=OuterRef("pk"))


def _queue_filter(queue: str) -> Q:
    if queue == "to_assign":
        return Q(Exists(_jobs().filter(status=JobStatus.UNASSIGNED)))
    if queue == "missing_file":
        no_file = ~Exists(ProductionFile.objects.filter(job=OuterRef("pk")))
        jobs = ProductionJob.objects.filter(
            order_item__order=OuterRef("pk"), status__in=_OPEN_JOB_STATUSES
        ).filter(no_file)
        return Q(Exists(jobs))
    if queue == "awaiting_label":
        open_label = Shipment.objects.filter(
            order=OuterRef("pk"), shipped_at__isnull=True, label__isnull=False
        )
        return Q(Exists(_jobs().filter(status=JobStatus.READY_TO_SHIP))) & ~Q(Exists(open_label))
    if queue == "overdue":
        late = _jobs().filter(status__in=_OPEN_JOB_STATUSES, post_by__lt=timezone.localdate())
        return Q(Exists(late))
    if queue == "issues":
        return Q(
            Exists(ProductionIssue.objects.filter(order=OuterRef("pk"), resolved_at__isnull=True))
        )
    raise ValueError(queue)


def _production_orders() -> QuerySet:
    """Pedidos pagos que ainda estão na produção."""
    return Order.objects.filter(status__in=(Order.Status.PAID, Order.Status.IN_PRODUCTION))


def queue_counts() -> dict[str, int]:
    orders = _production_orders()
    counts = {queue: orders.filter(_queue_filter(queue)).count() for queue in QUEUES}
    # Problemas podem existir em pedidos já enviados.
    counts["issues"] = Order.objects.filter(_queue_filter("issues")).count()
    counts["to_deliver"] = Order.objects.filter(status=Order.Status.SHIPPED).count()
    return counts


def with_post_by(orders: QuerySet) -> QuerySet:
    from django.db.models import Subquery

    return orders.annotate(post_by_date=Subquery(_jobs().values("post_by")[:1]))


def staff_orders(
    *,
    queue: str | None = None,
    status: str | None = None,
    q: str = "",
    partner_id: str | None = None,
    since: date | None = None,
    until: date | None = None,
) -> QuerySet:
    if queue == "issues":
        orders = Order.objects.filter(_queue_filter(queue))
    elif queue == "to_deliver":
        orders = Order.objects.filter(status=Order.Status.SHIPPED)
    elif queue:
        orders = _production_orders().filter(_queue_filter(queue))
    else:
        orders = Order.objects.all()
    if status:
        orders = orders.filter(status=status)
    q = q.strip()
    if q:
        orders = orders.filter(Q(number__icontains=q) | Q(customer_email__icontains=q.lower()))
    if partner_id:
        orders = orders.filter(Exists(_jobs().filter(partner__globalid=partner_id)))
    if since:
        orders = orders.filter(created_at__date__gte=since)
    if until:
        orders = orders.filter(created_at__date__lte=until)
    if queue and queue != "to_deliver":
        return with_post_by(orders).order_by("post_by_date", "created_at")
    return orders.order_by("-created_at")


def get_order(order_id) -> Order:
    order = Order.objects.filter(globalid=order_id).first()
    if order is None:
        raise ResourceNotFound("Pedido não encontrado.")
    return order


def order_jobs(order) -> list[ProductionJob]:
    return list(
        ProductionJob.objects.filter(order_item__order=order)
        .select_related("order_item__version__asset", "order_item__creation__input", "partner")
        .order_by("order_item__created_at")
    )


def order_events(order) -> QuerySet:
    """Histórico do pedido: eventos dele, dos jobs, das cobranças e dos envios."""
    ids = {order.globalid}
    ids |= set(
        ProductionJob.objects.filter(order_item__order=order).values_list("globalid", flat=True)
    )
    ids |= set(order.charges.values_list("globalid", flat=True))
    ids |= set(order.shipments.values_list("globalid", flat=True))
    return (
        DomainEvent.objects.filter(aggregate_id__in=ids)
        .select_related("actor_user")
        .order_by("created_at")
    )
