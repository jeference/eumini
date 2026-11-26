"""Temas que o cliente escolhe ao enviar a foto (PRD, Temas). São enums em código, não tabelas.

O tema é uma camada curada do prompt (`catalog/prompts.py`): acessórios, roupa e pose. Não muda
a categoria nem o preço, e nunca acrescenta pessoas ou animais.
"""

from django.db import models


class Theme(models.TextChoices):
    CHRISTMAS = "christmas", "Natal"
    GTA6 = "gta6", "GTA VI"
