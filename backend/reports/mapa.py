"""Reporte de mapa (Fase 2): territorio, detalle y hotspots de área/cuadrícula."""
from __future__ import annotations

from datetime import date
from typing import Any

from dashboard.calidad_territorio import build_calidad_territorio_payload
from dashboard.choropleth_territorial import build_choropleth_territorial_payload
from dashboard.hotspots import build_hotspots_payload
from dashboard.kpis import FiltrosKpi
from dashboard.mapa_detalle import build_mapa_detalle_payload

from .params import MapaQuery

TOP_TERRITORIOS_LIMITE = 15
TOP_CELDAS_LIMITE = 15


def _feature_props(feature: dict[str, Any]) -> dict[str, Any]:
    return feature.get("properties") or {}


def _territorio_row_from_props(props: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "nombre": props.get("nombre"),
        "comuna_nombre": props.get("comuna_nombre"),
        "incidentes": props.get("incidentes"),
        "densidad_km2": props.get("densidad_km2"),
        "ratio_vs_ciudad": props.get("ratio_vs_ciudad"),
        "area_km2": props.get("area_km2"),
        "sin_datos": props.get("sin_datos", False),
    }


def _to_top_territorios(choropleth: dict[str, Any], limite: int = TOP_TERRITORIOS_LIMITE) -> list[dict[str, Any]]:
    ranked: list[tuple[float, int, dict[str, Any]]] = []
    for feature in choropleth.get("features") or []:
        props = _feature_props(feature)
        inc = int(props.get("incidentes") or 0)
        if inc <= 0:
            continue
        dens = float(props.get("densidad_km2") or 0)
        ranked.append((dens, inc, props))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [_territorio_row_from_props(props, i + 1) for i, (_, __, props) in enumerate(ranked[:limite])]


def _to_top_celdas(features: list[dict[str, Any]], limite: int = TOP_CELDAS_LIMITE) -> list[dict[str, Any]]:
    top = sorted(
        (_feature_props(f) for f in (features or [])),
        key=lambda p: int(p.get("conteo") or 0),
        reverse=True,
    )[:limite]
    out: list[dict[str, Any]] = []
    for idx, p in enumerate(top, start=1):
        conteo = int(p.get("conteo") or 0)
        if conteo <= 0:
            continue
        out.append(
            {
                "rank": idx,
                "celda_id": p.get("celda_id") or f"C{idx:03d}",
                "conteo": conteo,
                "intensidad_celda": conteo,
                "densidad_por_km2": float(p.get("densidad_por_km2") or 0),
                "area_km2": float(p.get("area_km2") or 0),
            }
        )
    return out


def _resolve_territorio_resumen(
    choropleth: dict[str, Any],
    filtros: FiltrosKpi,
) -> dict[str, Any] | None:
    target_id = filtros.barrio_id if filtros.barrio_id is not None else filtros.comuna_id
    if target_id is None:
        return None
    for feature in choropleth.get("features") or []:
        props = _feature_props(feature)
        fid = props.get("id", props.get("territorio_id"))
        if fid is None:
            continue
        if str(fid) != str(target_id):
            continue
        row = _territorio_row_from_props(props, 0)
        row.pop("rank", None)
        row["nivel"] = "barrio" if filtros.barrio_id is not None else "comuna"
        return row
    return None


def _choropleth_indicadores(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    return {
        "nivel": meta.get("nivel"),
        "metrica": meta.get("metrica"),
        "metrica_etiqueta": meta.get("metrica_etiqueta"),
        "total_incidentes": meta.get("total_incidentes"),
        "poligonos_devueltos": meta.get("poligonos_devueltos"),
        "poligonos_con_incidentes": meta.get("poligonos_con_incidentes"),
        "densidad_ciudad_km2": meta.get("densidad_ciudad_km2"),
        "valor_min": meta.get("valor_min"),
        "valor_max": meta.get("valor_max"),
        "sin_datos": meta.get("sin_datos"),
        "nota_territorio": meta.get("nota_territorio"),
        "limitaciones": meta.get("limitaciones"),
    }


def _calidad_resumen(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[str, Any] | None:
    try:
        payload = build_calidad_territorio_payload(inicio, fin, filtros, limite_ejemplos=0)
    except Exception:
        return None
    meta = payload.get("meta") or {}
    if not meta.get("con_ubicacion"):
        return None
    return {
        "con_ubicacion": meta.get("con_ubicacion"),
        "pct_match_comuna": meta.get("pct_match_comuna"),
        "pct_match_barrio": meta.get("pct_match_barrio"),
        "pct_discrepancia_cualquiera": meta.get("pct_discrepancia_cualquiera"),
        "discrepancia_cualquiera": meta.get("discrepancia_cualquiera"),
    }


def _interpretacion_mapa(
    modo_vista: str,
    meta_modo: dict[str, Any],
    indicadores: dict[str, Any],
    filtros: FiltrosKpi,
) -> str:
    partes: list[str] = []
    metrica = meta_modo.get("metrica") or indicadores.get("metrica")
    if modo_vista == "territorio":
        nivel = meta_modo.get("nivel") or "comuna"
        partes.append(
            f"Vista territorial por {nivel}: colores según "
            f"{'conteo de incidentes' if metrica == 'conteo' else 'densidad (incidentes / km²)'}."
        )
        if indicadores.get("poligonos_con_incidentes") is not None:
            partes.append(
                f"{indicadores.get('poligonos_con_incidentes')} de "
                f"{indicadores.get('poligonos_devueltos')} polígonos con incidentes en el periodo."
            )
    elif modo_vista == "detalle":
        partes.append(
            "Vista de detalle: contorno territorial y muestra de incidentes georreferenciados."
        )
    else:
        metodo = meta_modo.get("metodo_hotspot") or "cuadricula"
        tam = meta_modo.get("tamano_celda_m")
        if metodo == "area":
            partes.append("Hotspots sobre un área dibujada en el mapa (celdas recortadas al polígono).")
        else:
            partes.append(f"Hotspots en cuadrícula P14 de {tam} m por celda.")
    if filtros.modo_territorio == "espacial":
        partes.append(
            "Modo espacial: atribución por polígono PostGIS (comuna_id_espacial / barrio_id_espacial)."
        )
    return " ".join(partes)


def build_mapa_report_body(
    desde: date,
    hasta: date,
    filtros: FiltrosKpi,
    mapa_query: MapaQuery,
) -> dict[str, Any]:
    view_mode = mapa_query.view_mode
    calidad = _calidad_resumen(desde, hasta, filtros)

    if view_mode == "detalle":
        detalle = build_mapa_detalle_payload(
            desde,
            hasta,
            filtros,
            nivel=mapa_query.nivel,
            metrica=mapa_query.choropleth_metric,
            limite=mapa_query.map_limite,
        )
        choropleth = detalle.get("choropleth") or {}
        meta_ch = choropleth.get("meta") or {}
        meta_modo = {
            "nivel": mapa_query.nivel,
            "metrica": mapa_query.choropleth_metric,
            "limite_puntos": mapa_query.map_limite,
        }
        indicadores = _choropleth_indicadores(meta_ch)
        return {
            "tipo": "mapa",
            "modo_vista": "detalle",
            "meta_modo": meta_modo,
            "indicadores": indicadores,
            "interpretacion": _interpretacion_mapa("detalle", meta_modo, indicadores, filtros),
            "calidad_territorial": calidad,
            "puntos_meta": detalle.get("puntos_meta"),
            "territorio_resumen": _resolve_territorio_resumen(choropleth, filtros),
        }

    if view_mode == "cuadricula":
        hotspots = build_hotspots_payload(
            desde,
            hasta,
            filtros,
            metodo=mapa_query.metodo_hotspot,  # type: ignore[arg-type]
            tamano_celda_m=mapa_query.tamano_celda_m,
            geojson=mapa_query.geojson,
        )
        meta = hotspots.get("meta") or {}
        meta_modo = {
            "metodo_hotspot": mapa_query.metodo_hotspot,
            "tamano_celda_m": mapa_query.tamano_celda_m,
            "filtro_geojson": bool(mapa_query.geojson),
        }
        return {
            "tipo": "mapa",
            "modo_vista": "cuadricula",
            "meta_modo": meta_modo,
            "indicadores": {
                "total_incidentes": meta.get("total_incidentes"),
                "celdas_devueltas": meta.get("celdas_devueltas"),
                "celdas_con_incidentes": meta.get("celdas_con_incidentes"),
                "densidad_max_km2": meta.get("densidad_max_km2"),
                "sin_datos": meta.get("sin_datos"),
            },
            "interpretacion": _interpretacion_mapa("cuadricula", meta_modo, {}, filtros),
            "calidad_territorial": calidad,
            "hotspots_meta": meta,
            "top_celdas": _to_top_celdas(hotspots.get("features") or []),
        }

    choropleth = build_choropleth_territorial_payload(
        desde,
        hasta,
        filtros,
        nivel=mapa_query.nivel,
        metrica=mapa_query.choropleth_metric,
    )
    meta_ch = choropleth.get("meta") or {}
    meta_modo = {
        "nivel": mapa_query.nivel,
        "metrica": mapa_query.choropleth_metric,
    }
    indicadores = _choropleth_indicadores(meta_ch)
    territorio_resumen = _resolve_territorio_resumen(choropleth, filtros)
    top = _to_top_territorios(choropleth)

    return {
        "tipo": "mapa",
        "modo_vista": "territorio",
        "meta_modo": meta_modo,
        "indicadores": indicadores,
        "interpretacion": _interpretacion_mapa("territorio", meta_modo, indicadores, filtros),
        "calidad_territorial": calidad,
        "choropleth_meta": meta_ch,
        "territorio_resumen": territorio_resumen,
        "top_territorios": top,
        "sin_poligono_seleccionado": bool(
            filtros.barrio_id is not None and not territorio_resumen and not top
        ),
    }
