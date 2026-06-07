"""
F4 / P14 — Hotspots espaciales exploratorios (PostGIS).

Cuadrícula en EPSG:3857 (metros), opcionalmente acotada por polígono (área dibujada).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Literal

from django.db import connection

from .area_analisis import build_area_resumen
from .kpis import FiltrosKpi
from .map_cache import get_cached_map_payload, hotspots_cache_key
from .territorio_sql import (
    append_filtro_bbox,
    append_filtro_geojson,
    append_filtros_territoriales,
    meta_bbox_dict,
    meta_filtros_dict,
    nota_modo_territorio,
    parse_filtro_geojson,
)

MetodoHotspot = Literal["cuadricula", "area"]

DEFAULT_TAMANO_CELDA_M = 300.0
TAMANO_CELDA_AREA_M = 100.0
MIN_TAMANO_CELDA_M = 50.0
MAX_TAMANO_CELDA_M = 2000.0
DEFAULT_LIMITE_CELDAS = 800
MAX_LIMITE_CELDAS = 2000
MAX_CELDAS_MALLA_AREA = 2000
DEFAULT_LIMITE_RANKING_G06 = 15
MAX_LIMITE_RANKING_G06 = 50


def geojson_cache_fingerprint(geojson: str | None) -> str:
    if not geojson or not str(geojson).strip():
        return ""
    return hashlib.sha256(str(geojson).encode()).hexdigest()[:16]


def clamp_tamano_celda_m(
    raw: float | int | None,
    *,
    metodo: MetodoHotspot = "cuadricula",
) -> float:
    if metodo == "area":
        return TAMANO_CELDA_AREA_M
    if raw is None:
        return DEFAULT_TAMANO_CELDA_M
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_TAMANO_CELDA_M
    return max(MIN_TAMANO_CELDA_M, min(MAX_TAMANO_CELDA_M, v))


def clamp_limite_celdas(raw: int | None) -> int:
    if raw is None:
        return DEFAULT_LIMITE_CELDAS
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMITE_CELDAS
    return max(1, min(MAX_LIMITE_CELDAS, v))


def parse_metodo_hotspot(raw: str | None) -> MetodoHotspot:
    if raw and str(raw).strip().lower() in (
        "area",
        "area_seleccion",
        "seleccion",
        "poligono",
        "polygon",
    ):
        return "area"
    return "cuadricula"


def clamp_limite_ranking_g06(raw: int | None) -> int:
    if raw is None:
        return DEFAULT_LIMITE_RANKING_G06
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMITE_RANKING_G06
    return max(1, min(MAX_LIMITE_RANKING_G06, v))


def _where_clause(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
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


def _count_incidentes(where: str, params: list[Any]) -> int:
    sql = f"SELECT COUNT(*)::bigint FROM incidente i WHERE {where}"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _count_celdas_cuadricula(where: str, params: list[Any], tamano_celda_m: float) -> int:
    sql = f"""
    WITH filtered AS (
      SELECT ST_Transform(i.ubicacion, 3857) AS g3857
      FROM incidente i
      WHERE {where}
    )
    SELECT COUNT(DISTINCT ST_SnapToGrid(g3857, %s))::int FROM filtered
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [*params, tamano_celda_m])
        row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _rows_from_cuadricula_cursor(
    cursor,
    *,
    recortada: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for conteo, area_m2, geometry_json in cursor.fetchall():
        area_km2 = float(area_m2 or 0) / 1_000_000.0
        densidad = float(conteo) / area_km2 if area_km2 > 0 else 0.0
        rows.append(
            {
                "conteo": int(conteo),
                "area_m2": float(area_m2 or 0),
                "area_km2": round(area_km2, 6),
                "densidad_por_km2": round(densidad, 4),
                "geometry": json.loads(geometry_json) if geometry_json else None,
                "recortada": recortada,
            }
        )
    return rows


def _count_celdas_malla_area(clip_geojson: str, tamano_celda_m: float) -> int:
    """Celdas de la malla ST_SquareGrid que intersectan el polígono (modo área)."""
    sql = """
    WITH selection AS (
      SELECT ST_MakeValid(
        ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 3857)
      ) AS poly_3857
    )
    SELECT COUNT(*)::int
    FROM selection s
    CROSS JOIN LATERAL ST_SquareGrid(%s, ST_Envelope(s.poly_3857)) AS g
    WHERE ST_Intersects((g).geom, s.poly_3857)
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [clip_geojson, tamano_celda_m])
        row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _query_cuadricula_malla_area(
    where: str,
    params: list[Any],
    tamano_celda_m: float,
    clip_geojson: str,
) -> list[dict[str, Any]]:
    """Todas las celdas del polígono (conteo 0 en gris en el cliente)."""
    size = tamano_celda_m
    gj = str(clip_geojson).strip()
    sql = f"""
    WITH selection AS (
      SELECT ST_MakeValid(
        ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 3857)
      ) AS poly_3857
    ),
    filtered AS (
      SELECT ST_Transform(i.ubicacion, 3857) AS g3857
      FROM incidente i
      WHERE {where}
    ),
    incident_counts AS (
      SELECT
        ST_X(ST_SnapToGrid(g3857, %s)) AS cell_x,
        ST_Y(ST_SnapToGrid(g3857, %s)) AS cell_y,
        COUNT(*)::int AS conteo
      FROM filtered
      GROUP BY 1, 2
    ),
    all_squares AS (
      SELECT (g).geom AS cell_full_3857
      FROM selection s
      CROSS JOIN LATERAL ST_SquareGrid(%s, ST_Envelope(s.poly_3857)) AS g
      WHERE ST_Intersects((g).geom, s.poly_3857)
    ),
    joined AS (
      SELECT
        sq.cell_full_3857,
        COALESCE(ic.conteo, 0)::int AS conteo
      FROM all_squares sq
      LEFT JOIN incident_counts ic
        ON ic.cell_x = ST_XMin(sq.cell_full_3857)
       AND ic.cell_y = ST_YMin(sq.cell_full_3857)
    ),
    clipped AS (
      SELECT
        j.conteo,
        ST_Intersection(j.cell_full_3857, s.poly_3857) AS cell_geom_3857
      FROM joined j
      CROSS JOIN selection s
      WHERE ST_Area(ST_Intersection(j.cell_full_3857, s.poly_3857)) > 1
    )
    SELECT
      c.conteo,
      ST_Area(c.cell_geom_3857)::double precision AS area_m2,
      ST_AsGeoJSON(ST_Transform(c.cell_geom_3857, 4326))::text AS geometry_json
    FROM clipped c
    ORDER BY c.conteo DESC, ST_YMin(c.cell_geom_3857) DESC
    """
    qparams = [gj, *params, size, size, size]
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
        return _rows_from_cuadricula_cursor(cursor, recortada=True)


def _query_cuadricula(
    where: str,
    params: list[Any],
    tamano_celda_m: float,
    limite_celdas: int,
    *,
    clip_geojson: str | None = None,
    malla_completa: bool = False,
) -> list[dict[str, Any]]:
    size = tamano_celda_m
    if clip_geojson and str(clip_geojson).strip() and malla_completa:
        return _query_cuadricula_malla_area(where, params, size, str(clip_geojson).strip())

    sql = f"""
    WITH filtered AS (
      SELECT ST_Transform(i.ubicacion, 3857) AS g3857
      FROM incidente i
      WHERE {where}
    ),
    cells AS (
      SELECT
        ST_SnapToGrid(g3857, %s) AS cell_ll,
        COUNT(*)::int AS conteo
      FROM filtered
      GROUP BY 1
    ),
    enriched AS (
      SELECT
        c.conteo,
        ST_MakeEnvelope(
          ST_X(c.cell_ll),
          ST_Y(c.cell_ll),
          ST_X(c.cell_ll) + %s,
          ST_Y(c.cell_ll) + %s,
          3857
        ) AS cell_poly_3857
      FROM cells c
    )
    SELECT
      e.conteo,
      ST_Area(e.cell_poly_3857)::double precision AS area_m2,
      ST_AsGeoJSON(ST_Transform(e.cell_poly_3857, 4326))::text AS geometry_json
    FROM enriched e
    ORDER BY e.conteo DESC
    LIMIT %s
    """
    qparams = [*params, size, size, size, limite_celdas]
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
        return _rows_from_cuadricula_cursor(cursor, recortada=False)


def _rows_to_feature_collection(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    features: list[dict[str, Any]] = []
    densidad_max = 0.0
    for rank, row in enumerate(rows, start=1):
        geom = row.get("geometry")
        if not geom:
            continue
        densidad = float(row.get("densidad_por_km2") or 0)
        densidad_max = max(densidad_max, densidad)
        props: dict[str, Any] = {
            "rank": rank,
            "conteo": row["conteo"],
            "area_m2": row.get("area_m2"),
            "area_km2": row.get("area_km2"),
            "densidad_por_km2": densidad,
            "recortada": bool(row.get("recortada")),
        }
        features.append(
            {
                "type": "Feature",
                "id": rank,
                "properties": props,
                "geometry": geom,
            }
        )
    return features, densidad_max


def _empty_hotspots_meta(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    *,
    metodo: MetodoHotspot,
    tamano_celda_m: float,
    limite_celdas: int,
    bbox: tuple[float, float, float, float] | None,
    geojson: str | None,
    mensaje: str,
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [],
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "metodo": metodo,
            "tamano_celda_m": tamano_celda_m,
            "limite_celdas": limite_celdas,
            "total_incidentes": 0,
            "total_celdas": 0,
            "celdas_devueltas": 0,
            "densidad_max_km2": 0.0,
            "sin_datos": True,
            "descripcion": mensaje,
            "filtros": meta_filtros_dict(filtros),
            "bbox": meta_bbox_dict(bbox),
            "filtro_geojson": bool(geojson and str(geojson).strip()),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            "limitaciones": (
                "Cuadrícula fija en metros (ST_SnapToGrid en EPSG:3857). "
                "Modo área: dibuje un polígono en el mapa. Exploratorio, no inferencia causal."
            ),
        },
    }


def build_hotspots_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    metodo: MetodoHotspot = "cuadricula",
    tamano_celda_m: float = DEFAULT_TAMANO_CELDA_M,
    limite_celdas: int = DEFAULT_LIMITE_CELDAS,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    tamano_celda_m = clamp_tamano_celda_m(tamano_celda_m, metodo=metodo)
    limite_celdas = clamp_limite_celdas(limite_celdas)
    geojson_fp = geojson_cache_fingerprint(geojson)

    cache_key = hotspots_cache_key(
        inicio.isoformat(),
        fin.isoformat(),
        filtros,
        metodo=metodo,
        tamano_celda_m=tamano_celda_m,
        limite_celdas=limite_celdas,
        geojson_fp=geojson_fp,
    )

    def _build() -> dict[str, Any]:
        return _build_hotspots_payload_uncached(
            inicio,
            fin,
            filtros,
            metodo=metodo,
            tamano_celda_m=tamano_celda_m,
            limite_celdas=limite_celdas,
            bbox=bbox,
            geojson=geojson,
        )

    return get_cached_map_payload(cache_key, _build)


def _build_hotspots_payload_uncached(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    *,
    metodo: MetodoHotspot,
    tamano_celda_m: float,
    limite_celdas: int,
    bbox: tuple[float, float, float, float] | None,
    geojson: str | None,
) -> dict[str, Any]:
    if metodo == "area" and not (geojson and str(geojson).strip()):
        return _empty_hotspots_meta(
            inicio,
            fin,
            filtros,
            metodo=metodo,
            tamano_celda_m=tamano_celda_m,
            limite_celdas=limite_celdas,
            bbox=bbox,
            geojson=geojson,
            mensaje=(
                "Modo área: dibuje un polígono en el mapa (control de selección) "
                "y aplique los filtros para calcular la cuadrícula dentro del área."
            ),
        )

    where, params = _where_clause(inicio, fin, filtros, bbox, geojson)
    total_incidentes = _count_incidentes(where, params)

    clip = geojson if metodo == "area" and geojson and str(geojson).strip() else None
    malla_completa = bool(clip)
    malla_area_excedida = False
    if malla_completa and clip:
        n_malla = _count_celdas_malla_area(clip, tamano_celda_m)
        if n_malla > MAX_CELDAS_MALLA_AREA:
            malla_area_excedida = True
            rows = []
            total_celdas = n_malla
        else:
            rows = _query_cuadricula(
                where,
                params,
                tamano_celda_m,
                limite_celdas,
                clip_geojson=clip,
                malla_completa=True,
            )
            total_celdas = len(rows)
    else:
        rows = _query_cuadricula(
            where, params, tamano_celda_m, limite_celdas, clip_geojson=clip
        )
        if len(rows) >= limite_celdas:
            total_celdas = _count_celdas_cuadricula(where, params, tamano_celda_m)
        else:
            total_celdas = len(rows)

    celdas_con_incidentes = sum(1 for r in rows if int(r.get("conteo") or 0) > 0)

    if metodo == "area":
        descripcion = (
            f"Malla completa de {int(TAMANO_CELDA_AREA_M)} m dentro del polígono "
            "(celdas sin incidentes incluidas). Recorte ST_Intersection al borde. Exploratorio."
        )
    else:
        descripcion = (
            "Cuadrícula fija en metros (ST_SnapToGrid en EPSG:3857). "
            "Densidad = conteo / área de celda (km²). Exploratorio, no inferencia causal."
        )

    features, densidad_max = _rows_to_feature_collection(rows)

    meta: dict[str, Any] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "metodo": metodo,
        "tamano_celda_m": tamano_celda_m,
        "limite_celdas": limite_celdas,
        "total_incidentes": total_incidentes,
        "total_celdas": total_celdas,
        "celdas_devueltas": len(features),
        "densidad_max_km2": round(densidad_max, 4),
        "sin_datos": malla_area_excedida or len(features) == 0,
        "descripcion": descripcion,
        "filtros": meta_filtros_dict(filtros),
        "bbox": meta_bbox_dict(bbox),
        "filtro_geojson": bool(geojson and str(geojson).strip()),
        "celdas_recortadas": bool(clip),
        "malla_completa": malla_completa,
        "celdas_con_incidentes": celdas_con_incidentes,
        "celdas_sin_incidentes": max(0, len(features) - celdas_con_incidentes),
        "malla_area_excedida": malla_area_excedida,
        "max_celdas_malla_area": MAX_CELDAS_MALLA_AREA if malla_completa else None,
        "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        "limitaciones": (
            "No sustituye análisis de kernel ni modelo espacial formal. "
            "La cuadrícula depende del tamaño de celda y la alineación global EPSG:3857; "
            "En modo área la malla incluye celdas vacías (gris) recortadas al polígono. "
            "Incidentes sin ubicacion PostGIS quedan fuera."
        ),
    }
    if malla_area_excedida:
        meta["descripcion"] = (
            f"El polígono generaría más de {MAX_CELDAS_MALLA_AREA} celdas de "
            f"{int(tamano_celda_m)} m. Reduzca el área dibujada."
        )

    if metodo == "area" and geojson and str(geojson).strip() and not malla_area_excedida:
        meta["area_resumen"] = build_area_resumen(
            inicio,
            fin,
            where,
            params,
            str(geojson).strip(),
            total_incidentes=total_incidentes,
            total_celdas=total_celdas,
            celdas_devueltas=len(features),
            tamano_celda_m=tamano_celda_m,
            grid_rows=rows,
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": meta,
    }


def _query_ranking_celdas(
    where: str,
    params: list[Any],
    tamano_celda_m: float,
    limite: int,
    *,
    orden: str = "densidad",
) -> list[dict[str, Any]]:
    size = tamano_celda_m
    order_sql = (
        "densidad_km2 DESC, conteo DESC"
        if orden == "densidad"
        else "conteo DESC, densidad_km2 DESC"
    )
    sql = f"""
    WITH filtered AS (
      SELECT ST_Transform(i.ubicacion, 3857) AS g3857
      FROM incidente i
      WHERE {where}
    ),
    cells AS (
      SELECT
        ST_SnapToGrid(g3857, %s) AS cell_ll,
        COUNT(*)::int AS conteo
      FROM filtered
      GROUP BY 1
    ),
    enriched AS (
      SELECT
        c.conteo,
        ST_MakeEnvelope(
          ST_X(c.cell_ll),
          ST_Y(c.cell_ll),
          ST_X(c.cell_ll) + %s,
          ST_Y(c.cell_ll) + %s,
          3857
        ) AS cell_poly_3857
      FROM cells c
    )
    SELECT
      e.conteo,
      ST_Area(e.cell_poly_3857)::double precision AS area_m2,
      ST_Y(ST_Transform(ST_Centroid(e.cell_poly_3857), 4326))::double precision AS latitud,
      ST_X(ST_Transform(ST_Centroid(e.cell_poly_3857), 4326))::double precision AS longitud,
      CASE
        WHEN ST_Area(e.cell_poly_3857) > 0
        THEN e.conteo / (ST_Area(e.cell_poly_3857) / 1e6)
        ELSE 0
      END AS densidad_km2,
      (
        SELECT c.nombre
        FROM comuna c
        WHERE c.geom IS NOT NULL
          AND ST_Contains(
            c.geom,
            ST_Transform(ST_Centroid(e.cell_poly_3857), 4326)
          )
        ORDER BY ST_Area(c.geom::geography) ASC
        LIMIT 1
      ) AS comuna_nombre
    FROM enriched e
    ORDER BY {order_sql}
    LIMIT %s
    """
    qparams = [*params, size, size, size, limite]
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
        for conteo, area_m2, lat, lon, densidad, comuna_nombre in cursor.fetchall():
            rows.append(
                {
                    "conteo": int(conteo),
                    "area_m2": float(area_m2 or 0),
                    "area_km2": round(float(area_m2 or 0) / 1_000_000.0, 6),
                    "densidad_por_km2": round(float(densidad or 0), 4),
                    "latitud": round(float(lat), 6),
                    "longitud": round(float(lon), 6),
                    "comuna_nombre": str(comuna_nombre).strip() if comuna_nombre else None,
                }
            )
    return rows


def build_hotspots_ranking_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    tamano_celda_m: float = DEFAULT_TAMANO_CELDA_M,
    limite: int = DEFAULT_LIMITE_RANKING_G06,
    orden: str = "densidad",
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    """F5 / G06 — Top-N celdas calientes (tabla, sin GeoJSON completo)."""
    filtros = filtros or FiltrosKpi()
    tamano_celda_m = clamp_tamano_celda_m(tamano_celda_m)
    limite = clamp_limite_ranking_g06(limite)
    orden_norm = "conteo" if str(orden).strip().lower() == "conteo" else "densidad"

    where, params = _where_clause(inicio, fin, filtros, bbox, geojson)
    total_incidentes = _count_incidentes(where, params)
    rows = _query_ranking_celdas(
        where, params, tamano_celda_m, limite, orden=orden_norm
    )
    ranking: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        ranking.append({"rank": rank, **row})

    return {
        "meta": {
            "indicador": "G06",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "tamano_celda_m": tamano_celda_m,
            "limite": limite,
            "orden": orden_norm,
            "total_incidentes": total_incidentes,
            "celdas_devueltas": len(ranking),
            "sin_datos": total_incidentes == 0 or len(ranking) == 0,
            "filtros": meta_filtros_dict(filtros),
            "bbox": meta_bbox_dict(bbox),
            "filtro_geojson": bool(geojson and str(geojson).strip()),
            "descripcion": (
                "Top celdas de la cuadrícula P14 ordenadas por densidad o conteo. "
                "Comuna según polígono oficial que contiene el centroide de la celda."
            ),
            "limitaciones": (
                "Misma cuadrícula fija que P14; sensible al tamaño de celda. Exploratorio."
            ),
        },
        "ranking": ranking,
    }
