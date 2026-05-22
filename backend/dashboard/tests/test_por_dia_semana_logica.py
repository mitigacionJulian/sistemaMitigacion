"""Lógica de participación semanal y semáforo (sin depender de datos reales en BD)."""

from datetime import date
from unittest.mock import patch

import pytest

from dashboard.kpis import FiltrosKpi
from dashboard.por_dia_semana import build_dia_semana_payload


@pytest.mark.django_db
def test_participacion_incidentes_suma_100():
    act = {d: (10, 0) for d in range(7)}
    with patch("dashboard.por_dia_semana._query_por_dia", return_value=act):
        p = build_dia_semana_payload(date(2021, 1, 1), date(2021, 1, 31), FiltrosKpi())
    total = sum(row["participacion_incidentes_pct"] for row in p["serie"])
    assert abs(total - 100.0) < 0.1
    for row in p["serie"]:
        assert row["carga_dia_nivel"] == "bajo"
        assert row["riesgo_nivel"] == row["carga_dia_nivel"]
        assert row["riesgo_score"] == row["participacion_incidentes_pct"]


@pytest.mark.django_db
def test_dia_pico_concentracion_alta():
    act = {d: (5 if d != 4 else 40, 0) for d in range(7)}
    with patch("dashboard.por_dia_semana._query_por_dia", return_value=act):
        p = build_dia_semana_payload(date(2021, 1, 1), date(2021, 1, 31), FiltrosKpi())
    jueves = next(r for r in p["serie"] if r["dia_semana"] == 4)
    assert jueves["incidentes_periodo_actual"] == 40
    assert jueves["carga_dia_nivel"] == "alto"
    assert jueves["ratio_vs_reparto_uniforme"] >= 1.45
