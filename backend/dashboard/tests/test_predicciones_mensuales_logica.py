"""Lógica de proyección mensual sin depender de datos reales en BD."""
from datetime import date
from unittest.mock import patch

from dashboard.kpis import FiltrosKpi
from dashboard.predicciones_mensuales import (
    _query_mensual_valores,
    build_predicciones_mensuales_payload,
)


def test_un_solo_mes_sin_modelo():
    act = {"2021-01": 5}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(date(2021, 1, 1), date(2021, 1, 31), FiltrosKpi(), 3)
    assert p["meta"]["sin_modelo"] is True
    assert p["proyeccion"] == []
    assert len(p["serie_historica"]) == 1
    assert p["serie_historica"][0]["incidentes_ajuste_lineal"] is None


def test_recta_conocida_y_proyeccion():
    act = {"2021-01": 10, "2021-02": 12, "2021-03": 14}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(date(2021, 1, 1), date(2021, 3, 31), FiltrosKpi(), 2)
    assert p["meta"]["sin_modelo"] is False
    assert p["meta"].get("interpretacion_bondad")
    assert p["meta"].get("bondad_nivel") in ("bueno", "moderado", "bajo")
    assert abs(p["meta"]["coeficientes"]["pendiente_b_mes"] - 2.0) < 1e-5
    assert abs(p["meta"]["coeficientes"]["intercepto_a"] - 10.0) < 1e-5
    assert p["meta"]["coeficientes"]["r2"] == 1.0
    assert len(p["proyeccion"]) == 2
    assert p["proyeccion"][0]["mes_clave"] == "2021-04"
    assert abs(p["proyeccion"][0]["incidentes_proyectados"] - 16.0) < 0.01
    assert p["proyeccion"][1]["mes_clave"] == "2021-05"
    assert abs(p["proyeccion"][1]["incidentes_proyectados"] - 18.0) < 0.01


def test_proyeccion_recortada_a_cero():
    act = {"2021-01": 10, "2021-02": 5}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(date(2021, 1, 1), date(2021, 2, 28), FiltrosKpi(), 6)
    assert p["meta"]["sin_modelo"] is False
    for row in p["proyeccion"]:
        assert row["incidentes_proyectados"] >= 0


def test_estacional_tres_meses():
    act = {"2021-01": 10, "2021-02": 12, "2021-03": 14}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2021, 1, 1),
            date(2021, 3, 31),
            FiltrosKpi(),
            1,
            modelo="estacional",
            variable="incidentes",
        )
    assert p["meta"]["modelo"] == "estacional"
    assert p["meta"]["sin_modelo"] is False
    assert len(p["proyeccion"]) == 1
    assert p["serie_historica"][0]["observados"] == 10


def test_victimas_variable():
    act = {"2021-01": 5, "2021-02": 7, "2021-03": 9}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2021, 1, 1),
            date(2021, 3, 31),
            FiltrosKpi(),
            2,
            modelo="ols",
            variable="victimas",
        )
    assert p["meta"]["variable"] == "victimas"
    assert p["serie_historica"][0]["observados"] == 5
    assert "incidentes_observados" not in p["serie_historica"][0]


def test_poisson_dos_meses_minimo():
    act = {"2021-01": 4, "2021-02": 6, "2021-03": 8}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2021, 1, 1),
            date(2021, 3, 31),
            FiltrosKpi(),
            1,
            modelo="poisson",
        )
    assert p["meta"]["modelo"] == "poisson"
    assert p["meta"]["sin_modelo"] is False


def test_poisson_no_explota_con_serie_larga():
    act = {}
    for y in (2016, 2017):
        for m in range(1, 13):
            act[f"{y}-{m:02d}"] = 1800 + m * 25
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2016, 1, 1),
            date(2017, 12, 31),
            FiltrosKpi(),
            6,
            modelo="poisson",
        )
    assert p["meta"]["sin_modelo"] is False
    for row in p["serie_historica"]:
        if row["ajuste_modelo"] is not None:
            assert row["ajuste_modelo"] < 10_000
    for row in p["proyeccion"]:
        assert row["proyectados"] < 10_000
    b1 = abs(p["meta"]["coeficientes"].get("pendiente_t_log", 0))
    assert b1 < 2.0 or p["meta"]["coeficientes"].get("fallback_estacional")


def test_excluir_covid_deja_hueco_sin_ajuste():
    act = {"2020-02": 100, "2020-03": 10, "2020-04": 5, "2020-07": 90, "2020-08": 95}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2020, 1, 1),
            date(2020, 8, 31),
            FiltrosKpi(),
            1,
            modelo="ols",
            excluir_covid=True,
        )
    by_mes = {r["mes_clave"]: r["ajuste_modelo"] for r in p["serie_historica"]}
    assert by_mes["2020-03"] is None
    assert by_mes["2020-04"] is None
    assert by_mes["2020-02"] is not None


def test_media_movil_tres_meses():
    act = {"2021-01": 10, "2021-02": 20, "2021-03": 30}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2021, 1, 1),
            date(2021, 3, 31),
            FiltrosKpi(),
            2,
            modelo="media_movil",
            ventana_ma=3,
        )
    assert p["meta"]["modelo"] == "media_movil"
    assert p["meta"]["ventana_meses"] == 3
    assert p["meta"]["sin_modelo"] is False
    assert p["meta"]["coeficientes"]["ultima_media_movil"] == 20.0
    hist = [r["ajuste_modelo"] for r in p["serie_historica"]]
    assert hist == [10.0, 15.0, 20.0]
    assert len(p["proyeccion"]) == 2
    assert p["proyeccion"][0]["incidentes_proyectados"] == 20.0
    assert p["proyeccion"][1]["incidentes_proyectados"] == 20.0


def test_media_movil_insuficiente_meses():
    act = {"2021-01": 10, "2021-02": 12}
    with patch("dashboard.predicciones_mensuales._query_mensual_valores", return_value=act):
        p = build_predicciones_mensuales_payload(
            date(2021, 1, 1),
            date(2021, 2, 28),
            FiltrosKpi(),
            1,
            modelo="media_movil",
            ventana_ma=3,
        )
    assert p["meta"]["sin_modelo"] is True
    assert p["proyeccion"] == []


def test_desglose_clase():
    def fake_query(inicio, fin, filtros, variable):
        if filtros.clase_incidente_id == 1:
            return {"2021-01": 10, "2021-02": 12}
        if filtros.clase_incidente_id == 2:
            return {"2021-01": 3, "2021-02": 4}
        return {}

    with patch("dashboard.predicciones_mensuales._query_mensual_valores", side_effect=fake_query):
        with patch(
            "dashboard.predicciones_mensuales._query_clases_con_datos",
            return_value=[(1, "Choque", 22), (2, "Atropello", 7)],
        ):
            p = build_predicciones_mensuales_payload(
                date(2021, 1, 1),
                date(2021, 2, 28),
                FiltrosKpi(),
                1,
                modelo="ols",
                desglose_clase=True,
            )
    assert p["meta"]["desglose_clase"] is True
    assert len(p["series_por_clase"]) == 2
    assert p["serie_historica"] == []
