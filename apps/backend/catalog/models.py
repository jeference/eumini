from django.db import models

from catalog.categories import Category
from common.models import BaseModel


class ProductSize(BaseModel):
    """Tamanho vendido. `longest_side_mm` é a maior dimensão da peça (RN-12)."""

    code = models.CharField(max_length=16, unique=True)
    label = models.CharField(max_length=40)
    longest_side_mm = models.PositiveIntegerField()
    package_weight_grams = models.PositiveIntegerField()
    package_width_cm = models.PositiveSmallIntegerField()
    package_height_cm = models.PositiveSmallIntegerField()
    package_length_cm = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["sort_order"]


class ProductPrice(BaseModel):
    """Preço por categoria e tamanho (RN-11). Só existem as combinações vendidas."""

    category = models.CharField(max_length=16, choices=Category.choices)
    size = models.ForeignKey(ProductSize, on_delete=models.PROTECT, related_name="prices")
    price_cents = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["category", "size"], name="product_price_uq")
        ]


class Filament(BaseModel):
    """Preparação: hoje as cores só orientam os prompts (catalog/prompts.py)."""

    name = models.CharField(max_length=40, unique=True)
    hex_code = models.CharField(max_length=7)
    brand = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
