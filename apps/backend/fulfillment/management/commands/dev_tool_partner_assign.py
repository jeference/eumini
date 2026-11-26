"""dev_tool_partner_assign: atribui um pedido pago a um parceiro e sobe o 3MF de cada item.

Só com DEBUG. Faz o papel da equipe até o app Staff existir.

Exemplo:
  python manage.py dev_tool_partner_assign EM23456789 parceiro@teste.com \
    --3mf ../../testes_impressoes/amostragem/casal_01/multicor.3mf
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from fulfillment import services
from fulfillment.management.commands._dev import order_by_number, require_debug
from fulfillment.models import PartnerMember, ProductionJob


class Command(BaseCommand):
    help = "DEV: atribui o pedido ao parceiro e sobe o 3MF."

    def add_arguments(self, parser):
        parser.add_argument("number", help="Número do pedido (EM...).")
        parser.add_argument("email", help="E-mail do login do parceiro.")
        parser.add_argument("--3mf", dest="file", required=True, help="Arquivo 3MF de exemplo.")

    def handle(self, *args, **options):
        require_debug()
        order = order_by_number(options["number"])
        member = (
            PartnerMember.objects.select_related("partner")
            .filter(user__email=options["email"].strip().lower())
            .first()
        )
        if member is None:
            raise CommandError("Nenhum parceiro com esse e-mail.")
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"Arquivo não encontrado: {path}")
        data = path.read_bytes()
        services.assign_order(order=order, partner=member.partner)
        jobs = ProductionJob.objects.filter(order_item__order=order).exclude(
            status=ProductionJob.Status.CANCELLED
        )
        for job in jobs.select_related("order_item__order"):
            services.add_production_file(job=job, data=data)
        self.stdout.write(
            self.style.SUCCESS(f"Pedido {order.number} atribuído a {member.partner.name}.")
        )
