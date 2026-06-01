"""Endpoint combinado mapa detalle: coroplética + puntos en una respuesta."""
from __future__ import annotations

from datetime import date
from typing import Any

from .choropleth_territorial import (
    NivelChoropleth,
    MetricaChoropleth,
    build_choropleth_territorial_payload,
)
from .incidentes_mapa import build_incidentes_mapa_payload
from .kpis import FiltrosKpi
from .map_cache import get_cached_map_payload, mapa_detalle_cache_key


def build_mapa_detalle_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    *,
    nivel: NivelChoropleth = "comuna",
    metrica: MetricaChoropleth = "densidad",
    limite: int = 10_000,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    limite_int = int(limite)
    cache_key = mapa_detalle_cache_key(
        inicio.isoformat(),
        fin.isoformat(),
        filtros,
        nivel=nivel,
        metrica=metrica,
        limite=limite_int,
    )

    def _build() -> dict[str, Any]:
        choropleth = build_choropleth_territorial_payload(
            inicio,
            fin,
            filtros,
            nivel=nivel,
            metrica=metrica,
        )
        puntos_payload = build_incidentes_mapa_payload(
            inicio,
            fin,
            filtros,
            limite_int,
        )
        return {
            "meta": {
                "indicador": "mapa-detalle",
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
                "nivel": nivel,
                "metrica": metrica,
                "limite_puntos": puntos_payload["meta"].get("limite"),
                "puntos_devueltos": puntos_payload["meta"].get("puntos_devueltos"),
                "total_con_coordenadas_en_rango": puntos_payload["meta"].get(
                    "total_con_coordenadas_en_rango"
                ),
                "muestra_truncada": puntos_payload["meta"].get("muestra_truncada"),
                "formato_puntos": puntos_payload["meta"].get("formato_puntos"),
                "columnas_puntos": puntos_payload["meta"].get("columnas_puntos"),
                "formato_geometria": choropleth.get("meta", {}).get("formato_geometria", "geojson"),
            },
            "choropleth": choropleth,
            "puntos": puntos_payload["puntos"],
            "puntos_meta": puntos_payload["meta"],
        }

    return get_cached_map_payload(cache_key, _build)
