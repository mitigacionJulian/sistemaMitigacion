"""
Puntos de incidentes con coordenadas válidas para mapas (muestra acotada).

F3: filtros territoriales espaciales; consulta sobre incidente.ubicacion (PostGIS).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi
from .map_cache import get_cached_map_payload, incidentes_mapa_cache_key
from .territorio_sql import (
    append_filtro_bbox,
    append_filtro_geojson,
    append_filtros_territoriales,
    meta_bbox_dict,
    meta_filtros_dict,
    nota_modo_territorio,
)

MAPA_CAP_SIN_LIMITE = 100_000

PUNTOS_COLUMNAS = [
    "id",
    "latitud",
    "longitud",
    "radicado",
    "fecha_incidente",
    "clase_incidente",
]


def _puntos_a_compacto(puntos: list[dict[str, Any]]) -> list[list[Any]]:
    compacto: list[list[Any]] = []
    for p in puntos:
        compacto.append(
            [
                p["id"],
                p["latitud"],
                p["longitud"],
                p.get("radicado"),
                p.get("fecha_incidente"),
                p.get("clase_incidente") or "",
            ]
        )
    return compacto


def _query_incidentes_puntos(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    limite_filas: int | None,
    cap_sin_limite: int = MAPA_CAP_SIN_LIMITE,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    where = [
        "i.fecha_incidente >= %s",
        "i.fecha_incidente <= %s",
        "i.ubicacion IS NOT NULL",
    ]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)
    append_filtro_bbox(where, params, bbox)
    append_filtro_geojson(where, params, geojson)

    wh = " AND ".join(where)

    sql_count = f"SELECT COUNT(*)::bigint FROM incidente i WHERE {wh}"
    sql_points = f"""
    SELECT
      i.id,
      i.radicado,
      i.fecha_incidente,
      ST_Y(i.ubicacion)::double precision AS latitud,
      ST_X(i.ubicacion)::double precision AS longitud,
      ci.nombre AS clase_incidente
    FROM incidente i
    LEFT JOIN clase_incidente ci ON ci.id = i.clase_incidente_id
    WHERE {wh}
    ORDER BY i.fecha_incidente DESC, i.id DESC
    LIMIT %s
    """
    puntos: list[dict[str, Any]] = []
    total = 0
    with connection.cursor() as cursor:
        cursor.execute(sql_count, params)
        row = cursor.fetchone()
        total = int(row[0] or 0) if row else 0

        if limite_filas is None:
            sql_limit = min(total, cap_sin_limite) if total > 0 else 0
        else:
            sql_limit = limite_filas

        params_lim = list(params) + [sql_limit]
        cursor.execute(sql_points, params_lim)
        for row in cursor.fetchall():
            puntos.append(
                {
                    "id": int(row[0]),
                    "radicado": row[1],
                    "fecha_incidente": row[2].isoformat() if row[2] else None,
                    "latitud": float(row[3]),
                    "longitud": float(row[4]),
                    "clase_incidente": row[5] or "",
                }
            )
    return puntos, total


def build_incidentes_mapa_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    limite: int = 10_000,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    limite_int = int(limite)
    cache_key = incidentes_mapa_cache_key(
        inicio.isoformat(),
        fin.isoformat(),
        filtros,
        limite=limite_int,
    )

    def _build() -> dict[str, Any]:
        return _build_incidentes_mapa_payload_uncached(
            inicio, fin, filtros, limite_int, bbox, geojson
        )

    return get_cached_map_payload(cache_key, _build)


def _build_incidentes_mapa_payload_uncached(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    limite: int,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    sin_limite_solicitado = int(limite) == 0
    if sin_limite_solicitado:
        puntos, total_con_coord = _query_incidentes_puntos(
            inicio, fin, filtros, None, MAPA_CAP_SIN_LIMITE, bbox, geojson
        )
        lim_aplicado = min(total_con_coord, MAPA_CAP_SIN_LIMITE) if total_con_coord > 0 else 0
    else:
        lim = max(100, min(MAPA_CAP_SIN_LIMITE, int(limite)))
        puntos, total_con_coord = _query_incidentes_puntos(
            inicio, fin, filtros, lim, MAPA_CAP_SIN_LIMITE, bbox, geojson
        )
        lim_aplicado = lim

    truncado = total_con_coord > len(puntos)
    recorte_abs = sin_limite_solicitado and total_con_coord > MAPA_CAP_SIN_LIMITE
    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "limite": lim_aplicado,
            "sin_limite_solicitado": sin_limite_solicitado,
            "tope_absoluto_sin_limite": MAPA_CAP_SIN_LIMITE if sin_limite_solicitado else None,
            "recorte_por_tope_absoluto": recorte_abs,
            "total_con_coordenadas_en_rango": total_con_coord,
            "puntos_devueltos": len(puntos),
            "muestra_truncada": truncado,
            "descripcion": (
                "Incidentes con ubicacion PostGIS en el rango; orden descendente por fecha. "
                "La capa usa circulos semitransparentes: donde hay mas solapamiento se percibe mayor densidad."
            ),
            "filtros": meta_filtros_dict(filtros),
            "bbox": meta_bbox_dict(bbox),
            "filtro_geojson": bool(geojson and str(geojson).strip()),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            "formato_puntos": "compacto",
            "columnas_puntos": PUNTOS_COLUMNAS,
        },
        "puntos": _puntos_a_compacto(puntos),
    }
