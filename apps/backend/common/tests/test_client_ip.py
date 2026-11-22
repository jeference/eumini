"""IP real do cliente atrás da borda (Cloudflare) e do Next."""

from __future__ import annotations

from django.test import RequestFactory

from common.http import client_ip
from common.middleware import TrustedClientIpMiddleware


def _through_middleware(request):
    TrustedClientIpMiddleware(lambda req: None)(request)
    return request


def test_cabecalho_da_borda_vira_o_remote_addr(settings):
    settings.CLIENT_IP_HEADER = "CF-Connecting-IP"
    settings.NUM_PROXIES = 0
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="172.18.0.5",
        HTTP_CF_CONNECTING_IP="203.0.113.7",
        HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.7, 172.18.0.4",
    )

    _through_middleware(request)

    assert request.META["REMOTE_ADDR"] == "203.0.113.7"
    assert client_ip(request) == "203.0.113.7"


def test_x_forwarded_for_forjado_nao_muda_o_ip(settings):
    settings.CLIENT_IP_HEADER = "CF-Connecting-IP"
    settings.NUM_PROXIES = 0
    request = RequestFactory().get(
        "/",
        HTTP_CF_CONNECTING_IP="203.0.113.7",
        HTTP_X_FORWARDED_FOR="1.2.3.4",
    )

    assert client_ip(_through_middleware(request)) == "203.0.113.7"


def test_valor_invalido_no_cabecalho_e_ignorado(settings):
    settings.CLIENT_IP_HEADER = "CF-Connecting-IP"
    request = RequestFactory().get("/", REMOTE_ADDR="172.18.0.5", HTTP_CF_CONNECTING_IP="x, y")

    _through_middleware(request)

    assert request.META["REMOTE_ADDR"] == "172.18.0.5"


def test_sem_configuracao_o_cabecalho_nao_tem_efeito(settings):
    settings.CLIENT_IP_HEADER = ""
    request = RequestFactory().get("/", REMOTE_ADDR="172.18.0.5", HTTP_CF_CONNECTING_IP="1.2.3.4")

    _through_middleware(request)

    assert request.META["REMOTE_ADDR"] == "172.18.0.5"
