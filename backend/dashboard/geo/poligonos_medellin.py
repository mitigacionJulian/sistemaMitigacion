"""
Carga poligonos de barrios y comunas desde shapefile oficial (Medellin).

Fuente por defecto: docs/shp/shp_barrios_y_veredas_mr/barrios_y_veredas_mr.shp
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import connection, transaction

SOURCE_SRID = 9377
TARGET_SRID = 4326

# Comunas urbanas: subtipo_ba=1 (barrio). Corregimientos: subtipo_ba=2 (vereda).
CORREGIMIENTO_CODES = frozenset({"50", "60", "70", "80", "90"})
SKIP_COMUNA_CODES = frozenset({"SN01", "SN02"})


def default_shapefile_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / "docs" / "shp" / "shp_barrios_y_veredas_mr" / "barrios_y_veredas_mr.shp"


def norm_name(value: str) -> str:
    s = str(value or "").upper().strip()
    s = s.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    return " ".join(s.split())


def to_multipolygon_4326(ogr_geom) -> MultiPolygon | None:
    if ogr_geom is None:
        return None
    try:
        g = GEOSGeometry(ogr_geom.wkt, srid=SOURCE_SRID)
        g.transform(TARGET_SRID)
    except Exception:
        return None
    if isinstance(g, Polygon):
        return MultiPolygon(g, srid=TARGET_SRID)
    if isinstance(g, MultiPolygon):
        g.srid = TARGET_SRID
        return g
    unified = g.unary_union
    if isinstance(unified, Polygon):
        return MultiPolygon(unified, srid=TARGET_SRID)
    if isinstance(unified, MultiPolygon):
        unified.srid = TARGET_SRID
        return unified
    return None


def _feature_comuna_code(feat) -> str:
    return str(feat.get("limitecomu") or "").strip().upper()


def _include_for_comuna(feat) -> bool:
    com = _feature_comuna_code(feat)
    if com in SKIP_COMUNA_CODES:
        return False
    sub = int(feat.get("subtipo_ba") or 0)
    if com in CORREGIMIENTO_CODES:
        return sub == 2 or (com == "70" and sub == 1)
    return sub == 1


def _include_for_barrio(feat) -> bool:
    return int(feat.get("subtipo_ba") or 0) == 1 and _feature_comuna_code(feat) not in SKIP_COMUNA_CODES


@dataclass
class LoadStats:
    barrios_actualizados: int = 0
    barrios_sin_match: int = 0
    comunas_actualizadas: int = 0
    comunas_sin_match: int = 0
    features_barrio: int = 0
    features_comuna: int = 0


def _load_barrio_index() -> tuple[dict[str, tuple[int, str, str]], dict[tuple[str, str], list[tuple[int, str, str]]]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT b.id, b.codigo, b.nombre, c.codigo AS comuna_codigo
            FROM barrio b
            JOIN comuna c ON b.comuna_id = c.id
            """
        )
        rows = cursor.fetchall()

    by_code: dict[str, tuple[int, str, str]] = {}
    by_name_com: dict[tuple[str, str], list[tuple[int, str, str]]] = defaultdict(list)
    for barrio_id, codigo, nombre, comuna_codigo in rows:
        code = str(codigo or "").strip().upper()
        com = str(comuna_codigo or "").strip().upper()
        by_code[code] = (barrio_id, str(nombre), com)
        by_name_com[(norm_name(nombre), com)].append((barrio_id, str(nombre), com))
    return by_code, by_name_com


def _match_barrio_id(
    feat,
    by_code: dict[str, tuple[int, str, str]],
    by_name_com: dict[tuple[str, str], list[tuple[int, str, str]]],
) -> int | None:
    ident = str(feat.get("identifica") or "").strip().upper()
    codigo = str(feat.get("codigo") or "").strip().upper()
    comuna = _feature_comuna_code(feat)
    nombre = str(feat.get("nombre") or "")

    for key in (codigo, ident):
        if key and key in by_code:
            bid, _, com = by_code[key]
            if com == comuna:
                return bid

    candidates = by_name_com.get((norm_name(nombre), comuna), [])
    if len(candidates) == 1:
        return candidates[0][0]
    return None


def _update_geom(table: str, row_id: int, geom: MultiPolygon) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} SET geom = ST_Multi(ST_GeomFromEWKB(%s)::geometry) WHERE id = %s",
            [memoryview(geom.ewkb), row_id],
        )


def _load_comuna_ids() -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, codigo FROM comuna")
        return {str(cod).strip().upper(): int(rid) for rid, cod in cursor.fetchall()}


def cargar_poligonos(
    shapefile: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> LoadStats:
    if not shapefile.is_file():
        raise FileNotFoundError(f"No existe el shapefile: {shapefile}")

    ds = DataSource(str(shapefile))
    layer = ds[0]
    stats = LoadStats()
    by_code, by_name_com = _load_barrio_index()
    comuna_ids = _load_comuna_ids()

    barrio_updates: dict[int, MultiPolygon] = {}
    comuna_parts: dict[str, list[MultiPolygon]] = defaultdict(list)

    for feat in layer:
        if _include_for_barrio(feat):
            stats.features_barrio += 1
            geom = to_multipolygon_4326(feat.geom)
            if geom is None:
                stats.barrios_sin_match += 1
                continue
            barrio_id = _match_barrio_id(feat, by_code, by_name_com)
            if barrio_id is None:
                stats.barrios_sin_match += 1
                if verbose:
                    print(
                        "sin match barrio:",
                        feat.get("codigo"),
                        feat.get("nombre"),
                        _feature_comuna_code(feat),
                    )
                continue
            barrio_updates[barrio_id] = geom

        if _include_for_comuna(feat):
            stats.features_comuna += 1
            com = _feature_comuna_code(feat)
            geom = to_multipolygon_4326(feat.geom)
            if geom is not None:
                comuna_parts[com].append(geom)

    comuna_updates: dict[int, MultiPolygon] = {}
    for com_code, parts in comuna_parts.items():
        comuna_id = comuna_ids.get(com_code)
        if comuna_id is None:
            stats.comunas_sin_match += 1
            continue
        merged: GEOSGeometry = parts[0]
        for part in parts[1:]:
            merged = merged.union(part)
        if isinstance(merged, Polygon):
            mp = MultiPolygon(merged, srid=TARGET_SRID)
        elif isinstance(merged, MultiPolygon):
            mp = merged
            mp.srid = TARGET_SRID
        else:
            unified = merged.unary_union
            mp = (
                MultiPolygon(unified, srid=TARGET_SRID)
                if isinstance(unified, Polygon)
                else unified
            )
            if hasattr(mp, "srid"):
                mp.srid = TARGET_SRID
        comuna_updates[comuna_id] = mp

    if dry_run:
        stats.barrios_actualizados = len(barrio_updates)
        stats.comunas_actualizadas = len(comuna_updates)
        return stats

    with transaction.atomic():
        for barrio_id, geom in barrio_updates.items():
            _update_geom("barrio", barrio_id, geom)
        stats.barrios_actualizados = len(barrio_updates)

        for comuna_id, geom in comuna_updates.items():
            _update_geom("comuna", comuna_id, geom)
        stats.comunas_actualizadas = len(comuna_updates)

    return stats


def poligonos_status() -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'comuna'
                  AND column_name = 'geom'
            )
            """
        )
        has_geom = cursor.fetchone()[0]
        if not has_geom:
            return {"ready": False, "message": "Falta comuna.geom. Ejecute 004_comuna_barrio_geom.sql"}

        cursor.execute(
            """
            SELECT
                (SELECT count(*) FROM comuna) AS comunas,
                (SELECT count(*) FROM comuna WHERE geom IS NOT NULL) AS comunas_geom,
                (SELECT count(*) FROM barrio) AS barrios,
                (SELECT count(*) FROM barrio WHERE geom IS NOT NULL) AS barrios_geom
            """
        )
        row = cursor.fetchone()
        cursor.execute(
            """
            SELECT count(*) FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'comuna' AND indexname = 'idx_comuna_geom'
            """
        )
        idx_com = cursor.fetchone()[0] > 0
        cursor.execute(
            """
            SELECT count(*) FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'barrio' AND indexname = 'idx_barrio_geom'
            """
        )
        idx_bar = cursor.fetchone()[0] > 0

    comunas, comunas_geom, barrios, barrios_geom = row
    return {
        "ready": True,
        "comunas": comunas,
        "comunas_con_geom": comunas_geom,
        "barrios": barrios,
        "barrios_con_geom": barrios_geom,
        "idx_comuna_geom": idx_com,
        "idx_barrio_geom": idx_bar,
    }
