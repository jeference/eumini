"""Perguntas do classificador Jev (TypeSafe) e a regra de decisão.

Sem Django: o teste em `docs/classificador/teste_jev.py` importa este módulo, então o teste e a
produção usam o mesmo texto. Mudar uma pergunta exige rodar o teste de novo e subir
`QUESTION_SET_VERSION` (RN-36).
"""

from __future__ import annotations

QUESTION_SET_VERSION = "2026-11-19"

# Na v1 do teste, os personagens ficaram entre 0,97 e 0,99, e o maior caso negativo em 0,67.
CHARACTER_THRESHOLD = 0.8
# O Jev recusa imagens com um lado menor que 256 px (erro 400 "Invalid image dimensions").
MIN_SIDE = 280

SUBJECT_PHOTO = {
    "person": "Exactly one real human being, and no animal.",
    "pet": "Exactly one real living animal of any species, and no human.",
    "couple": "Exactly two real human beings, and no animal.",
    "person_pet": "Exactly one real human being together with exactly one real living animal.",
    "three_or_more_people": "Three or more real human beings, and no animal.",
    "multiple_pets": "Two or more real living animals, and no human.",
    "group_with_pets": (
        "Humans and animals together, with two or more humans or two or more animals."
    ),
    "no_subject": (
        "No real human being or real living animal: objects, food, vehicles, buildings, "
        "landscapes, documents, text, toys, plush animals, statues or figurines."
    ),
}

SUBJECT_VERSION = {
    "person": "Exactly one human figure, and no animal figure.",
    "pet": (
        "Exactly one animal figure (even if it wears clothes or a costume, or poses like a human), "
        "and no human figure."
    ),
    "couple": "Exactly two human figures, and no animal figure.",
    "person_pet": "Exactly one human figure together with exactly one animal figure.",
    "three_or_more_people": "Three or more human figures, and no animal figure.",
    "multiple_pets": "Two or more animal figures, and no human figure.",
    "group_with_pets": (
        "Human and animal figures together, with two or more humans or two or more animals."
    ),
    "no_subject": (
        "No human or animal figure: objects, food, vehicles, buildings, abstract shapes or text."
    ),
}

CHARACTER = (
    "Does `{ref}` show a copyrighted or trademarked fictional character, mascot or superhero "
    "(for example Mickey Mouse, Batman, Spider-Man or Pikachu), or a person or animal wearing "
    "such a character's costume or logo?"
)


def questions(target: str) -> dict:
    """`target` é `photo` (a foto do cliente) ou `version` (uma imagem gerada)."""
    if target == "photo":
        subject = {
            "type": "choice",
            "instructions": (
                "Count only the main subjects of `photo`. Ignore people or animals that are tiny, "
                "blurred or far in the background. Who is in `photo`?"
            ),
            "criteria": SUBJECT_PHOTO,
        }
    else:
        subject = {
            "type": "choice",
            "instructions": (
                "`photo` is a render of a collectible figurine. Count the characters that make "
                "up the figurine."
            ),
            "criteria": SUBJECT_VERSION,
        }
    return {
        "subject": subject,
        "character": {"type": "noul", "instructions": CHARACTER.format(ref="photo")},
    }


def decide(answers: dict) -> str:
    """Personagem primeiro; senão, vale a escolha de quem aparece."""
    if answers["character"]["noul"] >= CHARACTER_THRESHOLD:
        return "protected_character"
    return answers["subject"]["choice"]
