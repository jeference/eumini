from __future__ import annotations

import io

import pytest
from PIL import ExifTags, Image, ImageCms

from common.exceptions import GuardFailed
from media import services
from media.models import Asset


def test_signed_url_serves_file_and_rejects_tampering(anon):
    asset = services.store(data=b"conteudo", kind=Asset.Kind.IMAGE, mime="image/png")
    url = services.signed_url(asset)
    response = anon.get(url)
    assert response.status_code == 200
    assert response.content == b"conteudo"
    assert anon.get(url[:-3] + "xx/").status_code == 404


def test_purged_asset_has_no_url():
    asset = services.store(data=b"x", kind=Asset.Kind.PHOTO, mime="image/png")
    services.purge(asset)
    assert services.signed_url(asset) == ""


def _photo_with_metadata(image_format: str, size=(2000, 1000)) -> bytes:
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "Camera do cliente"
    exif[ExifTags.Base.Orientation] = 6
    exif.get_ifd(ExifTags.IFD.GPSInfo)[ExifTags.GPS.GPSLatitudeRef] = "S"
    icc_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(
        buffer, format=image_format, exif=exif, icc_profile=icc_profile
    )
    return buffer.getvalue()


def test_prepare_photo_limits_normalized_size_and_validates_type():
    buffer = io.BytesIO()
    Image.new("RGB", (2000, 1000)).save(buffer, format="JPEG")
    normalized = Image.open(io.BytesIO(services.prepare_photo(buffer.getvalue()).normalized))
    assert normalized.format == "PNG"
    assert max(normalized.size) == 1024
    with pytest.raises(GuardFailed):
        services.prepare_photo(b"isto nao e imagem")
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, format="GIF")
    with pytest.raises(GuardFailed):
        services.prepare_photo(gif.getvalue())


def test_prepare_photo_rejects_huge_resolution_before_decoding(monkeypatch):
    monkeypatch.setattr(services, "PHOTO_MAX_PIXELS", 100 * 100)
    buffer = io.BytesIO()
    Image.new("RGB", (101, 100)).save(buffer, format="PNG")
    with pytest.raises(GuardFailed) as exc:
        services.prepare_photo(buffer.getvalue())
    assert exc.value.code == "photo_too_large"


def test_prepare_photo_enlarges_small_photos_for_the_classifier():
    buffer = io.BytesIO()
    Image.new("RGB", (231, 300)).save(buffer, format="PNG")
    prepared = services.prepare_photo(buffer.getvalue())
    normalized = Image.open(io.BytesIO(prepared.normalized))
    assert min(normalized.size) == 280
    assert Image.open(io.BytesIO(prepared.original)).size == (231, 300)


@pytest.mark.parametrize(
    ("image_format", "mime"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_prepare_photo_keeps_original_without_metadata(image_format, mime):
    raw = _photo_with_metadata(image_format)
    assert Image.open(io.BytesIO(raw)).getexif().get_ifd(ExifTags.IFD.GPSInfo)

    prepared = services.prepare_photo(raw)

    original = Image.open(io.BytesIO(prepared.original))
    assert prepared.original_mime == mime
    assert original.format == image_format
    # A orientação do EXIF é aplicada aos pixels antes de ser descartada.
    assert original.size == (1000, 2000)
    assert original.info.get("icc_profile")
    for data in (prepared.original, prepared.normalized):
        image = Image.open(io.BytesIO(data))
        assert not image.getexif()
        assert b"Camera do cliente" not in data
