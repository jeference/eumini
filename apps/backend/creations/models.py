"""Uma criação: a entrada do cliente, as versões de imagem e cada tarefa de IA."""

from django.conf import settings
from django.db import models

from catalog.categories import Category
from catalog.themes import Theme
from common.models import BaseModel

# Categoria vendida ou motivo de recusa: o resultado de uma classificação.
_RESULT_MAX_LENGTH = 32


class Creation(BaseModel):
    class Status(models.TextChoices):
        CLASSIFYING = "classifying", "Lendo a foto"
        REJECTED = "rejected", "Foto não aceita"
        GENERATING_IMAGE = "generating_image", "Gerando imagem"
        READY = "ready", "Pronta para comprar"
        FAILED = "failed", "Não deu certo"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="creations",
    )
    visitor = models.ForeignKey(
        "accounts.Visitor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="creations",
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CLASSIFYING)
    # A página de entrada é só uma sugestão: quem decide a categoria é o classificador (RN-32).
    requested_category = models.CharField(max_length=16, choices=Category.choices)
    category = models.CharField(max_length=16, choices=Category.choices, blank=True)
    rejection_reason = models.CharField(max_length=_RESULT_MAX_LENGTH, blank=True)
    current_version = models.ForeignKey(
        "creations.ImageVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    last_error_code = models.CharField(max_length=32, blank=True)
    last_error_message = models.CharField(max_length=255, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["user", "-created_at"])]


class CreationInput(BaseModel):
    creation = models.OneToOneField(Creation, on_delete=models.CASCADE, related_name="input")
    theme = models.CharField(max_length=20, choices=Theme.choices, blank=True)
    photo = models.ForeignKey("media.Asset", on_delete=models.PROTECT, related_name="+")
    original_photo = models.ForeignKey(
        "media.Asset", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    terms_version = models.CharField(max_length=16, blank=True)


class ProviderTask(BaseModel):
    """Uma chamada a um provedor de IA. É também a fila do worker."""

    class Kind(models.TextChoices):
        # Sem `source_version`, classifica a foto; com ela, a versão gerada.
        CLASSIFY = "classify", "Classificação"
        GENERATE = "generate", "Foto para imagem"
        EDIT = "edit", "Edição de imagem"

    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Em execução"
        SUCCEEDED = "succeeded", "Concluída"
        FAILED = "failed", "Falhou"
        CANCELLED = "cancelled", "Cancelada"

    creation = models.ForeignKey(Creation, on_delete=models.CASCADE, related_name="tasks")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    source_version = models.ForeignKey(
        "creations.ImageVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    instruction = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=32, blank=True)
    model_name = models.CharField(max_length=64, blank=True)
    rendered_prompt = models.TextField(blank=True)
    prompt_version = models.CharField(max_length=16, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=32, blank=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["status", "next_attempt_at"])]


class ImageVersion(BaseModel):
    class Origin(models.TextChoices):
        PHOTO = "photo", "Foto"
        EDIT = "edit", "Edição"

    creation = models.ForeignKey(Creation, on_delete=models.CASCADE, related_name="versions")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    number = models.PositiveSmallIntegerField()
    origin = models.CharField(max_length=8, choices=Origin.choices)
    instruction = models.CharField(max_length=255, blank=True)
    asset = models.ForeignKey("media.Asset", on_delete=models.PROTECT, related_name="+")
    task = models.ForeignKey(
        ProviderTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # A classificação da versão define a categoria e o preço (RN-34). Os dois vazios: ainda não
    # foi classificada. Com motivo de recusa, a versão não pode ser comprada.
    category = models.CharField(max_length=16, choices=Category.choices, blank=True)
    rejection_reason = models.CharField(max_length=_RESULT_MAX_LENGTH, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["creation", "number"], name="version_number_uq")
        ]


class QuotaReservation(BaseModel):
    """Cota reservada ao iniciar e consumida só no sucesso (RN-02)."""

    class Kind(models.TextChoices):
        IMAGE = "image", "Geração 2D"
        EDIT = "edit", "Edição"
        CLASSIFY = "classify", "Classificação da foto"

    class State(models.TextChoices):
        RESERVED = "reserved", "Reservada"
        CONSUMED = "consumed", "Consumida"
        RELEASED = "released", "Liberada"

    actor_key = models.CharField(max_length=32)
    ip_hash = models.CharField(max_length=64, blank=True)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    day = models.DateField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.RESERVED)
    task = models.OneToOneField(
        ProviderTask, on_delete=models.CASCADE, related_name="quota_reservation"
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["actor_key", "kind", "day"]),
            models.Index(fields=["ip_hash", "kind", "day"]),
        ]


class Classification(BaseModel):
    """Toda classificação, da foto ou de uma versão (RN-36)."""

    class Decision(models.TextChoices):
        ACCEPTED = "accepted", "Aceita"
        REJECTED = "rejected", "Recusada"

    creation = models.ForeignKey(Creation, on_delete=models.CASCADE, related_name="classifications")
    version = models.ForeignKey(
        ImageVersion, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    task = models.ForeignKey(
        ProviderTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    requested_category = models.CharField(max_length=16, choices=Category.choices)
    result = models.CharField(max_length=_RESULT_MAX_LENGTH)
    decision = models.CharField(max_length=8, choices=Decision.choices)
    confidence = models.FloatField(null=True, blank=True)
    probabilities = models.JSONField(default=dict, blank=True)
    character_probability = models.FloatField(null=True, blank=True)
    model_name = models.CharField(max_length=64)
    question_set_version = models.CharField(max_length=16)
    ip_hash = models.CharField(max_length=64, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["result", "-created_at"])]


class WaitlistEntry(BaseModel):
    """Quem foi recusado e quer ser avisado quando a categoria existir (RN-37)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    visitor = models.ForeignKey(
        "accounts.Visitor", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    email = models.EmailField()
    classification = models.ForeignKey(
        Classification, on_delete=models.PROTECT, related_name="waitlist_entries"
    )
    reason = models.CharField(max_length=_RESULT_MAX_LENGTH)
    consent_version = models.CharField(max_length=16)
    consented_at = models.DateTimeField()
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["email", "reason"], name="waitlist_email_reason_uq")
        ]
