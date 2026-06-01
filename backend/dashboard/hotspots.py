"""
F4 / P14 — Hotspots espaciales exploratorios (PostGIS).

Cuadrícula en EPSG:3857 (metros) o clusters ST_ClusterDBSCAN.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

from django.db import connection

from .kpis import FiltrosKpi
from .map_cache import get_cached_map_payload, hotspots_cache_key
from .territorio_sql import (
    append_filtro_bbox,
    append_filtro_geojson,
    append_filtros_territoriales,
    meta_bbox_dict,
    meta_filtros_dict,
    nota_modo_territorio,
)

MetodoHotspot = Literal["cuadricula", "dbscan"]

DEFAULT_TAMANO_CELDA_M = 300.0
MIN_TAMANO_CELDA_M = 50.0
MAX_TAMANO_CELDA_M = 2000.0
DEFAULT_LIMITE_CELDAS = 800
MAX_LIMITE_CELDAS = 2000
DEFAULT_DBSCAN_EPS_M = 150.0
MIN_DBSCAN_EPS_M = 25.0
MAX_DBSCAN_EPS_M = 1000.0
DEFAULT_DBSCAN_MINPOINTS = 5
MIN_DBSCAN_MINPOINTS = 3
MAX_DBSCAN_MINPOINTS = 50
DEFAULT_LIMITE_RANKING_G06 = 15
MAX_LIMITE_RANKING_G06 = 50


def clamp_tamano_celda_m(raw: float | int | None) -> float:
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
    if raw and str(raw).strip().lower() in ("dbscan", "cluster", "clusters"):
        return "dbscan"
    return "cuadricula"


def clamp_dbscan_eps_m(raw: float | int | None) -> float:
    if raw is None:
        return DEFAULT_DBSCAN_EPS_M
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_DBSCAN_EPS_M
    return max(MIN_DBSCAN_EPS_M, min(MAX_DBSCAN_EPS_M, v))


def clamp_dbscan_minpoints(raw: int | None) -> int:
    if raw is None:
        return DEFAULT_DBSCAN_MINPOINTS
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_DBSCAN_MINPOINTS
    return max(MIN_DBSCAN_MINPOINTS, min(MAX_DBSCAN_MINPOINTS, v))


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


def _query_cuadricula(
    where: str,
    params: list[Any],
    tamano_celda_m: float,
    limite_celdas: int,
) -> list[dict[str, Any]]:
    size = tamano_celda_m
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
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
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
                }
            )
    return rows


def _query_dbscan(
    where: str,
    params: list[Any],
    eps_m: float,
    minpoints: int,
    limite_celdas: int,
) -> list[dict[str, Any]]:
    sql = f"""
    WITH filtered AS (
      SELECT
        i.id,
        ST_Transform(i.ubicacion, 3857) AS g3857,
        i.ubicacion AS g4326
      FROM incidente i
      WHERE {where}
    ),
    clustered AS (
      SELECT
        id,
        g3857,
        g4326,
        ST_ClusterDBSCAN(g3857, eps := %s, minpoints := %s) OVER () AS cid
      FROM filtered
    ),
    groups AS (
      SELECT
        cid,
        COUNT(*)::int AS conteo,
        ST_Collect(g3857) AS geom_collect_3857
      FROM clustered
      WHERE cid IS NOT NULL
      GROUP BY cid
    )
    SELECT
      g.cid,
      g.conteo,
      ST_Area(ST_ConvexHull(g.geom_collect_3857))::double precision AS area_m2,
      ST_AsGeoJSON(
        ST_Transform(ST_Buffer(ST_ConvexHull(g.geom_collect_3857), 5), 4326)
      )::text AS geometry_json
    FROM groups g
    ORDER BY g.conteo DESC
    LIMIT %s
    """
    qparams = [*params, eps_m, minpoints, limite_celdas]
    rows: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, qparams)
        for cid, conteo, area_m2, geometry_json in cursor.fetchall():
            area_km2 = float(area_m2 or 0) / 1_000_000.0
            densidad = float(conteo) / area_km2 if area_km2 > 0 else 0.0
            rows.append(
                {
                    "cluster_id": int(cid),
                    "conteo": int(conteo),
                    "area_m2": float(area_m2 or 0),
                    "area_km2": round(area_km2, 6),
                    "densidad_por_km2": round(densidad, 4),
                    "geometry": json.loads(geometry_json) if geometry_json else None,
                }
            )
    return rows


def _rows_to_feature_collection(
    rows: list[dict[str, Any]],
    metodo: MetodoHotspot,
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
        }
        if metodo == "dbscan" and row.get("cluster_id") is not None:
            props["cluster_id"] = row["cluster_id"]
        features.append(
            {
                "type": "Feature",
                "id": rank,
                "properties": props,
                "geometry": geom,
            }
        )
    return features, densidad_max


def build_hotspots_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    metodo: MetodoHotspot = "cuadricula",
    tamano_celda_m: float = DEFAULT_TAMANO_CELDA_M,
    limite_celdas: int = DEFAULT_LIMITE_CELDAS,
    dbscan_eps_m: float = DEFAULT_DBSCAN_EPS_M,
    dbscan_minpoints: int = DEFAULT_DBSCAN_MINPOINTS,
    bbox: tuple[float, float, float, float] | None = None,
    geojson: str | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    tamano_celda_m = clamp_tamano_celda_m(tamano_celda_m)
    limite_celdas = clamp_limite_celdas(limite_celdas)
    dbscan_eps_m = clamp_dbscan_eps_m(dbscan_eps_m)
    dbscan_minpoints = clamp_dbscan_minpoints(dbscan_minpoints)

    cache_key = hotspots_cache_key(
        inicio.isoformat(),
        fin.isoformat(),
        filtros,
        metodo=metodo,
        tamano_celda_m=tamano_celda_m,
        limite_celdas=limite_celdas,
        dbscan_eps_m=dbscan_eps_m,
        dbscan_minpoints=dbscan_minpoints,
    )

    def _build() -> dict[str, Any]:
        return _build_hotspots_payload_uncached(
            inicio,
            fin,
            filtros,
            metodo=metodo,
            tamano_celda_m=tamano_celda_m,
            limite_celdas=limite_celdas,
            dbscan_eps_m=dbscan_eps_m,
            dbscan_minpoints=dbscan_minpoints,
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
    dbscan_eps_m: float,
    dbscan_minpoints: int,
    bbox: tuple[float, float, float, float] | None,
    geojson: str | None,
) -> dict[str, Any]:

    where, params = _where_clause(inicio, fin, filtros, bbox, geojson)
    total_incidentes = _count_incidentes(where, params)

    if metodo == "dbscan":
        rows = _query_dbscan(where, params, dbscan_eps_m, dbscan_minpoints, limite_celdas)
        total_celdas = len(rows)
        descripcion = (
            "Clusters DBSCAN sobre incidente.ubicacion (EPSG:3857, eps en metros). "
            "Polígono = envolvente con buffer de 5 m; exploratorio, no inferencia causal."
        )
    else:
        rows = _query_cuadricula(where, params, tamano_celda_m, limite_celdas)
        if len(rows) >= limite_celdas:
            total_celdas = _count_celdas_cuadricula(where, params, tamano_celda_m)
        else:
            total_celdas = len(rows)
        descripcion = (
            "Cuadrícula fija en metros (ST_SnapToGrid en EPSG:3857). "
            "Densidad = conteo / área de celda (km²). Exploratorio, no inferencia causal."
        )

    features, densidad_max = _rows_to_feature_collection(rows, metodo)

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "metodo": metodo,
            "tamano_celda_m": tamano_celda_m if metodo == "cuadricula" else None,
            "dbscan_eps_m": dbscan_eps_m if metodo == "dbscan" else None,
            "dbscan_minpoints": dbscan_minpoints if metodo == "dbscan" else None,
            "limite_celdas": limite_celdas,
            "total_incidentes": total_incidentes,
            "total_celdas": total_celdas,
            "celdas_devueltas": len(features),
            "densidad_max_km2": round(densidad_max, 4),
            "sin_datos": total_incidentes == 0 or len(features) == 0,
            "descripcion": descripcion,
            "filtros": meta_filtros_dict(filtros),
            "bbox": meta_bbox_dict(bbox),
            "filtro_geojson": bool(geojson and str(geojson).strip()),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            "limitaciones": (
                "No sustituye análisis de kernel ni modelo espacial formal. "
                "La cuadrícula depende del tamaño de celda; DBSCAN depende de eps y minpoints. "
                "Incidentes sin ubicacion PostGIS quedan fuera."
            ),
        },
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
