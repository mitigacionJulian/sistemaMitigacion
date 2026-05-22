from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
@patch("django.db.connection")
def test_dashboard_rango_fechas_hay_datos(mock_connection):
    cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchone.return_value = (date(2014, 1, 1), date(2021, 9, 30))

    c = APIClient()
    r = c.get(reverse("dashboard-rango-fechas"))
    assert r.status_code == 200
    assert r.data["hay_datos"] is True
    assert r.data["ultimo_anio_con_datos"] == 2021
    assert r.data["default_hasta"] == "2021-09-30"
    assert r.data["default_desde"] == "2021-01-01"
