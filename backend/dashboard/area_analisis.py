"""
Resumen exploratorio del polígono dibujado en el mapa (modo área P14).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import _fatal_sql_expr, dias_en_rango


def _polygon_area_km2(geojson: str) -> float:
    sql = """
    SELECT ST_Area(
      ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 3857)
    )::double precision / 1e6
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [geojson])
        row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _victimas_fatales_en_filtro(where: str, params: list[Any]) -> int:
    fatal = _fatal_sql_expr("gv")
    sql = f"""
    SELECT COALESCE(SUM(CASE WHEN {fatal} THEN 1 ELSE 0 END), 0)::bigint
    FROM incidente i
    LEFT JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    WHERE {where}
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _clases_principales(where: str, params: list[Any], *, limite: int = 5) -> list[dict[str, Any]]:
    sql = f"""
    SELECT
      COALESCE(ci.nombre, 'Sin clase') AS clase,
      COUNT(DISTINCT i.id)::int AS conteo
    FROM incidente i
    LEFT JOIN clase_incidente ci ON i.clase_incidente_id = ci.id
    WHERE {where}
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT %s
    """
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, [*params, limite])
        for clase, conteo in cursor.fetchall():
            rows.append({"clase": str(clase), "conteo": int(conteo)})
    return rows


def build_area_resumen(
    inicio: date,
    fin: date,
    where: str,
    params: list[Any],
    geojson: str,
    *,
    total_incidentes: int,
    total_celdas: int,
    celdas_devueltas: int,
    tamano_celda_m: float,
    grid_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Métricas agregadas del polígono y la cuadrícula P14 dentro de él."""
    area_km2 = round(_polygon_area_km2(geojson), 4)
    dias = max(1, dias_en_rango(inicio, fin))
    densidad_area = (
        round(total_incidentes / area_km2, 4) if area_km2 > 0 and total_incidentes > 0 else 0.0
    )
    fatales = _victimas_fatales_en_filtro(where, params)
    clases = _clases_principales(where, params)
    for item in clases:
        item["porcentaje"] = (
            round(item["conteo"] / total_incidentes * 100, 1) if total_incidentes > 0 else 0.0
        )

    top_celdas: list[dict[str, Any]] = []
    for rank, row in enumerate(grid_rows[:5], start=1):
        top_celdas.append(
            {
                "rank": rank,
                "conteo": row.get("conteo"),
                "densidad_por_km2": row.get("densidad_por_km2"),
                "area_km2": row.get("area_km2"),
            }
        )

    celda_top = top_celdas[0] if top_celdas else None
    conteo_celdas = sum(int(r.get("conteo") or 0) for r in grid_rows)
    promedio_celda = round(conteo_celdas / len(grid_rows), 2) if grid_rows else 0.0

    return {
        "area_km2": area_km2,
        "total_incidentes": total_incidentes,
        "densidad_incidentes_km2": densidad_area,
        "tasa_incidentes_por_dia": round(total_incidentes / dias, 4),
        "dias_en_periodo": dias,
        "victimas_fatales": fatales,
        "total_celdas_estimadas": total_celdas,
        "celdas_con_datos": celdas_devueltas,
        "promedio_incidentes_por_celda": promedio_celda,
        "tamano_celda_m": tamano_celda_m,
        "celda_mas_caliente": celda_top,
        "top_celdas": top_celdas,
        "clases_principales": clases,
        "nota": (
            "Resumen exploratorio del polígono dibujado. La densidad del área usa la superficie "
            "del polígono; las celdas P14 se recortan al borde (ST_Intersection). No implica causalidad."
        ),
    }
