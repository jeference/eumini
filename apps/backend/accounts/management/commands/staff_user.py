"""staff_user: cria ou remove contas da equipe (RF-STF-03). Roda também em produção.

  python manage.py staff_user add fulana@eumini.com
  python manage.py staff_user remove fulana@eumini.com

`add` cria a conta sem senha, se não existir, e concede o papel `staff`. A pessoa define a senha
em "Esqueci a senha" no app Staff, o que também confirma o e-mail. `remove` tira os papéis da
equipe e encerra as sessões abertas.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role
from accounts.services.users import blacklist_all_tokens, grant_role

User = get_user_model()


class Command(BaseCommand):
    help = "Cria ou remove uma conta da equipe."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["add", "remove"])
        parser.add_argument("email")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if options["action"] == "add":
            with transaction.atomic():
                user = User.objects.filter(email=email).first()
                created = user is None
                if created:
                    user = User.objects.create_user(email=email, password=None)
                grant_role(user=user, name=Role.Name.STAFF)
            how = "Defina a senha em 'Esqueci a senha' no app Staff." if created else ""
            self.stdout.write(self.style.SUCCESS(f"{email} agora é da equipe. {how}".strip()))
            return

        user = User.objects.filter(email=email).first()
        if user is None:
            raise CommandError("Usuário não encontrado.")
        with transaction.atomic():
            Role.objects.filter(user=user, name__in=[Role.Name.STAFF, Role.Name.ADMIN]).delete()
            blacklist_all_tokens(user)
        self.stdout.write(self.style.SUCCESS(f"{email} não é mais da equipe."))
