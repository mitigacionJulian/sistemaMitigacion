"""Cache en memoria (Django LocMem) para respuestas pesadas del mapa."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any, TypeVar

from django.conf import settings
from django.core.cache import cache

from .kpis import FiltrosKpi

T = TypeVar("T")


def _filtros_part(filtros: FiltrosKpi | None) -> str:
    f = filtros or FiltrosKpi()
    return (
        f"{f.comuna_id}|{f.barrio_id}|{f.clase_incidente_id}|"
        f"{f.modo_territorio}|{f.via_id}|{f.punto_critico_id}"
    )


def map_cache_key(prefix: str, **parts: Any) -> str:
    raw = prefix + "|" + "|".join(f"{k}={parts[k]}" for k in sorted(parts))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"map:{prefix}:{digest}"


def choropleth_cache_key(
    inicio: str,
    fin: str,
    filtros: FiltrosKpi | None,
    *,
    nivel: str,
    metrica: str,
) -> str:
    return map_cache_key(
        "choropleth",
        inicio=inicio,
        fin=fin,
        filtros=_filtros_part(filtros),
        nivel=nivel,
        metrica=metrica,
    )


def hotspots_cache_key(
    inicio: str,
    fin: str,
    filtros: FiltrosKpi | None,
    *,
    metodo: str,
    tamano_celda_m: float,
    limite_celdas: int,
    geojson_fp: str = "",
) -> str:
    return map_cache_key(
        "hotspots",
        inicio=inicio,
        fin=fin,
        filtros=_filtros_part(filtros),
        metodo=metodo,
        tamano=tamano_celda_m,
        limite=limite_celdas,
        geojson=geojson_fp or "none",
        malla="m2" if metodo == "area" else "std",
    )


def incidentes_mapa_cache_key(
    inicio: str,
    fin: str,
    filtros: FiltrosKpi | None,
    *,
    limite: int,
) -> str:
    return map_cache_key(
        "incidentes-mapa",
        inicio=inicio,
        fin=fin,
        filtros=_filtros_part(filtros),
        limite=limite,
    )


def mapa_detalle_cache_key(
    inicio: str,
    fin: str,
    filtros: FiltrosKpi | None,
    *,
    nivel: str,
    metrica: str,
    limite: int,
) -> str:
    return map_cache_key(
        "mapa-detalle",
        inicio=inicio,
        fin=fin,
        filtros=_filtros_part(filtros),
        nivel=nivel,
        metrica=metrica,
        limite=limite,
    )


def get_cached_map_payload(key: str, builder: Callable[[], T]) -> T:
    ttl = int(getattr(settings, "MAP_API_CACHE_TTL", 900))
    if ttl > 0:
        cached = cache.get(key)
        if cached is not None:
            return cached
    result = builder()
    if ttl > 0:
        cache.set(key, result, ttl)
    return result
