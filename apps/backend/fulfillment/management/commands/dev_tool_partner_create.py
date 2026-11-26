"""dev_tool_partner_create: cria um parceiro de teste, com login pronto e tarifas de exemplo.

Só com DEBUG. Em produção, o parceiro entra por convite feito pelo app Staff.

Exemplo:
  python manage.py dev_tool_partner_create parceiro@teste.com Senha-forte-123 --name "Ateliê 3D"
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import ProductPrice
from fulfillment.management.commands._dev import require_debug
from fulfillment.models import Partner, PartnerMember, PartnerRate

User = get_user_model()
# Tarifa de exemplo: uma fração do preço de venda. Os valores reais saem da amostragem de custo.
_SAMPLE_RATE_SHARE = 0.35


class Command(BaseCommand):
    help = "DEV: cria um parceiro com login e tarifas de exemplo."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("password")
        parser.add_argument("--name", default="Parceiro de teste")
        parser.add_argument("--cep", default="01001000")
        parser.add_argument("--pix", default="parceiro@teste.com")

    def handle(self, *args, **options):
        require_debug()
        email = options["email"].strip().lower()
        with transaction.atomic():
            user = User.objects.filter(email=email).first() or User.objects.create_user(email=email)
            user.set_password(options["password"])
            user.email_verified = True
            user.save()
            member = PartnerMember.objects.filter(user=user).select_related("partner").first()
            if member is None:
                partner = Partner.objects.create(
                    name=options["name"],
                    origin_postal_code=options["cep"],
                    pix_key=options["pix"],
                )
                PartnerMember.objects.create(partner=partner, user=user)
            else:
                partner = member.partner
            created_rates = 0
            for price in ProductPrice.objects.filter(is_active=True):
                _, created = PartnerRate.objects.get_or_create(
                    category=price.category,
                    size=price.size,
                    defaults={"amount_cents": round(price.price_cents * _SAMPLE_RATE_SHARE)},
                )
                created_rates += created
        self.stdout.write(
            self.style.SUCCESS(
                f"Parceiro '{partner.name}' pronto. Login: {email}. Tarifas novas: {created_rates}."
            )
        )
