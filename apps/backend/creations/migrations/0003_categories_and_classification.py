"""Categorias, classificação, lista de espera; o estilo sai (RN-30 a RN-38)."""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


_STATUS = {"image_failed": "failed"}
_KINDS = {"photo_to_image": "generate", "image_edit": "edit"}


def rename_values(apps, schema_editor):
    creation_model = apps.get_model("creations", "Creation")
    task_model = apps.get_model("creations", "ProviderTask")
    for old, new in _STATUS.items():
        creation_model.objects.filter(status=old).update(status=new)
    for old, new in _KINDS.items():
        task_model.objects.filter(kind=old).update(kind=new)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("creations", "0002_creationinput_original_photo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="creation",
            name="style",
        ),
        migrations.AddField(
            model_name="creation",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("person", "Pessoa"),
                    ("pet", "Pet"),
                    ("couple", "Casal"),
                    ("person_pet", "Pessoa + Pet"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="creation",
            name="rejection_reason",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="creation",
            name="requested_category",
            field=models.CharField(
                choices=[
                    ("person", "Pessoa"),
                    ("pet", "Pet"),
                    ("couple", "Casal"),
                    ("person_pet", "Pessoa + Pet"),
                ],
                default="person",
                max_length=16,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="imageversion",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("person", "Pessoa"),
                    ("pet", "Pet"),
                    ("couple", "Casal"),
                    ("person_pet", "Pessoa + Pet"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="imageversion",
            name="rejection_reason",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterField(
            model_name="creation",
            name="status",
            field=models.CharField(
                choices=[
                    ("classifying", "Lendo a foto"),
                    ("rejected", "Foto não aceita"),
                    ("generating_image", "Gerando imagem"),
                    ("ready", "Pronta para comprar"),
                    ("failed", "Não deu certo"),
                ],
                default="classifying",
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="providertask",
            name="kind",
            field=models.CharField(
                choices=[
                    ("classify", "Classificação"),
                    ("generate", "Foto para imagem"),
                    ("edit", "Edição de imagem"),
                ],
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="quotareservation",
            name="kind",
            field=models.CharField(
                choices=[
                    ("image", "Geração 2D"),
                    ("edit", "Edição"),
                    ("classify", "Classificação da foto"),
                ],
                max_length=8,
            ),
        ),
        migrations.CreateModel(
            name="Classification",
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
                    "requested_category",
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
                ("result", models.CharField(max_length=32)),
                (
                    "decision",
                    models.CharField(
                        choices=[("accepted", "Aceita"), ("rejected", "Recusada")], max_length=8
                    ),
                ),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("probabilities", models.JSONField(blank=True, default=dict)),
                ("character_probability", models.FloatField(blank=True, null=True)),
                ("model_name", models.CharField(max_length=64)),
                ("question_set_version", models.CharField(max_length=16)),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
                (
                    "creation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="classifications",
                        to="creations.creation",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="creations.providertask",
                    ),
                ),
                (
                    "version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="creations.imageversion",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="WaitlistEntry",
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
                ("email", models.EmailField(max_length=254)),
                ("reason", models.CharField(max_length=32)),
                ("consent_version", models.CharField(max_length=16)),
                ("consented_at", models.DateTimeField()),
                ("notified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "classification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="waitlist_entries",
                        to="creations.classification",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "visitor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="accounts.visitor",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="classification",
            index=models.Index(
                fields=["result", "-created_at"], name="creations_c_result_b9724f_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="waitlistentry",
            constraint=models.UniqueConstraint(
                fields=("email", "reason"), name="waitlist_email_reason_uq"
            ),
        ),
        migrations.RunPython(rename_values, migrations.RunPython.noop),
    ]
