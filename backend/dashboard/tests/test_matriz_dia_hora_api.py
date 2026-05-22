from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_matriz_dia_hora_ok():
    fake = {
        "meta": {"fecha_inicio": "2021-01-01", "fecha_fin": "2021-09-30"},
        "serie": [
            {
                "dia_semana": 1,
                "hora": 8,
                "total_incidentes_actual": 12,
                "total_incidentes_anterior": 9,
                "delta_abs": 3,
            }
        ],
    }
    with patch("dashboard.views.build_matriz_dia_hora_payload", return_value=fake):
        c = APIClient()
        r = c.get(reverse("dashboard-matriz-dia-hora"), {"desde": "2021-01-01", "hasta": "2021-09-30"})
        assert r.status_code == 200
        assert r.data["serie"][0]["delta_abs"] == 3


@pytest.mark.django_db
def test_dashboard_matriz_dia_hora_rango_invalido():
    c = APIClient()
    r = c.get(reverse("dashboard-matriz-dia-hora"), {"desde": "2021-10-01", "hasta": "2021-09-30"})
    assert r.status_code == 400
