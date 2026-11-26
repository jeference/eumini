from django.db import migrations, models


class Migration(migrations.Migration):
    """Desfaz a 0004: os temas saíram e o pedido em texto no envio voltou."""

    dependencies = [
        ("creations", "0004_theme"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="creationinput",
            name="theme",
        ),
        migrations.AddField(
            model_name="creationinput",
            name="text",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
    ]
