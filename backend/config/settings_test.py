"""
Configuración para pytest/pytest-django (SQLite en memoria).

El proyecto en desarrollo usa PostgreSQL/PostGIS + GDAL (Windows OSGeo4W).
Las pruebas no requieren Postgres ni cargar GDAL: pytest no pasa por manage.py.
"""
from .settings import *  # noqa: F403

# Evita importar django.contrib.gis (GDAL) al arrancar pytest en Windows.
USE_POSTGIS = False
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django.contrib.gis"]  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
