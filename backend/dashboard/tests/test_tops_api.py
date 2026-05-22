from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_tops_ok():
    fake = {
        "meta": {"fecha_inicio": "2021-01-01", "fecha_fin": "2021-09-30", "total_victimas_periodo": 100, "limite": 10},
        "sexo": [{"rank": 1, "nombre": "M", "total_victimas": 60, "porcentaje": 60.0}],
        "edad": [],
        "condicion": [],
        "comuna": [],
        "barrio": [],
    }
    with patch("dashboard.views.build_tops_payload", return_value=fake):
        c = APIClient()
        r = c.get(reverse("dashboard-tops"), {"desde": "2021-01-01", "hasta": "2021-09-30"})
        assert r.status_code == 200
        assert r.data["sexo"][0]["nombre"] == "M"


@pytest.mark.django_db
def test_dashboard_tops_rango_invalido():
    c = APIClient()
    r = c.get(reverse("dashboard-tops"), {"desde": "2021-12-01", "hasta": "2021-01-01"})
    assert r.status_code == 400
