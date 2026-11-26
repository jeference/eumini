"""Autorização negada por padrão: cada endpoint declara o que permite.

A posse de um recurso é verificada no service, pelo escopo de cada domínio: recurso de
outro ator responde 404, sem revelar que existe.
"""

from rest_framework.permissions import BasePermission

from common.actor import actor_from_request


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class IsPublic(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return True


class IsAuthenticatedUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsActor(BasePermission):
    """Conta autenticada ou visitante com sessão válida."""

    def has_permission(self, request, view):
        return actor_from_request(request).is_identified


class IsStaff(BasePermission):
    """Conta da equipe (papel `staff` ou `admin`), conferida a cada requisição.

    Tirar o papel corta o acesso na hora, mesmo com o token ainda válido.
    """

    message = "Esta conta não é da equipe."

    def has_permission(self, request, view):
        from accounts.models import Role

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or not user.is_active:
            return False
        return user.user_roles.filter(name__in=(Role.Name.STAFF, Role.Name.ADMIN)).exists()


class IsPartnerMember(BasePermission):
    """Conta ligada a um parceiro ativo, conferida a cada requisição.

    Guarda o parceiro em `request.partner` para a view. Parceiro desativado perde o acesso
    na hora, mesmo com o token ainda válido.
    """

    message = "Esta conta não é de um parceiro ativo."

    def has_permission(self, request, view):
        from fulfillment.services import partner_for

        partner = partner_for(getattr(request, "user", None))
        request.partner = partner
        return partner is not None
