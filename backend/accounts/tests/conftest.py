"""Fixtures compartidas para pruebas de accounts."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import PerfilUsuario, Rol

User = get_user_model()


@pytest.fixture
def api_client():
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
