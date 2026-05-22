"""
Configuración para pytest/pytest-django (SQLite en memoria).
El proyecto en desarrollo y producción usa PostgreSQL; las pruebas no requieren Postgres.
"""
from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
