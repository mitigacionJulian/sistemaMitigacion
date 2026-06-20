"""Parseo de parámetros de consulta para reportes con filtros de tablero/mapa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from dashboard.kpis import FiltrosKpi
from dashboard.hotspots import (
    clamp_tamano_celda_m,
    parse_metodo_hotspot,
)
from dashboard.choropleth_territorial import (
    MetricaChoropleth,
    NivelChoropleth,
    parse_metrica_choropleth,
)
from dashboard.predicciones_mensuales import MA_VENTANA_DEFAULT, MA_VENTANA_MAX, MA_VENTANA_MIN
from dashboard.territorio_sql import parse_filtro_geojson, parse_modo_territorio


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def parse_tablero_query(query: dict | None) -> tuple[date, date, FiltrosKpi, int]:
    """
    Extrae rango de fechas, filtros KPI y top_n desde un dict (body.query o query string).
    """
    q = query or {}
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    desde_raw = q.get("desde")
    hasta_raw = q.get("hasta")
    desde = date.fromisoformat(desde_raw) if desde_raw else default_desde
    hasta = date.fromisoformat(hasta_raw) if hasta_raw else default_hasta

    filtros = FiltrosKpi(
        comuna_id=_optional_int(q.get("comuna_id")),
        barrio_id=_optional_int(q.get("barrio_id")),
        clase_incidente_id=_optional_int(q.get("clase_incidente_id")),
        modo_territorio=parse_modo_territorio(q.get("territorio")),
    )

    top_n = _optional_int(q.get("top_n"))
    if top_n is None:
        top_n = 10
    top_n = min(max(top_n, 1), 25)

    return desde, hasta, filtros, top_n


@dataclass(frozen=True)
class MapaQuery:
    view_mode: str
    choropleth_metric: MetricaChoropleth
    nivel: NivelChoropleth
    map_limite: int
    metodo_hotspot: str
    tamano_celda_m: float
    geojson: str | None


def resolve_mapa_nivel(view_mode: str, filtros: FiltrosKpi) -> NivelChoropleth:
    """Misma lógica que el mapa interactivo (resolveChoroplethNivel)."""
    if filtros.barrio_id is not None:
        return "barrio"
    if view_mode == "detalle" and filtros.comuna_id is not None:
        return "barrio"
    return "comuna"


def parse_mapa_query(query: dict | None, filtros: FiltrosKpi) -> MapaQuery:
    q = query or {}
    view_mode = str(q.get("view_mode") or "territorio").strip().lower()
    if view_mode not in ("territorio", "detalle", "cuadricula"):
        view_mode = "territorio"

    choropleth_metric = parse_metrica_choropleth(q.get("choropleth_metric"))
    nivel = resolve_mapa_nivel(view_mode, filtros)

    map_limite = _optional_int(q.get("map_limite"))
    if map_limite is None:
        map_limite = 10_000
    map_limite = max(0, min(100_000, map_limite))

    metodo_hotspot = parse_metodo_hotspot(q.get("metodo_hotspot"))
    tamano_celda_raw = q.get("tamano_celda_m")
    tamano_celda_m = clamp_tamano_celda_m(tamano_celda_raw, metodo=metodo_hotspot)

    geojson = parse_filtro_geojson(q.get("geojson"))
    return MapaQuery(
        view_mode=view_mode,
        choropleth_metric=choropleth_metric,
        nivel=nivel,
        map_limite=map_limite,
        metodo_hotspot=metodo_hotspot,
        tamano_celda_m=tamano_celda_m,
        geojson=geojson,
    )


def _parse_bool_flag(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "si", "sí", "yes")


def _parse_horizonte_meses(q: dict) -> int:
    raw = q.get("horizonte_meses") or q.get("meses")
    if raw is None or raw == "":
        return 3
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return 3
    return max(1, min(12, v))


def _parse_ventana_ma(q: dict) -> int:
    raw = q.get("ventana_ma") or q.get("ventana") or MA_VENTANA_DEFAULT
    try:
        v = int(raw)
    except (TypeError, ValueError):
        raise ValueError("ventana_ma")
    if not (MA_VENTANA_MIN <= v <= MA_VENTANA_MAX):
        raise ValueError("ventana_ma")
    return v


def _parse_modelo_pred(q: dict) -> str:
    raw = (q.get("modelo_pred") or q.get("modelo") or "ols").strip().lower()
    aliases = {
        "ols": "ols",
        "lineal": "ols",
        "estacional": "estacional",
        "seasonal": "estacional",
        "poisson": "poisson",
        "glm_poisson": "poisson",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
        "arima": "arima",
        "sarima": "sarima",
        "seasonal_arima": "sarima",
        "tres_sigma": "tres_sigma",
        "3_sigma": "tres_sigma",
        "3sigma": "tres_sigma",
        "tres_desviaciones": "tres_sigma",
        "media_3sigma": "tres_sigma",
    }
    if raw not in aliases:
        raise ValueError("modelo_pred")
    return aliases[raw]


def _parse_modelo_prop(q: dict) -> str:
    raw = (q.get("modelo_prop") or q.get("modelo") or "estacional").strip().lower()
    aliases = {
        "ols": "ols",
        "lineal": "ols",
        "logistica": "logistica",
        "logistic": "logistica",
        "estacional": "estacional",
        "seasonal": "estacional",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
        "arima": "arima",
        "sarima": "sarima",
        "seasonal_arima": "sarima",
    }
    if raw not in aliases:
        raise ValueError("modelo_prop")
    return aliases[raw]


def _parse_modelo_carga(q: dict) -> str:
    raw = (q.get("modelo_carga") or q.get("modelo") or "estacional").strip().lower()
    aliases = {
        "ols": "ols",
        "lineal": "ols",
        "estacional": "estacional",
        "seasonal": "estacional",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
        "arima": "arima",
        "sarima": "sarima",
        "seasonal_arima": "sarima",
        "tres_sigma": "tres_sigma",
        "3_sigma": "tres_sigma",
        "3sigma": "tres_sigma",
        "tres_desviaciones": "tres_sigma",
        "media_3sigma": "tres_sigma",
    }
    if raw not in aliases:
        raise ValueError("modelo_carga")
    return aliases[raw]


def _parse_variable_pred(q: dict) -> str:
    raw = (q.get("variable") or "incidentes").strip().lower()
    aliases = {
        "incidentes": "incidentes",
        "incidente": "incidentes",
        "victimas": "victimas",
        "victima": "victimas",
        "victimas_fatales": "victimas_fatales",
        "fatales": "victimas_fatales",
        "fatal": "victimas_fatales",
    }
    if raw not in aliases:
        raise ValueError("variable")
    return aliases[raw]


def _parse_nivel_territorio(q: dict, key: str, default: str = "comuna") -> str:
    raw = (q.get(key) or default).strip().lower()
    if raw not in ("comuna", "barrio"):
        raise ValueError(key)
    return raw


@dataclass(frozen=True)
class PrediccionesQuery:
    horizonte_meses: int
    modelo_pred: str
    modelo_prop: str
    modelo_carga: str
    variable: str
    ventana_ma: int
    nivel_prioridad: str
    nivel_carga: str
    limite_prioridad: int
    limite_carga: int
    excluir_covid: bool
    desglose_clase: bool
    desglose_comuna: bool
    serie_clase_idx: int
    serie_comuna_idx: int


def parse_predicciones_query(query: dict | None) -> PrediccionesQuery:
    q = query or {}
    limite_prioridad = _optional_int(q.get("limite_prioridad") or q.get("limite"))
    if limite_prioridad is None:
        limite_prioridad = 15
    limite_prioridad = min(max(limite_prioridad, 1), 50)

    limite_carga = _optional_int(q.get("limite_carga"))
    if limite_carga is None:
        limite_carga = 12
    limite_carga = min(max(limite_carga, 1), 50)

    serie_clase_idx = _optional_int(q.get("serie_clase_idx"))
    if serie_clase_idx is None:
        serie_clase_idx = 0
    serie_clase_idx = max(0, serie_clase_idx)

    serie_comuna_idx = _optional_int(q.get("serie_comuna_idx"))
    if serie_comuna_idx is None:
        serie_comuna_idx = 0
    serie_comuna_idx = max(0, serie_comuna_idx)

    return PrediccionesQuery(
        horizonte_meses=_parse_horizonte_meses(q),
        modelo_pred=_parse_modelo_pred(q),
        modelo_prop=_parse_modelo_prop(q),
        modelo_carga=_parse_modelo_carga(q),
        variable=_parse_variable_pred(q),
        ventana_ma=_parse_ventana_ma(q),
        nivel_prioridad=_parse_nivel_territorio(q, "nivel_prioridad", "comuna"),
        nivel_carga=_parse_nivel_territorio(q, "nivel_carga", "comuna"),
        limite_prioridad=limite_prioridad,
        limite_carga=limite_carga,
        excluir_covid=_parse_bool_flag(q.get("excluir_covid")) if q.get("excluir_covid") not in (None, "") else True,
        desglose_clase=_parse_bool_flag(q.get("desglose_clase")),
        desglose_comuna=_parse_bool_flag(q.get("desglose_comuna")),
        serie_clase_idx=serie_clase_idx,
        serie_comuna_idx=serie_comuna_idx,
    )
