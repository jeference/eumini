"""Convite de parceiro: a equipe cadastra, o parceiro cria a senha pelo link (RF-PAR-02).

Não há cadastro próprio. O convite é um código de uso único, com validade maior que os de
conta, enviado por e-mail com o link do app de parceiros.
"""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import VerificationCode
from accounts.services.auth_codes import issue_code, validate_code
from accounts.services.users import blacklist_all_tokens, validate_password_strength
from common.exceptions import CodeInvalid
from fulfillment.models import Partner, PartnerMember
from notifications.services import send_email

User = get_user_model()
_GENERIC_INVALID = "Convite inválido ou expirado. Peça um novo à EuMini."


def invite_partner_member(*, partner: Partner, email: str) -> PartnerMember:
    """Cria o login do parceiro, se não existir, e envia o convite. Reenviar gera outro código."""
    email = email.strip().lower()
    with transaction.atomic():
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, password=None)
        member, _ = PartnerMember.objects.get_or_create(partner=partner, user=user)
        hours = settings.BUSINESS["PARTNER_INVITE_TTL_HOURS"]
        code = issue_code(
            user=user,
            kind=VerificationCode.Kind.PARTNER_INVITE,
            enforce_cooldown=False,
            ttl=timedelta(hours=hours),
        )
    query = urlencode({"email": email, "codigo": code})
    transaction.on_commit(
        lambda: send_email(
            to=email,
            subject="Você foi convidado para imprimir com a EuMini",
            template="partner_invite",
            context={
                "partner_name": partner.name,
                "invite_url": f"{settings.PARTNERS_APP_URL}/convite?{query}",
                "ttl_hours": hours,
            },
        )
    )
    return member


def accept_partner_invite(*, email: str, code: str, password: str):
    """Define a senha e confirma o e-mail. Sem transação: as tentativas precisam ficar gravadas."""
    user = User.objects.filter(email=email.strip().lower(), is_active=True).first()
    if user is None or not PartnerMember.objects.filter(user=user).exists():
        raise CodeInvalid(_GENERIC_INVALID)
    validate_password_strength(password, user=user)
    try:
        validate_code(user=user, kind=VerificationCode.Kind.PARTNER_INVITE, submitted=code)
    except CodeInvalid:
        raise CodeInvalid(_GENERIC_INVALID) from None
    with transaction.atomic():
        user.set_password(password)
        user.email_verified = True
        user.save(update_fields=["password", "email_verified", "updated_at"])
        blacklist_all_tokens(user)
    return user
