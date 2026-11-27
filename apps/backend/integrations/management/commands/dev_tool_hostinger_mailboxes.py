"""dev_tool_hostinger_mailboxes — lista as caixas que o token da Mail API da Hostinger gerencia.

Imprime o `resource_id` e o endereço de cada caixa. O `resource_id` da caixa remetente vai em
`HOSTINGER_MAIL_MAILBOX_ID`.

Exemplo:
  python manage.py dev_tool_hostinger_mailboxes
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from hostinger_mail_api import AccountApi, ApiClient, Configuration
from hostinger_mail_api.rest import ApiException


class Command(BaseCommand):
    help = "Lista as caixas (resource_id e endereço) do token da Mail API da Hostinger."

    def handle(self, *args, **options):
        if not settings.HOSTINGER_MAIL_API_TOKEN:
            raise CommandError("Defina HOSTINGER_MAIL_API_TOKEN.")
        configuration = Configuration(access_token=settings.HOSTINGER_MAIL_API_TOKEN)
        try:
            with ApiClient(configuration) as client:
                account = AccountApi(client).get_current_account(_request_timeout=10.0)
        except ApiException as exc:
            raise CommandError(f"A Hostinger recusou ({exc.status}): {exc.body}")
        for mailbox in account.data.mailboxes:
            self.stdout.write(f"{mailbox.resource_id}  {mailbox.address}")
