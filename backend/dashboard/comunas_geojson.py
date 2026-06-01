"""
F3.7 — GeoJSON de límites comunales (comuna.geom PostGIS).
"""
from __future__ import annotations

import json
from typing import Any

from django.db import connection


def build_comunas_geojson(comuna_id: int | None = None) -> dict[str, Any]:
    where = ["c.geom IS NOT NULL"]
    params: list[Any] = []
    if comuna_id is not None:
        where.append("c.id = %s")
        params.append(comuna_id)
    wh = " AND ".join(where)
    sql = f"""
    SELECT
      c.id,
      c.nombre,
      c.codigo,
      ST_AsGeoJSON(c.geom)::text AS geometry_json
    FROM comuna c
    WHERE {wh}
    ORDER BY c.nombre
    """
    features: list[dict[str, Any]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for cid, nombre, codigo, geometry_json in cursor.fetchall():
            if not geometry_json:
                continue
            features.append(
                {
                    "type": "Feature",
                    "id": int(cid),
                    "properties": {
                        "id": int(cid),
                        "nombre": str(nombre or ""),
                        "codigo": str(codigo or ""),
                    },
                    "geometry": json.loads(geometry_json),
                }
            )

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "n_comunas": len(features),
            "srid": 4326,
            "filtro_comuna_id": comuna_id,
            "sin_datos": len(features) == 0,
        },
    }
