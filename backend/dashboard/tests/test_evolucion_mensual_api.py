from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_evolucion_mensual_ok():
    fake = {
        "meta": {
            "fecha_inicio": "2021-01-01",
            "fecha_fin": "2021-03-31",
            "fecha_inicio_anterior": "2020-01-01",
            "fecha_fin_anterior": "2020-03-31",
        },
        "serie": [
            {
                "mes_clave": "2021-01",
                "mes_etiqueta": "ene 2021",
                "incidentes_periodo_actual": 1,
                "victimas_periodo_actual": 2,
                "incidentes_periodo_anterior": 0,
                "victimas_periodo_anterior": 0,
            },
        ],
    }
    with patch("dashboard.views.build_evolucion_payload", return_value=fake):
        c = APIClient()
        r = c.get(reverse("dashboard-evolucion-mensual"), {"desde": "2021-01-01", "hasta": "2021-03-31"})
        assert r.status_code == 200
        assert len(r.data["serie"]) == 1


@pytest.mark.django_db
def test_dashboard_evolucion_rango_invalido():
    c = APIClient()
    r = c.get(
        reverse("dashboard-evolucion-mensual"),
        {"desde": "2021-05-01", "hasta": "2021-01-01"},
    )
    assert r.status_code == 400
