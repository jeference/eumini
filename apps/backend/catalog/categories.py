"""Categorias vendidas e motivos de recusa (RN-30, RN-31). São enums em código, não tabelas."""

from django.db import models


class Category(models.TextChoices):
    PERSON = "person", "Pessoa"
    PET = "pet", "Pet"
    COUPLE = "couple", "Casal"
    PERSON_PET = "person_pet", "Pessoa + Pet"


class RejectionReason(models.TextChoices):
    THREE_OR_MORE_PEOPLE = "three_or_more_people", "3 ou mais pessoas"
    MULTIPLE_PETS = "multiple_pets", "2 ou mais pets"
    GROUP_WITH_PETS = "group_with_pets", "Grupo com pets"
    NO_SUBJECT = "no_subject", "Sem pessoa nem pet"
    PROTECTED_CHARACTER = "protected_character", "Personagem ou marca"


# Recusas que viram "Recorte e nós fazemos": a foto tem gente ou pets demais (lista de espera).
GROUP_REASONS = frozenset(
    {
        RejectionReason.THREE_OR_MORE_PEOPLE,
        RejectionReason.MULTIPLE_PETS,
        RejectionReason.GROUP_WITH_PETS,
    }
)
