"""
F5 / G01–G02 — Densidad de incidentes por km² (comuna/barrio) y ratio vs. media ciudad.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from django.db import connection

from .kpis import FiltrosKpi
from .territorio_sql import (
    append_filtro_bbox,
    append_filtro_geojson,
    append_filtros_territoriales,
    barrio_fk_col,
    comuna_fk_col,
    meta_bbox_dict,
    meta_filtros_dict,
    nota_modo_territorio,
)

NivelDensidad = Literal["comuna", "barrio"]
DEFAULT_LIMITE_DENSIDAD = 16
MAX_LIMITE_DENSIDAD = 50


def clamp_limite_densidad(raw: int | None) -> int:
    if raw is None:
        return DEFAULT_LIMITE_DENSIDAD
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMITE_DENSIDAD
    return max(1, min(MAX_LIMITE_DENSIDAD, v))


def _incidentes_where(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    bbox: tuple[float, float, float, float] | None,
    geojson: str | None,
) -> tuple[str, list[Any]]:
    where = [
        "i.fecha_incidente >= %s",
        "i.fecha_incidente <= %s",
        "i.ubicacion IS NOT NULL",
    ]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)
    append_filtro_bbox(where, params, bbox)
    append_filtro_geojson(where, params, geojson)
    return " AND ".join(where), params


def _query_densidad_ciudad(
    wh: str,
    params: list[Any],
    nivel: NivelDensidad,
) -> tuple[int, float]:
    tabla = "comuna" if nivel == "comuna" else "barrio"
    sql_inc = f"SELECT COUNT(*)::bigint FROM incidente i WHERE {wh}"
    sql_area = f"""
    SELECT COALESCE(SUM(ST_Area(geom::geography) / 1e6), 0)::double precision
    FROM {tabla}
    WHERE geom IS NOT NULL
    """
    with connection.cursor() as cursor:
        cursor.execute(sql_inc, params)
        total = int((cursor.fetchone() or [0])[0] or 0)
        cursor.execute(sql_area)
        area = float((cursor.fetchone() or [0])[0] or 0)
    return total, area


def _query_ranking_densidad(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    nivel: NivelDensidad,
    limite: int,
    bbox: tuple[float, float, float, float] | None,
    geojson: str | None,
) -> list[dict[str, Any]]:
    wh, params = _incidentes_where(inicio, fin, filtros, bbox, geojson)
    modo = filtros.modo_territorio or "registro"
    col = comuna_fk_col(modo) if nivel == "comuna" else barrio_fk_col(modo)

    if nivel == "comuna":
        sql = f"""
        WITH incidentes AS (
          SELECT i.id, i.{col} AS territorio_id
          FROM incidente i
          WHERE {wh}
        ),
        territorios AS (
          SELECT c.id, c.nombre, c.codigo,
            (ST_Area(c.geom::geography) / 1e6)::double precision AS area_km2
          FROM comuna c
          WHERE c.geom IS NOT NULL
        ),
        agg AS (
          SELECT
            t.id,
            t.nombre,
            t.codigo,
            t.area_km2,
            COUNT(i.id)::int AS incidentes
          FROM territorios t
          LEFT JOIN incidentes i ON i.territorio_id = t.id
          GROUP BY t.id, t.nombre, t.codigo, t.area_km2
        )
        SELECT
          id,
          nombre,
          codigo,
          area_km2,
          incidentes,
          CASE WHEN area_km2 > 0 THEN incidentes / area_km2 ELSE 0 END AS densidad_km2,
          NULL::text AS comuna_nombre
        FROM agg
        WHERE incidentes > 0
        ORDER BY densidad_km2 DESC, incidentes DESC
        LIMIT %s
        """
    else:
        sql = f"""
        WITH incidentes AS (
          SELECT i.id, i.{col} AS territorio_id
          FROM incidente i
          WHERE {wh}
        ),
        territorios AS (
          SELECT b.id, b.nombre, b.codigo,
            (ST_Area(b.geom::geography) / 1e6)::double precision AS area_km2,
            co.nombre AS comuna_nombre
          FROM barrio b
          LEFT JOIN comuna co ON co.id = b.comuna_id
          WHERE b.geom IS NOT NULL
        ),
        agg AS (
          SELECT
            t.id,
            t.nombre,
            t.codigo,
            t.area_km2,
            t.comuna_nombre,
            COUNT(i.id)::int AS incidentes
          FROM territorios t
          LEFT JOIN incidentes i ON i.territorio_id = t.id
          GROUP BY t.id, t.nombre, t.codigo, t.area_km2, t.comuna_nombre
        )
        SELECT
          id,
          nombre,
          codigo,
          area_km2,
          incidentes,
          CASE WHEN area_km2 > 0 THEN incidentes / area_km2 ELSE 0 END AS densidad_km2,
          comuna_nombre
        FROM agg
        WHERE incidentes > 0
        ORDER BY densidad_km2 DESC, incidentes DESC
        LIMIT %s
        """
    qparams = list(params) + [limite]
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
        cols = [c[0] for c in cursor.description]
        for raw in cursor.fetchall():
            row = dict(zip(cols, raw))
            area = float(row.get("area_km2") or 0)
            inc = int(row.get("incidentes") or 0)
            dens = float(row.get("densidad_km2") or 0)
            item: dict[str, Any] = {
                "territorio_id": int(row["id"]),
                "nombre": str(row.get("nombre") or ""),
                "codigo": str(row.get("codigo") or ""),
                "incidentes": inc,
                "area_km2": round(area, 6),
                "densidad_km2": round(dens, 4),
            }
            if nivel == "barrio" and row.get("comuna_nombre"):
                item["comuna_nombre"] = str(row["comuna_nombre"])
            rows.append(item)
    return rows


def build_densidad_territorial_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    nivel: NivelDensidad = "comuna",
    limite: int = DEFAULT_LIMITE_DENSIDAD,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    limite = clamp_limite_densidad(limite)
    wh, params = _incidentes_where(inicio, fin, filtros, bbox, geojson)
    total_incidentes, area_ciudad_km2 = _query_densidad_ciudad(wh, params, nivel)
    densidad_ciudad = (
        round(total_incidentes / area_ciudad_km2, 4) if area_ciudad_km2 > 0 else None
    )

    ranking = _query_ranking_densidad(inicio, fin, filtros, nivel, limite, bbox, geojson)
    for rank, row in enumerate(ranking, start=1):
        row["rank"] = rank
        if densidad_ciudad and densidad_ciudad > 0:
            row["ratio_vs_ciudad"] = round(row["densidad_km2"] / densidad_ciudad, 4)
        else:
            row["ratio_vs_ciudad"] = None

    return {
        "meta": {
            "indicador": "G01-G02",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "nivel": nivel,
            "limite": limite,
            "total_incidentes": total_incidentes,
            "area_ciudad_km2": round(area_ciudad_km2, 4) if area_ciudad_km2 else None,
            "densidad_ciudad_km2": densidad_ciudad,
            "territorios_devueltos": len(ranking),
            "sin_datos": total_incidentes == 0 or len(ranking) == 0,
            "filtros": meta_filtros_dict(filtros),
            "bbox": meta_bbox_dict(bbox),
            "filtro_geojson": bool(geojson and str(geojson).strip()),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            "descripcion_g01": (
                "Incidentes en el periodo divididos entre el área del polígono oficial (km²)."
            ),
            "descripcion_g02": (
                "ratio_vs_ciudad = densidad del territorio / densidad promedio de la ciudad "
                "(total incidentes / suma de áreas con geometría)."
            ),
            "limitaciones": (
                "Barrios sin polígono cargado quedan fuera. El ratio G02 es relativo al periodo "
                "y filtros activos; no implica riesgo individual ni causalidad."
            ),
        },
        "ranking": ranking,
    }
