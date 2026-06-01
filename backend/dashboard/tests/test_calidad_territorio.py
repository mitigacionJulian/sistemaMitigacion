"""F2 / G03 — calidad territorial (PostGIS)."""
import pytest
from django.db import connection


def _uses_postgis() -> bool:
    return "postgis" in connection.settings_dict.get("ENGINE", "")


@pytest.mark.django_db
def test_calidad_territorio_api_structure(client):
    if not _uses_postgis():
        pytest.skip("SQLite test DB; usar PostGIS para G03")
    with connection.cursor() as c:
        c.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'incidente' AND column_name = 'comuna_id_espacial'
            )
            """
        )
        if not c.fetchone()[0]:
            pytest.skip("F2 SQL no aplicado")

    r = client.get(
        "/api/dashboard/calidad-territorio/",
        {"desde": "2021-01-01", "hasta": "2021-09-30", "limite_ejemplos": "3"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "meta" in data
    meta = data["meta"]
    assert meta.get("indicador") == "G03"
    assert "pct_discrepancia_comuna" in meta
    assert "pct_discrepancia_barrio" in meta
    assert "ejemplos_discrepancia" in data
