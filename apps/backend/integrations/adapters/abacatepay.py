"""AbacatePay v2, checkout transparente com PIX e cartão. Valores em centavos.

PIX: a confirmação vem do webhook; aqui só criamos a cobrança e consultamos o status, sem
dados do cliente (`customer` é opcional na API).

Cartão: o navegador gera um `ctok_` com o abacatepay.js (60 s, uso único, preso ao valor) e
cobramos com ele. O cartão exige `customer` completo, celular incluso. A resposta já diz se
foi aprovado; recusa vem como HTTP 4xx com `success: false`.
"""

from __future__ import annotations

import requests
import structlog
from django.conf import settings
from django.utils.dateparse import parse_datetime

from common.exceptions import PaymentDeclined, UpstreamUnavailable
from integrations.ports import CARD, GatewayCharge, GatewayCustomer, PaymentGatewayPort

_TIMEOUT_SECONDS = 30
_DESCRIPTION_MAX = 37

# PIX: só PAID e REDEEMED liquidam. APPROVED e UNDER_DISPUTE nunca: na dúvida, pendente.
_PIX_STATUS_MAP = {
    "PENDING": "pending",
    "APPROVED": "pending",
    "UNDER_DISPUTE": "pending",
    "PAID": "paid",
    "REDEEMED": "paid",
    "EXPIRED": "expired",
    "CANCELLED": "failed",
    "FAILED": "failed",
    "REFUNDED": "refunded",
}

# Cartão: APPROVED é o pagamento aprovado, e a passagem para PAID não dispara webhook.
_CARD_STATUS_MAP = {
    **_PIX_STATUS_MAP,
    "APPROVED": "paid",
}

# Erros de configuração nossa (chave errada, sem permissão) não são recusa do cartão.
_NOT_DECLINE = {401, 403, 404, 429}

log = structlog.get_logger(__name__)


class AbacatePayAdapter(PaymentGatewayPort):
    provider = "abacatepay"

    def __init__(self) -> None:
        self._base_url = settings.ABACATE_PAY_BASE_URL.rstrip("/")
        self._api_key = settings.ABACATE_PAY_API_KEY

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _map_status(self, raw: str, method: str) -> str:
        status_map = _CARD_STATUS_MAP if method == CARD else _PIX_STATUS_MAP
        if raw not in status_map:
            log.warning("abacatepay_unknown_status", status=raw, method=method)
        return status_map.get(raw, "pending")

    def _data_or_raise(
        self, response: requests.Response, operation: str, *, declinable: bool = False
    ) -> dict:
        try:
            body = response.json()
            parsed = isinstance(body, dict)
        except ValueError:
            parsed = False
        if not parsed:
            body = {}
        failed = body.get("error") or body.get("success") is False
        status_code = response.status_code
        if declinable and 400 <= status_code < 500 and status_code not in _NOT_DECLINE:
            # A mensagem do gateway vai para o log; o cliente vê uma mensagem nossa.
            log.warning(
                "abacatepay_card_declined",
                operation=operation,
                http_status=status_code,
                error=str(body.get("error") or "")[:300],
            )
            raise PaymentDeclined()
        if not response.ok or not parsed:
            log.error("abacatepay_http_error", operation=operation, http_status=status_code)
            raise UpstreamUnavailable("Gateway de pagamento indisponível.")
        if failed:
            log.error("abacatepay_api_error", operation=operation)
            raise UpstreamUnavailable("Gateway de pagamento retornou erro.")
        return body.get("data") or {}

    def _request(self, http_method: str, path: str, operation: str, **kwargs) -> requests.Response:
        try:
            return requests.request(
                http_method,
                f"{self._base_url}{path}",
                headers=self._headers(),
                timeout=_TIMEOUT_SECONDS,
                **kwargs,
            )
        except requests.RequestException as exc:
            log.error("abacatepay_request_exception", operation=operation, error=str(exc))
            raise UpstreamUnavailable("Gateway de pagamento indisponível.") from exc

    def create_charge(
        self,
        *,
        method: str,
        amount: int,
        reference: str,
        description: str,
        expires_in_seconds: int | None = None,
        card_token: str = "",
        customer: GatewayCustomer | None = None,
    ) -> GatewayCharge:
        data: dict = {
            "amount": int(amount),
            "description": description[:_DESCRIPTION_MAX],
            "metadata": {"kind": "order", "reference": reference},
        }
        if method == CARD:
            if not card_token or customer is None:
                raise ValueError("Cartão exige card_token e customer.")
            data["token"] = card_token
            data["customer"] = {
                "name": customer.name,
                "email": customer.email,
                "taxId": customer.tax_id,
                "cellphone": customer.cellphone,
            }
        else:
            data["expiresIn"] = expires_in_seconds
        response = self._request(
            "POST",
            "/transparents/create",
            "create_transparent",
            json={"method": method, "data": data},
        )
        body = self._data_or_raise(response, "create_transparent", declinable=method == CARD)
        external_id = str(body.get("id") or "")
        if not external_id:
            raise UpstreamUnavailable("Gateway de pagamento retornou resposta inválida.")
        status = self._map_status(body.get("status", "PENDING"), method)
        if method == CARD and status == "failed":
            log.warning("abacatepay_card_failed", external_id=external_id)
            raise PaymentDeclined()
        return GatewayCharge(
            external_id=external_id,
            status=status,
            amount=int(amount),
            pix_br_code=body.get("brCode", ""),
            pix_qr_base64=body.get("brCodeBase64", ""),
            expires_at=parse_datetime(body.get("expiresAt") or ""),
            card_brand=str(body.get("brand") or ""),
            card_last_four=str(body.get("lastFour") or ""),
        )

    def simulate_payment(self, *, external_id: str) -> dict:
        """Só desenvolvimento: faz o AbacatePay pagar a cobrança PIX e disparar o webhook.

        Fica fora do port porque é ferramenta de dev, própria do AbacatePay. Só funciona com
        chave de devMode; em produção a API recusa.
        """
        response = self._request(
            "POST",
            "/transparents/simulate-payment",
            "simulate_transparent_payment",
            params={"id": external_id},
            json={"metadata": {}},
        )
        return self._data_or_raise(response, "simulate_transparent_payment")

    def get_charge_status(self, *, external_id: str, method: str) -> str:
        # O `/check` só atende PIX; o cartão é consultado pelo `/get`.
        path = "/transparents/get" if method == CARD else "/transparents/check"
        response = self._request(
            "GET", path, "check_transparent_status", params={"id": external_id}
        )
        data = self._data_or_raise(response, "check_transparent_status")
        return self._map_status(data.get("status", "PENDING"), method)
