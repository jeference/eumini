"""O item do pedido congela a categoria; o estilo sai."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_alter_order_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="orderitem",
            name="style",
        ),
        migrations.AddField(
            model_name="orderitem",
            name="category",
            field=models.CharField(default="", max_length=16),
            preserve_default=False,
        ),
    ]
