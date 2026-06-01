import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

# Carga .env en la raíz del repo (gitignored). Docker Compose también puede inyectar las mismas variables.
load_dotenv(REPO_ROOT / ".env")


def _env(name: str, *, required: bool = False, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f"Defina {name} en el archivo .env de la raíz del proyecto "
            f"(copie .env.example → .env)."
        )
    return value or ""


SECRET_KEY = _env("DJANGO_SECRET_KEY", required=True)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# PostGIS / GeoDjango (F0). En Windows puede requerir GDAL instalado (ver POSTGIS_INICIO.md).
USE_POSTGIS = os.environ.get("DJANGO_USE_POSTGIS", "1") == "1"
if USE_POSTGIS:
    _gdal = os.environ.get("GDAL_LIBRARY_PATH")
    _geos = os.environ.get("GEOS_LIBRARY_PATH")
    GDAL_LIBRARY_PATH = _gdal  # type: ignore[assignment]
    GEOS_LIBRARY_PATH = _geos  # type: ignore[assignment]
    if _gdal:
        os.environ["GDAL_LIBRARY_PATH"] = _gdal
        os.add_dll_directory(str(Path(_gdal).parent))
    if _geos:
        os.environ["GEOS_LIBRARY_PATH"] = _geos
        os.add_dll_directory(str(Path(_geos).parent))

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    *(["django.contrib.gis"] if USE_POSTGIS else []),
    "rest_framework",
    "corsheaders",
    "accounts",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": (
            "django.contrib.gis.db.backends.postgis"
            if USE_POSTGIS
            else "django.db.backends.postgresql"
        ),
        "NAME": _env("POSTGRES_DB", default="mitigacion_accidentes"),
        "USER": _env("POSTGRES_USER", default="postgres"),
        "PASSWORD": _env("POSTGRES_PASSWORD", required=True),
        "HOST": _env("POSTGRES_HOST", default="localhost"),
        "PORT": _env("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache en memoria para coroplética / P14 / mapa-detalle (segundos). 0 = desactivado.
MAP_API_CACHE_TTL = int(os.environ.get("MAP_API_CACHE_TTL", "3600"))

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sg-mitigacion-map",
        "OPTIONS": {"MAX_ENTRIES": 500},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", "15"))
JWT_REFRESH_DAYS = int(os.environ.get("JWT_REFRESH_DAYS", "7"))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=JWT_ACCESS_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=JWT_REFRESH_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
PASSWORD_RESET_TOKEN_HOURS = int(os.environ.get("PASSWORD_RESET_TOKEN_HOURS", "1"))

# Inactividad alineada con vida del access token (minutos)
SESSION_COOKIE_AGE = JWT_ACCESS_MINUTES * 60

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
