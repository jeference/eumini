from __future__ import annotations

import pytest

from catalog import prompts
from catalog.categories import Category
from catalog.models import ProductPrice, ProductSize


def _prices(products) -> dict:
    return {
        p["category"]: [(size["code"], size["price_cents"]) for size in p["sizes"]]
        for p in products
    }


def test_products_are_public_with_price_table(anon):
    response = anon.get("/api/catalog/products/")
    assert response.status_code == 200
    assert [p["category"] for p in response.data] == ["person", "pet", "couple", "person_pet"]
    assert _prices(response.data) == {
        "person": [("6cm", 9990), ("8cm", 14490), ("10cm", 18990), ("12cm", 22990)],
        "pet": [("4cm", 6590), ("6cm", 10990), ("8cm", 15990)],
        "couple": [("6cm", 14990), ("8cm", 21990)],
        "person_pet": [("6cm", 12990), ("8cm", 18990), ("10cm", 24990), ("12cm", 29990)],
    }
    assert {p["category"]: p["from_price_cents"] for p in response.data} == {
        "person": 9990,
        "pet": 6590,
        "couple": 14990,
        "person_pet": 12990,
    }
    assert response.data[0]["label"] == "Pessoa"


def test_inactive_size_and_price_are_hidden(anon):
    ProductSize.objects.filter(code="4cm").update(is_active=False)
    ProductPrice.objects.filter(category="couple", size__code="8cm").update(is_active=False)
    prices = _prices(anon.get("/api/catalog/products/").data)
    assert [code for code, _ in prices["pet"]] == ["6cm", "8cm"]
    assert [code for code, _ in prices["couple"]] == ["6cm"]


def test_size_ids_are_shared_across_categories(anon):
    products = anon.get("/api/catalog/products/").data
    six = {size["id"] for p in products for size in p["sizes"] if size["code"] == "6cm"}
    assert len(six) == 1


@pytest.mark.parametrize("category", Category.values)
def test_prompt_per_category(category):
    prompt = prompts.photo_prompt(category=category)
    assert "one single figurine" in prompt or category in (Category.PERSON, Category.PET)
    assert f"exactly {prompts.MAX_PRINT_COLORS} colors" in prompt
    assert "sem chapéu" in prompts.photo_prompt(category=category, request="sem chapéu.")
    # Chaves no pedido do cliente não quebram a montagem do prompt.
    assert "com {chaves}" in prompts.photo_prompt(category=category, request="com {chaves}")


def test_two_figure_prompts_ask_for_one_piece():
    assert "two people" in prompts.photo_prompt(category=Category.COUPLE)
    assert "one person with one animal" in prompts.photo_prompt(category=Category.PERSON_PET)


def test_unknown_category_is_rejected():
    with pytest.raises(ValueError):
        prompts.photo_prompt(category="free")


def test_edit_prompt():
    assert "capa vermelha" in prompts.edit_prompt(instruction="capa vermelha.")
