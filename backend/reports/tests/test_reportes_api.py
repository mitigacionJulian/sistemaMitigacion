import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import PerfilUsuario, Rol

User = get_user_model()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.mark.django_db
def test_reportes_preview_requires_analista(api_client):
    ciudadano = Rol.objects.get(codigo="ciudadano")
    analista = Rol.objects.get(codigo="analista")

    u_c = User.objects.create_user(username="rep_c", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_c, rol=ciudadano, telefono="573001111111")

    u_a = User.objects.create_user(username="rep_a", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_a, rol=analista, telefono="573002222222")

    url = reverse("reportes-preview")

    r_anon = api_client.get(url)
    assert r_anon.status_code == 401

    login_c = api_client.post(
        reverse("auth-login"),
        {"username": "rep_c", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_c.data['access']}")
    r_ciudadano = api_client.get(url)
    assert r_ciudadano.status_code == 403

    login_a = api_client.post(
        reverse("auth-login"),
        {"username": "rep_a", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_a.data['access']}")
    r_analista = api_client.get(url, {"seccion": "tablero"})
    assert r_analista.status_code == 200
    body = r_analista.json()
    assert "meta" in body and "cuerpo" in body
    assert body["meta"]["seccion"] == "tablero"
    assert body["meta"]["rol_codigo"] == "analista"
    assert body["cuerpo"]["tipo"] == "placeholder"


@pytest.mark.django_db
def test_reportes_preview_post_con_filtros(analista_client):
    url = reverse("reportes-preview")
    filtros = {"desde": "2021-01-01", "hasta": "2021-09-30", "comuna": "La Candelaria"}
    r = analista_client.post(
        url,
        {
            "seccion": "tablero",
            "titulo": "Informe de prueba",
            "notas": "Nota opcional",
            "filtros": filtros,
        },
        format="json",
    )
    assert r.status_code == 200
    meta = r.json()["meta"]
    assert meta["titulo"] == "Informe de prueba"
    assert meta["notas"] == "Nota opcional"
    assert meta["filtros"] == filtros


@pytest.mark.django_db
def test_reportes_preview_filtros_json_invalido(analista_client):
    url = reverse("reportes-preview")
    r = analista_client.get(url, {"filtros": "{no-json"})
    assert r.status_code == 400


@pytest.mark.django_db
def test_reportes_preview_seccion_invalida(analista_client):
    url = reverse("reportes-preview")
    r = analista_client.get(url, {"seccion": "inventada"})
    assert r.status_code == 400


@pytest.mark.django_db
def test_reportes_preview_get_filtros_json(analista_client):
    url = reverse("reportes-preview")
    filtros = {"desde": "2021-01-01"}
    r = analista_client.get(
        url,
        {"seccion": "mapa", "filtros": json.dumps(filtros)},
    )
    assert r.status_code == 200
    assert r.json()["meta"]["filtros"] == filtros
