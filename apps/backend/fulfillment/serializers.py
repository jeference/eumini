"""Serializers do app de parceiros.

O parceiro nunca vê e-mail, CPF, telefone, endereço, valores pagos pelo cliente nem a foto
original (RN-PAR-09). Nome e endereço chegam só impressos na etiqueta.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from fulfillment import services
from fulfillment.models import PartnerEntry, PartnerOrderGroup, PartnerPayout, ProductionJob
from media import services as media


class PartnerMeSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    name = serializers.CharField()
    origin_postal_code = serializers.CharField()
    pix_key_masked = serializers.SerializerMethodField()

    def get_pix_key_masked(self, partner) -> str:
        key = partner.pix_key
        if not key:
            return ""
        if len(key) <= 6:
            return "•" * len(key)
        return f"{key[:3]}{'•' * (len(key) - 6)}{key[-3:]}"


class ProductionFileInfoSerializer(serializers.Serializer):
    version = serializers.IntegerField()
    uploaded_at = serializers.DateTimeField(source="created_at")


class PartnerItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="order_item.globalid")
    image_url = serializers.SerializerMethodField()
    category = serializers.CharField(source="order_item.category")
    size_label = serializers.CharField(source="order_item.size_label")
    longest_side_mm = serializers.IntegerField(source="order_item.longest_side_mm")
    quantity = serializers.IntegerField(source="order_item.quantity")
    status = serializers.ChoiceField(choices=ProductionJob.Status.choices)
    production_file = serializers.SerializerMethodField()

    def get_image_url(self, job) -> str:
        return media.signed_url(job.order_item.version.asset)

    @extend_schema_field(ProductionFileInfoSerializer(allow_null=True))
    def get_production_file(self, job):
        file = services.latest_file(job)
        return ProductionFileInfoSerializer(file).data if file else None


class PartnerLabelSerializer(serializers.Serializer):
    carrier = serializers.CharField()
    tracking_code = serializers.CharField()
    shipped_at = serializers.DateTimeField(allow_null=True)


class PartnerPhotoSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_url(self, photo) -> str:
        return media.signed_url(photo.asset)


class PartnerIssueSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="globalid")
    text = serializers.CharField()
    photo_url = serializers.SerializerMethodField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolution_note = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_photo_url(self, issue) -> str:
        return media.signed_url(issue.photo)


class _PartnerOrderBase(serializers.Serializer):
    # O pedido visto pelo parceiro, a partir dos jobs dele. O contexto traz `partner`.
    id = serializers.UUIDField(source="globalid")
    number = serializers.CharField()
    group = serializers.SerializerMethodField()
    post_by = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    is_due_soon = serializers.SerializerMethodField()
    piece_count = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    assigned_at = serializers.SerializerMethodField()

    def _jobs(self, order) -> list[ProductionJob]:
        cache = self.context.setdefault("_jobs", {})
        if order.pk not in cache:
            cache[order.pk] = services.partner_jobs(order, self.context["partner"])
        return cache[order.pk]

    def _active(self, order) -> bool:
        return self.get_group(order) not in (PartnerOrderGroup.POSTED, PartnerOrderGroup.CANCELLED)

    @extend_schema_field(serializers.ChoiceField(choices=PartnerOrderGroup.choices))
    def get_group(self, order) -> str:
        return services.group_of(
            self._jobs(order), has_label=services.open_shipment(order) is not None
        )

    @extend_schema_field(serializers.DateField(allow_null=True))
    def get_post_by(self, order):
        jobs = self._jobs(order)
        return jobs[0].post_by if jobs else None

    def get_is_overdue(self, order) -> bool:
        return self._active(order) and services.is_overdue(self.get_post_by(order))

    def get_is_due_soon(self, order) -> bool:
        return self._active(order) and services.due_soon(self.get_post_by(order))

    def get_piece_count(self, order) -> int:
        return sum(job.order_item.quantity for job in self._jobs(order))

    def get_thumbnail_url(self, order) -> str:
        jobs = self._jobs(order)
        return media.signed_url(jobs[0].order_item.version.asset) if jobs else ""

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_assigned_at(self, order):
        jobs = self._jobs(order)
        return jobs[0].assigned_at if jobs else None


class PartnerOrderListSerializer(_PartnerOrderBase):
    pass


class PartnerOrderDetailSerializer(_PartnerOrderBase):
    items = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    issues = serializers.SerializerMethodField()

    @extend_schema_field(PartnerItemSerializer(many=True))
    def get_items(self, order):
        jobs = self._jobs(order)
        return PartnerItemSerializer(jobs, many=True).data

    @extend_schema_field(PartnerLabelSerializer(allow_null=True))
    def get_label(self, order):
        partner = self.context["partner"]
        shipment = (
            order.shipments.filter(partner=partner, label__isnull=False)
            .order_by("-created_at")
            .first()
        )
        return PartnerLabelSerializer(shipment).data if shipment else None

    @extend_schema_field(PartnerPhotoSerializer(many=True))
    def get_photos(self, order):
        return PartnerPhotoSerializer(
            services.photos_for(order, self.context["partner"]), many=True
        ).data

    @extend_schema_field(PartnerIssueSerializer(many=True))
    def get_issues(self, order):
        return PartnerIssueSerializer(
            services.issues_for(order, self.context["partner"]), many=True
        ).data


class PartnerOrderSummarySerializer(serializers.Serializer):
    to_print = serializers.IntegerField()
    in_production = serializers.IntegerField()
    awaiting_label = serializers.IntegerField()
    to_post = serializers.IntegerField()
    posted = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    overdue = serializers.IntegerField()


class DownloadRequestSerializer(serializers.Serializer):
    file = serializers.ChoiceField(choices=[("3mf", "3MF"), ("image", "Imagem de referência")])


class DownloadSerializer(serializers.Serializer):
    url = serializers.CharField()
    filename = serializers.CharField()


class RefuseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=services.REFUSE_MAX_CHARS)


class ReadySerializer(serializers.Serializer):
    photos = serializers.ListField(child=serializers.ImageField(), allow_empty=False)


class IssueCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=services.ISSUE_MAX_CHARS)
    photo = serializers.ImageField(required=False)


class InviteAcceptSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    password = serializers.CharField(max_length=128, write_only=True)


class PartnerBalanceSerializer(serializers.Serializer):
    to_receive_cents = serializers.IntegerField()
    paid_cents = serializers.IntegerField()


class PartnerEntrySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)
    order_number = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    size_label = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    payout_id = serializers.SerializerMethodField()

    class Meta:
        model = PartnerEntry
        fields = [
            "id",
            "kind",
            "amount_cents",
            "note",
            "order_number",
            "category",
            "size_label",
            "quantity",
            "is_paid",
            "payout_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_order_number(self, entry) -> str:
        return entry.job.order_item.order.number if entry.job else ""

    def get_category(self, entry) -> str:
        return entry.job.order_item.category if entry.job else ""

    def get_size_label(self, entry) -> str:
        return entry.job.order_item.size_label if entry.job else ""

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_quantity(self, entry):
        return entry.job.order_item.quantity if entry.job else None

    def get_is_paid(self, entry) -> bool:
        return entry.payout_id is not None

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_payout_id(self, entry):
        return entry.payout.globalid if entry.payout else None


class PartnerPayoutSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="globalid", read_only=True)
    entry_count = serializers.SerializerMethodField()

    class Meta:
        model = PartnerPayout
        fields = ["id", "paid_on", "amount_cents", "note", "entry_count", "created_at"]
        read_only_fields = fields

    def get_entry_count(self, payout) -> int:
        return payout.entries.count()
