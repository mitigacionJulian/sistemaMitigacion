import pytest
from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_kpis_ok(monkeypatch):
    fake_payload = {
        "meta": {"es_demostracion": False},
        "kpis_periodo_actual": {},
        "kpis_periodo_anterior": {},
        "comparacion": {},
    }
    with patch("dashboard.views.build_kpis_payload", return_value=fake_payload):
        c = APIClient()
        r = c.get(reverse("dashboard-kpis"))
        assert r.status_code == 200
        assert r.data["meta"]["es_demostracion"] is False


@pytest.mark.django_db
def test_dashboard_kpis_rango_invalido():
    c = APIClient()
    r = c.get(reverse("dashboard-kpis"), {"desde": "2026-05-01", "hasta": "2026-01-01"})
    assert r.status_code == 400
