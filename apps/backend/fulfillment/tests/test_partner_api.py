"""App de parceiros: acesso, fluxo do pedido, arquivos, privacidade e ganhos."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import DomainEvent
from catalog.models import ProductPrice
from common.dates import add_business_days
from common.exceptions import CodeInvalid, GuardFailed
from conftest import photo_upload
from fulfillment import services
from fulfillment.invites import accept_partner_invite, invite_partner_member
from fulfillment.models import (
    Partner,
    PartnerEntry,
    PartnerMember,
    PartnerPayout,
    PartnerRate,
    ProductionIssue,
    ProductionJob,
)
from integrations.adapters.email_console import outbox
from media.models import AssetDownload
from orders.models import Order
from payments.tests.test_payments import _paid_order, _webhook

User = get_user_model()
FAKE_3MF = b"PK\x03\x04" + b"3mf" * 10
FAKE_PDF = b"%PDF-1.4\n%%EOF\n"
PII_KEYS = {"customer_email", "customer_name", "cpf_masked", "email", "street", "total_cents"}


def _partner_client(email="parceiro@exemplo.com", name="Ateliê"):
    user = User.objects.create_user(email=email, password="Senha-forte-123", email_verified=True)
    partner = Partner.objects.create(name=name, origin_postal_code="01001000", pix_key="chave-pix")
    PartnerMember.objects.create(partner=partner, user=user)
    client = APIClient(HTTP_X_EUMINI_CLIENT="web")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    client.user, client.partner = user, partner
    return client


@pytest.fixture
def partner_client():
    return _partner_client()


@pytest.fixture
def rates():
    for price in ProductPrice.objects.all():
        PartnerRate.objects.create(category=price.category, size=price.size, amount_cents=5000)


@pytest.fixture
def paid_order(visitor_client, anon, django_capture_on_commit_callbacks):
    order, external = _paid_order(visitor_client, anon, django_capture_on_commit_callbacks)
    order.external_charge = external
    return order


def _assign(order, partner, capture, *, with_file=True):
    with capture(execute=True):
        services.assign_order(order=order, partner=partner)
    if with_file:
        for job in ProductionJob.objects.filter(order_item__order=order):
            services.add_production_file(job=job, data=FAKE_3MF)


def _url(order, suffix=""):
    return f"/api/partner/orders/{order.globalid}/{suffix}"


# --- Acesso ---


def test_access_matrix(anon, user_client, partner_client, rates, paid_order, settings):
    assert anon.get("/api/partner/orders/").status_code == 401
    assert user_client.get("/api/partner/orders/").status_code == 403
    assert partner_client.get("/api/partner/me/").data["name"] == "Ateliê"

    partner_client.partner.status = Partner.Status.INACTIVE
    partner_client.partner.save()
    assert partner_client.get("/api/partner/me/").status_code == 403


def test_other_partner_gets_404(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    other = _partner_client(email="outro@exemplo.com", name="Outro")
    assert other.get(_url(paid_order)).status_code == 404
    assert other.post(_url(paid_order, "start/")).status_code == 404
    assert other.get("/api/partner/orders/").data["count"] == 0


def test_unassigned_orders_are_invisible(partner_client, paid_order):
    assert partner_client.get(_url(paid_order)).status_code == 404


# --- Fluxo ---


def test_full_flow(partner_client, rates, paid_order, django_capture_on_commit_callbacks):
    outbox.clear()
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    assert any("Nova impressão" in mail["subject"] for mail in outbox)

    listing = partner_client.get("/api/partner/orders/?group=to_print").data
    assert listing["count"] == 1
    assert listing["results"][0]["group"] == "to_print"
    job = ProductionJob.objects.get(order_item__order=paid_order)
    assert job.post_by == add_business_days(paid_order.paid_at.date(), 7)
    assert job.payout_cents == 5000

    with django_capture_on_commit_callbacks(execute=True):
        detail = partner_client.post(_url(paid_order, "start/"))
    assert detail.status_code == 200, detail.data
    assert detail.data["group"] == "in_production"
    assert Order.objects.get(pk=paid_order.pk).status == Order.Status.IN_PRODUCTION
    assert any("Em produção" in mail["subject"] for mail in outbox)

    detail = partner_client.post(
        _url(paid_order, "ready/"), {"photos": [photo_upload()]}, format="multipart"
    )
    assert detail.status_code == 200, detail.data
    assert detail.data["group"] == "awaiting_label"
    assert len(detail.data["photos"]) == 1

    assert partner_client.post(_url(paid_order, "post/")).data["code"] == "label_missing"
    with django_capture_on_commit_callbacks(execute=True):
        services.attach_label(
            order=paid_order, pdf=FAKE_PDF, carrier="Correios", tracking_code="AA1BR"
        )
    assert any("Etiqueta pronta" in mail["subject"] for mail in outbox)
    detail = partner_client.get(_url(paid_order)).data
    assert detail["group"] == "to_post"
    assert detail["label"]["tracking_code"] == "AA1BR"

    with django_capture_on_commit_callbacks(execute=True):
        detail = partner_client.post(_url(paid_order, "post/"))
    assert detail.data["group"] == "posted"
    order = Order.objects.get(pk=paid_order.pk)
    assert order.status == Order.Status.SHIPPED
    assert any("Enviado" in mail["subject"] for mail in outbox)

    earnings = partner_client.get("/api/partner/earnings/").data
    assert earnings == {"to_receive_cents": 5000, "paid_cents": 0}
    entries = partner_client.get("/api/partner/earnings/entries/").data["results"]
    assert entries[0]["order_number"] == order.number
    assert not entries[0]["is_paid"]

    events = set(
        DomainEvent.objects.filter(aggregate_id=job.globalid).values_list("event", flat=True)
    )
    assert events == {"assign", "start", "mark_ready", "post"}


def test_start_requires_production_file(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks, with_file=False)
    response = partner_client.post(_url(paid_order, "start/"))
    assert response.status_code == 422
    assert response.data["code"] == "production_file_missing"


def test_actions_out_of_order_are_rejected(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    assert partner_client.post(_url(paid_order, "post/")).status_code == 409
    response = partner_client.post(
        _url(paid_order, "ready/"), {"photos": [photo_upload()]}, format="multipart"
    )
    assert response.status_code == 409


def test_ready_requires_photo(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    partner_client.post(_url(paid_order, "start/"))
    response = partner_client.post(_url(paid_order, "ready/"), {}, format="multipart")
    assert response.status_code == 400


def test_refuse_returns_order_to_unassigned(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    assert partner_client.post(_url(paid_order, "refuse/"), {"reason": ""}).status_code == 400
    response = partner_client.post(_url(paid_order, "refuse/"), {"reason": "Impressora parada"})
    assert response.status_code == 204
    job = ProductionJob.objects.get(order_item__order=paid_order)
    assert job.status == ProductionJob.Status.UNASSIGNED
    assert job.partner is None and job.payout_cents is None
    assert partner_client.get(_url(paid_order)).status_code == 404


def test_cannot_refuse_after_start(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    partner_client.post(_url(paid_order, "start/"))
    assert partner_client.post(_url(paid_order, "refuse/"), {"reason": "x"}).status_code == 409


def test_payout_is_frozen_at_assignment(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    PartnerRate.objects.update(amount_cents=99999)
    assert ProductionJob.objects.get(order_item__order=paid_order).payout_cents == 5000


def test_assign_without_rate_fails(partner_client, paid_order):
    with pytest.raises(GuardFailed) as error:
        services.assign_order(order=paid_order, partner=partner_client.partner)
    assert error.value.code == "partner_rate_missing"


def test_refund_cancels_and_warns_partner(
    partner_client, rates, paid_order, anon, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    partner_client.post(_url(paid_order, "start/"))
    outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        _webhook(anon, paid_order.external_charge, event="transparent.refunded", event_id="evt_r")
    detail = partner_client.get(_url(paid_order)).data
    assert detail["group"] == "cancelled"
    assert any(
        "cancelado" in mail["subject"] and mail["to"] == "parceiro@exemplo.com" for mail in outbox
    )
    assert partner_client.get("/api/partner/earnings/").data["to_receive_cents"] == 0


# --- Arquivos e privacidade ---


def test_downloads_are_logged(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    item_id = partner_client.get(_url(paid_order)).data["items"][0]["id"]
    response = partner_client.post(_url(paid_order, f"items/{item_id}/download/"), {"file": "3mf"})
    assert response.status_code == 200
    assert response.data["filename"].endswith("-v1.3mf")
    served = partner_client.get(response.data["url"])
    assert served.status_code == 200
    assert "attachment" in served["Content-Disposition"]

    partner_client.post(_url(paid_order, f"items/{item_id}/download/"), {"file": "image"})
    assert AssetDownload.objects.filter(user=partner_client.user).count() == 2
    assert partner_client.post(_url(paid_order, "label/download/")).status_code == 404


def test_new_production_file_replaces_previous(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    job = ProductionJob.objects.get(order_item__order=paid_order)
    services.add_production_file(job=job, data=FAKE_3MF + b"v2")
    item = partner_client.get(_url(paid_order)).data["items"][0]
    assert item["production_file"]["version"] == 2


def test_partner_never_sees_customer_data(
    partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    detail = partner_client.get(_url(paid_order)).data
    listing = partner_client.get("/api/partner/orders/").data["results"][0]
    for payload in (detail, listing, *detail["items"]):
        assert not PII_KEYS & set(payload), payload
    text = str(detail)
    assert paid_order.customer_email not in text
    assert paid_order.customer_name not in text


def test_customer_does_not_see_label_before_posting(
    visitor_client, partner_client, rates, paid_order, django_capture_on_commit_callbacks
):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    partner_client.post(_url(paid_order, "start/"))
    partner_client.post(
        _url(paid_order, "ready/"), {"photos": [photo_upload()]}, format="multipart"
    )
    services.attach_label(order=paid_order, pdf=FAKE_PDF, carrier="Correios", tracking_code="X1")
    assert visitor_client.get(f"/api/orders/{paid_order.globalid}/").data["shipment"] is None


def test_report_issue(partner_client, rates, paid_order, django_capture_on_commit_callbacks):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    response = partner_client.post(
        _url(paid_order, "issues/"),
        {"text": "O 3MF veio sem a base", "photo": photo_upload()},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert response.data["issues"][0]["text"] == "O 3MF veio sem a base"
    assert response.data["issues"][0]["photo_url"]
    assert ProductionIssue.objects.filter(order=paid_order).count() == 1


# --- Fila e ganhos ---


def test_summary_and_overdue(partner_client, rates, paid_order, django_capture_on_commit_callbacks):
    _assign(paid_order, partner_client.partner, django_capture_on_commit_callbacks)
    ProductionJob.objects.update(post_by=date.today() - timedelta(days=1))
    summary = partner_client.get("/api/partner/orders/summary/").data
    assert summary["to_print"] == 1
    assert summary["overdue"] == 1
    assert partner_client.get("/api/partner/orders/").data["results"][0]["is_overdue"] is True


def test_payouts_and_balance(partner_client):
    partner = partner_client.partner
    payout = PartnerPayout.objects.create(partner=partner, paid_on=date.today(), amount_cents=3000)
    PartnerEntry.objects.create(
        partner=partner, kind=PartnerEntry.Kind.ADJUSTMENT, amount_cents=3000, payout=payout
    )
    PartnerEntry.objects.create(
        partner=partner, kind=PartnerEntry.Kind.ADJUSTMENT, amount_cents=-500, note="Desconto"
    )
    assert partner_client.get("/api/partner/earnings/").data == {
        "to_receive_cents": -500,
        "paid_cents": 3000,
    }
    payouts = partner_client.get("/api/partner/payouts/").data["results"]
    assert payouts[0]["entry_count"] == 1


# --- Convite ---


def test_invite_and_accept(anon, django_capture_on_commit_callbacks, monkeypatch):
    partner = Partner.objects.create(name="Novo", origin_postal_code="01001000")
    monkeypatch.setattr("accounts.services.auth_codes._generate_code", lambda: "123456")
    with django_capture_on_commit_callbacks(execute=True):
        invite_partner_member(partner=partner, email="Novo@Exemplo.com")
    mail = outbox[-1]
    assert "convite?email=novo%40exemplo.com&codigo=123456" in mail["body"]

    payload = {"email": "novo@exemplo.com", "code": "000000", "password": "Senha-forte-123"}
    assert anon.post("/api/partner/invite/accept/", payload).status_code == 422
    payload["code"] = "123456"
    assert anon.post("/api/partner/invite/accept/", payload).status_code == 204
    assert anon.post("/api/partner/invite/accept/", payload).status_code == 422

    login = anon.post(
        "/api/auth/login/", {"email": "novo@exemplo.com", "password": "Senha-forte-123"}
    )
    assert login.status_code == 200


def test_invite_requires_partner_membership(user):
    with pytest.raises(CodeInvalid):
        accept_partner_invite(email=user.email, code="123456", password="Senha-forte-123")
