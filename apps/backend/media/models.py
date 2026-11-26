from django.conf import settings
from django.db import models

from common.models import AppendOnlyModel, BaseModel


class Asset(BaseModel):
    """Um arquivo no storage. O arquivo pode ser expurgado; o registro permanece."""

    class Kind(models.TextChoices):
        ORIGINAL = "original", "Foto original do cliente"
        PHOTO = "photo", "Foto do cliente"
        IMAGE = "image", "Imagem gerada"
        PRODUCTION = "production", "Arquivo de produção"
        PARTNER_PHOTO = "partner_photo", "Foto enviada pelo parceiro"

    key = models.CharField(max_length=255, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    mime = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    purged_at = models.DateTimeField(null=True, blank=True)


class AssetDownload(AppendOnlyModel):
    """Registro de cada download de arquivo de produção (RN-PAR-10)."""

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="downloads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    # De onde veio o download, para auditoria (ex.: "partner_order:<id>").
    context = models.CharField(max_length=80)
