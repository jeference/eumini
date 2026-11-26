"""Serializers do app Staff. A equipe vÃª os dados do cliente, com o CPF sempre mascarado."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from audit.models import DomainEvent
from fulfillment import operations, services
from fulfillment.models import Partner, PartnerPayout, ProductionJob
from media import services as media
from orders.models import Order
from payments.models import Charge

JobStatus = ProductionJob.Status

# Etapa da produÃ§Ã£o, vista pela equipe. `mixed` nÃ£o deve acontecer: as aÃ§Ãµes valem para o
# pedido inteiro.
PRODUCTION_STAGES = [
    ("none", "Sem produÃ§Ã£o"),
    ("unassigned", "Sem parceiro"),
    ("assigned", "AtribuÃ­da"),
    ("in_production", "Em produÃ§Ã£o"),
    ("awaiting_label", "Aguardando etiqueta"),
    ("to_post", "Para postar"),
    ("shipped", "Postada"),
    ("cancelled", "Cancelada"),
    ("mixed", "Itens em etapas diferentes"),
]


def _jobs(serializer, order) -> list[ProductionJob]:
    cache = serializer.context.setdefault("_jobs", {})
    if order.pk not in cache:
        from staff.queries import order_jobs

        cache[order.pk] = order_jobs(order)
    return cache[order.pk]


def stage_of(jobs: list[ProductionJob], *, has_label: bool) -> str:
    if not jobs:
        return "none"
    statuses = {job.status for job in jobs}
    if len(statuses) > 1:
        return "mixed"
    status = statuses.pop()
    if status == JobStatus.READY_TO_SHIP:
        return "to_post" if has_label else "awaiting_label"
    return status


class PartnerRefSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    name = serializers.CharField()


class _StaffOrderBase(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)
    stage = serializers.SerializerMethodField()
    partner = serializers.SerializerMethodField()
    post_by = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    piece_count = serializers.SerializerMethodField()
    open_issues = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    def _has_label(self, order) -> bool:
        return services.open_shipment(order) is not None

    @extend_schema_field(serializers.ChoiceField(choices=PRODUCTION_STAGES))
    def get_stage(self, order) -> str:
        return stage_of(_jobs(self, order), has_label=self._has_label(order))

    @extend_schema_field(PartnerRefSerializer(allow_null=True))
    def get_partner(self, order):
        partners = [job.partner for job in _jobs(self, order) if job.partner is not None]
        return PartnerRefSerializer(partners[0]).data if partners else None

    @extend_schema_field(serializers.DateField(allow_null=True))
    def get_post_by(self, order):
        jobs = _jobs(self, order)
        return jobs[0].post_by if jobs else None

    def get_is_overdue(self, order) -> bool:
        open_jobs = [
            job
            for job in _jobs(self, order)
            if job.status not in (JobStatus.SHIPPED, JobStatus.CANCELLED)
        ]
        return bool(open_jobs) and services.is_overdue(open_jobs[0].post_by)

    def get_piece_count(self, order) -> int:
        return sum(job.order_item.quantity for job in _jobs(self, order)) or sum(
            item.quantity for item in order.items.all()
        )

    def get_open_issues(self, order) -> int:
        return order.production_issues.filter(resolved_at__isnull=True).count()

    def get_thumbnail_url(self, order) -> str:
        item = order.items.select_related("version__asset").first()
        return media.signed_url(item.version.asset) if item else ""


class StaffOrderListSerializer(_StaffOrderBase):
    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "customer_name",
            "customer_email",
            "total_cents",
            "stage",
            "partner",
            "post_by",
            "is_overdue",
            "piece_count",
            "open_issues",
            "thumbnail_url",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class StaffFileSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    version = serializers.IntegerField()
    size_bytes = serializers.IntegerField(source="asset.size_bytes")
    uploaded_at = serializers.DateTimeField(source="created_at")


class StaffItemSerializer(serializers.Serializer):
    # Item a partir do job: cada job traz o seu item.
    id = serializers.UUIDField(source="order_item.globalid")
    image_url = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    category = serializers.CharField(source="order_item.category")
    size_label = serializers.CharField(source="order_item.size_label")
    longest_side_mm = serializers.IntegerField(source="order_item.longest_side_mm")
    quantity = serializers.IntegerField(source="order_item.quantity")
    unit_price_cents = serializers.IntegerField(source="order_item.unit_price_cents")
    customer_text = serializers.SerializerMethodField()
    prompt_text = serializers.CharField(source="order_item.prompt_text")
    job_status = serializers.ChoiceField(source="status", choices=JobStatus.choices)
    payout_cents = serializers.IntegerField(allow_null=True)
    files = serializers.SerializerMethodField()

    def get_image_url(self, job) -> str:
        return media.signed_url(job.order_item.version.asset)

    def get_photo_url(self, job) -> str:
        source = job.order_item.creation.input
        return media.signed_url(source.photo)

    def get_customer_text(self, job) -> str:
        return job.order_item.creation.input.text

    @extend_schema_field(StaffFileSerializer(many=True))
    def get_files(self, job):
        return StaffFileSerializer(
            job.files.select_related("asset").order_by("-version"), many=True
        ).data


class StaffChargeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)

    class Meta:
        model = Charge
        fields = [
            "id",
            "method",
            "status",
            "amount_cents",
            "card_brand",
            "card_last_four",
            "expires_at",
            "paid_at",
            "disputed_at",
            "created_at",
        ]
        read_only_fields = fields


class StaffShipmentSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    carrier = serializers.CharField()
    tracking_code = serializers.CharField()
    has_label = serializers.SerializerMethodField()
    shipped_at = serializers.DateTimeField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)

    def get_has_label(self, shipment) -> bool:
        return shipment.label_id is not None


class StaffPhotoSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_url(self, photo) -> str:
        return media.signed_url(photo.asset)


class StaffIssueSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    partner = PartnerRefSerializer()
    text = serializers.CharField()
    photo_url = serializers.SerializerMethodField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolution_note = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_photo_url(self, issue) -> str:
        return media.signed_url(issue.photo)


class StaffOrderDetailSerializer(_StaffOrderBase):
    cpf_masked = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    charges = serializers.SerializerMethodField()
    shipment = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    issues = serializers.SerializerMethodField()
    assigned_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "customer_name",
            "customer_email",
            "cpf_masked",
            "postal_code",
            "street",
            "address_number",
            "complement",
            "neighborhood",
            "city",
            "state",
            "subtotal_cents",
            "shipping_cents",
            "total_cents",
            "shipping_service_name",
            "shipping_company",
            "delivery_days",
            "stage",
            "partner",
            "assigned_at",
            "post_by",
            "is_overdue",
            "piece_count",
            "open_issues",
            "thumbnail_url",
            "items",
            "charges",
            "shipment",
            "photos",
            "issues",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_cpf_masked(self, order) -> str:
        return f"***.***.***-{order.cpf_last_digits}"

    @extend_schema_field(StaffItemSerializer(many=True))
    def get_items(self, order):
        return StaffItemSerializer(_jobs(self, order), many=True).data

    @extend_schema_field(StaffChargeSerializer(many=True))
    def get_charges(self, order):
        return StaffChargeSerializer(order.charges.order_by("created_at"), many=True).data

    @extend_schema_field(StaffShipmentSerializer(allow_null=True))
    def get_shipment(self, order):
        shipment = order.shipments.order_by("-created_at").first()
        return StaffShipmentSerializer(shipment).data if shipment else None

    @extend_schema_field(StaffPhotoSerializer(many=True))
    def get_photos(self, order):
        photos = order.production_photos.select_related("asset")
        return StaffPhotoSerializer(photos, many=True).data

    @extend_schema_field(StaffIssueSerializer(many=True))
    def get_issues(self, order):
        issues = order.production_issues.select_related("partner", "photo")
        return StaffIssueSerializer(issues, many=True).data

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_assigned_at(self, order):
        jobs = _jobs(self, order)
        return jobs[0].assigned_at if jobs else None


class StaffQueueSummarySerializer(serializers.Serializer):
    to_assign = serializers.IntegerField()
    missing_file = serializers.IntegerField()
    awaiting_label = serializers.IntegerField()
    overdue = serializers.IntegerField()
    issues = serializers.IntegerField()
    to_deliver = serializers.IntegerField()


_AGGREGATES = {
    "orders.Order": "order",
    "fulfillment.ProductionJob": "job",
    "payments.Charge": "charge",
    "fulfillment.Shipment": "shipment",
}


class StaffEventSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)
    aggregate = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()

    class Meta:
        model = DomainEvent
        fields = [
            "id",
            "aggregate",
            "event",
            "from_state",
            "to_state",
            "actor",
            "payload",
            "created_at",
        ]
        read_only_fields = fields

    def get_aggregate(self, event) -> str:
        return _AGGREGATES.get(event.aggregate_type, "other")

    def get_actor(self, event) -> str:
        """E-mail de quem fez, "cliente" para o visitante e "sistema" para o resto."""
        if event.actor_user is not None:
            return event.actor_user.email
        if event.actor_label.startswith("visitor:"):
            return "cliente"
        return "sistema"


# --- AÃ§Ãµes ---


class StaffDownloadRequestSerializer(serializers.Serializer):
    file = serializers.ChoiceField(
        choices=[("image", "Imagem comprada"), ("photo", "Foto do cliente"), ("3mf", "3MF")]
    )


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class AssignSerializer(serializers.Serializer):
    partner_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class LabelSerializer(serializers.Serializer):
    pdf = serializers.FileField()
    carrier = serializers.CharField(max_length=64)
    tracking_code = serializers.CharField(max_length=64)


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000)


# --- Parceiros ---


class StaffPartnerSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)
    login_email = serializers.SerializerMethodField()
    invite_accepted = serializers.SerializerMethodField()
    active_orders = serializers.SerializerMethodField()
    overdue_orders = serializers.SerializerMethodField()
    to_receive_cents = serializers.SerializerMethodField()
    paid_cents = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "status",
            "is_internal",
            "origin_postal_code",
            "pix_key",
            "login_email",
            "invite_accepted",
            "active_orders",
            "overdue_orders",
            "to_receive_cents",
            "paid_cents",
            "created_at",
        ]
        read_only_fields = fields

    def _member_user(self, partner):
        member = partner.members.select_related("user").order_by("created_at").first()
        return member.user if member else None

    def get_login_email(self, partner) -> str:
        user = self._member_user(partner)
        return user.email if user else ""

    def get_invite_accepted(self, partner) -> bool:
        user = self._member_user(partner)
        return bool(user and user.has_usable_password())

    def _active_jobs(self, partner):
        return partner.jobs.filter(status__in=operations.ACTIVE_STATUSES)

    def get_active_orders(self, partner) -> int:
        return self._active_jobs(partner).values("order_item__order").distinct().count()

    def get_overdue_orders(self, partner) -> int:
        from django.utils import timezone

        late = self._active_jobs(partner).filter(post_by__lt=timezone.localdate())
        return late.values("order_item__order").distinct().count()

    def get_to_receive_cents(self, partner) -> int:
        return services.partner_balance(partner).to_receive_cents

    def get_paid_cents(self, partner) -> int:
        return services.partner_balance(partner).paid_cents


class PartnerCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    origin_postal_code = serializers.CharField(max_length=9)
    pix_key = serializers.CharField(max_length=140, required=False, allow_blank=True)


class PartnerUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    origin_postal_code = serializers.CharField(max_length=9, required=False)
    pix_key = serializers.CharField(max_length=140, required=False, allow_blank=True)


class StaffPayoutSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)
    entry_count = serializers.SerializerMethodField()
    receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = PartnerPayout
        fields = [
            "id",
            "paid_on",
            "amount_cents",
            "note",
            "entry_count",
            "receipt_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_entry_count(self, payout) -> int:
        return payout.entries.count()

    def get_receipt_url(self, payout) -> str:
        return media.signed_url(payout.receipt)


class PayoutCreateSerializer(serializers.Serializer):
    entry_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    paid_on = serializers.DateField()
    amount_cents = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    receipt = serializers.FileField(required=False)


class AdjustmentCreateSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField()
    note = serializers.CharField(max_length=1000)


class RateRowSerializer(serializers.Serializer):
    category = serializers.CharField()
    size_id = serializers.UUIDField(source="size_globalid")
    size_label = serializers.CharField()
    price_cents = serializers.IntegerField()
    amount_cents = serializers.IntegerField(allow_null=True)


class RateInputSerializer(serializers.Serializer):
    category = serializers.CharField()
    size_id = serializers.UUIDField()
    amount_cents = serializers.IntegerField(allow_null=True, min_value=1)


class RatesUpdateSerializer(serializers.Serializer):
    rates = RateInputSerializer(many=True)
