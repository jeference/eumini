from __future__ import annotations

from conftest import creation_payload, drain_worker, make_ready_creation, photo_upload
from creations.models import CreationInput, ProviderTask, QuotaReservation
from media.models import Asset


def _create(client, **fields):
    payload = creation_payload(**{"text": "um gato", **fields})
    return client.post("/api/creations/", payload, format="multipart")


def test_create_from_photo_and_request_is_ready_to_buy(visitor_client):
    response = _create(visitor_client)
    assert response.status_code == 202
    assert response.data["status"] == "classifying"
    assert response.data["requested_category"] == "person"
    assert response.data["is_generating"] is True
    drain_worker()
    detail = visitor_client.get(f"/api/creations/{response.data['id']}/").data
    assert detail["status"] == "ready"
    assert detail["category"] == "person"
    assert detail["is_generating"] is False
    assert len(detail["versions"]) == 1
    assert detail["versions"][0]["image_url"]
    assert detail["versions"][0]["category"] == "person"
    assert detail["current_version_id"] == detail["versions"][0]["id"]
    tasks = ProviderTask.objects.filter(creation__globalid=response.data["id"]).order_by("pk")
    # Lê a foto, gera a imagem e lê a imagem gerada.
    assert [(t.kind, t.source_version_id is not None) for t in tasks] == [
        (ProviderTask.Kind.CLASSIFY, False),
        (ProviderTask.Kind.GENERATE, False),
        (ProviderTask.Kind.CLASSIFY, True),
    ]
    generate = tasks[1]
    assert "um gato" in generate.rendered_prompt and generate.prompt_version
    assert all(t.status == ProviderTask.Status.SUCCEEDED for t in tasks)


def test_create_stores_original_photo_without_exposing_it(visitor_client):
    response = _create(visitor_client)
    source = CreationInput.objects.get(creation__globalid=response.data["id"])
    assert source.original_photo.kind == Asset.Kind.ORIGINAL
    assert source.original_photo.key.startswith("original/")
    drain_worker()
    detail = visitor_client.get(f"/api/creations/{response.data['id']}/")
    assert source.original_photo.key not in detail.content.decode()
    assert "original_photo" not in detail.data


def test_create_accepts_iphone_heic_photo(visitor_client):
    photo = photo_upload(size=(400, 300), image_format="HEIF", name="IMG_0001.HEIC")
    response = _create(visitor_client, photo=photo)
    assert response.status_code == 202, response.data
    source = CreationInput.objects.get(creation__globalid=response.data["id"])
    assert source.original_photo.mime == "image/jpeg"
    assert source.original_photo.key.endswith(".jpg")
    assert source.photo.mime == "image/png"


def test_create_requires_photo(visitor_client):
    response = visitor_client.post(
        "/api/creations/", {"text": "um gato", "requested_category": "person"}, format="multipart"
    )
    assert response.status_code == 400
    assert not ProviderTask.objects.exists()


def test_invalid_category(visitor_client):
    response = _create(visitor_client, requested_category="inexistente")
    assert response.status_code == 400
    assert not ProviderTask.objects.exists()


def test_photo_without_request(visitor_client):
    response = _create(visitor_client, text="")
    assert response.status_code == 202, response.data
    drain_worker()
    detail = visitor_client.get(f"/api/creations/{response.data['id']}/").data
    assert detail["status"] == "ready"
    assert detail["versions"][0]["origin"] == "photo"


def test_other_visitor_cannot_see_or_act(visitor_client, other_visitor_client, user_client):
    creation_id = _create(visitor_client).data["id"]
    for client in (other_visitor_client, user_client):
        assert client.get(f"/api/creations/{creation_id}/").status_code == 404
        assert client.post(f"/api/creations/{creation_id}/retry/").status_code == 404
        assert client.delete(f"/api/creations/{creation_id}/").status_code == 404
    assert other_visitor_client.get("/api/creations/").data["count"] == 0


def test_list_is_scoped_and_paginated(visitor_client):
    _create(visitor_client)
    data = visitor_client.get("/api/creations/").data
    assert data["count"] == 1
    assert data["results"][0]["status"] == "classifying"


def test_content_refusal_shows_message_and_releases_quota(visitor_client):
    creation_id = _create(visitor_client, text="__recusar__").data["id"]
    drain_worker()
    detail = visitor_client.get(f"/api/creations/{creation_id}/").data
    assert detail["status"] == "failed"
    assert detail["error"]["code"] == "content_refused"
    assert "regras de conteúdo" in detail["error"]["message"]
    reservation = QuotaReservation.objects.get(
        task__creation__globalid=creation_id, kind=QuotaReservation.Kind.IMAGE
    )
    assert reservation.state == QuotaReservation.State.RELEASED
    assert visitor_client.get("/api/quota/").data["image"]["used"] == 0


def test_provider_failure_retries_then_fails_and_user_can_retry(visitor_client):
    creation_id = _create(visitor_client, text="__falhar__").data["id"]
    drain_worker()
    task = ProviderTask.objects.get(creation__globalid=creation_id, kind=ProviderTask.Kind.GENERATE)
    assert task.attempts == 3
    assert task.status == ProviderTask.Status.FAILED
    detail = visitor_client.get(f"/api/creations/{creation_id}/").data
    assert detail["status"] == "failed"
    response = visitor_client.post(f"/api/creations/{creation_id}/retry/")
    assert response.status_code == 202
    assert response.data["status"] == "generating_image"
    assert response.data["error"] is None


def _edit_task_model(client, detail) -> str:
    client.post(
        f"/api/creations/{detail['id']}/edits/",
        {"version_id": detail["versions"][0]["id"], "instruction": "capa vermelha"},
    )
    drain_worker()
    edit = ProviderTask.objects.get(creation__globalid=detail["id"], kind=ProviderTask.Kind.EDIT)
    assert edit.status == ProviderTask.Status.SUCCEEDED
    return edit.model_name


def test_main_model_generates_and_edits(visitor_client):
    detail = make_ready_creation(visitor_client)
    photo = ProviderTask.objects.get(
        creation__globalid=detail["id"], kind=ProviderTask.Kind.GENERATE
    )
    assert photo.model_name == "stub-image"
    assert _edit_task_model(visitor_client, detail) == "stub-image"


def test_fallback_model_takes_over_and_keeps_the_edits(visitor_client):
    detail = make_ready_creation(visitor_client, text="__recusar_principal__")
    photo = ProviderTask.objects.get(
        creation__globalid=detail["id"], kind=ProviderTask.Kind.GENERATE
    )
    assert photo.model_name == "stub-image-reserva"
    assert photo.attempts == 1
    assert _edit_task_model(visitor_client, detail) == "stub-image-reserva"


def test_edit_creates_version_and_apply_switches_image(visitor_client):
    detail = make_ready_creation(visitor_client)
    first_version = detail["versions"][0]["id"]
    response = visitor_client.post(
        f"/api/creations/{detail['id']}/edits/",
        {"version_id": first_version, "instruction": "capa vermelha"},
    )
    assert response.status_code == 202
    assert response.data["edit_tasks"][0]["is_active"] is True
    drain_worker()
    edited = visitor_client.get(f"/api/creations/{detail['id']}/").data
    assert len(edited["versions"]) == 2
    assert edited["versions"][1]["parent_id"] == first_version
    assert edited["versions"][1]["category"] == "person"
    assert edited["status"] == "ready"
    assert edited["current_version_id"] == first_version

    applied = visitor_client.post(
        f"/api/creations/{detail['id']}/apply-version/",
        {"version_id": edited["versions"][1]["id"]},
    ).data
    assert applied["status"] == "ready"
    assert applied["current_version_id"] == edited["versions"][1]["id"]


def test_edit_while_generating_is_refused(visitor_client):
    creation = _create(visitor_client).data
    response = visitor_client.post(
        f"/api/creations/{creation['id']}/edits/",
        {"version_id": creation["id"], "instruction": "azul"},
    )
    assert response.data["code"] == "not_editable"


def test_edit_validations(visitor_client):
    detail = make_ready_creation(visitor_client)
    version = detail["versions"][0]["id"]
    url = f"/api/creations/{detail['id']}/edits/"
    assert visitor_client.post(url, {"version_id": version, "instruction": " "}).status_code == 400
    too_long = "x" * 201
    assert (
        visitor_client.post(url, {"version_id": version, "instruction": too_long}).status_code
        == 400
    )


def test_cancel_queued_edit_releases_quota(visitor_client):
    detail = make_ready_creation(visitor_client)
    response = visitor_client.post(
        f"/api/creations/{detail['id']}/edits/",
        {"version_id": detail["versions"][0]["id"], "instruction": "azul"},
    )
    task_id = response.data["edit_tasks"][0]["id"]
    cancel = visitor_client.post(f"/api/creations/{detail['id']}/edits/{task_id}/cancel/")
    assert cancel.status_code == 200
    drain_worker()
    assert len(visitor_client.get(f"/api/creations/{detail['id']}/").data["versions"]) == 1
    assert visitor_client.get("/api/quota/").data["edit"]["used"] == 0


def test_delete_hides_creation(visitor_client):
    creation_id = _create(visitor_client).data["id"]
    assert visitor_client.delete(f"/api/creations/{creation_id}/").status_code == 204
    assert visitor_client.get(f"/api/creations/{creation_id}/").status_code == 404
    assert visitor_client.get("/api/creations/").data["count"] == 0
