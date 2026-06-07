from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_dashboard_predicciones_mensuales_ok(analista_client):
    fake = {
        "meta": {
            "fecha_inicio": "2021-01-01",
            "fecha_fin": "2021-03-31",
            "horizonte_meses": 3,
            "sin_modelo": False,
            "metodo": "test",
            "coeficientes": {"intercepto_a": 0, "pendiente_b_mes": 1, "r2": 1},
            "limitaciones": "",
            "filtros": {"comuna_id": None, "barrio_id": None, "clase_incidente_id": None},
        },
        "serie_historica": [],
        "proyeccion": [{"mes_clave": "2021-04", "mes_etiqueta": "abr 2021", "incidentes_proyectados": 1.0}],
    }
    with patch("dashboard.views.build_predicciones_mensuales_payload", return_value=fake):
        r = analista_client.get(
            reverse("dashboard-predicciones-mensuales"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "horizonte_meses": "3"},
        )
        assert r.status_code == 200
        assert len(r.data["proyeccion"]) == 1


@pytest.mark.django_db
def test_dashboard_predicciones_rango_invalido(analista_client):
    r = analista_client.get(
        reverse("dashboard-predicciones-mensuales"),
        {"desde": "2021-05-01", "hasta": "2021-01-01"},
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_dashboard_predicciones_parametros_fase_a(analista_client):
    fake = {
        "meta": {
            "modelo": "estacional",
            "variable": "victimas",
            "desglose_clase": False,
        },
        "serie_historica": [{"mes_etiqueta": "ene 2021", "observados": 1}],
        "proyeccion": [],
    }
    with patch("dashboard.views.build_predicciones_mensuales_payload", return_value=fake) as build:
        r = analista_client.get(
            reverse("dashboard-predicciones-mensuales"),
            {
                "desde": "2021-01-01",
                "hasta": "2021-03-31",
                "modelo": "estacional",
                "variable": "victimas",
            },
        )
        assert r.status_code == 200
        build.assert_called_once()
        kwargs = build.call_args.kwargs
        assert kwargs["modelo"] == "estacional"
        assert kwargs["variable"] == "victimas"


@pytest.mark.django_db
def test_dashboard_predicciones_desglose_con_clase_conflict(analista_client):
    r = analista_client.get(
        reverse("dashboard-predicciones-mensuales"),
        {
            "desde": "2021-01-01",
            "hasta": "2021-03-31",
            "desglose_clase": "1",
            "clase_incidente_id": "2",
        },
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_dashboard_predicciones_modelo_invalido(analista_client):
    r = analista_client.get(
        reverse("dashboard-predicciones-mensuales"),
        {
            "desde": "2021-01-01",
            "hasta": "2021-03-31",
            "modelo": "arima",
        },
    )
    assert r.status_code == 400
