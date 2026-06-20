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
def admin_user(db):
    rol = Rol.objects.get(codigo="administrador")
    user = User.objects.create_user(
        username="pytest_admin",
        email="admin@test.local",
        password="AdminTest123!",
    )
    PerfilUsuario.objects.create(user=user, rol=rol, telefono="573009998877")
    return user


@pytest.fixture
def admin_client(api_client, admin_user):
    login = api_client.post(
        reverse("auth-login"),
        {"username": "pytest_admin", "password": "AdminTest123!"},
        format="json",
    )
    assert login.status_code == 200, login.data
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return api_client


@pytest.fixture
def ciudadano_user(db):
    rol = Rol.objects.get(codigo="ciudadano")
    user = User.objects.create_user(
        username="pytest_ciudadano",
        email="c@test.local",
        password="CiudadanoTest123!",
    )
    PerfilUsuario.objects.create(user=user, rol=rol, telefono="573001234567")
    return user


@pytest.mark.django_db
def test_admin_usuarios_requires_administrador(api_client, ciudadano_user):
    login = api_client.post(
        reverse("auth-login"),
        {"username": "pytest_ciudadano", "password": "CiudadanoTest123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    r = api_client.get(reverse("admin-usuarios"))
    assert r.status_code == 403


@pytest.mark.django_db
def test_admin_list_create_update_delete(admin_client, admin_user):
    r_list = admin_client.get(reverse("admin-usuarios"))
    assert r_list.status_code == 200
    assert isinstance(r_list.data, list)
    assert any(u["username"] == "pytest_admin" for u in r_list.data)

    r_create = admin_client.post(
        reverse("admin-usuarios"),
        {
            "username": "nuevo_admin_test",
            "email": "nuevo@test.local",
            "password": "NuevaClaveSegura1!",
            "telefono": "3007654321",
            "rol_codigo": "analista",
            "first_name": "Nuevo",
            "last_name": "Analista",
        },
        format="json",
    )
    assert r_create.status_code == 201
    user_id = r_create.data["id"]
    assert r_create.data["perfil"]["rol_codigo"] == "analista"

    r_patch = admin_client.patch(
        reverse("admin-usuario-detail", args=[user_id]),
        {"rol_codigo": "ciudadano", "is_active": False},
        format="json",
    )
    assert r_patch.status_code == 200
    assert r_patch.data["perfil"]["rol_codigo"] == "ciudadano"
    assert r_patch.data["is_active"] is False

    r_delete = admin_client.delete(reverse("admin-usuario-detail", args=[user_id]))
    assert r_delete.status_code == 204
    assert not User.objects.filter(pk=user_id).exists()


@pytest.mark.django_db
def test_admin_cannot_delete_self(admin_client, admin_user):
    r = admin_client.delete(reverse("admin-usuario-detail", args=[admin_user.pk]))
    assert r.status_code == 400


@pytest.mark.django_db
def test_administrador_access_predicciones(api_client, admin_user):
    url = reverse("dashboard-predicciones-mensuales") + "?desde=2021-01-01&hasta=2021-03-31"
    login = api_client.post(
        reverse("auth-login"),
        {"username": "pytest_admin", "password": "AdminTest123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    r = api_client.get(url)
    assert r.status_code in (200, 500, 503)


@pytest.mark.django_db
def test_seed_admin_user_exists(db):
    user = User.objects.filter(username="admin").first()
    if user is None:
        pytest.skip("Migración 0005 no aplicada en esta BD de prueba")
    assert user.perfil.rol.codigo == "administrador"
