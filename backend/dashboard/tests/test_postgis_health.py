"""F0.5 — Salud PostGIS (solo si el motor de pruebas es PostGIS; pytest usa SQLite por defecto)."""
import pytest
from django.db import connection


def _uses_postgis() -> bool:
    return "postgis" in connection.settings_dict.get("ENGINE", "")


@pytest.mark.django_db
def test_postgis_version_when_postgis_backend():
    if not _uses_postgis():
        pytest.skip("settings_test usa SQLite; PostGIS se valida con manage.py check_postgis")
    with connection.cursor() as cursor:
        cursor.execute("SELECT postgis_full_version();")
        row = cursor.fetchone()
    assert row and row[0]
