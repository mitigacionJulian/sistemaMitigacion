"""P07 — proporción mensual de víctimas fatales."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.kpis import FiltrosKpi
from dashboard.proporcion_fatales_mensual import (
    MIN_VICTIMAS_MES,
    _pct_fatales,
    build_proporcion_fatales_payload,
)


def test_pct_fatales_umbral():
    assert _pct_fatales(MIN_VICTIMAS_MES - 1, 1) is None
    assert _pct_fatales(MIN_VICTIMAS_MES, 2) == pytest.approx(20.0)


def test_proporcion_ols_con_datos():
    raw = {
        "2021-01": {"victimas": 100, "fatales": 10},
        "2021-02": {"victimas": 120, "fatales": 12},
        "2021-03": {"victimas": 110, "fatales": 11},
    }
    with patch(
        "dashboard.proporcion_fatales_mensual._query_victimas_fatales_mes",
        return_value=raw,
    ):
        p = build_proporcion_fatales_payload(
            date(2021, 1, 1),
            date(2021, 3, 31),
            FiltrosKpi(),
            horizonte_meses=2,
            modelo="ols",
        )

    assert not p["meta"]["sin_modelo"]
    assert p["meta"].get("interpretacion_bondad")
    assert p["meta"].get("bondad_nivel")
    assert len(p["serie_historica"]) == 3
    assert p["serie_historica"][0]["pct_fatales"] == 10.0
    assert len(p["proyeccion"]) == 2
    assert p["proyeccion"][0]["pct_fatales_proyectado"] >= 5.0


def test_proporcion_media_movil():
    raw = {
        "2021-01": {"victimas": 100, "fatales": 10},
        "2021-02": {"victimas": 120, "fatales": 18},
        "2021-03": {"victimas": 110, "fatales": 11},
    }
    with patch(
        "dashboard.proporcion_fatales_mensual._query_victimas_fatales_mes",
        return_value=raw,
    ):
        p = build_proporcion_fatales_payload(
            date(2021, 1, 1),
            date(2021, 3, 31),
            FiltrosKpi(),
            horizonte_meses=2,
            modelo="media_movil",
            ventana_ma=3,
        )

    assert p["meta"]["modelo"] == "media_movil"
    assert p["meta"]["ventana_meses"] == 3
    assert not p["meta"]["sin_modelo"]
    assert p["meta"]["coeficientes"]["ultima_media_movil"] == pytest.approx(11.6667, rel=1e-3)
    assert p["proyeccion"][0]["pct_fatales_proyectado"] == pytest.approx(11.67, abs=0.02)
    assert p["proyeccion"][1]["pct_fatales_proyectado"] == pytest.approx(11.67, abs=0.02)


def test_proyeccion_estable_no_cae_a_cero():
    raw = {
        f"2020-{m:02d}": {"victimas": 200, "fatales": 20}
        for m in range(1, 13)
    }
    with patch(
        "dashboard.proporcion_fatales_mensual._query_victimas_fatales_mes",
        return_value=raw,
    ):
        p = build_proporcion_fatales_payload(
            date(2020, 1, 1),
            date(2020, 12, 31),
            FiltrosKpi(),
            horizonte_meses=3,
            modelo="ols",
            excluir_covid=False,
        )
    assert not p["meta"]["sin_modelo"]
    assert all(x["pct_fatales_proyectado"] >= 8.0 for x in p["proyeccion"])


@pytest.mark.django_db
def test_api_proporcion_fatales_ok():
    fake = {
        "meta": {"modelo": "ols", "sin_modelo": False},
        "serie_historica": [{"mes_clave": "2021-01", "pct_fatales": 5.0}],
        "proyeccion": [],
    }
    with patch("dashboard.views.build_proporcion_fatales_payload", return_value=fake):
        c = APIClient()
        r = c.get(
            reverse("dashboard-proporcion-fatales-mensual"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "modelo": "ols"},
        )
        assert r.status_code == 200
        assert r.data["meta"]["modelo"] == "ols"
