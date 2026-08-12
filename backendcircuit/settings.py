"""
Django settings for travel_api project.
Security hardened: JWT, CORS allow-list, CSRF trusted origins,
HSTS, XSS/CSP-friendly headers, Argon2 password hashing.
"""
from datetime import timedelta
from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",

    # local
    "api",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "backendcircuit.security_middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "backendcircuit.urls"
WSGI_APPLICATION = "backendcircuit.wsgi.application"
ASGI_APPLICATION = "backendcircuit.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# Database — Postgres via DATABASE_URL, SQLite fallback
DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password hashers — Argon2 first
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dubai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- DRF ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Lenient: a stale/expired admin token must not 401 public GETs.
        "api.authentication.OptionalJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("ANON_THROTTLE", default="1200/min"),
        "user": "600/min",
        # public un-authenticated form submissions (enquiry / contact)
        "public_form": config("PUBLIC_FORM_THROTTLE", default="8/min"),
    },
    "EXCEPTION_HANDLER": "backendcircuit.exception_handler.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Travel API",
    "DESCRIPTION": "REST API for the travel website (packages, deals, visas, hotels, activities, gallery, bookings, enquiries, payments).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---- CORS ----
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173,https://circuit.muhammedswafwanck.workers.dev",
    cast=Csv(),
)
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=DEBUG, cast=bool)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# ---- Security headers ----
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---- Email ----
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="muhammedswafwanck@gmail.com")
if not EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---- Adyen ----
ADYEN_API_KEY = config("ADYEN_API_KEY", default="")
ADYEN_MERCHANT_ACCOUNT = config("ADYEN_MERCHANT_ACCOUNT", default="")
ADYEN_CLIENT_KEY = config("ADYEN_CLIENT_KEY", default="")
ADYEN_HMAC_KEY = config("ADYEN_HMAC_KEY", default="")
ADYEN_ENV = config("ADYEN_ENV", default="test")

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")


# --------------------------------------------------------------------------- #
# Public form delivery (enquiry / visa / contact)
# --------------------------------------------------------------------------- #
SITE_NAME = config("SITE_NAME", default="Circuit Travels")

# Google Form — server-side submission. GOOGLE_FORM_ID accepts either the bare
# ID or the complete /viewform URL. Take entry IDs from a pre-filled link:
#   https://docs.google.com/forms/d/e/<GOOGLE_FORM_ID>/viewform?entry.123=Name
GOOGLE_FORM_ID = config("GOOGLE_FORM_ID", default="")
GOOGLE_FORM_ENTRIES = {
    "name": config("GOOGLE_FORM_ENTRY_NAME", default=""),
    "email": config("GOOGLE_FORM_ENTRY_EMAIL", default=""),
    "phone": config("GOOGLE_FORM_ENTRY_PHONE", default=""),
    "message": config("GOOGLE_FORM_ENTRY_MESSAGE", default=""),
    "type": config("GOOGLE_FORM_ENTRY_TYPE", default=""),
    "item_title": config("GOOGLE_FORM_ENTRY_ITEM_TITLE", default=""),
    "item_type": config("GOOGLE_FORM_ENTRY_ITEM_TYPE", default=""),
}

# WhatsApp — plain wa.me deep link, no third-party provider/API. Keep the
# production business number as the fallback so a missing optional .env value
# cannot silently create enquiries with an empty whatsapp_url.
WHATSAPP_NUMBER = config("WHATSAPP_NUMBER", default="918301847136")

# Gmail notification recipients for contact messages (and enquiries if enabled)
CONTACT_NOTIFY_EMAILS = config("CONTACT_NOTIFY_EMAILS", default="", cast=Csv())
NOTIFY_ENQUIRY_BY_EMAIL = config("NOTIFY_ENQUIRY_BY_EMAIL", default=False, cast=bool)

# Inline delivery is the reliable default. Daemon threads can be terminated by
# production WSGI workers before they finish. A real task queue can be added for
# high-volume deployments; set True only where worker lifetime is guaranteed.
DELIVERY_ASYNC = config("DELIVERY_ASYNC", default=False, cast=bool)

# --------------------------------------------------------------------------- #
# Hardening
# --------------------------------------------------------------------------- #
# Image/gallery uploads from the admin panel are multipart and can be large.
MAX_REQUEST_BODY_BYTES = config("MAX_REQUEST_BODY_BYTES", default=50 * 1024 * 1024, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_REQUEST_BODY_BYTES
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
APPEND_SLASH = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}