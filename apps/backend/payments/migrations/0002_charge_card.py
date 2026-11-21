from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="charge",
            name="method",
            field=models.CharField(
                choices=[("PIX", "Pix"), ("CARD", "Cartão de crédito")],
                default="PIX",
                max_length=8,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="charge",
            name="card_brand",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="charge",
            name="card_last_four",
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AlterField(
            model_name="charge",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
