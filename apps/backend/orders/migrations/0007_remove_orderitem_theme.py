from django.db import migrations, models


class Migration(migrations.Migration):
    """Desfaz a 0006: os temas saíram e o snapshot do pedido em texto voltou."""

    dependencies = [
        ("orders", "0006_orderitem_theme"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="orderitem",
            name="theme",
        ),
        migrations.AddField(
            model_name="orderitem",
            name="prompt_text",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
    ]
