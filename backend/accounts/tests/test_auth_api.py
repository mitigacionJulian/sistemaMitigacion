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


@pytest.mark.django_db
def test_register_creates_user_perfil_and_session(api_client, rol_ciudadano):
    url = reverse("auth-register")
    r = api_client.post(
        url,
        {
            "username": "nuevo_usuario",
            "email": "nuevo@example.com",
            "password": "UnaClaveSegura123",
            "password_confirm": "UnaClaveSegura123",
            "first_name": "Ana",
            "last_name": "López",
        },
        format="json",
    )
    assert r.status_code == 201
    assert User.objects.filter(username="nuevo_usuario").exists()
    user = User.objects.get(username="nuevo_usuario")
    assert hasattr(user, "perfil")
    assert user.perfil.rol_id == rol_ciudadano.id
    assert r.data["username"] == "nuevo_usuario"
    assert r.data["perfil"]["rol_codigo"] == "ciudadano"


@pytest.mark.django_db
def test_login_logout_me(api_client, rol_ciudadano):
    user = User.objects.create_user(
        username="operador1",
        email="op@example.com",
        password="OtraClaveSegura456",
    )
    PerfilUsuario.objects.create(user=user, rol=rol_ciudadano)

    login_url = reverse("auth-login")
    r = api_client.post(
        login_url,
        {"username": "operador1", "password": "OtraClaveSegura456"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["username"] == "operador1"

    me_url = reverse("auth-me")
    r_me = api_client.get(me_url)
    assert r_me.status_code == 200
    assert r_me.data["username"] == "operador1"

    logout_url = reverse("auth-logout")
    r_out = api_client.post(logout_url)
    assert r_out.status_code == 204

    r_me2 = api_client.get(me_url)
    assert r_me2.status_code == 403


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
    assert r.status_code == 400
