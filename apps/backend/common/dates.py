from __future__ import annotations

from datetime import date, timedelta


def add_business_days(start: date, days: int) -> date:
    """Soma dias úteis, pulando sábado e domingo. Feriados ainda não entram [Proposta]."""
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current
