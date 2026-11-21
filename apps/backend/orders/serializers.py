from __future__ import annotations

import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from common.serializers import GlobalIdSerializer
from media import services as media
from orders import services
from orders.models import Address, CartItem, Order, OrderItem
from payments.models import Charge
from payments.serializers import ChargeSerializer


class CartItemSerializer(GlobalIdSerializer):
    creation_id = serializers.UUIDField(source="creation.globalid", read_only=True)
    size_id = serializers.UUIDField(source="size.globalid", read_only=True)
    size_label = serializers.CharField(source="size.label", read_only=True)
    unit_price_cents = serializers.SerializerMethodField()
    category = serializers.CharField(source="version.category", read_only=True)
    line_total_cents = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    unavailable_reason = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "creation_id",
            "size_id",
            "size_label",
            "category",
            "quantity",
            "unit_price_cents",
            "line_total_cents",
            "image_url",
            "unavailable_reason",
        ]
        read_only_fields = fields

    def get_unit_price_cents(self, item) -> int | None:
        return services.unit_price_cents(item)

    def get_line_total_cents(self, item) -> int:
        return (services.unit_price_cents(item) or 0) * item.quantity

    def get_image_url(self, item) -> str:
        return media.signed_url(item.version.asset)

    def get_unavailable_reason(self, item) -> str:
        return services.unavailable_reason(item)


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    subtotal_cents = serializers.IntegerField()
    item_count = serializers.IntegerField()


class CartItemCreateSerializer(serializers.Serializer):
    creation_id = serializers.UUIDField()
    size_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=10)


class OrderPaySerializer(serializers.Serializer):
    """Sem corpo, gera o PIX. Cartão traz o token do abacatepay.js e o celular, que o
    gateway exige no cartão e que não guardamos."""

    method = serializers.ChoiceField(choices=Charge.Method.choices, default=Charge.Method.PIX)
    card_token = serializers.CharField(max_length=128, required=False, allow_blank=True)
    cellphone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["method"] != Charge.Method.CARD:
            return {"method": attrs["method"]}
        token = attrs.get("card_token", "")
        if not token.startswith("ctok_"):
            raise serializers.ValidationError({"card_token": "Token do cartão inválido."})
        digits = re.sub(r"\D", "", attrs.get("cellphone", ""))
        if len(digits) not in (10, 11) or digits[0] == "0":
            raise serializers.ValidationError({"cellphone": "Informe um celular com DDD."})
        return {"method": Charge.Method.CARD, "card_token": token, "cellphone": digits}


class OrderCreateSerializer(serializers.Serializer):
    item_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    shipping_quote_id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField(max_length=120)
    cpf = serializers.CharField(max_length=14)
    postal_code = serializers.CharField(max_length=9)
    street = serializers.CharField(max_length=160)
    number = serializers.CharField(max_length=20)
    complement = serializers.CharField(max_length=80, required=False, allow_blank=True)
    neighborhood = serializers.CharField(max_length=80)
    city = serializers.CharField(max_length=80)
    state = serializers.CharField(max_length=2)


class OrderItemSerializer(GlobalIdSerializer):
    creation_id = serializers.UUIDField(source="creation.globalid", read_only=True)
    image_url = serializers.SerializerMethodField()
    line_total_cents = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "creation_id",
            "size_label",
            "category",
            "quantity",
            "unit_price_cents",
            "line_total_cents",
            "image_url",
        ]
        read_only_fields = fields

    def get_image_url(self, item) -> str:
        return media.signed_url(item.version.asset)

    def get_line_total_cents(self, item) -> int:
        return item.unit_price_cents * item.quantity


class ShipmentInfoSerializer(serializers.Serializer):
    carrier = serializers.CharField()
    tracking_code = serializers.CharField()
    shipped_at = serializers.DateTimeField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)


def _latest_shipment(order):
    return order.shipments.order_by("-created_at").first()


class OrderListSerializer(GlobalIdSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "total_cents",
            "thumbnail_url",
            "item_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_thumbnail_url(self, order) -> str:
        item = order.items.select_related("version__asset").first()
        return media.signed_url(item.version.asset) if item else ""

    def get_item_count(self, order) -> int:
        return sum(item.quantity for item in order.items.all())


class OrderDetailSerializer(GlobalIdSerializer):
    """Só para o dono do pedido. CPF sempre mascarado."""

    items = OrderItemSerializer(many=True, read_only=True)
    cpf_masked = serializers.SerializerMethodField()
    charge = serializers.SerializerMethodField()
    shipment = serializers.SerializerMethodField()
    can_renew_payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "customer_email",
            "customer_name",
            "cpf_masked",
            "postal_code",
            "street",
            "address_number",
            "complement",
            "neighborhood",
            "city",
            "state",
            "items",
            "subtotal_cents",
            "shipping_cents",
            "total_cents",
            "shipping_service_name",
            "shipping_company",
            "delivery_days",
            "charge",
            "shipment",
            "can_renew_payment",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_cpf_masked(self, order) -> str:
        return f"***.***.***-{order.cpf_last_digits}"

    @extend_schema_field(ChargeSerializer(allow_null=True))
    def get_charge(self, order):
        charge = order.charges.order_by("-created_at").first()
        return ChargeSerializer(charge).data if charge else None

    @extend_schema_field(ShipmentInfoSerializer(allow_null=True))
    def get_shipment(self, order):
        shipment = _latest_shipment(order)
        return ShipmentInfoSerializer(shipment).data if shipment else None

    def get_can_renew_payment(self, order) -> bool:
        from payments.services import can_renew_payment

        return can_renew_payment(order)


class OrderTrackingSerializer(GlobalIdSerializer):
    """Acompanhamento por link, sem login: sem e-mail, CPF, telefone nem endereço completo."""

    items = OrderItemSerializer(many=True, read_only=True)
    shipment = serializers.SerializerMethodField()
    address_masked = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "items",
            "subtotal_cents",
            "shipping_cents",
            "total_cents",
            "shipping_service_name",
            "delivery_days",
            "address_masked",
            "shipment",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(ShipmentInfoSerializer(allow_null=True))
    def get_shipment(self, order):
        shipment = _latest_shipment(order)
        return ShipmentInfoSerializer(shipment).data if shipment else None

    def get_address_masked(self, order) -> str:
        return f"{order.city}/{order.state}, CEP {order.postal_code[:5]}-***"


class AddressSerializer(GlobalIdSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "postal_code",
            "street",
            "number",
            "complement",
            "neighborhood",
            "city",
            "state",
        ]
        read_only_fields = fields


class ResendTrackingSerializer(serializers.Serializer):
    email = serializers.EmailField()
