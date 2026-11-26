"""App Staff: acesso, fila, pedido, atribuição, etiqueta, entrega, parceiros, tarifas e repasses."""

from __future__ import annotations

import io
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Role
from catalog.models import ProductPrice
from conftest import photo_upload
from fulfillment.models import (
    PartnerEntry,
    PartnerRate,
    ProductionIssue,
    ProductionJob,
    Shipment,
)
from fulfillment.tests.test_partner_api import FAKE_3MF, FAKE_PDF, _partner_client
from integrations.adapters.email_console import outbox
from media.models import AssetDownload
from orders.models import Order
from payments.tests.test_payments import _paid_order

User = get_user_model()


def _client_for(user):
    client = APIClient(HTTP_X_EUMINI_CLIENT="web")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    client.user = user
    return client


@pytest.fixture
def staff_client():
    user = User.objects.create_user(
        email="equipe@eumini.com", password="Senha-forte-123", email_verified=True
    )
    Role.objects.create(user=user, name=Role.Name.STAFF)
    return _client_for(user)


@pytest.fixture
def partner_client():
    return _partner_client()


@pytest.fixture
def rates():
    for price in ProductPrice.objects.all():
        PartnerRate.objects.create(category=price.category, size=price.size, amount_cents=5000)


@pytest.fixture
def paid_order(visitor_client, anon, django_capture_on_commit_callbacks):
    order, _ = _paid_order(visitor_client, anon, django_capture_on_commit_callbacks)
    return order


def _o(order, suffix=""):
    return f"/api/staff/orders/{order.globalid}/{suffix}"


def _upload(data: bytes, name: str):
    buffer = io.BytesIO(data)
    buffer.name = name
    return buffer


def _item_id(staff_client, order) -> str:
    return staff_client.get(_o(order)).data["items"][0]["id"]


def _send_3mf(staff_client, order):
    item_id = _item_id(staff_client, order)
    response = staff_client.post(
        _o(order, f"items/{item_id}/files/"),
        {"file": _upload(FAKE_3MF, "peca.3mf")},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    return response


def _assign(staff_client, order, partner, capture):
    with capture(execute=True):
        response = staff_client.post(_o(order, "assign/"), {"partner_id": str(partner.globalid)})
    assert response.status_code == 200, response.data
    return response


# --- Acesso ---


def test_access_matrix(anon, user_client, partner_client, staff_client):
    assert anon.get("/api/staff/orders/").status_code == 401
    assert user_client.get("/api/staff/orders/").status_code == 403
    assert partner_client.get("/api/staff/orders/").status_code == 403
    assert staff_client.get("/api/staff/orders/").status_code == 200

    admin = User.objects.create_user(email="admin@eumini.com", password="x", email_verified=True)
    Role.objects.create(user=admin, name=Role.Name.ADMIN)
    assert _client_for(admin).get("/api/staff/orders/summary/").status_code == 200

    Role.objects.filter(user=staff_client.user).delete()
    assert staff_client.get("/api/staff/orders/").status_code == 403


# --- Fila e pedido ---


def test_queue_and_detail(staff_client, paid_order):
    summary = staff_client.get("/api/staff/orders/summary/").data
    assert summary["to_assign"] == 1
    assert summary["missing_file"] == 1
    queue = staff_client.get("/api/staff/orders/?fila=to_assign").data["results"]
    assert [row["number"] for row in queue] == [paid_order.number]

    detail = staff_client.get(_o(paid_order)).data
    assert detail["customer_email"] == paid_order.customer_email
    assert detail["cpf_masked"].startswith("***.***.***-")
    assert detail["stage"] == "unassigned"
    assert detail["items"][0]["photo_url"]
    assert detail["charges"][0]["status"] == "paid"
    assert "pix_br_code" not in detail["charges"][0]

    found = staff_client.get(f"/api/staff/orders/?q={paid_order.number.lower()}").data
    assert found["count"] == 1
    assert staff_client.get("/api/staff/orders/?q=nao-existe").data["count"] == 0


def test_overdue_queue(staff_client, paid_order):
    ProductionJob.objects.update(post_by=date.today() - timedelta(days=1))
    assert staff_client.get("/api/staff/orders/summary/").data["overdue"] == 1
    row = staff_client.get("/api/staff/orders/?fila=overdue").data["results"][0]
    assert row["is_overdue"] is True


def test_downloads_are_logged(staff_client, paid_order):
    item_id = _item_id(staff_client, paid_order)
    for file in ("image", "photo"):
        response = staff_client.post(_o(paid_order, f"items/{item_id}/download/"), {"file": file})
        assert response.status_code == 200, response.data
    assert (
        staff_client.post(_o(paid_order, f"items/{item_id}/download/"), {"file": "3mf"}).status_code
        == 404
    )
    _send_3mf(staff_client, paid_order)
    response = staff_client.post(_o(paid_order, f"items/{item_id}/download/"), {"file": "3mf"})
    assert response.data["filename"].endswith("-v1.3mf")
    assert AssetDownload.objects.filter(user=staff_client.user).count() == 3


def test_production_file_validation(staff_client, paid_order):
    item_id = _item_id(staff_client, paid_order)
    response = staff_client.post(
        _o(paid_order, f"items/{item_id}/files/"),
        {"file": _upload(b"nao e zip", "peca.3mf")},
        format="multipart",
    )
    assert response.status_code == 422
    assert response.data["code"] == "production_file_invalid"
    _send_3mf(staff_client, paid_order)
    detail = _send_3mf(staff_client, paid_order).data
    assert [file["version"] for file in detail["items"][0]["files"]] == [2, 1]
    assert staff_client.get("/api/staff/orders/summary/").data["missing_file"] == 0


# --- Fluxo completo ---


def test_full_flow_with_partner(
    staff_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    partner = partner_client.partner
    _send_3mf(staff_client, paid_order)
    _assign(staff_client, paid_order, partner, django_capture_on_commit_callbacks)
    partner_url = f"/api/partner/orders/{paid_order.globalid}/"
    assert partner_client.post(partner_url + "start/").status_code == 200
    partner_client.post(partner_url + "ready/", {"photos": [photo_upload()]}, format="multipart")
    assert staff_client.get("/api/staff/orders/summary/").data["awaiting_label"] == 1

    outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        detail = staff_client.post(
            _o(paid_order, "label/"),
            {
                "pdf": _upload(FAKE_PDF, "etiqueta.pdf"),
                "carrier": "Correios",
                "tracking_code": "AA1BR",
            },
            format="multipart",
        )
    assert detail.status_code == 200, detail.data
    assert detail.data["stage"] == "to_post"
    assert any("Etiqueta pronta" in mail["subject"] for mail in outbox)
    assert staff_client.post(_o(paid_order, "label/download/")).status_code == 200

    with django_capture_on_commit_callbacks(execute=True):
        partner_client.post(partner_url + "post/")
    assert staff_client.get("/api/staff/orders/summary/").data["to_deliver"] == 1

    with django_capture_on_commit_callbacks(execute=True):
        detail = staff_client.post(_o(paid_order, "deliver/"))
    assert detail.data["status"] == "delivered"
    assert detail.data["shipment"]["delivered_at"]
    assert any("Entregue" in mail["subject"] for mail in outbox)

    events = [event["event"] for event in staff_client.get(_o(paid_order, "events/")).data]
    for expected in ("pay", "assign", "start", "label_attached", "post", "ship", "deliver"):
        assert expected in events
    actors = {event["actor"] for event in staff_client.get(_o(paid_order, "events/")).data}
    assert "equipe@eumini.com" in actors

    # Repasse do ganho.
    entries = staff_client.get(f"/api/staff/partners/{partner.globalid}/entries/?aberto=1").data
    entry_ids = [entry["id"] for entry in entries["results"]]
    payout_url = f"/api/staff/partners/{partner.globalid}/payouts/"
    wrong = staff_client.post(
        payout_url,
        {"entry_ids": entry_ids, "paid_on": "2026-11-26", "amount_cents": 1},
        format="multipart",
    )
    assert wrong.data["code"] == "payout_mismatch"
    outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        payout = staff_client.post(
            payout_url,
            {
                "entry_ids": entry_ids,
                "paid_on": "2026-11-26",
                "amount_cents": 5000,
                "receipt": _upload(FAKE_PDF, "comprovante.pdf"),
            },
            format="multipart",
        )
    assert payout.status_code == 201, payout.data
    assert payout.data["receipt_url"]
    assert any("Repasse de" in mail["subject"] for mail in outbox)
    assert partner_client.get("/api/partner/earnings/").data == {
        "to_receive_cents": 0,
        "paid_cents": 5000,
    }
    again = staff_client.post(
        payout_url,
        {"entry_ids": entry_ids, "paid_on": "2026-11-26", "amount_cents": 5000},
        format="multipart",
    )
    assert again.data["code"] == "payout_entries_invalid"


# --- Atribuição ---


def test_reassign_moves_order_and_warns_old_partner(
    staff_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _send_3mf(staff_client, paid_order)
    _assign(staff_client, paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    partner_client.post(f"/api/partner/orders/{paid_order.globalid}/start/")

    other = _partner_client(email="outro@exemplo.com", name="Outro")
    outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        detail = staff_client.post(
            _o(paid_order, "assign/"),
            {"partner_id": str(other.partner.globalid), "reason": "Atrasou"},
        )
    assert detail.data["partner"]["name"] == "Outro"
    assert detail.data["stage"] == "assigned"
    assert any(
        "saiu da sua fila" in mail["subject"] and mail["to"] == "parceiro@exemplo.com"
        for mail in outbox
    )
    assert any(mail["to"] == "outro@exemplo.com" for mail in outbox)
    assert partner_client.get(f"/api/partner/orders/{paid_order.globalid}/").status_code == 404
    assert Order.objects.get(pk=paid_order.pk).status == Order.Status.IN_PRODUCTION


def test_unassign_discards_open_label(
    staff_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _send_3mf(staff_client, paid_order)
    _assign(staff_client, paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    url = f"/api/partner/orders/{paid_order.globalid}/"
    partner_client.post(url + "start/")
    partner_client.post(url + "ready/", {"photos": [photo_upload()]}, format="multipart")
    staff_client.post(
        _o(paid_order, "label/"),
        {"pdf": _upload(FAKE_PDF, "e.pdf"), "carrier": "Correios", "tracking_code": "X"},
        format="multipart",
    )
    assert staff_client.post(_o(paid_order, "unassign/"), {"reason": ""}).status_code == 400
    detail = staff_client.post(_o(paid_order, "unassign/"), {"reason": "Parceiro sumiu"}).data
    assert detail["stage"] == "unassigned"
    assert detail["partner"] is None
    assert not Shipment.objects.filter(order=paid_order).exists()
    assert ProductionJob.objects.get(order_item__order=paid_order).payout_cents is None


def test_assign_same_partner_twice_fails(
    staff_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(staff_client, paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    response = staff_client.post(
        _o(paid_order, "assign/"), {"partner_id": str(partner_client.partner.globalid)}
    )
    assert response.data["code"] == "same_partner"


def test_deliver_requires_shipped(staff_client, paid_order):
    assert staff_client.post(_o(paid_order, "deliver/")).status_code == 409


def test_resolve_issue(
    staff_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(staff_client, paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    partner_client.post(
        f"/api/partner/orders/{paid_order.globalid}/issues/",
        {"text": "Falta o 3MF"},
        format="multipart",
    )
    assert staff_client.get("/api/staff/orders/summary/").data["issues"] == 1
    issue = ProductionIssue.objects.get(order=paid_order)
    url = f"/api/staff/issues/{issue.globalid}/resolve/"
    detail = staff_client.post(url, {"note": "Subimos o arquivo"}).data
    assert detail["issues"][0]["resolution_note"] == "Subimos o arquivo"
    assert staff_client.post(url, {"note": "de novo"}).status_code == 409
    assert staff_client.get("/api/staff/orders/summary/").data["issues"] == 0


# --- Parceiros ---


def test_create_partner_sends_invite(staff_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = staff_client.post(
            "/api/staff/partners/",
            {
                "name": "Ateliê Novo",
                "email": "Novo@Exemplo.com",
                "origin_postal_code": "01310-100",
                "pix_key": "novo@pix.com",
            },
        )
    assert response.status_code == 201, response.data
    assert response.data["origin_postal_code"] == "01310100"
    assert response.data["login_email"] == "novo@exemplo.com"
    assert response.data["invite_accepted"] is False
    assert "convite?email=novo%40exemplo.com" in outbox[-1]["body"]

    duplicate = staff_client.post(
        "/api/staff/partners/",
        {"name": "Outro", "email": "novo@exemplo.com", "origin_postal_code": "01310100"},
    )
    assert duplicate.data["code"] == "email_in_use"

    partner_id = response.data["id"]
    outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        assert staff_client.post(f"/api/staff/partners/{partner_id}/invite/").status_code == 204
    assert outbox
    edited = staff_client.patch(f"/api/staff/partners/{partner_id}/", {"pix_key": "nova"})
    assert edited.data["pix_key"] == "nova"


def test_deactivate_blocks_with_active_orders(
    staff_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    partner = partner_client.partner
    _assign(staff_client, paid_order, partner, django_capture_on_commit_callbacks)
    url = f"/api/staff/partners/{partner.globalid}/"
    assert staff_client.post(url + "deactivate/").data["code"] == "partner_has_active_orders"
    staff_client.post(_o(paid_order, "unassign/"), {"reason": "Teste"})
    assert staff_client.post(url + "deactivate/").data["status"] == "inactive"
    assert partner_client.get("/api/partner/me/").status_code == 403
    assert staff_client.post(url + "reactivate/").data["status"] == "active"
    listing = staff_client.get("/api/staff/partners/").data["results"]
    assert any(row["name"] == "Ateliê" for row in listing)


def test_adjustment(staff_client, partner_client):
    url = f"/api/staff/partners/{partner_client.partner.globalid}/adjustments/"
    assert staff_client.post(url, {"amount_cents": 0, "note": "x"}).data["code"] == (
        "adjustment_invalid"
    )
    assert staff_client.post(url, {"amount_cents": -500}).status_code == 400
    response = staff_client.post(url, {"amount_cents": -500, "note": "Peça com defeito"})
    assert response.status_code == 201, response.data
    assert partner_client.get("/api/partner/earnings/").data["to_receive_cents"] == -500
    assert PartnerEntry.objects.filter(kind=PartnerEntry.Kind.ADJUSTMENT).count() == 1


# --- Tarifas ---


def test_rates_table(staff_client):
    rows = staff_client.get("/api/staff/rates/").data
    assert len(rows) == ProductPrice.objects.filter(is_active=True).count()
    assert all(row["amount_cents"] is None for row in rows)

    first = rows[0]
    body = {
        "rates": [
            {"category": first["category"], "size_id": first["size_id"], "amount_cents": 4200}
        ]
    }
    updated = staff_client.put("/api/staff/rates/", body, format="json").data
    assert (
        next(
            row
            for row in updated
            if row["size_id"] == first["size_id"] and row["category"] == first["category"]
        )["amount_cents"]
        == 4200
    )

    body["rates"][0]["amount_cents"] = None
    staff_client.put("/api/staff/rates/", body, format="json")
    assert PartnerRate.objects.count() == 0

    bad = {"rates": [{"category": "dragon", "size_id": first["size_id"], "amount_cents": 1}]}
    assert staff_client.put("/api/staff/rates/", bad, format="json").data["code"] == "rate_not_sold"


# --- Comando das contas da equipe ---


def test_staff_user_command(anon):
    from django.core.management import call_command

    call_command("staff_user", "add", "Nova@EuMini.com")
    user = User.objects.get(email="nova@eumini.com")
    assert user.roles == ["staff"]
    assert not user.has_usable_password()
    call_command("staff_user", "remove", "nova@eumini.com")
    assert User.objects.get(pk=user.pk).roles == []
