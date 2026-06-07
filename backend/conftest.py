"""Fixtures compartidas para pytest (backend)."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import PerfilUsuario, Rol

User = get_user_model()


@pytest.fixture
def analista_client(db):
    """APIClient autenticado con rol analista (endpoints de predicciones)."""
    rol = Rol.objects.get(codigo="analista")
    user = User.objects.create_user(username="pytest_analista", password="TestPass123!")
    PerfilUsuario.objects.create(user=user, rol=rol, telefono="573009999999")
    client = APIClient()
    login = client.post(
        reverse("auth-login"),
        {"username": "pytest_analista", "password": "TestPass123!"},
        format="json",
    )
    assert login.status_code == 200, login.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client
