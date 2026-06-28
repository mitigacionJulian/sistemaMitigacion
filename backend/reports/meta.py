"""Metadatos comunes para respuestas de reportes (Fase 0+)."""

from django.utils import timezone

from config.brand import APP_NAME

SECCION_LABELS = {
    "preview": "Vista previa (infraestructura)",
    "tablero": "Tablero de indicadores",
    "mapa": "Mapa de accidentalidad",
    "predicciones": "Predicciones",
    "asistente": "Asistente de accidentalidad",
    "pruebas": "Pruebas del sistema",
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
    ahora = timezone.localtime(timezone.now())
    numero_reporte = ahora.strftime("SG-%Y%m%d-%H%M%S")
    titulo_limpio = (titulo or "").strip()
    seccion_etiqueta = SECCION_LABELS.get(seccion, seccion)
    titulo_display = titulo_limpio or f"Reporte {seccion_etiqueta} — {numero_reporte}"

    return {
        "usuario": nombre or user.username,
        "username": user.username,
        "email": user.email or "",
        "rol": rol_nombre,
        "rol_codigo": rol_codigo,
        "generado_en": ahora.isoformat(),
        "seccion": seccion,
        "seccion_etiqueta": seccion_etiqueta,
        "filtros": filtros or {},
        "titulo": titulo_limpio,
        "titulo_display": titulo_display,
        "numero_reporte": numero_reporte,
        "notas": (notas or "").strip(),
        "sistema": APP_NAME,
    }
