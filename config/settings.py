
"""
Django settings for the Rust Apartment Maintenance Portal.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the project root.
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """Read a boolean environment variable safely."""
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip().lower()

    if value in {"true", "1", "yes", "on"}:
        return True

    if value in {"false", "0", "no", "off"}:
        return False

    raise ValueError(
        f"Invalid value for {name}. Use true or false."
    )


def env_required(name):
    """Require a non-empty environment variable."""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(
            f"Missing required environment variable: {name}. "
            "Add it to your .env file."
        )

    return value.strip()


# -------------------------------------------------------------------
# Security and environment
# -------------------------------------------------------------------

SECRET_KEY = env_required("DJANGO_SECRET_KEY")

DEBUG = env_bool("DJANGO_DEBUG", default=False)

DJANGO_ADMIN_URL = os.getenv(
    "DJANGO_ADMIN_URL",
    "admin/",
).strip("/")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError(
        "DJANGO_ALLOWED_HOSTS must contain at least one hostname "
        "when DJANGO_DEBUG is false."
    )

# HTTPS and browser security.
# Secure defaults are enabled when DEBUG is false.
SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    default=not DEBUG,
)

SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE",
    default=not DEBUG,
)

CSRF_COOKIE_SECURE = env_bool(
    "CSRF_COOKIE_SECURE",
    default=not DEBUG,
)

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = int(
    os.getenv(
        "SECURE_HSTS_SECONDS",
        "0" if DEBUG else "31536000",
    )
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)

SECURE_HSTS_PRELOAD = env_bool(
    "SECURE_HSTS_PRELOAD",
    default=False,
)

# Only enable proxy SSL headers when the deployment proxy is trusted
# and is configured to overwrite the header from external requests.
if env_bool("USE_X_FORWARDED_HOST", default=False):
    USE_X_FORWARDED_HOST = True

if env_bool("TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# -------------------------------------------------------------------
# Applications
# -------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "maintenance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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


# -------------------------------------------------------------------
# Database: MySQL
# -------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env_required("DB_NAME"),
        "USER": env_required("DB_USER"),
        "PASSWORD": env_required("DB_PASSWORD"),
        "HOST": env_required("DB_HOST"),
        "PORT": env_required("DB_PORT"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": (
                "SET sql_mode = "
                "'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,"
                "NO_ENGINE_SUBSTITUTION'"
            ),
        },
    }
}


# -------------------------------------------------------------------
# Authentication and password validation
# -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# -------------------------------------------------------------------
# Internationalization
# -------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"

USE_I18N = True
USE_TZ = True


# -------------------------------------------------------------------
# Static files and uploads
# -------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = (
    [BASE_DIR / "static"]
    if (BASE_DIR / "static").is_dir()
    else []
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Restrict uploaded request photographs to a reasonable size.
# Image-specific format and pixel validation will be implemented
# in the upload form/service in a later security step.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


# -------------------------------------------------------------------
# Defaults
# -------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
