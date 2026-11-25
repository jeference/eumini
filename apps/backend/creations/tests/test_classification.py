"""Classificação da foto e das versões (RN-30 a RN-38) e lista de espera."""

from __future__ import annotations

from conftest import creation_payload, drain_worker, make_ready_creation
from creations.models import Classification, Creation, ProviderTask, WaitlistEntry
from orders.tests.helpers import size_id


def _classify_as(settings, photo="person", version=None):
    settings.STUB_CLASSIFICATION = {"photo": photo, "version": version or photo}


def _create(client, **fields):
    return client.post("/api/creations/", creation_payload(**fields), format="multipart")


def _detail(client, creation_id):
    return client.get(f"/api/creations/{creation_id}/").data


def test_rejected_photo_generates_nothing_and_spends_no_image_quota(visitor_client, settings):
    _classify_as(settings, "multiple_pets")
    creation_id = _create(visitor_client).data["id"]
    drain_worker()
    detail = _detail(visitor_client, creation_id)
    assert detail["status"] == "rejected"
    assert detail["rejection_reason"] == "multiple_pets"
    assert detail["versions"] == []
    assert not ProviderTask.objects.filter(kind=ProviderTask.Kind.GENERATE).exists()
    quota = visitor_client.get("/api/quota/").data
    assert quota["image"]["used"] == 0
    assert quota["classify"]["used"] == 1
    classification = Classification.objects.get()
    assert classification.decision == Classification.Decision.REJECTED
    assert classification.version is None
    assert classification.requested_category == "person"
    assert classification.question_set_version and classification.model_name


def test_version_classification_keeps_who_asked(visitor_client):
    make_ready_creation(visitor_client)
    photo, version = Classification.objects.order_by("created_at")
    assert version.version is not None
    assert photo.ip_hash and version.ip_hash == photo.ip_hash


def test_protected_character_is_rejected(visitor_client, settings):
    _classify_as(settings, "protected_character")
    creation_id = _create(visitor_client).data["id"]
    drain_worker()
    assert _detail(visitor_client, creation_id)["rejection_reason"] == "protected_character"


def test_detected_category_wins_over_the_page(visitor_client, settings):
    _classify_as(settings, "pet")
    creation_id = _create(visitor_client, requested_category="person").data["id"]
    drain_worker()
    detail = _detail(visitor_client, creation_id)
    assert (detail["requested_category"], detail["category"]) == ("person", "pet")
    assert detail["status"] == "ready"
    generate = ProviderTask.objects.get(kind=ProviderTask.Kind.GENERATE)
    assert "The subject is one animal" in generate.rendered_prompt


def test_version_category_sets_the_price(visitor_client, settings):
    _classify_as(settings, "couple")
    detail = make_ready_creation(visitor_client)
    assert detail["versions"][0]["category"] == "couple"
    response = visitor_client.post(
        "/api/cart/items/",
        {"creation_id": detail["id"], "size_id": size_id(visitor_client, "6cm"), "quantity": 1},
    )
    assert response.status_code == 201, response.data
    assert (response.data["category"], response.data["unit_price_cents"]) == ("couple", 17990)


def test_size_not_sold_in_the_category(visitor_client, settings):
    _classify_as(settings, "couple")
    detail = make_ready_creation(visitor_client)
    response = visitor_client.post(
        "/api/cart/items/",
        {"creation_id": detail["id"], "size_id": size_id(visitor_client, "10cm"), "quantity": 1},
    )
    assert response.status_code == 422
    assert response.data["code"] == "size_not_sold"


def test_edit_that_changes_the_category_changes_the_price(visitor_client, settings):
    detail = make_ready_creation(visitor_client)
    _classify_as(settings, "person", version="person_pet")
    visitor_client.post(
        f"/api/creations/{detail['id']}/edits/",
        {"version_id": detail["versions"][0]["id"], "instruction": "com meu cachorro"},
    )
    drain_worker()
    edited = _detail(visitor_client, detail["id"])["versions"][1]
    assert edited["category"] == "person_pet"
    visitor_client.post(
        f"/api/creations/{detail['id']}/apply-version/", {"version_id": edited["id"]}
    )
    item = visitor_client.post(
        "/api/cart/items/",
        {"creation_id": detail["id"], "size_id": size_id(visitor_client), "quantity": 1},
    ).data
    assert (item["category"], item["unit_price_cents"]) == ("person_pet", 16990)


def test_version_outside_the_categories_cannot_be_bought(visitor_client, settings):
    _classify_as(settings, "person", version="three_or_more_people")
    detail = make_ready_creation(visitor_client)
    version = detail["versions"][0]
    assert (version["category"], version["rejection_reason"]) == ("", "three_or_more_people")
    response = visitor_client.post(
        "/api/cart/items/",
        {"creation_id": detail["id"], "size_id": size_id(visitor_client), "quantity": 1},
    )
    assert response.status_code == 422
    assert response.data["code"] == "version_not_sellable"


def test_photo_reading_failure_retries_only_the_reading(visitor_client, settings):
    _classify_as(settings, "__erro__")
    creation_id = _create(visitor_client).data["id"]
    drain_worker()
    detail = _detail(visitor_client, creation_id)
    assert detail["status"] == "failed"
    assert detail["error"]["code"] == "classification_failed"
    assert visitor_client.get("/api/quota/").data["classify"]["used"] == 0

    _classify_as(settings, "person")
    retried = visitor_client.post(f"/api/creations/{creation_id}/retry/").data
    assert retried["status"] == "classifying"
    drain_worker()
    assert _detail(visitor_client, creation_id)["status"] == "ready"


def test_version_reading_failure_does_not_generate_again(visitor_client, settings):
    _classify_as(settings, "person", version="__erro__")
    creation_id = _create(visitor_client).data["id"]
    drain_worker()
    detail = _detail(visitor_client, creation_id)
    assert detail["status"] == "failed"
    assert visitor_client.get("/api/quota/").data["image"]["used"] == 1

    _classify_as(settings, "person")
    assert visitor_client.post(f"/api/creations/{creation_id}/retry/").status_code == 202
    drain_worker()
    detail = _detail(visitor_client, creation_id)
    assert detail["status"] == "ready"
    assert len(detail["versions"]) == 1
    assert ProviderTask.objects.filter(kind=ProviderTask.Kind.GENERATE).count() == 1


def test_classification_has_its_own_daily_limit(visitor_client, settings):
    settings.BUSINESS = {
        **settings.BUSINESS,
        "QUOTA_PER_DAY": {**settings.BUSINESS["QUOTA_PER_DAY"], "classify": 1},
    }
    _classify_as(settings, "no_subject")
    assert _create(visitor_client).status_code == 202
    drain_worker()
    response = _create(visitor_client)
    assert response.status_code == 429
    assert response.data["code"] == "quota_exceeded"


def test_no_image_quota_left_refuses_before_reading_the_photo(visitor_client, settings):
    settings.BUSINESS = {
        **settings.BUSINESS,
        "QUOTA_PER_DAY": {**settings.BUSINESS["QUOTA_PER_DAY"], "image": 0},
    }
    response = _create(visitor_client)
    assert response.status_code == 429
    assert not Creation.objects.exists()


def test_quota_used_up_while_reading_fails_the_creation(visitor_client, settings):
    creation_id = _create(visitor_client).data["id"]
    settings.BUSINESS = {
        **settings.BUSINESS,
        "QUOTA_PER_DAY": {**settings.BUSINESS["QUOTA_PER_DAY"], "image": 0},
    }
    drain_worker()
    detail = _detail(visitor_client, creation_id)
    assert (detail["status"], detail["category"]) == ("failed", "person")
    assert detail["error"]["code"] == "quota_exceeded"


def _rejected(client, settings, reason="three_or_more_people"):
    _classify_as(settings, reason)
    creation_id = _create(client).data["id"]
    drain_worker()
    return creation_id


def test_waitlist_records_the_consent_of_sending_the_email(visitor_client, settings):
    creation_id = _rejected(visitor_client, settings)
    url = "/api/waitlist/"
    body = {"creation_id": creation_id, "email": "Ana@Exemplo.com"}
    assert visitor_client.post(url, body).status_code == 201
    assert visitor_client.post(url, body).status_code == 201
    entry = WaitlistEntry.objects.get()
    assert (entry.email, entry.reason) == ("ana@exemplo.com", "three_or_more_people")
    assert entry.consent_version and entry.consented_at
    assert entry.classification.creation.globalid.hex == creation_id.replace("-", "")


def test_waitlist_is_not_for_other_refusals(visitor_client, settings):
    creation_id = _rejected(visitor_client, settings, "no_subject")
    response = visitor_client.post(
        "/api/waitlist/", {"creation_id": creation_id, "email": "a@b.com"}
    )
    assert response.status_code == 422
    assert response.data["code"] == "not_waitlistable"


def test_waitlist_is_scoped_to_the_owner(visitor_client, other_visitor_client, settings):
    creation_id = _rejected(visitor_client, settings)
    response = other_visitor_client.post(
        "/api/waitlist/", {"creation_id": creation_id, "email": "a@b.com"}
    )
    assert response.status_code == 404
