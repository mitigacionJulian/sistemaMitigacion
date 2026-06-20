"""Detección de rol analista en peticiones al asistente (JWT opcional)."""

from accounts.roles import user_has_analista_access


def user_is_analista(request) -> bool:
    return user_has_analista_access(getattr(request, "user", None))
