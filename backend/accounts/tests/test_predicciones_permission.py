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
def test_predicciones_requires_analista(api_client):
    ciudadano = Rol.objects.get(codigo="ciudadano")
    analista = Rol.objects.get(codigo="analista")

    u_c = User.objects.create_user(username="c1", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_c, rol=ciudadano, telefono="573001111111")

    u_a = User.objects.create_user(username="a1", password="ClaveSegura123!")
    PerfilUsuario.objects.create(user=u_a, rol=analista, telefono="573002222222")

    url = reverse("dashboard-predicciones-mensuales") + "?desde=2021-01-01&hasta=2021-03-31"

    r_anon = api_client.get(url)
    assert r_anon.status_code == 401

    login_c = api_client.post(
        reverse("auth-login"),
        {"username": "c1", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_c.data['access']}")
    r_ciudadano = api_client.get(url)
    assert r_ciudadano.status_code == 403

    login_a = api_client.post(
        reverse("auth-login"),
        {"username": "a1", "password": "ClaveSegura123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_a.data['access']}")
    r_analista = api_client.get(url)
    assert r_analista.status_code in (200, 500, 503)
