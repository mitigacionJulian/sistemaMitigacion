"""
Coroplética territorial — concentración de incidentes por polígono (G01 en mapa).

Devuelve GeoJSON con incidentes, densidad por km² y ratio vs. ciudad por feature.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

from django.db import connection

from .densidad_territorial import _incidentes_where, _query_densidad_ciudad
from .kpis import FiltrosKpi
from .geo_topojson import wrap_choropleth_with_topojson
from .map_cache import choropleth_cache_key, get_cached_map_payload
from .territorio_sql import (
    barrio_fk_col,
    comuna_fk_col,
    meta_filtros_dict,
    nota_modo_territorio,
)

NivelChoropleth = Literal["comuna", "barrio"]
MetricaChoropleth = Literal["densidad", "conteo"]

# Simplificación WGS84 (~8 m) para respuesta web más liviana sin perder forma municipal.
CHOROPLETH_SIMPLIFY_TOLERANCE = 0.00008


def parse_nivel_choropleth(raw: str | None) -> NivelChoropleth:
    if raw and str(raw).strip().lower() == "barrio":
        return "barrio"
    return "comuna"


def parse_metrica_choropleth(raw: str | None) -> MetricaChoropleth:
    if raw and str(raw).strip().lower() in ("conteo", "count", "incidentes"):
        return "conteo"
    return "densidad"


def _query_choropleth_comuna(
    wh: str,
    params: list[Any],
    col: str,
) -> list[dict[str, Any]]:
    sql = f"""
    WITH incidentes AS (
      SELECT i.id, i.{col} AS territorio_id
      FROM incidente i
      WHERE {wh}
    ),
    territorios AS (
      SELECT
        c.id,
        c.nombre,
        c.codigo,
        (ST_Area(c.geom::geography) / 1e6)::double precision AS area_km2,
        ST_AsGeoJSON(ST_Simplify(c.geom, %s))::text AS geometry_json
      FROM comuna c
      WHERE c.geom IS NOT NULL
    ),
    agg AS (
      SELECT
        t.id,
        t.nombre,
        t.codigo,
        t.area_km2,
        t.geometry_json,
        COUNT(i.id)::int AS incidentes
      FROM territorios t
      LEFT JOIN incidentes i ON i.territorio_id = t.id
      GROUP BY t.id, t.nombre, t.codigo, t.area_km2, t.geometry_json
    )
    SELECT
      id,
      nombre,
      codigo,
      area_km2,
      geometry_json,
      incidentes,
      CASE WHEN area_km2 > 0 THEN incidentes / area_km2 ELSE 0 END AS densidad_km2
    FROM agg
    ORDER BY densidad_km2 DESC, incidentes DESC
    """
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, [*params, CHOROPLETH_SIMPLIFY_TOLERANCE])
        for cid, nombre, codigo, area_km2, geometry_json, incidentes, densidad_km2 in cursor.fetchall():
            if not geometry_json:
                continue
            rows.append(
                {
                    "territorio_id": int(cid),
                    "nombre": str(nombre or ""),
                    "codigo": str(codigo or ""),
                    "area_km2": round(float(area_km2 or 0), 6),
                    "incidentes": int(incidentes or 0),
                    "densidad_km2": round(float(densidad_km2 or 0), 4),
                    "geometry": json.loads(geometry_json),
                }
            )
    return rows


def _query_choropleth_barrio(
    wh: str,
    params: list[Any],
    col: str,
    comuna_id: int | None,
    barrio_id: int | None,
) -> list[dict[str, Any]]:
    poly_where = ["b.geom IS NOT NULL"]
    poly_params: list[Any] = []
    if barrio_id is not None:
        poly_where.append("b.id = %s")
        poly_params.append(barrio_id)
    elif comuna_id is not None:
        poly_where.append("b.comuna_id = %s")
        poly_params.append(comuna_id)
    poly_wh = " AND ".join(poly_where)

    sql = f"""
    WITH incidentes AS (
      SELECT i.id, i.{col} AS territorio_id
      FROM incidente i
      WHERE {wh}
    ),
    territorios AS (
      SELECT
        b.id,
        b.nombre,
        b.codigo,
        (ST_Area(b.geom::geography) / 1e6)::double precision AS area_km2,
        co.nombre AS comuna_nombre,
        ST_AsGeoJSON(ST_Simplify(b.geom, %s))::text AS geometry_json
      FROM barrio b
      LEFT JOIN comuna co ON co.id = b.comuna_id
      WHERE {poly_wh}
    ),
    agg AS (
      SELECT
        t.id,
        t.nombre,
        t.codigo,
        t.area_km2,
        t.comuna_nombre,
        t.geometry_json,
        COUNT(i.id)::int AS incidentes
      FROM territorios t
      LEFT JOIN incidentes i ON i.territorio_id = t.id
      GROUP BY t.id, t.nombre, t.codigo, t.area_km2, t.comuna_nombre, t.geometry_json
    )
    SELECT
      id,
      nombre,
      codigo,
      area_km2,
      comuna_nombre,
      geometry_json,
      incidentes,
      CASE WHEN area_km2 > 0 THEN incidentes / area_km2 ELSE 0 END AS densidad_km2
    FROM agg
    ORDER BY densidad_km2 DESC, incidentes DESC
    """
    qparams = list(params) + poly_params + [CHOROPLETH_SIMPLIFY_TOLERANCE]
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
        for (
            bid,
            nombre,
            codigo,
            area_km2,
            comuna_nombre,
            geometry_json,
            incidentes,
            densidad_km2,
        ) in cursor.fetchall():
            if not geometry_json:
                continue
            item: dict[str, Any] = {
                "territorio_id": int(bid),
                "nombre": str(nombre or ""),
                "codigo": str(codigo or ""),
                "area_km2": round(float(area_km2 or 0), 6),
                "incidentes": int(incidentes or 0),
                "densidad_km2": round(float(densidad_km2 or 0), 4),
                "geometry": json.loads(geometry_json),
            }
            if comuna_nombre:
                item["comuna_nombre"] = str(comuna_nombre)
            rows.append(item)
    return rows


def build_choropleth_territorial_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    nivel: NivelChoropleth = "comuna",
    metrica: MetricaChoropleth = "densidad",
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    cache_key = choropleth_cache_key(
        inicio.isoformat(),
        fin.isoformat(),
        filtros,
        nivel=nivel,
        metrica=metrica,
    )

    def _build() -> dict[str, Any]:
        return _build_choropleth_territorial_payload_uncached(
            inicio, fin, filtros, nivel=nivel, metrica=metrica
        )

    return get_cached_map_payload(cache_key, _build)


def _build_choropleth_territorial_payload_uncached(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    *,
    nivel: NivelChoropleth,
    metrica: MetricaChoropleth,
) -> dict[str, Any]:
    wh, params = _incidentes_where(inicio, fin, filtros, None, None)
    modo = filtros.modo_territorio or "registro"
    col = comuna_fk_col(modo) if nivel == "comuna" else barrio_fk_col(modo)

    total_incidentes, area_ciudad_km2 = _query_densidad_ciudad(wh, params, nivel)
    densidad_ciudad = (
        round(total_incidentes / area_ciudad_km2, 4) if area_ciudad_km2 > 0 else None
    )

    if nivel == "comuna":
        rows = _query_choropleth_comuna(wh, params, col)
    else:
        rows = _query_choropleth_barrio(
            wh,
            params,
            col,
            filtros.comuna_id,
            filtros.barrio_id,
        )

    metric_key = "incidentes" if metrica == "conteo" else "densidad_km2"
    values = [float(r.get(metric_key) or 0) for r in rows if (r.get(metric_key) or 0) > 0]
    val_min = min(values) if values else 0.0
    val_max = max(values) if values else 0.0

    features: list[dict[str, Any]] = []
    for row in rows:
        inc = int(row.get("incidentes") or 0)
        dens = float(row.get("densidad_km2") or 0)
        ratio = round(dens / densidad_ciudad, 4) if densidad_ciudad and densidad_ciudad > 0 else None
        props: dict[str, Any] = {
            "id": row["territorio_id"],
            "territorio_id": row["territorio_id"],
            "nombre": row["nombre"],
            "codigo": row.get("codigo") or "",
            "incidentes": inc,
            "area_km2": row.get("area_km2"),
            "densidad_km2": dens,
            "ratio_vs_ciudad": ratio,
            "valor_coropletica": inc if metrica == "conteo" else dens,
            "sin_datos": inc == 0,
        }
        if row.get("comuna_nombre"):
            props["comuna_nombre"] = row["comuna_nombre"]
        features.append(
            {
                "type": "Feature",
                "id": row["territorio_id"],
                "properties": props,
                "geometry": row["geometry"],
            }
        )

    with_incidentes = sum(1 for r in rows if (r.get("incidentes") or 0) > 0)

    payload = {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "indicador": "coropletica-G01",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "nivel": nivel,
            "metrica": metrica,
            "metrica_etiqueta": (
                "Incidentes en el periodo" if metrica == "conteo" else "Densidad (incidentes / km²)"
            ),
            "total_incidentes": total_incidentes,
            "area_ciudad_km2": round(area_ciudad_km2, 4) if area_ciudad_km2 else None,
            "densidad_ciudad_km2": densidad_ciudad,
            "poligonos_devueltos": len(features),
            "poligonos_con_incidentes": with_incidentes,
            "valor_min": round(val_min, 4),
            "valor_max": round(val_max, 4),
            "sin_datos": total_incidentes == 0 or with_incidentes == 0,
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            "srid": 4326,
            "limitaciones": (
                "Territorios sin polígono PostGIS no aparecen. La escala es relativa al periodo "
                "y filtros activos; no implica causalidad ni riesgo individual."
            ),
        },
    }
    return wrap_choropleth_with_topojson(payload)
