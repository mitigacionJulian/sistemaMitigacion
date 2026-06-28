"""Pruebas del panel administrador: ejecución y reporte imprimible."""
from __future__ import annotations

import json

import pytest
from django.test import override_settings
from django.urls import reverse

from accounts.pruebas_runner import ESTADO_IDLE, parse_allure_summary, state_file_path


@pytest.fixture(autouse=True)
def _limpiar_estado_runner(tmp_path, settings):
    settings.ALLURE_RESULTS_DIR = tmp_path / "allure-results"
    settings.PRUEBAS_RUNNER_STATE_FILE = tmp_path / "runner_state.json"
    settings.ALLOW_ADMIN_TEST_RUNNER = True
    yield


@pytest.mark.django_db
def test_admin_pruebas_estado_requires_administrador(api_client, ciudadano_user):
    login = api_client.post(
        reverse("auth-login"),
        {"username": "pytest_ciudadano", "password": "CiudadanoTest123!"},
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    r = api_client.get(reverse("admin-pruebas-estado"))
    assert r.status_code == 403


@pytest.mark.django_db
def test_admin_pruebas_estado_payload(admin_client):
    r = admin_client.get(reverse("admin-pruebas-estado"))
    assert r.status_code == 200
    assert r.data["puede_ejecutar"] is True
    assert r.data["estado"] == ESTADO_IDLE
    assert "resumen" in r.data
    assert r.data["resumen"]["total"] == 0
    assert "casos" in r.data["resumen"]


@pytest.mark.django_db
@override_settings(ALLOW_ADMIN_TEST_RUNNER=False)
def test_admin_pruebas_ejecutar_disabled(admin_client):
    r = admin_client.post(reverse("admin-pruebas-ejecutar"))
    assert r.status_code == 403
    assert r.data["code"] == "runner_disabled"


@pytest.mark.django_db
def test_parse_allure_summary_incluye_casos(tmp_path):
    results = tmp_path / "allure-results"
    results.mkdir()
    payload = {
        "name": "test_ejemplo",
        "status": "passed",
        "start": 1000,
        "stop": 1500,
        "labels": [
            {"name": "epic", "value": "Cuentas y autenticación"},
            {"name": "feature", "value": "Autenticación JWT"},
            {"name": "categoria", "value": "Autenticación y roles"},
        ],
    }
    (results / "demo-result.json").write_text(json.dumps(payload), encoding="utf-8")
    summary = parse_allure_summary(results)
    assert summary["hay_resultados"] is True
    assert summary["total"] == 1
    assert len(summary["casos"]) == 1
    assert summary["casos"][0]["nombre"] == "test_ejemplo"


@pytest.mark.django_db
def test_admin_pruebas_reporte_imprimible_sin_resultados(admin_client):
    r = admin_client.post(reverse("admin-pruebas-reporte"), {"titulo": "Test", "notas": ""}, format="json")
    assert r.status_code == 400
    assert r.data["code"] == "sin_resultados"


@pytest.mark.django_db
def test_admin_pruebas_reporte_imprimible_con_resultados(admin_client, tmp_path, settings):
    results = settings.ALLURE_RESULTS_DIR
    results.mkdir(parents=True, exist_ok=True)
    (results / "demo-result.json").write_text(
        json.dumps({"name": "test_ok", "status": "passed", "labels": [{"name": "epic", "value": "Demo"}]}),
        encoding="utf-8",
    )
    r = admin_client.post(
        reverse("admin-pruebas-reporte"),
        {"titulo": "Reporte pruebas", "notas": "Nota de prueba"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["meta"]["seccion"] == "pruebas"
    assert r.data["cuerpo"]["tipo"] == "pruebas"
    assert r.data["cuerpo"]["resumen"]["total"] == 1


@pytest.mark.django_db
def test_state_file_no_rompe_estado(admin_client):
    path = state_file_path()
    path.write_text('{"estado": "done", "codigo_salida": 0}', encoding="utf-8")
    r = admin_client.get(reverse("admin-pruebas-estado"))
    assert r.status_code == 200
    assert r.data["estado"] == "done"
    assert r.data["codigo_salida"] == 0
