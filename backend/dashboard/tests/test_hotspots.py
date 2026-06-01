"""F4 / P14 — hotspots espaciales."""
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.hotspots import (
    build_hotspots_payload,
    clamp_tamano_celda_m,
    parse_metodo_hotspot,
)
from dashboard.kpis import FiltrosKpi


class HotspotsParserTests(TestCase):
    def test_parse_metodo(self):
        self.assertEqual(parse_metodo_hotspot(None), "cuadricula")
        self.assertEqual(parse_metodo_hotspot("dbscan"), "dbscan")
        self.assertEqual(parse_metodo_hotspot("clusters"), "dbscan")

    def test_clamp_tamano_celda(self):
        self.assertEqual(clamp_tamano_celda_m(10), 50.0)
        self.assertEqual(clamp_tamano_celda_m(300), 300.0)
        self.assertEqual(clamp_tamano_celda_m(9999), 2000.0)


class HotspotsPayloadTests(TestCase):
    def test_build_cuadricula_empty(self):
        with patch("dashboard.hotspots._count_incidentes", return_value=0), patch(
            "dashboard.hotspots._query_cuadricula", return_value=[]
        ), patch("dashboard.hotspots._count_celdas_cuadricula", return_value=0):
            payload = build_hotspots_payload(date(2021, 1, 1), date(2021, 1, 31))
        self.assertEqual(payload["type"], "FeatureCollection")
        self.assertEqual(payload["features"], [])
        self.assertTrue(payload["meta"]["sin_datos"])
        self.assertEqual(payload["meta"]["metodo"], "cuadricula")
        self.assertEqual(payload["meta"]["tamano_celda_m"], 300.0)

    def test_build_cuadricula_with_cell(self):
        fake_geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        rows = [
            {
                "conteo": 12,
                "area_m2": 90000.0,
                "area_km2": 0.09,
                "densidad_por_km2": 133.3333,
                "geometry": fake_geom,
            }
        ]
        with patch("dashboard.hotspots._count_incidentes", return_value=12), patch(
            "dashboard.hotspots._query_cuadricula", return_value=rows
        ), patch("dashboard.hotspots._count_celdas_cuadricula", return_value=1):
            payload = build_hotspots_payload(
                date(2021, 1, 1),
                date(2021, 1, 31),
                FiltrosKpi(modo_territorio="espacial"),
                tamano_celda_m=300,
            )
        self.assertEqual(len(payload["features"]), 1)
        self.assertEqual(payload["features"][0]["properties"]["conteo"], 12)
        self.assertEqual(payload["features"][0]["properties"]["rank"], 1)
        self.assertAlmostEqual(payload["meta"]["densidad_max_km2"], 133.3333)
        self.assertEqual(payload["meta"]["filtros"]["territorio"], "espacial")

    def test_api_hotspots_ok(self):
        fake = {
            "type": "FeatureCollection",
            "features": [],
            "meta": {"metodo": "cuadricula", "sin_datos": True, "total_incidentes": 0},
        }
        with patch("dashboard.views.build_hotspots_payload", return_value=fake):
            r = APIClient().get(
                reverse("dashboard-hotspots-cuadricula"),
                {"desde": "2021-01-01", "hasta": "2021-01-31", "metodo": "cuadricula"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["meta"]["metodo"], "cuadricula")

    def test_api_hotspots_invalid_date(self):
        r = APIClient().get(
            reverse("dashboard-hotspots-cuadricula"),
            {"desde": "2021-12-01", "hasta": "2021-01-01"},
        )
        self.assertEqual(r.status_code, 400)
