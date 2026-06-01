"""F5 — indicadores geoespaciales G01–G03, G06."""
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.densidad_territorial import build_densidad_territorial_payload
from dashboard.hotspots import build_hotspots_ranking_payload


class DensidadTerritorialTests(TestCase):
    def test_build_densidad_mock(self):
        ranking = [
            {
                "territorio_id": 1,
                "nombre": "Centro",
                "codigo": "01",
                "incidentes": 100,
                "area_km2": 2.0,
                "densidad_km2": 50.0,
            }
        ]
        with patch(
            "dashboard.densidad_territorial._query_densidad_ciudad",
            return_value=(100, 10.0),
        ), patch(
            "dashboard.densidad_territorial._query_ranking_densidad",
            return_value=ranking,
        ):
            payload = build_densidad_territorial_payload(date(2021, 1, 1), date(2021, 1, 31))
        self.assertEqual(payload["meta"]["indicador"], "G01-G02")
        self.assertEqual(len(payload["ranking"]), 1)
        self.assertEqual(payload["ranking"][0]["rank"], 1)
        self.assertAlmostEqual(payload["ranking"][0]["ratio_vs_ciudad"], 5.0)


class HotspotsRankingTests(TestCase):
    def test_ranking_mock(self):
        rows = [
            {
                "conteo": 20,
                "area_m2": 90000.0,
                "area_km2": 0.09,
                "densidad_por_km2": 222.2,
                "latitud": 6.25,
                "longitud": -75.56,
                "comuna_nombre": "La Candelaria",
            }
        ]
        with patch("dashboard.hotspots._count_incidentes", return_value=20), patch(
            "dashboard.hotspots._query_ranking_celdas", return_value=rows
        ):
            payload = build_hotspots_ranking_payload(date(2021, 1, 1), date(2021, 1, 31))
        self.assertEqual(payload["meta"]["indicador"], "G06")
        self.assertEqual(payload["ranking"][0]["rank"], 1)
        self.assertEqual(payload["ranking"][0]["comuna_nombre"], "La Candelaria")


class DensidadApiTests(TestCase):
    def test_api_densidad_ok(self):
        fake = {"meta": {"indicador": "G01-G02", "sin_datos": True}, "ranking": []}
        with patch("dashboard.views.build_densidad_territorial_payload", return_value=fake):
            r = APIClient().get(
                reverse("dashboard-densidad-territorial"),
                {"desde": "2021-01-01", "hasta": "2021-01-31"},
            )
        self.assertEqual(r.status_code, 200)
