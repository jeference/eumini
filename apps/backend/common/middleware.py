"""Middlewares comuns: IP real do cliente e contexto por requisição (`request_id`)."""

import ipaddress
import uuid

import structlog
from django.conf import settings


class TrustedClientIpMiddleware:
    """Troca o `REMOTE_ADDR` pelo IP do cabeçalho confiável da borda, quando configurado.

    Em produção a Cloudflare grava o IP do visitante em `CF-Connecting-IP` e sobrescreve
    qualquer valor que venha do cliente. Como o servidor não tem porta aberta, todo acesso passa
    por ela. Gravar o IP em `REMOTE_ADDR`, com `NUM_PROXIES=0`, faz o `client_ip` e os limites
    do DRF verem o mesmo IP, venha a chamada pelo rewrite do Next ou pelo BFF.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header = settings.CLIENT_IP_HEADER
        if header:
            meta_key = "HTTP_" + header.upper().replace("-", "_")
            value = request.META.get(meta_key, "").strip()
            try:
                request.META["REMOTE_ADDR"] = str(ipaddress.ip_address(value))
            except ValueError:
                pass
        return self.get_response(request)


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID") or uuid.uuid4().hex
        request.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
