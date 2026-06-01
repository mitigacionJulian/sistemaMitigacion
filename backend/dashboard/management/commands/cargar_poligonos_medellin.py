"""
Carga poligonos de comunas/barrios desde shapefile (F1.5-F1.6).

Uso:
    python manage.py cargar_poligonos_medellin
    python manage.py cargar_poligonos_medellin --dry-run
    python manage.py cargar_poligonos_medellin --shp ruta/al/archivo.shp
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dashboard.geo.poligonos_medellin import cargar_poligonos, default_shapefile_path


class Command(BaseCommand):
    help = "Carga geom en comuna/barrio desde shapefile barrios_y_veredas_mr (EPSG:9377 -> 4326)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--shp",
            type=str,
            help="Ruta al .shp (default: docs/shp/.../barrios_y_veredas_mr.shp)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo cuenta matches, no escribe en la BD.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Lista barrios del shapefile sin match en BD.",
        )

    def handle(self, *args, **options):
        shp = Path(options["shp"]) if options.get("shp") else default_shapefile_path()
        try:
            stats = cargar_poligonos(
                shp,
                dry_run=bool(options.get("dry_run")),
                verbose=bool(options.get("verbose")),
            )
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        mode = " (dry-run)" if options.get("dry_run") else ""
        self.stdout.write(f"Shapefile: {shp}{mode}")
        self.stdout.write(
            f"Barrios: {stats.barrios_actualizados} actualizados, "
            f"{stats.barrios_sin_match} sin match ({stats.features_barrio} poligonos barrio en shp)"
        )
        self.stdout.write(
            f"Comunas: {stats.comunas_actualizadas} actualizadas, "
            f"{stats.comunas_sin_match} sin match ({stats.features_comuna} poligonos comuna en shp)"
        )
        if stats.barrios_actualizados >= 200 and stats.comunas_actualizadas >= 16:
            self.stdout.write(self.style.SUCCESS("F1.5 poligonos: criterio urbano cumplido"))
        elif not options.get("dry_run"):
            self.stdout.write(self.style.WARNING("Revise matches con --verbose o nombres en BD"))
