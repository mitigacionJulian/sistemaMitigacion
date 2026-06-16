"""Metadatos comunes para respuestas de reportes (Fase 0+)."""

from django.utils import timezone

SECCION_LABELS = {
    "preview": "Vista previa (infraestructura)",
    "tablero": "Tablero de indicadores",
    "mapa": "Mapa de accidentalidad",
    "predicciones": "Predicciones",
}

SECCIONES_VALIDAS = frozenset(SECCION_LABELS.keys())


def build_report_meta(
    request,
    *,
    seccion: str,
    filtros=None,
    titulo: str = "",
    notas: str = "",
) -> dict:
    user = request.user
    perfil = getattr(user, "perfil", None)
    rol_nombre = perfil.rol.nombre if perfil else ""
    rol_codigo = perfil.rol.codigo if perfil else ""
    nombre = (user.get_full_name() or "").strip()

    return {
        "usuario": nombre or user.username,
        "username": user.username,
        "email": user.email or "",
        "rol": rol_nombre,
        "rol_codigo": rol_codigo,
        "generado_en": timezone.localtime(timezone.now()).isoformat(),
        "seccion": seccion,
        "seccion_etiqueta": SECCION_LABELS.get(seccion, seccion),
        "filtros": filtros or {},
        "titulo": (titulo or "").strip(),
        "notas": (notas or "").strip(),
        "sistema": "SG Mitigación de Accidentes — Medellín",
    }
