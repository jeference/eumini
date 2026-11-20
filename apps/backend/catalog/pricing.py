"""Preço por categoria e tamanho (RN-10, RN-11). O servidor é a única fonte do preço."""

from __future__ import annotations

from catalog.categories import Category
from catalog.models import ProductPrice, ProductSize


def price_for(category: str, size: ProductSize) -> int | None:
    """Preço em centavos, ou None se o tamanho não é vendido nessa categoria."""
    if category not in Category.values or not size.is_active:
        return None
    return (
        ProductPrice.objects.filter(category=category, size=size, is_active=True)
        .values_list("price_cents", flat=True)
        .first()
    )


def catalog() -> list[dict]:
    """Cada categoria com os tamanhos à venda, do menor para o maior, e o preço "a partir de"."""
    prices = (
        ProductPrice.objects.filter(is_active=True, size__is_active=True)
        .select_related("size")
        .order_by("size__sort_order")
    )
    by_category: dict[str, list[dict]] = {category: [] for category in Category.values}
    for price in prices:
        by_category[price.category].append({"size": price.size, "price_cents": price.price_cents})
    return [
        {
            "category": category,
            "label": Category(category).label,
            "from_price_cents": min((s["price_cents"] for s in sizes), default=None),
            "sizes": sizes,
        }
        for category, sizes in by_category.items()
        if sizes
    ]
