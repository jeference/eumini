"""dev_tool_partner_label: anexa a etiqueta de um pedido pronto para envio.

Só com DEBUG. Sem `--pdf`, anexa uma etiqueta de mentira, de uma página.

Exemplo:
  python manage.py dev_tool_partner_label EM23456789 --tracking AA123456789BR
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from fulfillment import services
from fulfillment.management.commands._dev import order_by_number, require_debug

_FAKE_LABEL = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 283 425]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


class Command(BaseCommand):
    help = "DEV: anexa a etiqueta (PDF, transportadora e rastreio) ao pedido."

    def add_arguments(self, parser):
        parser.add_argument("number", help="Número do pedido (EM...).")
        parser.add_argument("--pdf", help="PDF da etiqueta. Sem ele, usa uma etiqueta falsa.")
        parser.add_argument("--carrier", default="Correios PAC")
        parser.add_argument("--tracking", default="AA123456789BR")

    def handle(self, *args, **options):
        require_debug()
        order = order_by_number(options["number"])
        if options["pdf"]:
            path = Path(options["pdf"])
            if not path.is_file():
                raise CommandError(f"Arquivo não encontrado: {path}")
            pdf = path.read_bytes()
        else:
            pdf = _FAKE_LABEL
        services.attach_label(
            order=order, pdf=pdf, carrier=options["carrier"], tracking_code=options["tracking"]
        )
        self.stdout.write(self.style.SUCCESS(f"Etiqueta anexada ao pedido {order.number}."))
