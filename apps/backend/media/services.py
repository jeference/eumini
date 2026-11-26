from __future__ import annotations

import hashlib
import io
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from common.exceptions import GuardFailed
from integrations.adapters.typesafe_questions import MIN_SIDE as PHOTO_MIN_SIDE
from integrations.ports import get_media_storage_port
from media.models import Asset

_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "model/3mf": "3mf",
}
_PHOTO_MIMES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
# HEIC (iPhone, alguns Android) e AVIF são aceitos, mas o original vira JPEG, ou PNG se tiver
# transparência: qualquer ferramenta lê, e os navegadores fora o Safari não mostram HEIC.
# MPO é o JPEG que o iPhone envia com uma segunda imagem embutida (o mapa de HDR): fica só a
# foto principal, num JPEG comum.
_CONVERTED_FORMATS = ("HEIF", "AVIF", "MPO")
_ORIGINAL_SAVE_OPTIONS = {"PNG": {}, "JPEG": {"quality": 95}, "WEBP": {"quality": 95}}
PHOTO_FORMATS_MESSAGE = "Envie uma foto em JPG, PNG, WEBP, HEIC ou AVIF."
# Depois da conversão a imagem é RGB(A): um perfil de cor de outro espaço a deixaria errada.
_RGB_COMPATIBLE_MODES = ("RGB", "RGBA", "P")
# Teto de resolução da foto: 50 MP cobre as câmeras de celular comuns (12 a 50 MP) e limita a
# memória de cada envio, que é decodificado e copiado algumas vezes.
PHOTO_MAX_PIXELS = 50_000_000


@dataclass(frozen=True)
class PreparedPhoto:
    original: bytes
    original_mime: str
    normalized: bytes


def store(*, data: bytes, kind: str, mime: str) -> Asset:
    key = f"{kind}/{uuid.uuid4().hex}.{_EXTENSIONS.get(mime, 'bin')}"
    get_media_storage_port().put(key=key, data=data, content_type=mime)
    return Asset.objects.create(
        key=key,
        kind=kind,
        mime=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def read(asset: Asset) -> bytes:
    data = get_media_storage_port().get(key=asset.key)
    if data is None:
        raise GuardFailed("Arquivo indisponível.", code="asset_missing")
    return data


def signed_url(asset: Asset | None, *, filename: str = "") -> str:
    """URL temporária do arquivo. Com `filename`, abre como download com esse nome."""
    if asset is None or asset.purged_at is not None:
        return ""
    return get_media_storage_port().signed_url(
        key=asset.key,
        ttl_seconds=settings.BUSINESS["SIGNED_URL_TTL_SECONDS"],
        content_type=asset.mime,
        filename=filename,
    )


def extension_of(asset: Asset) -> str:
    return _EXTENSIONS.get(asset.mime, "bin")


def purge(asset: Asset) -> None:
    """Apaga o arquivo e mantém o registro."""
    if asset.purged_at is not None:
        return
    get_media_storage_port().delete(key=asset.key)
    asset.purged_at = timezone.now()
    asset.save(update_fields=["purged_at", "updated_at"])


def prepare_photo(raw: bytes) -> PreparedPhoto:
    """Valida o tipo real da foto e devolve as duas versões guardadas, ambas sem metadados.

    O original mantém resolução e formato. A normalizada é o PNG de até IMAGE_SIZE usado na IA.
    """
    if len(raw) > settings.BUSINESS["PHOTO_MAX_BYTES"]:
        raise GuardFailed("A foto deve ter no máximo 10 MB.", code="photo_too_large")
    try:
        image = Image.open(io.BytesIO(raw))
        if image.format not in _PHOTO_MIMES and image.format not in _CONVERTED_FORMATS:
            raise GuardFailed(
                f"{PHOTO_FORMATS_MESSAGE} Imagem enviada em {image.format}.", code="photo_invalid"
            )
        # O open só lê o cabeçalho. Um arquivo pequeno pode declarar centenas de milhões de
        # pixels e ocupar gigabytes ao ser decodificado: recusa antes do load.
        if image.width * image.height > PHOTO_MAX_PIXELS:
            raise GuardFailed("A foto tem resolução grande demais.", code="photo_too_large")
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise GuardFailed("Não conseguimos ler essa foto.", code="photo_invalid") from exc
    source_format = image.format
    icc_profile = image.info.get("icc_profile") if image.mode in _RGB_COMPATIBLE_MODES else None
    # No HEIC o leitor já aplica a rotação e zera a orientação do EXIF: aqui não gira de novo.
    image = ImageOps.exif_transpose(image)
    has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
    if source_format in _CONVERTED_FORMATS:
        source_format = "PNG" if has_alpha else "JPEG"
    image = image.convert("RGBA" if has_alpha else "RGB")
    # Uma imagem nova recebe só os pixels: EXIF (com GPS), XMP e afins ficam para trás.
    clean = Image.new(image.mode, image.size)
    clean.paste(image)

    original = _encode(
        clean, source_format, icc_profile=icc_profile, **_ORIGINAL_SAVE_OPTIONS[source_format]
    )
    max_side = settings.BUSINESS["IMAGE_SIZE"]
    clean.thumbnail((max_side, max_side))
    # O classificador recusa imagens com um lado pequeno demais: amplia até o mínimo.
    if min(clean.size) < PHOTO_MIN_SIDE:
        scale = PHOTO_MIN_SIDE / min(clean.size)
        clean = clean.resize(
            (round(clean.width * scale), round(clean.height * scale)), Image.Resampling.LANCZOS
        )
    return PreparedPhoto(
        original=original,
        original_mime=_PHOTO_MIMES[source_format],
        normalized=_encode(clean, "PNG", icc_profile=icc_profile),
    )


def _encode(image: Image.Image, image_format: str, **options) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **options)
    return buffer.getvalue()
