"""Detección de rol analista en peticiones al asistente (JWT opcional)."""


def user_is_analista(request) -> bool:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return False
    return perfil.rol.codigo == "analista"
