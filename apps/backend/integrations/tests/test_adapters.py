"""Adapters reais, com as respostas documentadas pelos fornecedores simuladas (sem rede)."""

from __future__ import annotations

import base64
import io
import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses
from botocore.response import StreamingBody
from botocore.stub import Stubber

from common.exceptions import PaymentDeclined, ServiceBusy, UpstreamUnavailable
from integrations.adapters.abacatepay import AbacatePayAdapter
from integrations.adapters.media_s3 import S3MediaAdapter
from integrations.adapters.melhor_envio import MelhorEnvioAdapter
from integrations.adapters.runware import RunwareImageGenerationAdapter
from integrations.adapters.typesafe import TypeSafeClassificationAdapter
from integrations.adapters.viacep import ViaCepAdapter
from integrations.models import IntegrationCredential
from integrations.ports import (
    ContentRefused,
    GatewayCustomer,
    ProviderPermanentError,
    ProviderTemporaryError,
    ShippingItem,
)

RUNWARE = "https://api.runware.ai/v1"
PNG = base64.b64encode(b"imagem").decode()
GPT = "openai:gpt-image@2"


@pytest.fixture
def _keys(settings):
    settings.RUNWARE_API_KEY = "chave"
    settings.JEV_API_KEY = "chave"
    settings.JEV_MODEL = "jev-1.14.0"
    settings.ABACATE_PAY_API_KEY = "chave"
    settings.ABACATE_PAY_BASE_URL = "https://api.abacatepay.com/v2"
    settings.MELHOR_ENVIO_ACCESS_TOKEN = "token"
    settings.MELHOR_ENVIO_REFRESH_TOKEN = "refresh"
    settings.MELHOR_ENVIO_BASE_URL = "https://sandbox.melhorenvio.com.br"


# --- Runware ---


@responses.activate
def test_runware_edit_returns_bytes_and_cost(_keys):
    responses.post(
        RUNWARE,
        json={"data": [{"imageDataURI": f"data:image/png;base64,{PNG}", "cost": 0.015}]},
    )
    adapter = RunwareImageGenerationAdapter()
    result = adapter.edit(image=b"foto", prompt="um gato", size=1024, model=GPT)
    assert result.data == b"imagem"
    assert result.cost_usd == 0.015
    body = json.loads(responses.calls[0].request.body)[0]
    assert body["taskType"] == "imageInference"
    assert body["positivePrompt"] == "um gato"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer chave"


@responses.activate
def test_runware_edit_sends_reference_image(_keys):
    responses.post(RUNWARE, json={"data": [{"imageDataURI": f"data:image/png;base64,{PNG}"}]})
    RunwareImageGenerationAdapter().edit(image=b"foto", prompt="azul", size=1024, model=GPT)
    body = json.loads(responses.calls[0].request.body)[0]
    assert body["inputs"]["referenceImages"][0].startswith("data:image/png;base64,")


@responses.activate
def test_runware_uses_the_requested_model(_keys, settings):
    settings.RUNWARE_IMAGE_MODEL = GPT
    settings.RUNWARE_IMAGE_FALLBACK_MODEL = "google:4@2"
    adapter = RunwareImageGenerationAdapter()
    assert adapter.models == (GPT, "google:4@2")
    responses.post(RUNWARE, json={"data": [{"imageDataURI": f"data:image/png;base64,{PNG}"}]})
    adapter.edit(image=b"foto", prompt="azul", size=1024, model="google:4@2")
    assert json.loads(responses.calls[0].request.body)[0]["model"] == "google:4@2"


@responses.activate
def test_runware_refusal_becomes_content_refused(_keys):
    responses.post(
        RUNWARE,
        json={"data": [], "errors": [{"code": "x", "message": "Rejected by the safety system"}]},
    )
    with pytest.raises(ContentRefused):
        RunwareImageGenerationAdapter().edit(image=b"foto", prompt="x", size=1024, model=GPT)


@responses.activate
def test_runware_other_error_is_permanent(_keys):
    responses.post(
        RUNWARE, json={"data": [], "errors": [{"code": "x", "message": "Invalid model"}]}
    )
    with pytest.raises(ProviderPermanentError):
        RunwareImageGenerationAdapter().edit(image=b"foto", prompt="x", size=1024, model=GPT)


@responses.activate
def test_runware_network_and_5xx_are_temporary(_keys):
    responses.post(RUNWARE, body=requests.ConnectionError("fora"))
    with pytest.raises(ProviderTemporaryError):
        RunwareImageGenerationAdapter().edit(image=b"foto", prompt="x", size=1024, model=GPT)
    responses.replace(responses.POST, RUNWARE, json={"data": []}, status=503)
    with pytest.raises(ProviderTemporaryError):
        RunwareImageGenerationAdapter().edit(image=b"foto", prompt="x", size=1024, model=GPT)


@responses.activate
def test_runware_missing_image_is_permanent(_keys):
    responses.post(RUNWARE, json={"data": [{}]})
    with pytest.raises(ProviderPermanentError):
        RunwareImageGenerationAdapter().edit(image=b"foto", prompt="x", size=1024, model=GPT)


# --- AbacatePay ---

ABACATE = "https://api.abacatepay.com/v2"


@responses.activate
def test_abacatepay_create_charge(_keys):
    responses.post(
        f"{ABACATE}/transparents/create",
        json={
            "data": {
                "id": "pix_char_1",
                "status": "PENDING",
                "brCode": "000201",
                "brCodeBase64": "data:image/png;base64,abc",
                "expiresAt": "2026-11-04T12:00:00Z",
            },
            "success": True,
            "error": None,
        },
    )
    charge = AbacatePayAdapter().create_charge(
        method="PIX",
        amount=12990,
        reference="ref",
        description="Pedido EuMini EM123",
        expires_in_seconds=1800,
    )
    assert charge.external_id == "pix_char_1"
    assert charge.status == "pending"
    assert charge.pix_br_code == "000201"
    body = json.loads(responses.calls[0].request.body)
    assert body["method"] == "PIX"
    assert body["data"]["amount"] == 12990
    assert "customer" not in body["data"]


@pytest.mark.parametrize(
    ("raw", "mapped"),
    [
        ("PAID", "paid"),
        ("REDEEMED", "paid"),
        ("APPROVED", "pending"),
        ("UNDER_DISPUTE", "pending"),
        ("EXPIRED", "expired"),
        ("REFUNDED", "refunded"),
        ("NOVO_STATUS", "pending"),
    ],
)
@responses.activate
def test_abacatepay_only_paid_settles(_keys, raw, mapped):
    responses.get(f"{ABACATE}/transparents/check", json={"data": {"status": raw}, "success": True})
    assert AbacatePayAdapter().get_charge_status(external_id="pix", method="PIX") == mapped


@responses.activate
def test_abacatepay_errors_are_upstream_unavailable(_keys):
    responses.post(f"{ABACATE}/transparents/create", json={"error": "x", "success": False})
    with pytest.raises(UpstreamUnavailable):
        AbacatePayAdapter().create_charge(
            method="PIX", amount=1, reference="r", description="d", expires_in_seconds=1
        )
    responses.get(f"{ABACATE}/transparents/check", status=500)
    with pytest.raises(UpstreamUnavailable):
        AbacatePayAdapter().get_charge_status(external_id="pix", method="PIX")


_CUSTOMER = GatewayCustomer(
    name="Ana Souza", email="ana@exemplo.com", tax_id="52998224725", cellphone="11999998888"
)


@responses.activate
def test_abacatepay_card_charge_approved_is_paid(_keys):
    responses.post(
        f"{ABACATE}/transparents/create",
        json={
            "data": {"id": "card_1", "status": "APPROVED", "brand": "VISA", "lastFour": "4242"},
            "success": True,
            "error": None,
        },
    )
    charge = AbacatePayAdapter().create_charge(
        method="CARD",
        amount=12990,
        reference="ref",
        description="Pedido EuMini EM123",
        card_token="ctok_abc",
        customer=_CUSTOMER,
    )
    assert charge.status == "paid"
    assert (charge.card_brand, charge.card_last_four) == ("VISA", "4242")
    body = json.loads(responses.calls[0].request.body)
    assert body["method"] == "CARD"
    assert body["data"]["token"] == "ctok_abc"
    assert "expiresIn" not in body["data"]
    assert body["data"]["customer"] == {
        "name": "Ana Souza",
        "email": "ana@exemplo.com",
        "taxId": "52998224725",
        "cellphone": "11999998888",
    }


@pytest.mark.parametrize("http_status", [400, 422])
@responses.activate
def test_abacatepay_card_decline_is_payment_declined(_keys, http_status):
    responses.post(
        f"{ABACATE}/transparents/create",
        status=http_status,
        json={"data": None, "success": False, "error": "Cartão recusado"},
    )
    with pytest.raises(PaymentDeclined):
        AbacatePayAdapter().create_charge(
            method="CARD",
            amount=12990,
            reference="r",
            description="d",
            card_token="ctok_abc",
            customer=_CUSTOMER,
        )


@responses.activate
def test_abacatepay_card_auth_error_is_upstream(_keys):
    responses.post(f"{ABACATE}/transparents/create", status=401, json={"success": False})
    with pytest.raises(UpstreamUnavailable):
        AbacatePayAdapter().create_charge(
            method="CARD",
            amount=12990,
            reference="r",
            description="d",
            card_token="ctok_abc",
            customer=_CUSTOMER,
        )


@responses.activate
def test_abacatepay_card_status_uses_get(_keys):
    responses.get(
        f"{ABACATE}/transparents/get", json={"data": {"status": "APPROVED"}, "success": True}
    )
    assert AbacatePayAdapter().get_charge_status(external_id="card_1", method="CARD") == "paid"


# --- Melhor Envio ---

CALCULATE = "https://sandbox.melhorenvio.com.br/api/v2/me/shipment/calculate"
ITEM = ShippingItem("i", 12, 10, 12, 0.15, 12990, 2)


@responses.activate
def test_melhor_envio_uses_custom_values_and_skips_errors(_keys):
    responses.post(
        CALCULATE,
        json=[
            {
                "id": 2,
                "name": "SEDEX",
                "price": "40.00",
                "custom_price": "35.50",
                "custom_delivery_time": 3,
                "delivery_time": 2,
                "company": {"name": "Correios"},
            },
            {"id": 3, "name": "Jadlog", "error": "Sem atendimento"},
            {
                "id": 1,
                "name": "PAC",
                "custom_price": "20.10",
                "custom_delivery_time": 8,
                "company": {"name": "Correios"},
            },
        ],
    )
    options = MelhorEnvioAdapter().quote(
        origin_postal_code="01001000", destination_postal_code="01310100", items=[ITEM]
    )
    assert [option.service_name for option in options] == ["PAC", "SEDEX"]
    assert options[0].price_cents == 2010
    assert options[1].delivery_days == 3
    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer token"
    assert "User-Agent" in request.headers
    body = json.loads(request.body)
    assert body["from"]["postal_code"] == "01001000"
    assert body["products"][0]["insurance_value"] == 129.9
    assert body["products"][0]["quantity"] == 2


@responses.activate
def test_melhor_envio_invalid_cep_returns_no_options(_keys):
    responses.post(CALCULATE, json={"message": "invalid"}, status=422)
    assert (
        MelhorEnvioAdapter().quote(
            origin_postal_code="1", destination_postal_code="2", items=[ITEM]
        )
        == []
    )


@responses.activate
def test_melhor_envio_down_is_service_busy(_keys):
    responses.post(CALCULATE, status=500)
    with pytest.raises(ServiceBusy) as error:
        MelhorEnvioAdapter().quote(
            origin_postal_code="1", destination_postal_code="2", items=[ITEM]
        )
    assert error.value.code == "shipping_unavailable"


@responses.activate
def test_melhor_envio_refresh_stores_encrypted_and_is_used(_keys):
    responses.post(
        "https://sandbox.melhorenvio.com.br/oauth/token",
        json={"access_token": "novo", "refresh_token": "novo-refresh", "expires_in": 2592000},
    )
    MelhorEnvioAdapter().refresh_credentials()
    stored = IntegrationCredential.objects.get(provider="melhor_envio")
    assert "novo" not in stored.access_token_encrypted
    responses.post(CALCULATE, json=[])
    MelhorEnvioAdapter().quote(origin_postal_code="1", destination_postal_code="2", items=[ITEM])
    assert responses.calls[1].request.headers["Authorization"] == "Bearer novo"


# --- ViaCEP ---


@responses.activate
def test_viacep():
    responses.get(
        "https://viacep.com.br/ws/01001000/json/",
        json={"logradouro": "Praça da Sé", "bairro": "Sé", "localidade": "São Paulo", "uf": "SP"},
    )
    assert ViaCepAdapter().lookup(postal_code="01001000").city == "São Paulo"
    responses.get("https://viacep.com.br/ws/99999999/json/", json={"erro": "true"})
    assert ViaCepAdapter().lookup(postal_code="99999999") is None


# --- S3 ---


@pytest.fixture
def s3_adapter(settings):
    settings.AWS_ACCESS_KEY_ID = "AKIATESTE"
    settings.AWS_SECRET_ACCESS_KEY = "segredo-teste"
    settings.AWS_S3_ENDPOINT_URL = ""
    settings.AWS_S3_REGION_NAME = "sa-east-1"
    settings.AWS_STORAGE_BUCKET_NAME = "eumini-media-teste"
    return S3MediaAdapter()


def test_s3_put_and_get_use_the_private_bucket(s3_adapter):
    target = {"Bucket": "eumini-media-teste", "Key": "photo/a.png"}
    with Stubber(s3_adapter._client) as stub:
        stub.add_response("put_object", {}, {**target, "Body": b"foto", "ContentType": "image/png"})
        stub.add_response("get_object", {"Body": StreamingBody(io.BytesIO(b"foto"), 4)}, target)
        s3_adapter.put(key="photo/a.png", data=b"foto", content_type="image/png")
        assert s3_adapter.get(key="photo/a.png") == b"foto"
        stub.assert_no_pending_responses()


def test_s3_get_returns_none_for_missing_object(s3_adapter):
    with Stubber(s3_adapter._client) as stub:
        stub.add_client_error("get_object", "NoSuchKey", http_status_code=404)
        assert s3_adapter.get(key="photo/nao-existe.png") is None


def test_s3_signed_url_expires_and_is_signed(s3_adapter):
    url = urlparse(s3_adapter.signed_url(key="image/a.png", ttl_seconds=300))
    query = parse_qs(url.query)
    assert url.hostname == "eumini-media-teste.s3.sa-east-1.amazonaws.com"
    assert url.path == "/image/a.png"
    assert query["X-Amz-Expires"] == ["300"]
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-Signature"]


# --- TypeSafe (Jev) ---

TYPESAFE = "https://api.typesafe.ai/v1/systemone"


def _jev_answers(choice="person", character=0.02):
    return {
        "model": "jev-1.14.0",
        "answers": {
            "subject": {"choice": choice, "confidence": 0.87, "probabilities": {choice: 0.87}},
            "character": {"noul": character},
        },
        "usage": {"input_tokens": 2800},
    }


@responses.activate
def test_typesafe_classifies_photo_with_images_header(_keys):
    responses.post(TYPESAFE, json=_jev_answers("couple"))
    result = TypeSafeClassificationAdapter().classify(image=b"png", target="photo")
    assert (result.result, result.confidence) == ("couple", 0.87)
    assert result.model == "jev-1.14.0"
    assert result.question_set_version
    assert result.cost_usd == pytest.approx(2800 * 0.042 / 1_000_000)
    request = responses.calls[0].request
    assert request.headers["TypeSafe-Danger-Zone-Images"] == "true"
    assert request.headers["Authorization"] == "Bearer chave"
    body = json.loads(request.body)
    ref = body["state"]["photo"]
    assert body["assets"][ref]["data_base64"] == base64.b64encode(b"png").decode()
    assert set(body["questions"]) == {"subject", "character"}
    assert "real human being" in body["questions"]["subject"]["criteria"]["person"]


@responses.activate
def test_typesafe_character_overrides_the_subject(_keys):
    responses.post(TYPESAFE, json=_jev_answers("pet", character=0.97))
    result = TypeSafeClassificationAdapter().classify(image=b"png", target="version")
    assert result.result == "protected_character"
    body = json.loads(responses.calls[0].request.body)
    assert "figurine" in body["questions"]["subject"]["instructions"]


@responses.activate
@pytest.mark.parametrize(
    ("status", "error"),
    [(429, ProviderTemporaryError), (503, ProviderTemporaryError), (400, ProviderPermanentError)],
)
def test_typesafe_errors(_keys, status, error):
    responses.post(TYPESAFE, json={"error": "x"}, status=status)
    with pytest.raises(error):
        TypeSafeClassificationAdapter().classify(image=b"png", target="photo")


@responses.activate
def test_typesafe_unexpected_body_is_permanent(_keys):
    responses.post(TYPESAFE, json={"answers": {}})
    with pytest.raises(ProviderPermanentError):
        TypeSafeClassificationAdapter().classify(image=b"png", target="photo")
