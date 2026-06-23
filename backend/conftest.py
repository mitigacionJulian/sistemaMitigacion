"""Fixtures compartidas y metadatos Allure para pytest (backend)."""
from __future__ import annotations

from pathlib import Path

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


def _allure_dir_from_config(config) -> Path | None:
    path = config.getoption("--alluredir", default=None)
    if not path:
        return None
    return Path(path)


def pytest_runtest_setup(item):
    """Etiquetas Allure: epic, feature, categoría, severidad, capa, indicador."""
    try:
        import allure as allure_module
    except ImportError:
        return
    if not _allure_dir_from_config(item.config):
        return
    from allure_reporting import apply_allure_labels

    apply_allure_labels(item, allure_module)


def pytest_sessionstart(session):
    """Metadatos del reporte (entorno, categorías) al inicio de la sesión."""
    allure_dir = _allure_dir_from_config(session.config)
    if not allure_dir:
        return
    from allure_reporting import write_allure_metadata

    write_allure_metadata(allure_dir)
