"""Utilidades de roles de negocio (PerfilUsuario + Rol)."""

ROLES_ANALISTA_ACCESS = frozenset({"analista", "administrador"})


def get_user_rol_codigo(user) -> str | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return None
    return perfil.rol.codigo


def user_has_analista_access(user) -> bool:
    return get_user_rol_codigo(user) in ROLES_ANALISTA_ACCESS


def user_is_administrador(user) -> bool:
    return get_user_rol_codigo(user) == "administrador"
