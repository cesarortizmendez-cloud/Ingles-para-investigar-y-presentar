"""Configuración Django del curso «Inglés para investigar y presentar».

Variables de entorno (ver .env.example):
  DJANGO_SECRET_KEY   obligatoria en producción
  DJANGO_DEBUG        "1" para desarrollo local
  DATABASE_URL        Postgres en producción (Neon: la integración de Vercel la crea sola; también se acepta POSTGRES_URL)
  ALLOWED_HOSTS       lista separada por comas (se suman localhost y .vercel.app)
  TUTOR_PROVIDER      "simulated" (único disponible en el incremento 1)
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"

ON_VERCEL = bool(os.environ.get("VERCEL"))
# En el computador local el modo pruebas se activa solo; en Vercel queda apagado
# salvo que se pida explícitamente con DJANGO_DEBUG=1.
DEBUG = os.environ.get("DJANGO_DEBUG", "0" if ON_VERCEL else "1") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "solo-desarrollo-local-no-usar-en-produccion"
    else:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY (o DJANGO_DEBUG=1 en local).")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".vercel.app"] + [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"] + [
    f"https://{h.lstrip('.')}" for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps por responsabilidad estable (ver docs/ARQUITECTURA.md)
    "accounts",
    "curriculum",
    "activities",
    "voice",
    "review",
    "assessment",
    "portfolio",
    "plan",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Neon en Vercel: la integración define DATABASE_URL (con pooler, la usa la app) y DATABASE_URL_UNPOOLED
# (directa; vercel_build.py la usa para las migraciones). También se acepta POSTGRES_URL.
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
if ON_VERCEL and not DATABASE_URL:
    # El sistema de archivos de Vercel es efímero: SQLite perdería datos.
    raise ImproperlyConfigured("En Vercel se requiere DATABASE_URL (Postgres Neon).")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,                    # funciones sin servidor: una conexión por petición
            conn_health_checks=True,
            ssl_require=DATABASE_URL.startswith("postgres"),                   # Neon exige SSL
            disable_server_side_cursors=DATABASE_URL.startswith("postgres"),   # el pooler de Neon (PgBouncer) no los admite
        )
    }
else:
    DATABASES = {"default": dj_database_url.parse(f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60)}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Vercel ejecuta collectstatic al construir (porque STATIC_ROOT está definido) y sirve
# /static/ desde su CDN. WhiteNoise queda como respaldo y para `runserver` sin DEBUG.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sesión: «Mantener la sesión abierta» la deja 90 días (y se renueva con el uso);
# si no se marca, se cierra al cerrar el navegador o la app.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = "Lax"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Grabaciones: el límite de cuerpo de Vercel es 4,5 MB; las grabaciones se limitan en el cliente.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
RECORDING_MAX_BYTES = 4 * 1024 * 1024
RECORDING_MAX_SECONDS = 180

# Repaso espaciado (configuración provisional, §3 y §11 de la especificación)
REVIEW_INTERVALS_DAYS = (1, 3, 7, 14, 30)
REVIEW_DAILY_CAP = 20

TUTOR_PROVIDER = os.environ.get("TUTOR_PROVIDER", "simulated")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

# Errores a la consola: en Vercel aparecen en Logs (Deployments → Functions).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}
