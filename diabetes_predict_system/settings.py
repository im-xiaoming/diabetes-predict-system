from importlib.util import find_spec
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

if find_spec("dotenv"):
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")


def clean_env(name, default=None):
    value = os.environ.get(name, default)
    if isinstance(value, str):
        return value.strip().strip("\"'")
    return value


def env_bool(name, default=False):
    value = clean_env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    value = clean_env(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def database_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use postgres:// or postgresql://")

    query = parse_qs(parsed.query)
    sslmode = query.get("sslmode", [clean_env("PGSSLMODE", "require")])[0]
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or clean_env("PGPORT", "5432")),
        "CONN_MAX_AGE": int(clean_env("DB_CONN_MAX_AGE", "60")),
    }
    if sslmode:
        config["OPTIONS"] = {"sslmode": sslmode}
    return config


def database_config():
    database_url = clean_env("DJANGO_DATABASE_URL") or clean_env("DATABASE_URL")
    if database_url:
        return database_from_url(database_url)

    pg_host = clean_env("DJANGO_PGHOST") or clean_env("PGHOST")
    if pg_host:
        sslmode = clean_env("DJANGO_PGSSLMODE") or clean_env("PGSSLMODE", "require")
        config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": clean_env("DJANGO_PGDATABASE") or clean_env("PGDATABASE", "postgres"),
            "USER": clean_env("DJANGO_PGUSER") or clean_env("PGUSER", "postgres"),
            "PASSWORD": clean_env("DJANGO_PGPASSWORD") or clean_env("PGPASSWORD", ""),
            "HOST": pg_host,
            "PORT": clean_env("DJANGO_PGPORT") or clean_env("PGPORT", "5432"),
            "CONN_MAX_AGE": int(clean_env("DB_CONN_MAX_AGE", "60")),
        }
        if sslmode:
            config["OPTIONS"] = {"sslmode": sslmode}
        return config

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": clean_env("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }


SECRET_KEY = clean_env("DJANGO_SECRET_KEY", "django-insecure-dev-key-diabetes-predict-system")

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "dashboard",
    "patients",
    "predictions",
    "mock_his.apps.MockHisConfig",
    "monitor",
    "alerts",
    "history",
    "modeling",
    "logging_app.apps.LoggingConfig",
]

if find_spec("django_extensions"):
    INSTALLED_APPS.append("django_extensions")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "diabetes_predict_system.urls"

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
    }
]

WSGI_APPLICATION = "diabetes_predict_system.wsgi.application"

DATABASES = {"default": database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en"

TIME_ZONE = "Asia/Bangkok"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = clean_env("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

FASTAPI_BASE_URL = clean_env("FASTAPI_BASE_URL", "http://127.0.0.1:8001")

MOCK_HIS_AUTO_START = env_bool("MOCK_HIS_AUTO_START", True)
MOCK_HIS_AUTO_START_INTERVAL = int(os.environ.get("MOCK_HIS_AUTO_START_INTERVAL", "5"))
MOCK_HIS_AUTO_START_DELAY = int(os.environ.get("MOCK_HIS_AUTO_START_DELAY", "3"))
MOCK_HIS_AUTO_START_UNLABELED = env_bool("MOCK_HIS_AUTO_START_UNLABELED", False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
