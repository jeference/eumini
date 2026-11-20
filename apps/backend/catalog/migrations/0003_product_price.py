"""Preço por categoria e tamanho (RN-11). O tamanho perde o preço único."""

import django.db.models.deletion
import uuid
from django.db import migrations, models

# Tabela da RN-11 [Proposta], em centavos. Combinação ausente = tamanho não vendido na categoria.
_PRICES = {
    "person": {"6cm": 9990, "8cm": 14490, "10cm": 18990, "12cm": 22990},
    "pet": {"4cm": 6590, "6cm": 10990, "8cm": 15990},
    "person_pet": {"6cm": 12990, "8cm": 18990, "10cm": 24990, "12cm": 29990},
    "couple": {"6cm": 14990, "8cm": 21990},
}


def seed_prices(apps, schema_editor):
    size_model = apps.get_model("catalog", "ProductSize")
    price_model = apps.get_model("catalog", "ProductPrice")
    sizes = {size.code: size for size in size_model.objects.all()}
    for category, prices in _PRICES.items():
        for code, cents in prices.items():
            price_model.objects.create(category=category, size=sizes[code], price_cents=cents)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_seed"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="productsize",
            name="price_cents",
        ),
        migrations.CreateModel(
            name="ProductPrice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("globalid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("person", "Pessoa"),
                            ("pet", "Pet"),
                            ("couple", "Casal"),
                            ("person_pet", "Pessoa + Pet"),
                        ],
                        max_length=16,
                    ),
                ),
                ("price_cents", models.PositiveIntegerField()),
                ("is_active", models.BooleanField(default=True)),
                (
                    "size",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="prices",
                        to="catalog.productsize",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
                "constraints": [
                    models.UniqueConstraint(fields=("category", "size"), name="product_price_uq")
                ],
            },
        ),
        migrations.RunPython(seed_prices, migrations.RunPython.noop),
    ]
