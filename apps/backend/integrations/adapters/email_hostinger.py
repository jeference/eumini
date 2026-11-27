"""E-mail pela Mail API da Hostinger.

A API não tem campo de remetente: a mensagem sai da caixa `HOSTINGER_MAIL_MAILBOX_ID`, e só o
nome exibido no From muda (`HOSTINGER_MAIL_FROM_NAME`). O ID da caixa sai do comando
`dev_tool_hostinger_mailboxes`.
"""

from __future__ import annotations

import structlog
from django.conf import settings
from hostinger_mail_api import ApiClient, Configuration, SendApi, V1SendRequest
from hostinger_mail_api.rest import ApiException

from integrations.ports import EmailPort

_TIMEOUT_SECONDS = 10.0
log = structlog.get_logger(__name__)


class HostingerEmailAdapter(EmailPort):
    def send(self, *, to: str, subject: str, body: str, html_body: str | None = None) -> None:
        request = V1SendRequest(
            to=[to],
            subject=subject,
            text=body,
            html=html_body,
            display_name=settings.HOSTINGER_MAIL_FROM_NAME,
        )
        configuration = Configuration(access_token=settings.HOSTINGER_MAIL_API_TOKEN)
        try:
            with ApiClient(configuration) as client:
                SendApi(client).send_email(
                    settings.HOSTINGER_MAIL_MAILBOX_ID, request, _request_timeout=_TIMEOUT_SECONDS
                )
        except ApiException as exc:
            log.warning("hostinger_mail_failed", status=exc.status, body=(exc.body or "")[:200])
            raise
