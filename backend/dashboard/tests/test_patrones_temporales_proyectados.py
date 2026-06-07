from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.patrones_temporales_proyectados import (
    _distribuir_enteros,
    build_dia_semana_proyectado_payload,
    build_matriz_dia_hora_proyectada_payload,
)


def test_distribuir_enteros_suma_objetivo():
    assert sum(_distribuir_enteros([1.0, 2.0, 3.0], 10)) == 10
    assert sum(_distribuir_enteros([0.0, 0.0], 5)) == 5


@patch("dashboard.patrones_temporales_proyectados._total_proyectado_horizonte", return_value=(90.0, {"sin_modelo": False}))
@patch("dashboard.patrones_temporales_proyectados._query_heatmap")
def test_matriz_proyectada_reparte_total(mock_heat, _mock_total):
    mock_heat.return_value = {(1, 8): 10, (2, 9): 30}
    payload = build_matriz_dia_hora_proyectada_payload(
        date(2021, 1, 1),
        date(2021, 9, 30),
        horizonte_meses=3,
    )
    assert payload["meta"]["sin_datos"] is False
    assert payload["meta"]["total_proyectado_horizonte"] == 90.0
    assert sum(c["incidentes_proyectados_horizonte"] for c in payload["serie"]) == 90


@patch("dashboard.patrones_temporales_proyectados._total_proyectado_horizonte", return_value=(100.0, {"sin_modelo": False}))
@patch("dashboard.patrones_temporales_proyectados._query_heatmap")
def test_matriz_delta_coherente_por_celda(mock_heat, _mock_total):
    """Δ celda = proyección − periodo; ΣΔ = total proy − total periodo."""
    mock_heat.return_value = {(0, 0): 40, (1, 8): 10}
    payload = build_matriz_dia_hora_proyectada_payload(
        date(2021, 1, 1),
        date(2021, 3, 31),
        horizonte_meses=3,
    )
    total_hist = 50
    total_proj = 100
    v = payload["meta"]["validacion_diferencia"]
    assert v["coherente"] is True
    assert v["suma_observados_periodo"] == total_hist
    assert v["suma_proyectados_horizonte"] == total_proj
    assert v["suma_delta_celdas"] == total_proj - total_hist
    for cell in payload["serie"]:
        assert cell["delta_proyeccion_menos_periodo"] == (
            cell["incidentes_proyectados_horizonte"] - cell["incidentes_observados_periodo"]
        )
    c00 = next(c for c in payload["serie"] if c["dia_semana"] == 0 and c["hora"] == 0)
    assert c00["incidentes_observados_periodo"] == 40
    assert c00["delta_proyeccion_menos_periodo"] == c00["incidentes_proyectados_horizonte"] - 40


@patch("dashboard.patrones_temporales_proyectados._total_proyectado_horizonte", return_value=(90.0, {"sin_modelo": False}))
@patch("dashboard.patrones_temporales_proyectados._query_heatmap")
def test_matriz_proyectada_modelo_media_movil(mock_heat, mock_total):
    mock_heat.return_value = {(1, 8): 10, (2, 9): 30}
    payload = build_matriz_dia_hora_proyectada_payload(
        date(2021, 1, 1),
        date(2021, 9, 30),
        horizonte_meses=3,
        modelo="media_movil",
        ventana_ma=6,
    )
    assert payload["meta"]["modelo"] == "media_movil"
    assert payload["meta"]["ventana_meses"] == 6
    mock_total.assert_called_once()
    assert mock_total.call_args.args[4] == "media_movil"


@patch("dashboard.patrones_temporales_proyectados._total_proyectado_horizonte", return_value=(None, {"sin_modelo": True}))
@patch("dashboard.patrones_temporales_proyectados._query_heatmap", return_value={(0, 0): 5})
def test_matriz_proyectada_sin_modelo(_mock_heat, _mock_total):
    payload = build_matriz_dia_hora_proyectada_payload(
        date(2021, 1, 1),
        date(2021, 3, 31),
    )
    assert payload["meta"]["sin_datos"] is True


@patch("dashboard.patrones_temporales_proyectados._total_proyectado_horizonte", return_value=(70.0, {"sin_modelo": False}))
@patch("dashboard.patrones_temporales_proyectados._query_por_dia")
def test_dia_semana_proyectado_siete_dias(mock_dia, _mock_total):
    mock_dia.return_value = {i: (10 * (i + 1), 0) for i in range(7)}
    payload = build_dia_semana_proyectado_payload(
        date(2021, 1, 1),
        date(2021, 9, 30),
        horizonte_meses=3,
    )
    assert len(payload["serie"]) == 7
    assert sum(r["incidentes_proyectados_horizonte"] for r in payload["serie"]) == 70
    assert payload["serie"][0]["carga_dia_nivel_proyectado"] in ("alto", "medio", "bajo")


@pytest.mark.django_db
def test_api_matriz_dia_hora_proyectada_ok(analista_client):
    fake = {
        "meta": {"sin_datos": False, "horizonte_meses": 3},
        "serie": [{"dia_semana": 1, "hora": 8, "incidentes_proyectados_horizonte": 5}],
    }
    with patch(
        "dashboard.views.build_matriz_dia_hora_proyectada_payload",
        return_value=fake,
    ):
        r = analista_client.get(
            reverse("dashboard-matriz-dia-hora-proyectada"),
            {"desde": "2021-01-01", "hasta": "2021-09-30", "horizonte_meses": 3},
        )
        assert r.status_code == 200
        assert r.data["serie"][0]["incidentes_proyectados_horizonte"] == 5


@pytest.mark.django_db
def test_api_dia_semana_proyectado_rango_invalido(analista_client):
    r = analista_client.get(
        reverse("dashboard-por-dia-semana-proyectado"),
        {"desde": "2021-10-01", "hasta": "2021-09-30"},
    )
    assert r.status_code == 400
