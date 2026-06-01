"""
Conversión FeatureCollection → TopoJSON (polígonos, sin dependencias externas).

Reduce tamaño de respuesta para coroplética territorial (~30–60 % vs GeoJSON repetido).
"""
from __future__ import annotations

from typing import Any

TOPOJSON_OBJECT_NAME = "territorios"
TOPOJSON_QUANTIZE = 100_000


def _collect_coords(geometry: dict[str, Any], out: list[list[float]]) -> None:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return
    if gtype == "Polygon":
        for ring in coords:
            out.extend(ring)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                out.extend(ring)


def _quantize_coords(
    raw: list[list[float]],
) -> tuple[list[list[int]], dict[str, Any]]:
    if not raw:
        return [], {"scale": [1, 1], "translate": [0, 0]}
    xs = [c[0] for c in raw]
    ys = [c[1] for c in raw]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x or 1e-12
    span_y = max_y - min_y or 1e-12
    scale = [span_x, span_y]
    translate = [min_x, min_y]
    q: list[list[int]] = []
    for x, y in raw:
        qx = int(round((x - min_x) / span_x * TOPOJSON_QUANTIZE))
        qy = int(round((y - min_y) / span_y * TOPOJSON_QUANTIZE))
        q.append([qx, qy])
    return q, {"scale": scale, "translate": translate}


def feature_collection_to_topology(
    fc: dict[str, Any],
    *,
    object_name: str = TOPOJSON_OBJECT_NAME,
) -> dict[str, Any] | None:
    features = fc.get("features") or []
    if not features:
        return None

    all_coords: list[list[float]] = []
    for feat in features:
        geom = feat.get("geometry")
        if geom:
            _collect_coords(geom, all_coords)
    if not all_coords:
        return None

    _, transform = _quantize_coords(all_coords)

    # Segunda pasada: arcos globales compartidos
    arcs: list[list[list[int]]] = []
    arc_key: dict[tuple[int, ...], int] = {}

    def arc_index_for_ring(ring: list[list[float]]) -> list[int]:
        scale = transform["scale"]
        translate = transform["translate"]
        qring: list[list[int]] = []
        for x, y in ring:
            qx = int(round((x - translate[0]) / scale[0] * TOPOJSON_QUANTIZE))
            qy = int(round((y - translate[1]) / scale[1] * TOPOJSON_QUANTIZE))
            qring.append([qx, qy])
        result: list[int] = []
        for i in range(len(qring) - 1):
            a, b = qring[i], qring[i + 1]
            fwd = (a[0], a[1], b[0], b[1])
            rev = (b[0], b[1], a[0], a[1])
            if fwd in arc_key:
                result.append(arc_key[fwd])
            elif rev in arc_key:
                result.append(~arc_key[rev])
            else:
                dx, dy = b[0] - a[0], b[1] - a[1]
                arc_key[fwd] = len(arcs)
                arcs.append([[dx, dy]])
                result.append(arc_key[fwd])
        return result

    geometries: list[dict[str, Any]] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        props = feat.get("properties") or {}
        topo_geom: dict[str, Any] = {"type": gtype, "properties": props}
        if gtype == "Polygon" and coords:
            topo_geom["arcs"] = [arc_index_for_ring(ring) for ring in coords]
        elif gtype == "MultiPolygon" and coords:
            topo_geom["arcs"] = [
                [arc_index_for_ring(ring) for ring in poly] for poly in coords
            ]
        else:
            continue
        geometries.append(topo_geom)

    if not geometries:
        return None

    return {
        "type": "Topology",
        "transform": transform,
        "objects": {
            object_name: {
                "type": "GeometryCollection",
                "geometries": geometries,
            }
        },
        "arcs": arcs,
    }


def wrap_choropleth_with_topojson(payload: dict[str, Any]) -> dict[str, Any]:
    """Devuelve GeoJSON. TopoJSON deshabilitado hasta encoder compatible con topojson-client."""
    return payload
