"""Tests lógica reporte mapa."""
from datetime import date
from unittest.mock import patch

import pytest

from dashboard.kpis import FiltrosKpi
from reports.mapa import _to_top_territorios, build_mapa_report_body
from reports.params import MapaQuery, resolve_mapa_nivel


def test_resolve_mapa_nivel_comuna_con_filtro_comuna():
    assert resolve_mapa_nivel("territorio", FiltrosKpi(comuna_id=5)) == "comuna"


def test_resolve_mapa_nivel_barrio_con_filtro_barrio():
    assert resolve_mapa_nivel("territorio", FiltrosKpi(comuna_id=5, barrio_id=10)) == "barrio"


def test_resolve_mapa_nivel_detalle_comuna():
    assert resolve_mapa_nivel("detalle", FiltrosKpi(comuna_id=5)) == "barrio"


def test_to_top_territorios_solo_con_incidentes():
    choropleth = {
        "features": [
            {"properties": {"nombre": "A", "incidentes": 0, "densidad_km2": 0}},
            {"properties": {"nombre": "B", "incidentes": 5, "densidad_km2": 2.5}},
            {"properties": {"nombre": "C", "incidentes": 10, "densidad_km2": 1.0}},
        ]
    }
    top = _to_top_territorios(choropleth, limite=5)
    assert len(top) == 2
    assert top[0]["nombre"] == "B"
    assert top[0]["rank"] == 1


@pytest.mark.django_db
def test_build_mapa_territorio_mock():
    fake_choropleth = {
        "meta": {
            "nivel": "comuna",
            "metrica": "densidad",
            "total_incidentes": 100,
            "poligonos_devueltos": 21,
            "poligonos_con_incidentes": 3,
            "densidad_ciudad_km2": 5.0,
            "valor_min": 0,
            "valor_max": 12.0,
            "sin_datos": False,
        },
        "features": [
            {
                "properties": {
                    "id": 3,
                    "nombre": "La Candelaria",
                    "incidentes": 40,
                    "densidad_km2": 8.0,
                    "ratio_vs_ciudad": 1.6,
                    "area_km2": 5.0,
                }
            }
        ],
    }
    mapa_query = MapaQuery(
        view_mode="territorio",
        choropleth_metric="densidad",
        nivel="comuna",
        map_limite=10_000,
        metodo_hotspot="cuadricula",
        tamano_celda_m=300,
        geojson=None,
    )
    with patch("reports.mapa.build_choropleth_territorial_payload", return_value=fake_choropleth):
        with patch("reports.mapa.build_calidad_territorio_payload", return_value={"meta": {"con_ubicacion": 50}}):
            body = build_mapa_report_body(
                date(2017, 1, 1),
                date(2017, 3, 31),
                FiltrosKpi(comuna_id=3),
                mapa_query,
            )
    assert body["modo_vista"] == "territorio"
    assert body["territorio_resumen"]["nombre"] == "La Candelaria"
    assert len(body["top_territorios"]) == 1
    assert body["interpretacion"]
