"""API do app de parceiros, em `/api/partner/`.

Toda rota exige um parceiro ativo (`IsPartnerMember`), menos o aceite do convite. Pedido de
outro parceiro responde 404, sem revelar que existe.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.permissions import IsPartnerMember, IsPublic
from fulfillment import serializers as s
from fulfillment import services
from fulfillment.invites import accept_partner_invite
from fulfillment.models import PartnerOrderGroup


class _PartnerView(APIView):
    permission_classes = [IsPartnerMember]
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
        self.throttle_scope = "partner_read" if self.request.method == "GET" else "partner_write"
        return super().get_throttles()

    def _order(self, request, order_id):
        return services.get_partner_order(partner=request.partner, order_id=order_id)

    def _detail(self, request, order) -> Response:
        order.refresh_from_db()
        return Response(
            s.PartnerOrderDetailSerializer(order, context={"partner": request.partner}).data
        )


class PartnerMeView(_PartnerView):
    @extend_schema(responses=s.PartnerMeSerializer)
    def get(self, request):
        return Response(s.PartnerMeSerializer(request.partner).data)


class PartnerOrderListView(ListAPIView):
    permission_classes = [IsPartnerMember]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "partner_read"
    serializer_class = s.PartnerOrderListSerializer

    def get_queryset(self):
        group = self.request.query_params.get("group") or None
        if group not in (None, *PartnerOrderGroup.values):
            group = None
        orders = services.partner_orders(self.request.partner, group)
        # Os ativos por prazo; os encerrados pelo mais recente.
        if group in (PartnerOrderGroup.POSTED, PartnerOrderGroup.CANCELLED):
            return orders.order_by("-updated_at")
        return services.with_post_by(orders).order_by("post_by_date", "created_at")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "partner": self.request.partner}

    @extend_schema(
        parameters=[OpenApiParameter("group", str, enum=PartnerOrderGroup.values, required=False)]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PartnerOrderSummaryView(_PartnerView):
    @extend_schema(responses=s.PartnerOrderSummarySerializer)
    def get(self, request):
        return Response(
            s.PartnerOrderSummarySerializer(services.group_counts(request.partner)).data
        )


class PartnerOrderDetailView(_PartnerView):
    @extend_schema(responses=s.PartnerOrderDetailSerializer)
    def get(self, request, order_id):
        return self._detail(request, self._order(request, order_id))


class PartnerItemDownloadView(_PartnerView):
    @extend_schema(request=s.DownloadRequestSerializer, responses=s.DownloadSerializer)
    def post(self, request, order_id, item_id):
        data = s.DownloadRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        download = services.download_item_file(
            order=self._order(request, order_id),
            partner=request.partner,
            user=request.user,
            item_id=item_id,
            file=data.validated_data["file"],
        )
        return Response(s.DownloadSerializer(download).data)


class PartnerLabelDownloadView(_PartnerView):
    @extend_schema(request=None, responses=s.DownloadSerializer)
    def post(self, request, order_id):
        download = services.download_label(
            order=self._order(request, order_id), partner=request.partner, user=request.user
        )
        return Response(s.DownloadSerializer(download).data)


class PartnerRefuseView(_PartnerView):
    @extend_schema(request=s.RefuseSerializer, responses={204: None})
    def post(self, request, order_id):
        data = s.RefuseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.refuse_order(
            order=self._order(request, order_id),
            partner=request.partner,
            user=request.user,
            reason=data.validated_data["reason"],
        )
        # O pedido sai do parceiro: não há mais detalhe para devolver.
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartnerStartView(_PartnerView):
    @extend_schema(request=None, responses=s.PartnerOrderDetailSerializer)
    def post(self, request, order_id):
        order = self._order(request, order_id)
        services.start_order(order=order, partner=request.partner, user=request.user)
        return self._detail(request, order)


class PartnerReadyView(_PartnerView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": s.ReadySerializer},
        responses=s.PartnerOrderDetailSerializer,
    )
    def post(self, request, order_id):
        order = self._order(request, order_id)
        data = s.ReadySerializer(data={"photos": request.FILES.getlist("photos")})
        data.is_valid(raise_exception=True)
        services.mark_ready(
            order=order,
            partner=request.partner,
            user=request.user,
            photos=[photo.read() for photo in data.validated_data["photos"]],
        )
        return self._detail(request, order)


class PartnerPostView(_PartnerView):
    @extend_schema(request=None, responses=s.PartnerOrderDetailSerializer)
    def post(self, request, order_id):
        order = self._order(request, order_id)
        services.post_order(order=order, partner=request.partner, user=request.user)
        return self._detail(request, order)


class PartnerIssueView(_PartnerView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": s.IssueCreateSerializer},
        responses={201: s.PartnerOrderDetailSerializer},
    )
    def post(self, request, order_id):
        order = self._order(request, order_id)
        data = s.IssueCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        photo = data.validated_data.get("photo")
        services.report_issue(
            order=order,
            partner=request.partner,
            user=request.user,
            text=data.validated_data["text"],
            photo=photo.read() if photo else None,
        )
        response = self._detail(request, order)
        response.status_code = status.HTTP_201_CREATED
        return response


class PartnerBalanceView(_PartnerView):
    @extend_schema(responses=s.PartnerBalanceSerializer)
    def get(self, request):
        return Response(s.PartnerBalanceSerializer(services.partner_balance(request.partner)).data)


class PartnerEntryListView(ListAPIView):
    permission_classes = [IsPartnerMember]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "partner_read"
    serializer_class = s.PartnerEntrySerializer

    def get_queryset(self):
        return services.partner_entries(self.request.partner).order_by("-created_at")


class PartnerPayoutListView(ListAPIView):
    permission_classes = [IsPartnerMember]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "partner_read"
    serializer_class = s.PartnerPayoutSerializer

    def get_queryset(self):
        return services.partner_payouts(self.request.partner)


class PartnerInviteAcceptView(APIView):
    authentication_classes: list = []
    permission_classes = [IsPublic]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "partner_invite"

    @extend_schema(request=s.InviteAcceptSerializer, responses={204: None}, auth=[])
    def post(self, request):
        data = s.InviteAcceptSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        accept_partner_invite(**data.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)
