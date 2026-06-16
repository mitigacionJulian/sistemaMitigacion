import pytest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import PerfilUsuario, Rol

User = get_user_model()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


FAKE_CUERPO = {
    "tipo": "tablero",
    "kpis": {"meta": {}, "comparacion": {}},
    "evolucion_mensual": {"serie": []},
    "dia_semana": {"serie": []},
    "matriz_dia_hora": {"resumen": {}},
    "distribucion_clase_incidente": {"serie": []},
    "distribucion_gravedad": {"serie": []},
    "tops": {"sexo": []},
}


@pytest.mark.django_db
def test_reporte_tablero_requires_analista(api_client):
    ciudadano = Rol.objects.get(codigo="ciudadano")
    analista = Rol.objects.get(codigo="analista")

    u_c = User.objects.create_user(username="tab_c", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_c, rol=ciudadano, telefono="573001111111")

    u_a = User.objects.create_user(username="tab_a", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_a, rol=analista, telefono="573002222222")

    url = reverse("reportes-tablero")
    body = {
        "titulo": "Test",
        "filtros": {"desde": "2021-01-01"},
        "query": {"desde": "2021-01-01", "hasta": "2021-03-31"},
    }

    r_anon = api_client.post(url, body, format="json")
    assert r_anon.status_code == 401

    login_c = api_client.post(
        reverse("auth-login"),
        {"username": "tab_c", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_c.data['access']}")
    r_ciudadano = api_client.post(url, body, format="json")
    assert r_ciudadano.status_code == 403

    login_a = api_client.post(
        reverse("auth-login"),
        {"username": "tab_a", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_a.data['access']}")

    with patch("reports.views.build_tablero_report_body", return_value=FAKE_CUERPO):
        r_analista = api_client.post(url, body, format="json")
    assert r_analista.status_code == 200
    data = r_analista.json()
    assert data["meta"]["seccion"] == "tablero"
    assert data["cuerpo"]["tipo"] == "tablero"


@pytest.mark.django_db
def test_reporte_tablero_rango_invalido(analista_client):
    url = reverse("reportes-tablero")
    r = analista_client.post(
        url,
        {"query": {"desde": "2026-05-01", "hasta": "2026-01-01"}},
        format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_reporte_tablero_ok_mock(analista_client):
    url = reverse("reportes-tablero")
    with patch("reports.views.build_tablero_report_body", return_value=FAKE_CUERPO):
        r = analista_client.post(
            url,
            {
                "titulo": "Informe Q1",
                "notas": "Prueba",
                "filtros": {"desde": "2021-01-01", "hasta": "2021-03-31"},
                "query": {
                    "desde": "2021-01-01",
                    "hasta": "2021-03-31",
                    "top_n": 10,
                },
            },
            format="json",
        )
    assert r.status_code == 200
    assert r.json()["meta"]["titulo"] == "Informe Q1"
    assert r.json()["meta"]["notas"] == "Prueba"
