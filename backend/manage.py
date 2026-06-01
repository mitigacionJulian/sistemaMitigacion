#!/usr/bin/env python
import os
import sys
from pathlib import Path


def _bootstrap_env() -> None:
    """Carga .env y DLL de OSGeo4W antes de importar Django/GeoDjango (Windows)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")
    gdal = os.environ.get("GDAL_LIBRARY_PATH")
    geos = os.environ.get("GEOS_LIBRARY_PATH")
    if gdal:
        os.environ["GDAL_LIBRARY_PATH"] = gdal
        gdal_dir = Path(gdal).parent
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(gdal_dir))
        # PROJ/GDAL data (Windows OSGeo4W): necesario para transform 9377->4326
        osgeo_root = gdal_dir.parent
        proj_lib = osgeo_root / "share" / "proj"
        gdal_data = osgeo_root / "share" / "gdal"
        if proj_lib.is_dir():
            os.environ.setdefault("PROJ_LIB", str(proj_lib))
        if gdal_data.is_dir():
            os.environ.setdefault("GDAL_DATA", str(gdal_data))
    if geos:
        os.environ["GEOS_LIBRARY_PATH"] = geos
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(Path(geos).parent))


_bootstrap_env()


def main():
    # Siempre PostgreSQL/PostGIS: pytest usa config.settings_test vía pytest.ini,
    # no debe heredarse a runserver (provoca "unrecognized token: :" en SQL ::bigint).
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Active el entorno virtual e instale dependencias."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
