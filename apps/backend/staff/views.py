"""API do app Staff, em `/api/staff/`. Toda rota exige o papel `staff` ou `admin`."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.exceptions import GuardFailed, ResourceNotFound
from common.permissions import IsStaff
from fulfillment import operations, services
from fulfillment.models import Partner, ProductionIssue, ProductionJob
from fulfillment.serializers import DownloadSerializer, PartnerEntrySerializer
from orders.models import Order
from staff import queries
from staff import serializers as s

_QUEUE_CHOICES = [*queries.QUEUES, "to_deliver"]


class _StaffView(APIView):
    permission_classes = [IsStaff]
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
        self.throttle_scope = "staff_read" if self.request.method == "GET" else "staff_write"
        return super().get_throttles()

    def _detail(self, order) -> Response:
        order.refresh_from_db()
        return Response(s.StaffOrderDetailSerializer(order).data)


class _StaffList(ListAPIView):
    permission_classes = [IsStaff]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "staff_read"


def _file_bytes(upload) -> bytes:
    return upload.read() if upload else b""


# --- Pedidos ---


class StaffQueueSummaryView(_StaffView):
    @extend_schema(responses=s.StaffQueueSummarySerializer)
    def get(self, request):
        return Response(s.StaffQueueSummarySerializer(queries.queue_counts()).data)


class StaffOrderListView(_StaffList):
    serializer_class = s.StaffOrderListSerializer

    def get_queryset(self):
        params = self.request.query_params
        queue = params.get("fila") or None
        status_ = params.get("status") or None
        return queries.staff_orders(
            queue=queue if queue in _QUEUE_CHOICES else None,
            status=status_ if status_ in Order.Status.values else None,
            q=params.get("q", ""),
            partner_id=params.get("parceiro") or None,
            since=_date(params.get("desde")),
            until=_date(params.get("ate")),
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("fila", str, enum=_QUEUE_CHOICES, required=False),
            OpenApiParameter("status", str, enum=Order.Status.values, required=False),
            OpenApiParameter("q", str, required=False, description="NÃºmero ou e-mail"),
            OpenApiParameter("parceiro", str, required=False),
            OpenApiParameter("desde", str, required=False, description="AAAA-MM-DD"),
            OpenApiParameter("ate", str, required=False, description="AAAA-MM-DD"),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


def _date(value):
    from datetime import date

    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


class StaffOrderDetailView(_StaffView):
    @extend_schema(responses=s.StaffOrderDetailSerializer)
    def get(self, request, order_id):
        return self._detail(queries.get_order(order_id))


class StaffOrderEventsView(_StaffView):
    @extend_schema(responses=s.StaffEventSerializer(many=True))
    def get(self, request, order_id):
        order = queries.get_order(order_id)
        return Response(s.StaffEventSerializer(queries.order_events(order), many=True).data)


class StaffItemDownloadView(_StaffView):
    @extend_schema(request=s.StaffDownloadRequestSerializer, responses=DownloadSerializer)
    def post(self, request, order_id, item_id):
        data = s.StaffDownloadRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        download = operations.download_item_file(
            order=queries.get_order(order_id),
            item_id=item_id,
            file=data.validated_data["file"],
            user=request.user,
        )
        return Response(DownloadSerializer(download).data)


class StaffItemFileView(_StaffView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": s.FileUploadSerializer},
        responses={201: s.StaffOrderDetailSerializer},
    )
    def post(self, request, order_id, item_id):
        order = queries.get_order(order_id)
        job = ProductionJob.objects.filter(
            order_item__order=order, order_item__globalid=item_id
        ).first()
        if job is None:
            raise ResourceNotFound("Item nÃ£o encontrado.")
        if job.status in (ProductionJob.Status.SHIPPED, ProductionJob.Status.CANCELLED):
            raise GuardFailed("Este item jÃ¡ saiu da produÃ§Ã£o.", code="job_closed")
        data = s.FileUploadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.add_production_file(
            job=job, data=_file_bytes(data.validated_data["file"]), actor=request.user
        )
        response = self._detail(order)
        response.status_code = status.HTTP_201_CREATED
        return response


class StaffAssignView(_StaffView):
    @extend_schema(request=s.AssignSerializer, responses=s.StaffOrderDetailSerializer)
    def post(self, request, order_id):
        order = queries.get_order(order_id)
        data = s.AssignSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        partner = operations.get_partner(data.validated_data["partner_id"])
        operations.reassign_order(
            order=order,
            partner=partner,
            actor=request.user,
            reason=data.validated_data.get("reason", ""),
        )
        return self._detail(order)


class StaffUnassignView(_StaffView):
    @extend_schema(request=s.ReasonSerializer, responses=s.StaffOrderDetailSerializer)
    def post(self, request, order_id):
        order = queries.get_order(order_id)
        data = s.ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        operations.unassign_order(
            order=order, actor=request.user, reason=data.validated_data["reason"]
        )
        return self._detail(order)


class StaffLabelView(_StaffView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": s.LabelSerializer},
        responses=s.StaffOrderDetailSerializer,
    )
    def post(self, request, order_id):
        order = queries.get_order(order_id)
        data = s.LabelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.attach_label(
            order=order,
            pdf=_file_bytes(data.validated_data["pdf"]),
            carrier=data.validated_data["carrier"],
            tracking_code=data.validated_data["tracking_code"],
            actor=request.user,
        )
        return self._detail(order)


class StaffLabelDownloadView(_StaffView):
    @extend_schema(request=None, responses=DownloadSerializer)
    def post(self, request, order_id):
        download = operations.download_label(order=queries.get_order(order_id), user=request.user)
        return Response(DownloadSerializer(download).data)


class StaffDeliverView(_StaffView):
    @extend_schema(request=None, responses=s.StaffOrderDetailSerializer)
    def post(self, request, order_id):
        order = queries.get_order(order_id)
        operations.mark_delivered(order=order, actor=request.user)
        return self._detail(order)


class StaffIssueResolveView(_StaffView):
    @extend_schema(request=s.NoteSerializer, responses=s.StaffOrderDetailSerializer)
    def post(self, request, issue_id):
        issue = ProductionIssue.objects.select_related("order").filter(globalid=issue_id).first()
        if issue is None:
            raise ResourceNotFound("Problema nÃ£o encontrado.")
        data = s.NoteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        operations.resolve_issue(issue=issue, actor=request.user, note=data.validated_data["note"])
        return self._detail(issue.order)


# --- Parceiros ---


class StaffPartnerListView(_StaffList):
    serializer_class = s.StaffPartnerSerializer

    def get_queryset(self):
        return Partner.objects.order_by("status", "name")

    def get_throttles(self):
        self.throttle_scope = "staff_read" if self.request.method == "GET" else "staff_write"
        return super().get_throttles()

    @extend_schema(request=s.PartnerCreateSerializer, responses={201: s.StaffPartnerSerializer})
    def post(self, request):
        data = s.PartnerCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        partner = operations.create_partner(actor=request.user, **data.validated_data)
        return Response(s.StaffPartnerSerializer(partner).data, status=status.HTTP_201_CREATED)


class StaffPartnerDetailView(_StaffView):
    @extend_schema(responses=s.StaffPartnerSerializer)
    def get(self, request, partner_id):
        return Response(s.StaffPartnerSerializer(operations.get_partner(partner_id)).data)

    @extend_schema(request=s.PartnerUpdateSerializer, responses=s.StaffPartnerSerializer)
    def patch(self, request, partner_id):
        partner = operations.get_partner(partner_id)
        data = s.PartnerUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        operations.update_partner(partner=partner, actor=request.user, **data.validated_data)
        return Response(s.StaffPartnerSerializer(partner).data)


class StaffPartnerInviteView(_StaffView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request, partner_id):
        operations.resend_invite(partner=operations.get_partner(partner_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffPartnerDeactivateView(_StaffView):
    @extend_schema(request=None, responses=s.StaffPartnerSerializer)
    def post(self, request, partner_id):
        partner = operations.set_partner_status(
            partner=operations.get_partner(partner_id), active=False, actor=request.user
        )
        return Response(s.StaffPartnerSerializer(partner).data)


class StaffPartnerReactivateView(_StaffView):
    @extend_schema(request=None, responses=s.StaffPartnerSerializer)
    def post(self, request, partner_id):
        partner = operations.set_partner_status(
            partner=operations.get_partner(partner_id), active=True, actor=request.user
        )
        return Response(s.StaffPartnerSerializer(partner).data)


class StaffPartnerEntryListView(_StaffList):
    serializer_class = PartnerEntrySerializer

    def get_queryset(self):
        partner = operations.get_partner(self.kwargs["partner_id"])
        entries = services.partner_entries(partner).order_by("-created_at")
        if self.request.query_params.get("aberto") == "1":
            entries = entries.filter(payout__isnull=True)
        return entries

    @extend_schema(
        parameters=[OpenApiParameter("aberto", str, enum=["1"], required=False)],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class StaffPartnerPayoutListView(_StaffList):
    serializer_class = s.StaffPayoutSerializer
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        return services.partner_payouts(operations.get_partner(self.kwargs["partner_id"]))

    def get_throttles(self):
        self.throttle_scope = "staff_read" if self.request.method == "GET" else "staff_write"
        return super().get_throttles()

    @extend_schema(
        request={"multipart/form-data": s.PayoutCreateSerializer},
        responses={201: s.StaffPayoutSerializer},
    )
    def post(self, request, partner_id):
        partner = operations.get_partner(partner_id)
        data = s.PayoutCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        payout = operations.record_payout(
            partner=partner,
            entry_ids=values["entry_ids"],
            paid_on=values["paid_on"],
            amount_cents=values["amount_cents"],
            receipt=_file_bytes(values.get("receipt")) or None,
            note=values.get("note", ""),
            actor=request.user,
        )
        return Response(s.StaffPayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class StaffPartnerAdjustmentView(_StaffView):
    @extend_schema(request=s.AdjustmentCreateSerializer, responses={201: PartnerEntrySerializer})
    def post(self, request, partner_id):
        partner = operations.get_partner(partner_id)
        data = s.AdjustmentCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        entry = operations.add_adjustment(
            partner=partner, actor=request.user, **data.validated_data
        )
        return Response(PartnerEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


# --- Tarifas ---


class StaffRatesView(_StaffView):
    parser_classes = [JSONParser]

    @extend_schema(responses=s.RateRowSerializer(many=True))
    def get(self, request):
        return Response(s.RateRowSerializer(operations.rate_table(), many=True).data)

    @extend_schema(request=s.RatesUpdateSerializer, responses=s.RateRowSerializer(many=True))
    def put(self, request):
        data = s.RatesUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        rows = operations.set_rates(rows=data.validated_data["rates"], actor=request.user)
        return Response(s.RateRowSerializer(rows, many=True).data)
