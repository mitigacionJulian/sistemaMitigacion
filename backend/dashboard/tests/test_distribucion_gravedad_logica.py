"""Lógica de distribución por gravedad (serie sin categorías vacías)."""
from datetime import date
from unittest.mock import patch

from dashboard.distribucion_gravedad import build_distribucion_gravedad_payload
from dashboard.kpis import FiltrosKpi


@patch("dashboard.distribucion_gravedad._query_distribucion")
def test_serie_omite_categorias_sin_victimas(mock_query):
    mock_query.side_effect = [
        {"FATAL": ("Fatal", 12), "HERIDO": ("Heridos", 2100)},
        {"FATAL": ("Fatal", 10), "HERIDO": ("Heridos", 1700)},
    ]
    payload = build_distribucion_gravedad_payload(
        date(2021, 1, 1),
        date(2021, 2, 28),
        FiltrosKpi(),
    )
    serie = payload["serie"]
    assert len(serie) == 2
    codigos = {r["codigo"] for r in serie}
    assert codigos == {"FATAL", "HERIDO"}
    for row in serie:
        assert row["victimas_periodo_actual"] > 0 or row["victimas_periodo_anterior"] > 0


@patch("dashboard.distribucion_gravedad._query_distribucion")
def test_serie_no_duplica_otro_vacio(mock_query):
    mock_query.side_effect = [
        {"FATAL": ("Fatal", 5), "HERIDO": ("Heridos", 100)},
        {"FATAL": ("Fatal", 4), "HERIDO": ("Heridos", 80)},
    ]
    payload = build_distribucion_gravedad_payload(
        date(2021, 1, 1),
        date(2021, 2, 28),
        FiltrosKpi(),
    )
    labels = [r["gravedad"] for r in payload["serie"]]
    assert "Otro / sin clasificar" not in labels
    assert labels == ["Fatal", "Heridos"]
