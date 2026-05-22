from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dashboard_incidentes_mapa_ok():
    fake = {
        "meta": {
            "fecha_inicio": "2021-01-01",
            "fecha_fin": "2021-03-31",
            "limite": 3000,
            "total_con_coordenadas_en_rango": 1,
            "puntos_devueltos": 1,
            "muestra_truncada": False,
            "descripcion": "",
            "filtros": {"comuna_id": None, "barrio_id": None, "clase_incidente_id": None},
        },
        "puntos": [
            {
                "id": 1,
                "radicado": "A",
                "fecha_incidente": "2021-02-01",
                "latitud": 6.25,
                "longitud": -75.56,
                "clase_incidente": "Choque",
            },
        ],
    }
    with patch("dashboard.views.build_incidentes_mapa_payload", return_value=fake):
        c = APIClient()
        r = c.get(
            reverse("dashboard-incidentes-mapa"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "limite": "100"},
        )
        assert r.status_code == 200
        assert len(r.data["puntos"]) == 1


@pytest.mark.django_db
def test_dashboard_incidentes_mapa_limite_cero_pasa_a_build():
    fake = {
        "meta": {
            "fecha_inicio": "2021-01-01",
            "fecha_fin": "2021-03-31",
            "limite": 500,
            "sin_limite_solicitado": True,
            "tope_absoluto_sin_limite": 100_000,
            "recorte_por_tope_absoluto": False,
            "total_con_coordenadas_en_rango": 500,
            "puntos_devueltos": 500,
            "muestra_truncada": False,
            "descripcion": "",
            "filtros": {"comuna_id": None, "barrio_id": None, "clase_incidente_id": None},
        },
        "puntos": [],
    }
    with patch("dashboard.views.build_incidentes_mapa_payload", return_value=fake) as m:
        c = APIClient()
        r = c.get(
            reverse("dashboard-incidentes-mapa"),
            {"desde": "2021-01-01", "hasta": "2021-03-31", "limite": "0"},
        )
        assert r.status_code == 200
        assert m.call_args is not None
        assert m.call_args[0][3] == 0


@pytest.mark.django_db
def test_dashboard_incidentes_mapa_rango_invalido():
    c = APIClient()
    r = c.get(
        reverse("dashboard-incidentes-mapa"),
        {"desde": "2021-05-01", "hasta": "2021-01-01"},
    )
    assert r.status_code == 400
