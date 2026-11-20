from rest_framework import serializers

from catalog.categories import Category


class ProductSizeSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="size.globalid")
    code = serializers.CharField(source="size.code")
    label = serializers.CharField(source="size.label")
    longest_side_mm = serializers.IntegerField(source="size.longest_side_mm")
    is_default = serializers.BooleanField(source="size.is_default")
    price_cents = serializers.IntegerField()


class ProductSerializer(serializers.Serializer):
    """Uma categoria vendida, com os tamanhos e preços dela."""

    category = serializers.ChoiceField(choices=Category.choices)
    label = serializers.CharField()
    from_price_cents = serializers.IntegerField()
    sizes = ProductSizeSerializer(many=True)
