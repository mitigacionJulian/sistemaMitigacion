"""P05 — índice de prioridad territorial."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.kpis import FiltrosKpi
from dashboard.prioridad_territorial import (
    MIN_INCIDENTES_BARRIO,
    MIN_INCIDENTES_COMUNA,
    PESOS_COMPONENTES,
    build_prioridad_territorial_payload,
    min_incidentes_territorio,
)


def test_delta_promedios_territorio():
    from dashboard.prioridad_territorial import _delta_promedios_territorio

    assert _delta_promedios_territorio([1, 1, 1, 1, 1, 1]) == 0.0
    # 6 meses: últimos 3 altos vs primeros 3 bajos
    d = _delta_promedios_territorio([10, 10, 10, 20, 20, 20])
    assert d is not None and d > 0


def test_delta_15_meses_solo_ultimos_12():
    """Con 15 meses, N=6: ignora los 3 primeros; compara últimos 6 vs 6 previos."""
    from dashboard.prioridad_territorial import _delta_promedios_territorio

    vals = [5] * 3 + [10] * 6 + [20] * 6
    assert _delta_promedios_territorio(vals) == 10.0


def test_delta_9_meses_ventana_mitad():
    from dashboard.prioridad_territorial import _delta_promedios_territorio

    # n=9 → w=4; últimos 4 vs 4 previos; atenuación × 9/12
    vals = [1, 10, 10, 10, 10, 20, 20, 20, 20]
    d = _delta_promedios_territorio(vals)
    assert d is not None
    assert abs(d - 10.0 * 9 / 12) < 1e-9


def test_indice_compuesto_orden():
    totales = {
        1: {"incidentes": 100, "victimas": 120, "fatales": 10, "nombre": "A"},
        2: {"incidentes": 50, "victimas": 60, "fatales": 2, "nombre": "B"},
    }
    mensual = {
        1: {f"2021-{m:02d}": 10 + m for m in range(1, 13)},
        2: {f"2021-{m:02d}": 5 for m in range(1, 13)},
    }

    with patch(
        "dashboard.prioridad_territorial._query_totales_territorio",
        return_value=totales,
    ):
        with patch(
            "dashboard.prioridad_territorial._query_mensual_por_territorio",
            return_value=mensual,
        ):
            with patch(
                "dashboard.prioridad_territorial._query_area_km2",
                return_value={1: 10.0, 2: 10.0},
            ):
                p = build_prioridad_territorial_payload(
                    date(2021, 1, 1),
                    date(2021, 12, 31),
                    FiltrosKpi(),
                    nivel="comuna",
                    limite=10,
                )

    assert not p["meta"]["sin_datos"]
    assert p["meta"]["pesos"] == PESOS_COMPONENTES
    assert "densidad_km2" in p["meta"]["pesos"]
    assert len(p["ranking"]) == 2
    assert p["ranking"][0]["comuna_id"] == 1
    assert p["ranking"][0]["indice_prioridad"] >= p["ranking"][1]["indice_prioridad"]
    assert p["ranking"][0]["nivel_prioridad"] in ("alto", "medio", "bajo")
    assert p["ranking"][0]["rank_frecuencia"] == 1
    assert len(p["ranking_por_frecuencia"]) == 2
    assert p["ranking_por_frecuencia"][0]["incidentes_periodo"] >= p["ranking_por_frecuencia"][1]["incidentes_periodo"]
    assert "densidad_incidentes_km2" in p["ranking"][0]
    assert "sensibilidad_pesos" in p["meta"]


def test_min_incidentes_por_nivel():
    assert min_incidentes_territorio("comuna") == MIN_INCIDENTES_COMUNA
    assert min_incidentes_territorio("barrio") == MIN_INCIDENTES_BARRIO
    assert MIN_INCIDENTES_BARRIO > MIN_INCIDENTES_COMUNA


def test_alerta_cuando_lider_no_es_frecuencia():
    totales = {
        1: {"incidentes": 100, "victimas": 120, "fatales": 10, "nombre": "Grande"},
        2: {"incidentes": 10, "victimas": 12, "fatales": 1, "nombre": "Pequeño"},
    }
    mensual = {
        1: {f"2021-{m:02d}": 20 + m for m in range(1, 13)},
        2: {f"2021-{m:02d}": (1 if m < 10 else 15) for m in range(1, 13)},
    }

    with patch("dashboard.prioridad_territorial._query_totales_territorio", return_value=totales):
        with patch("dashboard.prioridad_territorial._query_mensual_por_territorio", return_value=mensual):
            with patch("dashboard.prioridad_territorial._query_area_km2", return_value={1: 5.0, 2: 1.0}):
                p = build_prioridad_territorial_payload(
                    date(2021, 1, 1),
                    date(2021, 12, 31),
                    FiltrosKpi(),
                    nivel="comuna",
                    limite=10,
                )

    top = p["ranking"][0]
    if top["comuna_id"] == 2:
        assert p["meta"].get("alerta_liderazgo") is not None
        assert top["rank_frecuencia"] > 1


@pytest.mark.django_db
def test_api_prioridad_territorial_ok(analista_client):
    fake = {
        "meta": {"nivel": "comuna", "sin_datos": False, "pesos": PESOS_COMPONENTES},
        "ranking": [{"rank": 1, "comuna_id": 1, "indice_prioridad": 70.0, "rank_frecuencia": 1}],
        "ranking_por_frecuencia": [{"rank": 1, "comuna_id": 1, "indice_prioridad": 70.0}],
    }
    with patch("dashboard.views.build_prioridad_territorial_payload", return_value=fake):
        r = analista_client.get(
            reverse("dashboard-prioridad-territorial"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "nivel": "comuna"},
        )
        assert r.status_code == 200
        assert r.data["ranking"][0]["rank"] == 1
        assert "ranking_por_frecuencia" in r.data
