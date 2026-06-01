"""
Backfill comuna_id_espacial / barrio_id_espacial (F2.3).

Usa JOIN con indice GIST (&&) + ST_Contains; mucho mas rapido que subconsultas por fila.

Uso:
    python manage.py actualizar_territorio_espacial
"""
import time

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from dashboard.calidad_territorio import territorio_espacial_status

UPDATE_COMUNA_SQL = """
UPDATE incidente i
SET comuna_id_espacial = pick.comuna_id
FROM (
    SELECT DISTINCT ON (i.id)
        i.id,
        c.id AS comuna_id
    FROM incidente i
    INNER JOIN comuna c
        ON c.geom IS NOT NULL
       AND c.geom && i.ubicacion
       AND ST_Contains(c.geom, i.ubicacion)
    WHERE i.ubicacion IS NOT NULL
      {extra_where}
    ORDER BY i.id, ST_Area(c.geom::geography) ASC
) pick
WHERE i.id = pick.id
"""

UPDATE_BARRIO_SQL = """
UPDATE incidente i
SET barrio_id_espacial = pick.barrio_id
FROM (
    SELECT DISTINCT ON (i.id)
        i.id,
        b.id AS barrio_id
    FROM incidente i
    INNER JOIN barrio b
        ON b.geom IS NOT NULL
       AND b.geom && i.ubicacion
       AND ST_Contains(b.geom, i.ubicacion)
    WHERE i.ubicacion IS NOT NULL
      {extra_where}
    ORDER BY i.id, ST_Area(b.geom::geography) ASC
) pick
WHERE i.id = pick.id
"""


class Command(BaseCommand):
    help = "Rellena comuna_id_espacial y barrio_id_espacial desde poligonos (ST_Contains)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recalcular todos los incidentes con ubicacion",
        )

    def handle(self, *args, **options):
        st = territorio_espacial_status()
        if not st.get("ready"):
            self.stderr.write(self.style.ERROR(st.get("message", "F2 no aplicado")))
            return

        force = bool(options.get("force"))
        extra = "" if force else "AND i.comuna_id_espacial IS NULL"
        extra_b = "" if force else "AND i.barrio_id_espacial IS NULL"

        self.stdout.write("Actualizando comuna_id_espacial (JOIN GIST)...")
        t0 = time.perf_counter()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE incidente DISABLE TRIGGER trg_incidente_sync_territorio_espacial"
                )
                cursor.execute(UPDATE_COMUNA_SQL.format(extra_where=extra))
                n_com = cursor.rowcount
                self.stdout.write(f"  comuna: {n_com} filas en {time.perf_counter()-t0:.1f}s")

                t1 = time.perf_counter()
                self.stdout.write("Actualizando barrio_id_espacial (JOIN GIST)...")
                cursor.execute(UPDATE_BARRIO_SQL.format(extra_where=extra_b))
                n_bar = cursor.rowcount
                self.stdout.write(f"  barrio: {n_bar} filas en {time.perf_counter()-t1:.1f}s")
                cursor.execute(
                    "ALTER TABLE incidente ENABLE TRIGGER trg_incidente_sync_territorio_espacial"
                )

        st2 = territorio_espacial_status()
        con_ub = st2["con_ubicacion"]
        pct_c = round(100 * st2["con_comuna_espacial"] / con_ub, 1) if con_ub else 0
        pct_b = round(100 * st2["con_barrio_espacial"] / con_ub, 1) if con_ub else 0
        self.stdout.write(
            self.style.SUCCESS(
                f"F2 backfill OK | "
                f"comuna espacial {st2['con_comuna_espacial']}/{con_ub} ({pct_c}%) | "
                f"barrio espacial {st2['con_barrio_espacial']}/{con_ub} ({pct_b}%) | "
                f"discrepancias {st2['discrepancias']} ({st2.get('pct_discrepancia')}%)"
            )
        )
