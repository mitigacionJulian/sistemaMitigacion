"""
Comprueba que PostGIS esté activo en la base configurada en .env

Uso:
    python manage.py check_postgis
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verifica extensión PostGIS y operaciones básicas (Point SRID 4326)."

    def handle(self, *args, **options):
        engine = connection.settings_dict.get("ENGINE", "")
        if "postgis" not in engine:
            self.stderr.write(
                self.style.ERROR(
                    f"El motor actual no es PostGIS: {engine}. "
                    "Revise config/settings.py y DJANGO_USE_POSTGIS en .env."
                )
            )
            return

        with connection.cursor() as cursor:
            cursor.execute("SELECT postgis_full_version();")
            version = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"PostGIS: {version}"))

            cursor.execute(
                """
                SELECT ST_AsText(
                    ST_SetSRID(ST_MakePoint(-75.5636, 6.2518), 4326)
                );
                """
            )
            wkt = cursor.fetchone()[0]
            self.stdout.write(f"Punto de prueba (WKT): {wkt}")

        self.stdout.write(self.style.SUCCESS("check_postgis: OK"))
