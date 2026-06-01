import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import PerfilUsuario, Rol

User = get_user_model()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def rol_ciudadano(db):
    return Rol.objects.get(codigo="ciudadano")


@pytest.fixture
def rol_analista(db):
    return Rol.objects.get(codigo="analista")


@pytest.mark.django_db
def test_register_creates_user_perfil_and_jwt(api_client, rol_ciudadano):
    url = reverse("auth-register")
    r = api_client.post(
        url,
        {
            "username": "nuevo_usuario",
            "email": "nuevo@example.com",
            "password": "UnaClaveSegura123",
            "password_confirm": "UnaClaveSegura123",
            "telefono": "3001234567",
            "rol_codigo": "ciudadano",
        },
        format="json",
    )
    assert r.status_code == 201
    assert "tokens" in r.data
    assert r.data["tokens"]["access"]
    assert User.objects.filter(username="nuevo_usuario").exists()
    user = User.objects.get(username="nuevo_usuario")
    assert user.perfil.rol_id == rol_ciudadano.id
    assert user.perfil.telefono == "573001234567"


@pytest.mark.django_db
def test_register_analista(api_client, rol_analista):
    r = api_client.post(
        reverse("auth-register"),
        {
            "username": "analista1",
            "email": "a@example.com",
            "password": "UnaClaveSegura123",
            "password_confirm": "UnaClaveSegura123",
            "telefono": "3019876543",
            "rol_codigo": "analista",
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.data["perfil"]["rol_codigo"] == "analista"


@pytest.mark.django_db
def test_login_jwt_me_logout(api_client, rol_analista):
    user = User.objects.create_user(
        username="operador1",
        email="op@example.com",
        password="OtraClaveSegura456",
    )
    PerfilUsuario.objects.create(user=user, rol=rol_analista, telefono="573001112233")

    r = api_client.post(
        reverse("auth-login"),
        {"username": "operador1", "password": "OtraClaveSegura456"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["access"]
    assert r.data["user"]["perfil"]["rol_codigo"] == "analista"

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    r_me = api_client.get(reverse("auth-me"))
    assert r_me.status_code == 200

    r_out = api_client.post(reverse("auth-logout"))
    assert r_out.status_code == 204


@pytest.mark.django_db
def test_login_invalid_credentials(api_client):
    User.objects.create_user(
        username="solo_user",
        email="s@example.com",
        password="ClaveCorrecta999",
    )
    r = api_client.post(
        reverse("auth-login"),
        {"username": "solo_user", "password": "mala"},
        format="json",
    )
    assert r.status_code == 401


@pytest.mark.django_db
def test_password_reset_whatsapp_flow(api_client, rol_ciudadano):
    user = User.objects.create_user(
        username="reset_user",
        email="r@example.com",
        password="ClaveCorrecta999",
    )
    PerfilUsuario.objects.create(user=user, rol=rol_ciudadano, telefono="573009998877")

    r = api_client.post(
        reverse("auth-password-reset-request"),
        {"username": "reset_user", "telefono": "3009998877"},
        format="json",
    )
    assert r.status_code == 200
    assert "whatsapp_url" in r.data
    assert "wa.me/573009998877" in r.data["whatsapp_url"]
    assert "token=" in r.data["reset_url"]

    token = r.data["reset_url"].split("token=")[-1]
    r2 = api_client.post(
        reverse("auth-password-reset-confirm"),
        {
            "token": token,
            "password": "NuevaClaveSegura888",
            "password_confirm": "NuevaClaveSegura888",
        },
        format="json",
    )
    assert r2.status_code == 200
    user.refresh_from_db()
    assert user.check_password("NuevaClaveSegura888")
