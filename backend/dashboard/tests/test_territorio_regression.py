"""F3.8 — Regresión registro vs espacial (sin romper default)."""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.kpis import FiltrosKpi


class TerritorioRegressionApiTests(TestCase):
    def test_kpis_default_territorio_registro_en_meta(self):
        fake = {
            "meta": {
                "filtros": {"territorio": "registro"},
                "fecha_inicio": "2021-01-01",
                "fecha_fin": "2021-01-31",
            },
            "kpis_periodo_actual": {},
            "kpis_periodo_anterior": {},
            "comparacion": {},
        }
        with patch("dashboard.views.build_kpis_payload", return_value=fake):
            r = APIClient().get(
                reverse("dashboard-kpis"),
                {"desde": "2021-01-01", "hasta": "2021-01-31"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["meta"]["filtros"]["territorio"], "registro")

    def test_kpis_territorio_espacial_param(self):
        captured: list[FiltrosKpi] = []

        def _capture(inicio, fin, filtros):
            captured.append(filtros)
            return {
                "meta": {
                    "filtros": {"territorio": filtros.modo_territorio},
                    "nota_territorio": "espacial",
                },
                "kpis_periodo_actual": {},
                "kpis_periodo_anterior": {},
                "comparacion": {},
            }

        with patch("dashboard.views.build_kpis_payload", side_effect=_capture):
            r = APIClient().get(
                reverse("dashboard-kpis"),
                {"desde": "2021-01-01", "hasta": "2021-01-31", "territorio": "espacial"},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(captured[0].modo_territorio, "espacial")
