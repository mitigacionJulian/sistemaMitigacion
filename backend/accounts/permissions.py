from rest_framework.permissions import BasePermission


class IsAnalista(BasePermission):
    """Solo usuarios con perfil y rol de negocio «analista»."""

    message = "Se requiere rol analista para acceder a predicciones."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        perfil = getattr(user, "perfil", None)
        if perfil is None:
            return False
        return perfil.rol.codigo == "analista"
