"""Apoio aos comandos `dev_tool_partner_*`. Só rodam com DEBUG: fazem o papel da equipe, que
no futuro age pelo app Staff."""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import CommandError

from orders.models import Order


def require_debug() -> None:
    if not settings.DEBUG:
        raise CommandError("Indisponível fora de DEBUG: este comando faz o papel da equipe.")


def order_by_number(number: str) -> Order:
    order = Order.objects.filter(number=number.strip().upper()).first()
    if order is None:
        raise CommandError(f"Nenhum pedido com o número {number}.")
    return order
