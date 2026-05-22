from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_distribucion_gravedad_ok():
    fake = {
        "meta": {"fecha_inicio": "2021-01-01", "fecha_fin": "2021-09-30"},
        "serie": [{"codigo": "FATAL", "gravedad": "Fatal", "victimas_periodo_actual": 5, "victimas_periodo_anterior": 4}],
    }
    with patch("dashboard.views.build_distribucion_gravedad_payload", return_value=fake):
        c = APIClient()
        r = c.get(reverse("dashboard-distribucion-gravedad"), {"desde": "2021-01-01", "hasta": "2021-09-30"})
        assert r.status_code == 200
        assert r.data["serie"][0]["codigo"] == "FATAL"


@pytest.mark.django_db
def test_dashboard_distribucion_gravedad_rango_invalido():
    c = APIClient()
    r = c.get(reverse("dashboard-distribucion-gravedad"), {"desde": "2021-12-01", "hasta": "2021-01-01"})
    assert r.status_code == 400
