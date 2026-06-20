from rest_framework.permissions import BasePermission

from .roles import user_has_analista_access, user_is_administrador


class IsAnalista(BasePermission):
    """Analista o administrador (acceso completo a predicciones y reportes)."""

    message = "Se requiere rol analista o administrador para acceder a predicciones."

    def has_permission(self, request, view):
        return user_has_analista_access(request.user)


class IsAdministrador(BasePermission):
    """Solo usuarios con rol de negocio «administrador»."""

    message = "Se requiere rol administrador para gestionar usuarios."

    def has_permission(self, request, view):
        return user_is_administrador(request.user)
