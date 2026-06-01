"""Tests coroplética territorial."""
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestChoroplethTerritorial:
    def test_build_payload_empty(self):
        from dashboard.choropleth_territorial import build_choropleth_territorial_payload
        from datetime import date

        with patch("dashboard.choropleth_territorial._query_densidad_ciudad", return_value=(0, 0.0)):
            with patch("dashboard.choropleth_territorial._query_choropleth_comuna", return_value=[]):
                payload = build_choropleth_territorial_payload(
                    date(2021, 1, 1),
                    date(2021, 12, 31),
                )
        assert payload["type"] == "FeatureCollection"
        assert payload["features"] == []
        assert payload["meta"]["sin_datos"] is True

    def test_api_choropleth_ok(self):
        fake = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"nombre": "Comuna 1", "incidentes": 10, "densidad_km2": 5.2},
                    "geometry": {"type": "Polygon", "coordinates": []},
                }
            ],
            "meta": {"nivel": "comuna", "metrica": "densidad", "valor_max": 5.2},
        }
        with patch("dashboard.views.build_choropleth_territorial_payload", return_value=fake):
            r = APIClient().get(
                reverse("dashboard-choropleth-territorial"),
                {"desde": "2021-01-01", "hasta": "2021-09-30"},
            )
        assert r.status_code == 200
        assert r.json()["type"] == "FeatureCollection"
        assert len(r.json()["features"]) == 1
