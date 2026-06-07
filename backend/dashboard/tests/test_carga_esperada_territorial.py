"""P08 — categoría de carga esperada territorial."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.kpis import FiltrosKpi
from dashboard.carga_esperada_territorial import build_carga_esperada_payload


def test_carga_terciles():
    totales = {
        1: {"incidentes": 100, "nombre": "A"},
        2: {"incidentes": 50, "nombre": "B"},
        3: {"incidentes": 30, "nombre": "C"},
    }

    def fake_carga(*_a, **_k):
        tid = _a[4]
        return {1: 30.0, 2: 15.0, 3: 5.0}[tid]

    with patch(
        "dashboard.carga_esperada_territorial._query_totales_territorio",
        return_value=totales,
    ):
        with patch(
            "dashboard.carga_esperada_territorial._carga_proyectada_territorio",
            side_effect=fake_carga,
        ):
            p = build_carga_esperada_payload(
                date(2021, 1, 1),
                date(2021, 3, 31),
                FiltrosKpi(),
                nivel="comuna",
                limite=10,
            )

    assert not p["meta"]["sin_datos"]
    assert p["meta"].get("interpretacion")
    assert p["meta"].get("que_mide")
    assert len(p["ranking"]) == 3
    assert p["ranking"][0]["categoria_esperada"] == "alto"
    assert p["ranking"][0]["comuna_id"] == 1


@pytest.mark.django_db
def test_api_carga_esperada_ok(analista_client):
    fake = {
        "meta": {"nivel": "comuna", "sin_datos": False, "horizonte_meses": 3},
        "ranking": [
            {
                "rank": 1,
                "comuna_id": 1,
                "categoria_esperada": "alto",
                "carga_proyectada_horizonte": 42.0,
            }
        ],
    }
    with patch("dashboard.views.build_carga_esperada_payload", return_value=fake):
        r = analista_client.get(
            reverse("dashboard-carga-esperada-territorial"),
            {
                "desde": "2021-01-01",
                "hasta": "2021-03-31",
                "nivel": "comuna",
                "modelo": "estacional",
            },
        )
        assert r.status_code == 200
        assert r.data["ranking"][0]["categoria_esperada"] == "alto"
