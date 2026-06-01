"""Cache, TopoJSON, mapa-detalle y formato compacto del mapa."""
from datetime import date
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.geo_topojson import feature_collection_to_topology, wrap_choropleth_with_topojson
from dashboard.incidentes_mapa import PUNTOS_COLUMNAS, build_incidentes_mapa_payload
from dashboard.kpis import FiltrosKpi
from dashboard.map_cache import choropleth_cache_key, get_cached_map_payload


def test_topojson_from_simple_polygon():
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1, "nombre": "A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.57, 6.24],
                            [-75.56, 6.24],
                            [-75.56, 6.25],
                            [-75.57, 6.25],
                            [-75.57, 6.24],
                        ]
                    ],
                },
            }
        ],
    }
    topo = feature_collection_to_topology(fc)
    assert topo is not None
    assert topo["type"] == "Topology"
    assert "territorios" in topo["objects"]


def test_wrap_choropleth_keeps_geojson():
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-75.57, 6.24],
                            [-75.56, 6.24],
                            [-75.56, 6.25],
                            [-75.57, 6.25],
                            [-75.57, 6.24],
                        ]
                    ],
                },
            }
        ],
        "meta": {"nivel": "comuna"},
    }
    out = wrap_choropleth_with_topojson(fc)
    assert out["type"] == "FeatureCollection"
    assert len(out["features"]) == 1


@pytest.mark.django_db
def test_dashboard_mapa_detalle_ok():
    fake = {
        "meta": {"indicador": "mapa-detalle", "puntos_devueltos": 1},
        "choropleth": {"type": "FeatureCollection", "features": [], "meta": {}},
        "puntos": [[1, 6.25, -75.56, "A", "2021-02-01", "Choque"]],
        "puntos_meta": {"formato_puntos": "compacto", "puntos_devueltos": 1},
    }
    with patch("dashboard.views.build_mapa_detalle_payload", return_value=fake):
        c = APIClient()
        r = c.get(
            reverse("dashboard-mapa-detalle"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "limite": "100"},
        )
        assert r.status_code == 200
        assert r.data["meta"]["indicador"] == "mapa-detalle"


@pytest.mark.django_db
def test_incidentes_mapa_formato_compacto():
    fake_puntos = [
        {
            "id": 1,
            "radicado": "RAD-1",
            "fecha_incidente": "2021-02-01",
            "latitud": 6.25,
            "longitud": -75.56,
            "clase_incidente": "Choque",
        },
    ]
    with patch(
        "dashboard.incidentes_mapa._query_incidentes_puntos",
        return_value=(fake_puntos, 1),
    ):
        payload = build_incidentes_mapa_payload(date(2021, 1, 1), date(2021, 3, 31), FiltrosKpi(), 100)
    assert payload["meta"]["formato_puntos"] == "compacto"
    assert payload["meta"]["columnas_puntos"] == PUNTOS_COLUMNAS
    assert payload["puntos"] == [[1, 6.25, -75.56, "RAD-1", "2021-02-01", "Choque"]]


def test_map_cache_hit():
    cache.clear()
    calls = {"n": 0}

    def builder():
        calls["n"] += 1
        return {"ok": True}

    key = choropleth_cache_key("2021-01-01", "2021-01-31", FiltrosKpi(), nivel="comuna", metrica="densidad")
    assert get_cached_map_payload(key, builder) == {"ok": True}
    assert get_cached_map_payload(key, builder) == {"ok": True}
    assert calls["n"] == 1
