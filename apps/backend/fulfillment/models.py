"""Produção: parceiros, tarefas por item, arquivos, envio e ganhos dos parceiros.

O cliente nunca vê quem produziu a peça. O parceiro não vê e-mail, CPF nem valores pagos pelo
cliente (RN-PAR-09). Ganhos do parceiro ficam aqui, separados do ledger de clientes.
"""

from django.conf import settings
from django.db import models

from catalog.categories import Category
from common.models import BaseModel


class Partner(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    name = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    origin_postal_code = models.CharField(max_length=8)
    is_internal = models.BooleanField(default=False)
    pix_key = models.CharField(max_length=140, blank=True)


class PartnerMember(BaseModel):
    """Login de um parceiro. É a fonte da autorização no app de parceiros."""

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="partner_memberships"
    )

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["partner", "user"], name="partner_member_uq")
        ]


class ProductionJob(BaseModel):
    class Status(models.TextChoices):
        UNASSIGNED = "unassigned", "Sem parceiro"
        ASSIGNED = "assigned", "Atribuída"
        IN_PRODUCTION = "in_production", "Em produção"
        READY_TO_SHIP = "ready_to_ship", "Pronta para envio"
        SHIPPED = "shipped", "Enviada"
        CANCELLED = "cancelled", "Cancelada"

    order_item = models.OneToOneField(
        "orders.OrderItem", on_delete=models.PROTECT, related_name="production_job"
    )
    partner = models.ForeignKey(
        Partner, null=True, blank=True, on_delete=models.PROTECT, related_name="jobs"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNASSIGNED)
    assigned_at = models.DateTimeField(null=True, blank=True)
    # Prazo de postagem: pagamento + prazo de produção em dias úteis (RN-PAR-04).
    post_by = models.DateField(null=True, blank=True)
    # Ganho do parceiro, congelado na atribuição (RN-PAR-06).
    payout_cents = models.PositiveIntegerField(null=True, blank=True)


class PartnerOrderGroup(models.TextChoices):
    """Onde o pedido aparece na fila do parceiro. Derivado dos jobs e da etiqueta."""

    TO_PRINT = "to_print", "Para imprimir"
    IN_PRODUCTION = "in_production", "Em produção"
    AWAITING_LABEL = "awaiting_label", "Aguardando etiqueta"
    TO_POST = "to_post", "Para postar"
    POSTED = "posted", "Postados"
    CANCELLED = "cancelled", "Cancelados"


class ProductionFile(BaseModel):
    """Arquivo de impressão do item. A versão mais alta é a que vale."""

    class Kind(models.TextChoices):
        THREE_MF = "3mf", "3MF"

    job = models.ForeignKey(ProductionJob, on_delete=models.CASCADE, related_name="files")
    kind = models.CharField(max_length=4, choices=Kind.choices, default=Kind.THREE_MF)
    version = models.PositiveSmallIntegerField(default=1)
    asset = models.ForeignKey("media.Asset", on_delete=models.PROTECT, related_name="+")

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["job", "kind", "version"], name="production_file_uq")
        ]


class Shipment(BaseModel):
    """Envio do pedido inteiro (RN-PAR-01). `shipped_at` é a postagem pelo parceiro."""

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="shipments")
    partner = models.ForeignKey(
        Partner, null=True, blank=True, on_delete=models.PROTECT, related_name="shipments"
    )
    carrier = models.CharField(max_length=64, blank=True)
    tracking_code = models.CharField(max_length=64, blank=True)
    label = models.ForeignKey(
        "media.Asset", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)


class ProductionPhoto(BaseModel):
    """Foto das peças prontas, enviada pelo parceiro ao marcar pronta (RN-PAR-12)."""

    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="production_photos"
    )
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="+")
    asset = models.ForeignKey("media.Asset", on_delete=models.PROTECT, related_name="+")

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]


class ProductionIssue(BaseModel):
    """Problema reportado pelo parceiro. Não muda o status do pedido."""

    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="production_issues"
    )
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="+")
    text = models.TextField()
    photo = models.ForeignKey(
        "media.Asset", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]


class PartnerRate(BaseModel):
    """Valor que o parceiro ganha por peça, por categoria e tamanho (RN-PAR-11)."""

    category = models.CharField(max_length=16, choices=Category.choices)
    size = models.ForeignKey("catalog.ProductSize", on_delete=models.PROTECT, related_name="+")
    amount_cents = models.PositiveIntegerField()

    class Meta(BaseModel.Meta):
        constraints = [models.UniqueConstraint(fields=["category", "size"], name="partner_rate_uq")]


class PartnerPayout(BaseModel):
    """Repasse feito por PIX fora do sistema e registrado pela equipe (RN-PAR-07)."""

    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="payouts")
    paid_on = models.DateField()
    amount_cents = models.PositiveIntegerField()
    receipt = models.ForeignKey(
        "media.Asset", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    note = models.TextField(blank=True)


class PartnerEntry(BaseModel):
    """Lançamento no extrato do parceiro. O valor nunca muda: correção é um novo ajuste.

    Um ganho nasce na postagem do item. Um repasse quita os lançamentos ligando-os a ele.
    """

    class Kind(models.TextChoices):
        EARNING = "earning", "Ganho"
        ADJUSTMENT = "adjustment", "Ajuste"

    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name="entries")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    job = models.ForeignKey(
        ProductionJob, null=True, blank=True, on_delete=models.PROTECT, related_name="entries"
    )
    # Com sinal: um ajuste pode ser débito.
    amount_cents = models.IntegerField()
    note = models.TextField(blank=True)
    payout = models.ForeignKey(
        PartnerPayout, null=True, blank=True, on_delete=models.PROTECT, related_name="entries"
    )

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["job"],
                condition=models.Q(kind="earning"),
                name="partner_entry_earning_uq",
            )
        ]
