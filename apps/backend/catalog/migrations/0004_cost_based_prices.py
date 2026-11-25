"""Tabela de preços da RN-11 refeita a partir da amostragem de custo de impressão.

Combinação fora da tabela deixa de ser vendida: a linha é apagada.
"""

from django.db import migrations

# Em centavos. Combinação ausente = tamanho não vendido na categoria.
_PRICES = {
    "person": {"6cm": 12990, "8cm": 15990, "10cm": 18990},
    "pet": {"4cm": 12990, "6cm": 16990, "8cm": 22990},
    "couple": {"4cm": 12990, "6cm": 17990, "8cm": 23990},
    "person_pet": {"4cm": 12990, "6cm": 16990, "8cm": 21990},
}


def update_prices(apps, schema_editor):
    size_model = apps.get_model("catalog", "ProductSize")
    price_model = apps.get_model("catalog", "ProductPrice")
    sizes = {size.code: size for size in size_model.objects.all()}
    keep = []
    for category, prices in _PRICES.items():
        for code, cents in prices.items():
            price, _ = price_model.objects.update_or_create(
                category=category,
                size=sizes[code],
                defaults={"price_cents": cents, "is_active": True},
            )
            keep.append(price.pk)
    price_model.objects.exclude(pk__in=keep).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_product_price"),
    ]

    operations = [
        migrations.RunPython(update_prices, migrations.RunPython.noop),
    ]
