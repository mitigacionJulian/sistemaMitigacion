from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_distribucion_clase_incidente_ok():
    fake = {
        "meta": {"fecha_inicio": "2021-01-01", "fecha_fin": "2021-09-30"},
        "serie": [
            {
                "clase_incidente_id": 1,
                "codigo": "C1",
                "clase": "Choque",
                "incidentes_periodo_actual": 10,
                "incidentes_periodo_anterior": 8,
                "porcentaje_actual": 50.0,
                "porcentaje_anterior": 40.0,
            }
        ],
    }
    with patch("dashboard.views.build_distribucion_clase_incidente_payload", return_value=fake):
        c = APIClient()
        r = c.get(
            reverse("dashboard-distribucion-clase-incidente"),
            {"desde": "2021-01-01", "hasta": "2021-09-30"},
        )
        assert r.status_code == 200
        assert r.data["serie"][0]["clase"] == "Choque"


@pytest.mark.django_db
def test_dashboard_distribucion_clase_incidente_rango_invalido():
    c = APIClient()
    r = c.get(
        reverse("dashboard-distribucion-clase-incidente"),
        {"desde": "2021-12-01", "hasta": "2021-01-01"},
    )
    assert r.status_code == 400
