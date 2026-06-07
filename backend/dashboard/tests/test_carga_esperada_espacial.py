"""Fase C — carga esperada espacial P09–P11."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.kpis import FiltrosKpi
from dashboard.carga_esperada_espacial import build_carga_espacial_payload

FAKE_BLOQUE = {
    "meta": {"sin_modelo": False, "coeficientes": {"r2": 0.4}, "bondad_nivel": "moderado"},
    "serie_historica": [{"mes_etiqueta": "Ene 2021", "observados": 10, "ajuste_modelo": 9}],
    "proyeccion": [{"mes_etiqueta": "Feb 2021", "proyectados": 12, "ajuste_modelo": 12}],
}


def test_series_territorial_top():
    totales = {1: {"incidentes": 50, "nombre": "A"}, 2: {"incidentes": 30, "nombre": "B"}}
    with patch(
        "dashboard.carga_esperada_espacial._query_totales_territorio",
        return_value=totales,
    ):
        with patch(
            "dashboard.carga_esperada_espacial._bloque_territorio",
            return_value={
                "serie_historica": FAKE_BLOQUE["serie_historica"],
                "proyeccion": FAKE_BLOQUE["proyeccion"],
                "carga_proyectada_horizonte": 12.0,
                "meta": {"sin_modelo": False, "r2": 0.4},
            },
        ):
            p = build_carga_espacial_payload(
                date(2021, 1, 1),
                date(2021, 3, 31),
                FiltrosKpi(),
                tipo="series_territorial",
                nivel="comuna",
                limite=5,
            )

    assert p["meta"]["fase"] == "C"
    assert len(p["series"]) == 2
    assert p["series"][0]["rank"] == 1


@pytest.mark.django_db
def test_api_carga_espacial_ok(analista_client):
    fake = {
        "meta": {"fase": "C", "tipo": "ranking_via", "sin_datos": False},
        "series": [],
        "ranking": [{"rank": 1, "via_id": 1, "carga_proyectada_horizonte": 20.0}],
    }
    with patch("dashboard.views.build_carga_espacial_payload", return_value=fake):
        r = analista_client.get(
            reverse("dashboard-carga-esperada-espacial"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "tipo": "ranking_via"},
        )
        assert r.status_code == 200
        assert r.data["meta"]["tipo"] == "ranking_via"
