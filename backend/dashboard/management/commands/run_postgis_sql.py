"""
Ejecuta scripts SQL de backend/sql/postgis/ con psql (varias sentencias y PL/pgSQL).

Uso:
    python manage.py run_postgis_sql
    python manage.py run_postgis_sql --only 002_incidente_ubicacion.sql
"""
import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


def _sql_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "sql" / "postgis"


class Command(BaseCommand):
    help = "Aplica scripts SQL PostGIS desde backend/sql/postgis/ (requiere psql en PATH)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only",
            type=str,
            help="Nombre de archivo, ej. 002_incidente_ubicacion.sql",
        )

    def handle(self, *args, **options):
        sql_dir = _sql_dir()
        if not sql_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"No existe {sql_dir}"))
            return

        if not shutil.which("psql"):
            self.stderr.write(
                self.style.ERROR(
                    "psql no está en PATH. Ejecute los .sql en pgAdmin o agregue "
                    "PostgreSQL\\17\\bin al PATH."
                )
            )
            return

        files = sorted(sql_dir.glob("*.sql"))
        only = options.get("only")
        if only:
            files = [sql_dir / only]
            if not files[0].is_file():
                self.stderr.write(self.style.ERROR(f"No encontrado: {only}"))
                return

        db = settings.DATABASES["default"]
        env = {**os.environ, "PGPASSWORD": db.get("PASSWORD") or ""}
        base = [
            "psql",
            "-h",
            db.get("HOST") or "localhost",
            "-p",
            str(db.get("PORT") or 5432),
            "-U",
            db["USER"],
            "-d",
            db["NAME"],
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
        ]

        for path in files:
            self.stdout.write(f"Ejecutando {path.name} …")
            subprocess.run([*base, str(path)], env=env, check=True)
            self.stdout.write(self.style.SUCCESS(f"  OK: {path.name}"))
