"""P05 — índice de prioridad territorial."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.kpis import FiltrosKpi
from dashboard.prioridad_territorial import (
    PESOS_COMPONENTES,
    build_prioridad_territorial_payload,
)


def test_indice_compuesto_orden():
    totales = {
        1: {"incidentes": 100, "victimas": 120, "fatales": 10, "nombre": "A"},
        2: {"incidentes": 50, "victimas": 60, "fatales": 2, "nombre": "B"},
    }
    mensual = {
        1: {"2021-01": 10, "2021-02": 12, "2021-03": 14},
        2: {"2021-01": 5, "2021-02": 5, "2021-03": 5},
    }

    with patch(
        "dashboard.prioridad_territorial._query_totales_territorio",
        return_value=totales,
    ):
        with patch(
            "dashboard.prioridad_territorial._query_mensual_por_territorio",
            return_value=mensual,
        ):
            p = build_prioridad_territorial_payload(
                date(2021, 1, 1),
                date(2021, 3, 31),
                FiltrosKpi(),
                nivel="comuna",
                limite=10,
            )

    assert not p["meta"]["sin_datos"]
    assert p["meta"]["pesos"] == PESOS_COMPONENTES
    assert len(p["ranking"]) == 2
    assert p["ranking"][0]["comuna_id"] == 1
    assert p["ranking"][0]["indice_prioridad"] >= p["ranking"][1]["indice_prioridad"]
    assert p["ranking"][0]["nivel_prioridad"] in ("alto", "medio", "bajo")


@pytest.mark.django_db
def test_api_prioridad_territorial_ok(analista_client):
    fake = {
        "meta": {"nivel": "comuna", "sin_datos": False, "pesos": PESOS_COMPONENTES},
        "ranking": [{"rank": 1, "comuna_id": 1, "indice_prioridad": 70.0}],
    }
    with patch("dashboard.views.build_prioridad_territorial_payload", return_value=fake):
        r = analista_client.get(
            reverse("dashboard-prioridad-territorial"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "nivel": "comuna"},
        )
        assert r.status_code == 200
        assert r.data["ranking"][0]["rank"] == 1
