"""Tests ARIMA / SARIMA en proyección mensual."""
from datetime import date
from unittest.mock import patch

import pytest

from dashboard.kpis import FiltrosKpi
from dashboard.modelos_arima import (
    MIN_MESES_ARIMA,
    MIN_MESES_SARIMA,
    ajustar_y_proyectar_arima,
    parse_arima_order,
    parse_sarima_seasonal,
)
from dashboard.predicciones_mensuales import ArimaOpciones, build_predicciones_mensuales_payload

statsmodels = pytest.importorskip("statsmodels")


def _serie_24_meses():
    base = 80
    return {f"2020-{(i % 12) + 1:02d}": base + (i % 12) * 3 + (i // 12) * 5 for i in range(24)}


def test_arima_requiere_minimo_meses():
    ys = [float(i) for i in range(8)]
    assert ajustar_y_proyectar_arima(ys, 3, seasonal=False) is None


def test_sarima_requiere_24_meses():
    ys = [float(i) for i in range(18)]
    assert ajustar_y_proyectar_arima(ys, 3, seasonal=True) is None


def test_arima_ajusta_y_proyecta():
    ys = [float(50 + (i % 6) * 2) for i in range(MIN_MESES_ARIMA)]
    res = ajustar_y_proyectar_arima(ys, 2, seasonal=False)
    assert res is not None
    yhat, fore, coef = res
    assert len(yhat) == len(ys)
    assert len(fore) == 2
    assert all(x >= 0 for x in fore)
    assert coef.get("orden_arima") == [2, 1, 3]
    assert coef.get("aic") is not None


def test_build_payload_arima_mock_serie():
    act = {f"2020-{(i % 12) + 1:02d}": 40 + i for i in range(12)}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2020, 1, 1),
            date(2020, 12, 31),
            FiltrosKpi(),
            2,
            modelo="arima",
        )
    assert p["meta"]["modelo"] == "arima"
    assert p["meta"]["sin_modelo"] is False
    assert len(p["proyeccion"]) == 2


def test_build_payload_sarima_serie_larga():
    act = _serie_24_meses()
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2020, 1, 1),
            date(2021, 12, 31),
            FiltrosKpi(),
            3,
            modelo="sarima",
        )
    assert p["meta"]["modelo"] == "sarima"
    assert p["meta"]["sin_modelo"] is False
    assert len(p["proyeccion"]) == 3
    assert p["meta"]["coeficientes"].get("orden_estacional") is not None


def test_parse_arima_order_acepta_parentesis():
    assert parse_arima_order("(1,1,1)") == (1, 1, 1)
    assert parse_arima_order("2,1,3") == (2, 1, 3)
    assert parse_arima_order("9,1,1") is None


def test_parse_sarima_seasonal_requiere_periodo_12():
    assert parse_sarima_seasonal("(1,1,1,12)") == (1, 1, 1, 12)
    assert parse_sarima_seasonal("1,1,1,6") is None


def test_arima_orden_personalizado():
    ys = [float(50 + (i % 6) * 2) for i in range(MIN_MESES_ARIMA)]
    res = ajustar_y_proyectar_arima(ys, 2, seasonal=False, order=(1, 1, 1))
    assert res is not None
    _, _, coef = res
    assert coef.get("orden_arima") == [1, 1, 1]
    assert coef.get("orden_arima_solicitado") == [1, 1, 1]


def test_build_payload_arima_con_orden_query():
    act = {f"2020-{(i % 12) + 1:02d}": 40 + i for i in range(12)}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2020, 1, 1),
            date(2020, 12, 31),
            FiltrosKpi(),
            2,
            modelo="arima",
            arima_opciones=ArimaOpciones(order=(1, 1, 1)),
        )
    assert p["meta"]["arima_order"] == [1, 1, 1]
    assert p["meta"]["coeficientes"]["orden_arima_solicitado"] == [1, 1, 1]
