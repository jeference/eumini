"""dev_tool_get_verification_code — imprime um código de verificação de e-mail no terminal.

Em desenvolvimento não há e-mail real, então não existe caixa de entrada onde ler o código
enviado por `request_email_verification`. Como o código é guardado apenas hasheado
(`code_hash`), o texto original é irrecuperável depois de emitido — este command **emite um
código novo** (ignorando a espera de reenvio, o que invalida o anterior) e imprime o texto
puro, sem enviar e-mail.

Só roda com `DEBUG=True`: ele expõe deliberadamente um segredo e nunca deve tocar produção.

Exemplo:
  python manage.py dev_tool_get_verification_code fulano@eumini.com
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import VerificationCode
from accounts.services.auth_codes import issue_code

User = get_user_model()


class Command(BaseCommand):
    help = "DEV: emite e imprime um código de verificação de e-mail para um usuário."

    def add_arguments(self, parser):
        parser.add_argument("email", help="E-mail do usuário alvo.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Indisponível fora de DEBUG (expõe um código secreto).")

        email = options["email"].strip().lower()
        user = User.objects.filter(email=email, is_active=True).first()
        if user is None:
            raise CommandError(f"Nenhum usuário ativo com e-mail {email}.")

        if user.email_verified:
            self.stdout.write(f"E-mail {email} já está verificado.")
            return

        code = issue_code(
            user=user,
            kind=VerificationCode.Kind.EMAIL_VERIFICATION,
            enforce_cooldown=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Código de verificação para {email}: {code}"))
