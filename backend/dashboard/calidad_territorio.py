"""
F2 / G03 — Calidad territorial: discrepancia entre ID Mede y poligono PostGIS.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi
from .territorio_sql import (
    append_filtro_bbox,
    append_filtro_geojson,
    append_filtros_territoriales,
    meta_bbox_dict,
    meta_filtros_dict,
)


def _where_periodo(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    alias: str = "i",
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> tuple[str, list[Any]]:
    wh = [
        f"{alias}.fecha_incidente >= %s",
        f"{alias}.fecha_incidente <= %s",
        f"{alias}.ubicacion IS NOT NULL",
    ]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(wh, params, filtros, alias=alias)
    append_filtro_bbox(wh, params, bbox, alias=alias)
    append_filtro_geojson(wh, params, geojson, alias=alias)
    return " AND ".join(wh), params


def _pct(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return round(100.0 * num / den, 2)


def build_calidad_territorio_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    limite_ejemplos: int = 10,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    wh, params = _where_periodo(inicio, fin, filtros, bbox=bbox, geojson=geojson)

    sql_stats = f"""
    SELECT
        count(*)::bigint AS con_ubicacion,
        count(*) FILTER (WHERE i.comuna_id_espacial IS NOT NULL)::bigint AS match_comuna,
        count(*) FILTER (WHERE i.barrio_id_espacial IS NOT NULL)::bigint AS match_barrio,
        count(*) FILTER (
            WHERE i.comuna_id IS DISTINCT FROM i.comuna_id_espacial
        )::bigint AS disc_comuna,
        count(*) FILTER (
            WHERE i.barrio_id IS DISTINCT FROM i.barrio_id_espacial
        )::bigint AS disc_barrio,
        count(*) FILTER (
            WHERE i.comuna_id IS DISTINCT FROM i.comuna_id_espacial
               OR i.barrio_id IS DISTINCT FROM i.barrio_id_espacial
        )::bigint AS disc_cualquiera
    FROM incidente i
    WHERE {wh}
    """

    sql_ejemplos = f"""
    SELECT
        i.radicado,
        i.fecha_incidente,
        co_reg.nombre AS comuna_registro,
        co_esp.nombre AS comuna_espacial,
        b_reg.nombre AS barrio_registro,
        b_esp.nombre AS barrio_espacial
    FROM incidente i
    LEFT JOIN comuna co_reg ON co_reg.id = i.comuna_id
    LEFT JOIN comuna co_esp ON co_esp.id = i.comuna_id_espacial
    LEFT JOIN barrio b_reg ON b_reg.id = i.barrio_id
    LEFT JOIN barrio b_esp ON b_esp.id = i.barrio_id_espacial
    WHERE {wh}
      AND (
            i.comuna_id IS DISTINCT FROM i.comuna_id_espacial
            OR i.barrio_id IS DISTINCT FROM i.barrio_id_espacial
          )
    ORDER BY i.fecha_incidente DESC, i.radicado
    LIMIT %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_stats, params)
        row = cursor.fetchone()
        con_ub, match_c, match_b, disc_c, disc_b, disc_any = (int(x or 0) for x in row)

        ejemplos: list[dict[str, Any]] = []
        if limite_ejemplos > 0 and disc_any > 0:
            cursor.execute(sql_ejemplos, params + [limite_ejemplos])
            for r in cursor.fetchall():
                ejemplos.append(
                    {
                        "radicado": r[0],
                        "fecha_incidente": r[1].isoformat() if r[1] else None,
                        "comuna_registro": r[2],
                        "comuna_espacial": r[3],
                        "barrio_registro": r[4],
                        "barrio_espacial": r[5],
                    }
                )

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "indicador": "G03",
            "modo_territorio_recomendado": "hibrido",
            "politica": (
                "Por defecto los indicadores usan comuna_id/barrio_id del registro Mede. "
                "Parametro API territorio=espacial (F3) usara comuna_id_espacial/barrio_id_espacial."
            ),
            "con_ubicacion": con_ub,
            "match_comuna_espacial": match_c,
            "match_barrio_espacial": match_b,
            "pct_match_comuna": _pct(match_c, con_ub),
            "pct_match_barrio": _pct(match_b, con_ub),
            "discrepancia_comuna": disc_c,
            "discrepancia_barrio": disc_b,
            "discrepancia_cualquiera": disc_any,
            "pct_discrepancia_comuna": _pct(disc_c, con_ub),
            "pct_discrepancia_barrio": _pct(disc_b, con_ub),
            "pct_discrepancia_cualquiera": _pct(disc_any, con_ub),
            "vista_sql": "v_incidente_territorio_discrepancia",
            "filtros": meta_filtros_dict(filtros),
            "bbox": meta_bbox_dict(bbox),
            "filtro_geojson": bool(geojson and str(geojson).strip()),
        },
        "ejemplos_discrepancia": ejemplos,
    }


def territorio_espacial_status() -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'incidente'
                  AND column_name = 'comuna_id_espacial'
            )
            """
        )
        has_cols = cursor.fetchone()[0]
        if not has_cols:
            return {"ready": False, "message": "Ejecute 005_incidente_territorio_espacial.sql"}

        cursor.execute(
            """
            SELECT
                count(*) FILTER (WHERE ubicacion IS NOT NULL) AS con_ubicacion,
                count(*) FILTER (WHERE comuna_id_espacial IS NOT NULL) AS con_comuna_esp,
                count(*) FILTER (WHERE barrio_id_espacial IS NOT NULL) AS con_barrio_esp,
                count(*) FILTER (
                    WHERE ubicacion IS NOT NULL
                      AND (
                            comuna_id IS DISTINCT FROM comuna_id_espacial
                            OR barrio_id IS DISTINCT FROM barrio_id_espacial
                      )
                ) AS discrepancias
            FROM incidente
            """
        )
        row = cursor.fetchone()
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views
                WHERE table_schema = 'public'
                  AND table_name = 'v_incidente_territorio_discrepancia'
            )
            """
        )
        has_view = cursor.fetchone()[0]

    con_ub, com_esp, bar_esp, disc = (int(x or 0) for x in row)
    return {
        "ready": True,
        "con_ubicacion": con_ub,
        "con_comuna_espacial": com_esp,
        "con_barrio_espacial": bar_esp,
        "discrepancias": disc,
        "pct_discrepancia": _pct(disc, con_ub),
        "vista_discrepancia": has_view,
    }
