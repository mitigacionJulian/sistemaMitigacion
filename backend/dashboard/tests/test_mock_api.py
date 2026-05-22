import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_dashboard_mock_ok():
    from rest_framework.test import APIClient

    c = APIClient()
    r = c.get(reverse("dashboard-mock"))
    assert r.status_code == 200
    assert r.data["meta"]["es_demostracion"] is True
    assert "kpis" in r.data
    assert r.data["kpis"]["total_incidentes"] > 0
