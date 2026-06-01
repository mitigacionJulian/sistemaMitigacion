"""F3.7 — GeoJSON comunas."""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.comunas_geojson import build_comunas_geojson


class ComunasGeojsonTests(TestCase):
    def test_build_comunas_geojson_empty(self):
        with patch("dashboard.comunas_geojson.connection.cursor") as mock_cursor:
            ctx = mock_cursor.return_value.__enter__.return_value
            ctx.fetchall.return_value = []
            payload = build_comunas_geojson()
        self.assertEqual(payload["type"], "FeatureCollection")
        self.assertEqual(payload["features"], [])
        self.assertTrue(payload["meta"]["sin_datos"])

    def test_api_comunas_geojson_ok(self):
        fake = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {"id": 1, "nombre": "A"}}],
            "meta": {"n_comunas": 1, "sin_datos": False},
        }
        with patch("dashboard.views.build_comunas_geojson", return_value=fake):
            r = APIClient().get(reverse("dashboard-comunas-geojson"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["meta"]["n_comunas"], 1)
