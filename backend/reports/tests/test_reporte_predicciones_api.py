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


FAKE_CUERPO_PRED = {
    "tipo": "predicciones",
    "aviso": "Proyecciones, no hechos observados.",
    "configuracion": {"horizonte_meses": 3},
    "predicciones_mensuales": {"meta": {}, "tabla_mensual": []},
    "prioridad_territorial": {"meta": {}, "ranking": []},
    "proporcion_fatales": {"meta": {}, "tabla_mensual": []},
    "carga_esperada": {"meta": {}, "ranking": []},
    "matriz_dia_hora_proyectada": {"meta": {}, "resumen": {}},
    "dia_semana_proyectado": {"meta": {}, "serie": []},
}


@pytest.mark.django_db
def test_reporte_predicciones_requires_analista(api_client):
    ciudadano = Rol.objects.get(codigo="ciudadano")
    analista = Rol.objects.get(codigo="analista")

    u_c = User.objects.create_user(username="pred_c", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_c, rol=ciudadano, telefono="573001111111")

    u_a = User.objects.create_user(username="pred_a", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_a, rol=analista, telefono="573002222222")

    url = reverse("reportes-predicciones")
    body = {
        "titulo": "Test",
        "filtros": {"desde": "2021-01-01"},
        "query": {"desde": "2021-01-01", "hasta": "2021-03-31"},
    }

    r_anon = api_client.post(url, body, format="json")
    assert r_anon.status_code == 401

    login_c = api_client.post(
        reverse("auth-login"),
        {"username": "pred_c", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_c.data['access']}")
    r_ciudadano = api_client.post(url, body, format="json")
    assert r_ciudadano.status_code == 403

    login_a = api_client.post(
        reverse("auth-login"),
        {"username": "pred_a", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_a.data['access']}")

    with patch("reports.views.build_predicciones_report_body", return_value=FAKE_CUERPO_PRED):
        r_analista = api_client.post(url, body, format="json")
    assert r_analista.status_code == 200
    data = r_analista.json()
    assert data["meta"]["seccion"] == "predicciones"
    assert data["cuerpo"]["tipo"] == "predicciones"


@pytest.mark.django_db
def test_reporte_predicciones_rango_invalido(analista_client):
    url = reverse("reportes-predicciones")
    r = analista_client.post(
        url,
        {"query": {"desde": "2026-05-01", "hasta": "2026-01-01"}},
        format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_reporte_predicciones_ok_mock(analista_client):
    url = reverse("reportes-predicciones")
    with patch("reports.views.build_predicciones_report_body", return_value=FAKE_CUERPO_PRED):
        r = analista_client.post(
            url,
            {
                "titulo": "Informe proyecciones",
                "notas": "Prueba",
                "filtros": {"desde": "2021-01-01", "hasta": "2021-03-31"},
                "query": {
                    "desde": "2021-01-01",
                    "hasta": "2021-03-31",
                    "horizonte_meses": 3,
                    "modelo_pred": "ols",
                    "modelo_prop": "estacional",
                    "modelo_carga": "estacional",
                },
            },
            format="json",
        )
    assert r.status_code == 200
    assert r.json()["meta"]["titulo"] == "Informe proyecciones"
    assert r.json()["cuerpo"]["tipo"] == "predicciones"
