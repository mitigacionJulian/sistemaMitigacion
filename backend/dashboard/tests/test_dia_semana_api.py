from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_dia_semana_ok():
    fake = {
        "meta": {"fecha_inicio": "2021-01-01", "fecha_fin": "2021-09-30"},
        "serie": [
            {
                "dia_semana": 1,
                "dia": "Lunes",
                "incidentes_periodo_actual": 10,
                "victimas_periodo_actual": 14,
                "incidentes_periodo_anterior": 8,
                "victimas_periodo_anterior": 11,
                "participacion_incidentes_pct": 18.0,
                "ratio_vs_reparto_uniforme": 1.26,
                "carga_dia_nivel": "medio",
                "riesgo_score": 18.0,
                "riesgo_nivel": "medio",
            }
        ],
    }
    with patch("dashboard.views.build_dia_semana_payload", return_value=fake):
        c = APIClient()
        r = c.get(reverse("dashboard-por-dia-semana"), {"desde": "2021-01-01", "hasta": "2021-09-30"})
        assert r.status_code == 200
        assert r.data["serie"][0]["carga_dia_nivel"] == "medio"
        assert r.data["serie"][0]["participacion_incidentes_pct"] == 18.0


@pytest.mark.django_db
def test_dashboard_dia_semana_rango_invalido():
    c = APIClient()
    r = c.get(reverse("dashboard-por-dia-semana"), {"desde": "2021-10-01", "hasta": "2021-09-30"})
    assert r.status_code == 400
