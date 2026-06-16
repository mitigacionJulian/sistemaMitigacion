import pytest
from unittest.mock import patch

from django.urls import reverse


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


FAKE_CUERPO_MAPA = {
    "tipo": "mapa",
    "modo_vista": "territorio",
    "meta_modo": {"nivel": "comuna", "metrica": "densidad"},
    "top_territorios": [],
}


@pytest.mark.django_db
def test_reporte_mapa_requires_analista(api_client):
    url = reverse("reportes-mapa")
    r_anon = api_client.post(url, {"query": {"desde": "2021-01-01", "hasta": "2021-03-31"}}, format="json")
    assert r_anon.status_code == 401


@pytest.mark.django_db
def test_reporte_mapa_ok_mock(analista_client):
    url = reverse("reportes-mapa")
    with patch("reports.views.build_mapa_report_body", return_value=FAKE_CUERPO_MAPA):
        r = analista_client.post(
            url,
            {
                "titulo": "Mapa febrero",
                "filtros": {"desde": "2021-02-01", "hasta": "2021-02-28"},
                "query": {
                    "desde": "2021-02-01",
                    "hasta": "2021-02-28",
                    "view_mode": "territorio",
                    "choropleth_metric": "densidad",
                },
            },
            format="json",
        )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["seccion"] == "mapa"
    assert body["cuerpo"]["tipo"] == "mapa"


@pytest.mark.django_db
def test_reporte_mapa_rango_invalido(analista_client):
    url = reverse("reportes-mapa")
    r = analista_client.post(
        url,
        {"query": {"desde": "2026-06-01", "hasta": "2026-01-01"}},
        format="json",
    )
    assert r.status_code == 400
