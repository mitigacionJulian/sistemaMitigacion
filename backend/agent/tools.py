"""
Herramientas del asistente.

Datos públicos: tablero/mapa (siempre disponibles).
Predicciones: solo si la petición viene de un usuario autenticado con rol analista.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from dashboard.carga_esperada_territorial import build_carga_esperada_payload
from dashboard.distribucion_clase_incidente import build_distribucion_clase_incidente_payload
from dashboard.distribucion_gravedad import build_distribucion_gravedad_payload
from dashboard.evolucion_mensual import build_evolucion_payload
from dashboard.kpis import FiltrosKpi, build_kpis_payload
from dashboard.matriz_dia_hora import build_matriz_dia_hora_payload
from dashboard.patrones_temporales_proyectados import (
    build_dia_semana_proyectado_payload,
    build_matriz_dia_hora_proyectada_payload,
)
from dashboard.por_dia_semana import build_dia_semana_payload
from dashboard.predicciones_mensuales import build_predicciones_mensuales_payload
from dashboard.prioridad_territorial import build_prioridad_territorial_payload
from dashboard.tops import build_tops_payload
from dashboard.territorio_sql import parse_modo_territorio

from django.db import connection


def _parse_date(value: str | None, fallback: date | None = None) -> date | None:
    if not value:
        return fallback
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return fallback


def _filtros_from_args(args: dict[str, Any]) -> FiltrosKpi:
    comuna_id = args.get("comuna_id")
    barrio_id = args.get("barrio_id")
    clase_id = args.get("clase_incidente_id")
    return FiltrosKpi(
        comuna_id=int(comuna_id) if comuna_id not in (None, "") else None,
        barrio_id=int(barrio_id) if barrio_id not in (None, "") else None,
        clase_incidente_id=int(clase_id) if clase_id not in (None, "") else None,
        modo_territorio=parse_modo_territorio(args.get("territorio")),
    )


def _default_rango() -> tuple[date, date]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT MIN(fecha_incidente), MAX(fecha_incidente) FROM incidente")
        row = cursor.fetchone()
    if row and row[0] and row[1]:
        dmax = row[1] if isinstance(row[1], date) else date.fromisoformat(str(row[1])[:10])
        return date(dmax.year, 1, 1), dmax
    return date(2021, 1, 1), date(2021, 9, 30)


def _rango_from_args(args: dict[str, Any]) -> tuple[date, date]:
    default_desde, default_hasta = _default_rango()
    desde = _parse_date(args.get("desde"), default_desde)
    hasta = _parse_date(args.get("hasta"), default_hasta)
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha 'desde' no puede ser posterior a 'hasta'.")
    return desde or default_desde, hasta or default_hasta


def get_rango_fechas(_args: dict[str, Any]) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT MIN(fecha_incidente), MAX(fecha_incidente) FROM incidente")
        row = cursor.fetchone()
    if not row or not row[0] or not row[1]:
        return {
            "hay_datos": False,
            "default_desde": "2021-01-01",
            "default_hasta": "2021-09-30",
            "nota": "Sin registros en incidente; use el rango de referencia del proyecto.",
        }
    dmin = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0])[:10])
    dmax = row[1] if isinstance(row[1], date) else date.fromisoformat(str(row[1])[:10])
    return {
        "hay_datos": True,
        "fecha_minima": dmin.isoformat(),
        "fecha_maxima": dmax.isoformat(),
        "default_desde": date(dmax.year, 1, 1).isoformat(),
        "default_hasta": dmax.isoformat(),
    }


def get_catalogos(_args: dict[str, Any]) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, codigo, nombre FROM comuna
            WHERE COALESCE(activo, TRUE) ORDER BY nombre
            """
        )
        comunas = [{"id": r[0], "codigo": r[1], "nombre": r[2]} for r in cursor.fetchall()]
        cursor.execute(
            """
            SELECT id, codigo, nombre FROM clase_incidente
            WHERE COALESCE(activo, TRUE) ORDER BY nombre
            """
        )
        clases = [{"id": r[0], "codigo": r[1], "nombre": r[2]} for r in cursor.fetchall()]
    return {"comunas": comunas, "clases_incidente": clases}


def get_kpis(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    return build_kpis_payload(inicio, fin, _filtros_from_args(args))


def get_tops(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    limite = int(args.get("limite") or 10)
    return build_tops_payload(inicio, fin, _filtros_from_args(args), limite=min(max(limite, 1), 15))


def get_evolucion_mensual(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    return build_evolucion_payload(inicio, fin, _filtros_from_args(args))


def get_distribucion_gravedad(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    return build_distribucion_gravedad_payload(inicio, fin, _filtros_from_args(args))


def get_distribucion_clase_incidente(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    return build_distribucion_clase_incidente_payload(inicio, fin, _filtros_from_args(args))


def get_por_dia_semana(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    return build_dia_semana_payload(inicio, fin, _filtros_from_args(args))


def get_matriz_dia_hora(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    return build_matriz_dia_hora_payload(inicio, fin, _filtros_from_args(args))


def _horizonte_meses(args: dict[str, Any], default: int = 6) -> int:
    raw = args.get("horizonte_meses") or args.get("meses") or default
    try:
        v = int(raw)
    except (TypeError, ValueError):
        v = default
    return max(1, min(12, v))


def _bool_arg(args: dict[str, Any], key: str, default: bool = True) -> bool:
    raw = args.get(key)
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "si", "sí")


def get_predicciones_mensuales(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    filtros = _filtros_from_args(args)
    modelo = str(args.get("modelo") or "estacional").strip().lower()
    variable = str(args.get("variable") or "incidentes").strip().lower()
    return build_predicciones_mensuales_payload(
        inicio,
        fin,
        filtros,
        _horizonte_meses(args),
        modelo=modelo,
        variable=variable,
        excluir_covid=_bool_arg(args, "excluir_covid", True),
    )


def get_prioridad_territorial(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    nivel = str(args.get("nivel") or "comuna").strip().lower()
    if nivel not in ("comuna", "barrio"):
        nivel = "comuna"
    limite = int(args.get("limite") or 15)
    return build_prioridad_territorial_payload(
        inicio,
        fin,
        _filtros_from_args(args),
        nivel=nivel,
        limite=min(max(limite, 1), 20),
        excluir_covid=_bool_arg(args, "excluir_covid", True),
    )


def get_carga_esperada_territorial(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    nivel = str(args.get("nivel") or "comuna").strip().lower()
    if nivel not in ("comuna", "barrio"):
        nivel = "comuna"
    limite = int(args.get("limite") or 20)
    modelo = str(args.get("modelo") or "estacional").strip().lower()
    return build_carga_esperada_payload(
        inicio,
        fin,
        _filtros_from_args(args),
        nivel=nivel,
        horizonte_meses=_horizonte_meses(args),
        modelo=modelo,
        excluir_covid=_bool_arg(args, "excluir_covid", True),
        limite=min(max(limite, 1), 20),
    )


def get_matriz_dia_hora_proyectada(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    modelo = str(args.get("modelo") or "estacional").strip().lower()
    return build_matriz_dia_hora_proyectada_payload(
        inicio,
        fin,
        _filtros_from_args(args),
        horizonte_meses=_horizonte_meses(args),
        modelo=modelo,
        excluir_covid=_bool_arg(args, "excluir_covid", True),
    )


def get_dia_semana_proyectado(args: dict[str, Any]) -> dict[str, Any]:
    inicio, fin = _rango_from_args(args)
    modelo = str(args.get("modelo") or "estacional").strip().lower()
    return build_dia_semana_proyectado_payload(
        inicio,
        fin,
        _filtros_from_args(args),
        horizonte_meses=_horizonte_meses(args),
        modelo=modelo,
        excluir_covid=_bool_arg(args, "excluir_covid", True),
    )


PUBLIC_TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "get_rango_fechas",
        "description": "Obtiene el rango de fechas disponible en la base de incidentes y valores por defecto.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_catalogos",
        "description": "Lista comunas y clases de incidente para filtrar consultas.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_kpis",
        "description": "KPIs del periodo: incidentes, víctimas, fatales y tasa diaria vs año anterior.",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string", "description": "Fecha inicio ISO (YYYY-MM-DD)"},
                "hasta": {"type": "string", "description": "Fecha fin ISO (YYYY-MM-DD)"},
                "comuna_id": {"type": "integer"},
                "barrio_id": {"type": "integer"},
                "clase_incidente_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_tops",
        "description": "Rankings por sexo, edad, comuna, barrio, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string"},
                "hasta": {"type": "string"},
                "comuna_id": {"type": "integer"},
                "barrio_id": {"type": "integer"},
                "clase_incidente_id": {"type": "integer"},
                "limite": {"type": "integer", "description": "Máx. filas por ranking (1-15)"},
            },
        },
    },
    {
        "name": "get_evolucion_mensual",
        "description": "Serie mensual de incidentes y víctimas en el periodo.",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string"},
                "hasta": {"type": "string"},
                "comuna_id": {"type": "integer"},
                "barrio_id": {"type": "integer"},
                "clase_incidente_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_distribucion_gravedad",
        "description": "Distribución de víctimas por gravedad.",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string"},
                "hasta": {"type": "string"},
                "comuna_id": {"type": "integer"},
                "barrio_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_distribucion_clase_incidente",
        "description": "Distribución de incidentes por clase.",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string"},
                "hasta": {"type": "string"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_por_dia_semana",
        "description": "Patrones de incidentes por día de la semana.",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string"},
                "hasta": {"type": "string"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_matriz_dia_hora",
        "description": "Matriz día de semana × hora del día (patrones temporales).",
        "parameters": {
            "type": "object",
            "properties": {
                "desde": {"type": "string"},
                "hasta": {"type": "string"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
]

ANALYST_TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "get_predicciones_mensuales",
        "description": (
            "Proyección mensual de incidentes, víctimas o fatales para los próximos meses. "
            "Útil para identificar en qué mes se espera mayor carga."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "horizonte_meses": {
                    "type": "integer",
                    "description": "Meses a proyectar (1-12, default 6)",
                },
                "variable": {
                    "type": "string",
                    "description": "incidentes | victimas | victimas_fatales",
                },
                "modelo": {
                    "type": "string",
                    "description": "ols | estacional | poisson | media_movil",
                },
                "comuna_id": {"type": "integer"},
                "barrio_id": {"type": "integer"},
                "clase_incidente_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_prioridad_territorial",
        "description": (
            "Ranking de prioridad territorial (comunas o barrios) según tendencia, "
            "concentración y gravedad. Identifica sectores críticos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nivel": {"type": "string", "description": "comuna | barrio"},
                "limite": {"type": "integer", "description": "Máx. filas (1-20)"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_carga_esperada_territorial",
        "description": (
            "Categoría de carga esperada (alto/medio/bajo) por comuna o barrio "
            "en el horizonte proyectado."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nivel": {"type": "string", "description": "comuna | barrio"},
                "horizonte_meses": {"type": "integer"},
                "limite": {"type": "integer"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_matriz_dia_hora_proyectada",
        "description": "Matriz día×hora con incidentes proyectados en el horizonte.",
        "parameters": {
            "type": "object",
            "properties": {
                "horizonte_meses": {"type": "integer"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_dia_semana_proyectado",
        "description": "Incidentes proyectados por día de la semana en el horizonte.",
        "parameters": {
            "type": "object",
            "properties": {
                "horizonte_meses": {"type": "integer"},
                "comuna_id": {"type": "integer"},
            },
        },
    },
]

_PUBLIC_HANDLERS: dict[str, Any] = {
    "get_rango_fechas": get_rango_fechas,
    "get_catalogos": get_catalogos,
    "get_kpis": get_kpis,
    "get_tops": get_tops,
    "get_evolucion_mensual": get_evolucion_mensual,
    "get_distribucion_gravedad": get_distribucion_gravedad,
    "get_distribucion_clase_incidente": get_distribucion_clase_incidente,
    "get_por_dia_semana": get_por_dia_semana,
    "get_matriz_dia_hora": get_matriz_dia_hora,
}

_ANALYST_HANDLERS: dict[str, Any] = {
    "get_predicciones_mensuales": get_predicciones_mensuales,
    "get_prioridad_territorial": get_prioridad_territorial,
    "get_carga_esperada_territorial": get_carga_esperada_territorial,
    "get_matriz_dia_hora_proyectada": get_matriz_dia_hora_proyectada,
    "get_dia_semana_proyectado": get_dia_semana_proyectado,
}

# Compatibilidad con imports existentes
TOOL_DECLARATIONS = PUBLIC_TOOL_DECLARATIONS


def get_tool_declarations(is_analista: bool = False) -> list[dict[str, Any]]:
    if is_analista:
        return PUBLIC_TOOL_DECLARATIONS + ANALYST_TOOL_DECLARATIONS
    return list(PUBLIC_TOOL_DECLARATIONS)


def execute_tool(name: str, args: dict[str, Any] | None, *, is_analista: bool = False) -> dict[str, Any]:
    if name in _ANALYST_HANDLERS and not is_analista:
        return {
            "ok": False,
            "error": (
                "Predicciones requieren iniciar sesión como analista. "
                "Los datos históricos sí están disponibles sin login."
            ),
        }
    handler = _PUBLIC_HANDLERS.get(name) or _ANALYST_HANDLERS.get(name)
    if not handler:
        return {"ok": False, "error": f"Herramienta desconocida: {name}"}
    try:
        result = handler(args or {})
        return {"ok": True, "data": result}
    except Exception as exc:  # noqa: BLE001 — respuesta estructurada al LLM
        return {"ok": False, "error": str(exc)}
