from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta


load_dotenv()


def as_bool(value: str):
    return value.lower() in ["true", "yes"]


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# https://docs.djangoproject.com/en/dev/ref/settings/#debug
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = as_bool(os.getenv("DEBUG", "true"))

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
# ALLOWED_HOSTS = ["*"]
ALLOWED_HOSTS = [
    value.strip()
    for value in os.getenv("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")
]

# Application definition
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = [
    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used
    # "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "oauth2_provider",
    # Third-party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "corsheaders",
    "crispy_forms",
    "crispy_bootstrap5",
    "debug_toolbar",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "import_export",
    "dj_rest_auth",
    "rest_framework.authtoken",
    "phonenumber_field",
    "drf_yasg",
    "django_celery_beat",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "storages",
    # Local
    "accounts",
]

# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # WhiteNoise
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",  # Django Debug Toolbar
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # django-allauth
]

# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"

# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# https://docs.djangoproject.com/en/dev/ref/settings/#templates
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

# https://docs.djangoproject.com/en/dev/ref/settings/#databases
USE_SQLITE = as_bool(os.getenv("USE_SQLITE", "False"))

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "gtidigibankdb"),
            "USER": os.getenv("POSTGRES_USER", "gtiadmin"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "localhost"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),  # set in docker-compose.yml
            "PORT": int(os.getenv("POSTGRES_PORT", 5432)),  # default postgres port
            "OPTIONS": {"sslmode": os.getenv("PGSSLMODE", "prefer")},
        }
    }

# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
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

CORS_ORIGIN_ALLOW_ALL = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"

USE_I18N = True

LANGUAGES = (
    ("pt", "Portuguese"),
    ("en", "English"),
    ("fr", "French"),
    # ("es", "Spanish"),
)

# https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = "UTC"

# https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-USE_I18N
USE_I18N = True

# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [BASE_DIR / "locale"]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

# https://docs.djangoproject.com/en/dev/ref/settings/#static-root

# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# https://whitenoise.readthedocs.io/en/latest/django.html
# STORAGES = {
#     "default": {
#         "BACKEND": "django.core.files.storage.FileSystemStorage",
#     },
#     "staticfiles": {
#         "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
#     },
# }

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# django-crispy-forms
# https://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
if bool(os.getenv("USE_SMTP_EMAIL", True)):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_USE_TLS = True
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_TO_EMAIL = EMAIL_HOST_USER

# django-debug-toolbar
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html
# https://docs.djangoproject.com/en/dev/ref/settings/#internal-ips
INTERNAL_IPS = [
    value.strip()
    for value in os.getenv("INTERNAL_IPS", default="127.0.0.1,localhost").split(",")
]

# https://docs.djangoproject.com/en/dev/topics/auth/customizing/#substituting-a-custom-user-model
AUTH_USER_MODEL = "accounts.CustomUser"

# django-allauth config
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "/"

# https://django-allauth.readthedocs.io/en/latest/views.html#logout-account-logout
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# https://django-allauth.readthedocs.io/en/latest/installation.html?highlight=backends
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]

# X_FRAME_OPTIONS = "ALLOW"
CORS_ALLOW_ALL_ORIGINS = True

# PHONENUMBER_DEFAULT_REGION = "ST"
# PHONENUMBER_DB_FORMAT = "NATIONAL"


REST_AUTH = {
    "LOGIN_SERIALIZER": "accounts.serializers.CustomLoginSerializer",
    "TOKEN_SERIALIZER": "dj_rest_auth.serializers.TokenSerializer",
    "JWT_SERIALIZER": "dj_rest_auth.serializers.JWTSerializer",
    "JWT_SERIALIZER_WITH_EXPIRATION": "dj_rest_auth.serializers.JWTSerializerWithExpiration",
    "JWT_TOKEN_CLAIMS_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "USER_DETAILS_SERIALIZER": "accounts.serializers.UserSerializer",
    "PASSWORD_RESET_SERIALIZER": "dj_rest_auth.serializers.PasswordResetSerializer",
    "PASSWORD_RESET_CONFIRM_SERIALIZER": "dj_rest_auth.serializers.PasswordResetConfirmSerializer",
    "PASSWORD_CHANGE_SERIALIZER": "dj_rest_auth.serializers.PasswordChangeSerializer",
    "REGISTER_SERIALIZER": "dj_rest_auth.registration.serializers.RegisterSerializer",
    "REGISTER_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    # "TOKEN_MODEL": "rest_framework.authtoken.models.Token",
    # "TOKEN_CREATOR": "dj_rest_auth.utils.default_create_token",
    "PASSWORD_RESET_USE_SITES_DOMAIN": False,
    "OLD_PASSWORD_FIELD_ENABLED": False,
    "LOGOUT_ON_PASSWORD_CHANGE": False,
    "SESSION_LOGIN": True,
    "USE_JWT": True,
    "JWT_AUTH_REFRESH_COOKIE": "authentication-refresh-token",
    "JWT_AUTH_COOKIE": "authentication-auth",
    "JWT_AUTH_SECURE": False,
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_SAMESITE": "Lax",
    "JWT_AUTH_RETURN_EXPIRATION": True,
    "JWT_AUTH_COOKIE_USE_CSRF": True,
    "JWT_AUTH_COOKIE_ENFORCE_CSRF_ON_UNAUTHENTICATED": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API DOCUMENTATION",
    "DESCRIPTION": ("Api Documentation"),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # OTHER SETTINGS
}

THROTTLE_RATE = os.getenv("THROTTLE_RATE", "100/s")
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 64,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "NON_FIELD_ERRORS_KEY": "error",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        # "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "apis": THROTTLE_RATE,
    },
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
}
REST_USE_JWT = True

JWT_AUTH_COOKIE = "authentication-auth"

JWT_AUTH_REFRESH_COOKIE = "authentication-refresh-token"

JWT_AUTH_RETURN_EXPIRATION = True
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=3),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=20),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

DEFAULT_PARSER_CLASSES = (
    "rest_framework.parsers.MultiPartParser",
    "rest_framework.parsers.FileUploadParser",
    "rest_framework.parsers.FormParser",
    "rest_framework.parsers.JSONParser",
)


# CSRF
CSRF_TRUSTED_ORIGINS = [
    value.strip()
    for value in os.getenv(
        "CSRF_TRUSTED_ORIGINS", default="http://127.0.0.1,http://localhost"
    ).split(",")
]
for i in ALLOWED_HOSTS:
    if i not in ["localhost", "127.0.0.1"]:
        CSRF_TRUSTED_ORIGINS.append(f"https://{i}")

# READ HTTPS CONFIG FROM PROXY
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
REDIS_USERNAME = os.getenv("REDIS_USERNAME", default="default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", default="default")
REDIS_USE_TLS = as_bool(os.getenv("REDIS_USE_TLS", default="False"))
REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))
if REDIS_USE_TLS:
    REDIS_URL = f"rediss://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
else:
    REDIS_URL = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", default=3600))
# DJANGO CACHE
CACHE_DB_ID = int(os.getenv("CACHE_DB_ID", default="1"))
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/{CACHE_DB_ID}",
        # "OPTIONS": {"CACHE_TIMEOUT": CACHE_TIMEOUT},
    }
}
# CHANNELS FOR WEBSOCKET
CHANNEL_LAYER_DB_ID = int(os.getenv("CHANNEL_LAYER_DB_ID", default="0"))
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"{REDIS_URL}/{CHANNEL_LAYER_DB_ID}"],
        },
    },
}
THROTTLE_RATE = os.getenv("THROTTLE_RATE", "100/s")

# CELERY
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_DB_ID = int(os.getenv("CELERY_BROKER_DB_ID", default="2"))
CELERY_RESULT_BACKEND_DB_ID = int(os.getenv("CELERY_RESULT_BACKEND_DB_ID", default="3"))
CELERY_BROKER_URL = f"{REDIS_URL}/{CELERY_BROKER_DB_ID}"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/3"
if REDIS_USE_TLS:
    CELERY_BROKER_URL += "?ssl_cert_reqs=required"
    CELERY_RESULT_BACKEND += "?ssl_cert_reqs=required"
CELERY_TASK_ALWAYS_EAGER = as_bool(
    os.getenv("CELERY_TASK_ALWAYS_EAGER", default="False")
)


UNFOLD = {
    "SITE_TITLE": "BACK OFFICE",
    "SITE_HEADER": "BACK OFFICE",
    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "75 85 99",
            "default-dark": "209 213 219",
            "important-light": "17 24 39",
            "important-dark": "243 244 246",
        },
        "primary": {
            "50": "240 249 255",
            "100": "219 242 255",
            "200": "179 229 255",
            "300": "128 210 255",
            "400": "77 188 255",
            "500": "0 130 187",
            "600": "0 104 150",
            "700": "0 78 112",
            "800": "0 52 75",
            "900": "0 39 56",
            "950": "0 26 37",
        },
    },
}


# allow all headers
CORS_ALLOW_HEADERS = "*"

# PAYSTACK
PAYSTACK_PRIVATE_KEY = os.getenv("PAYSTACK_PRIVATE_KEY", default="")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", default="")
PAYSTACK_CALLBACK_URL = os.getenv("PAYSTACK_CALLBACK_URL", default="")

# MNOTIFY
MNOTIFY_SENDER_ID = os.getenv("MNOTIFY_SENDER_ID", "")
MNOTIFY_API_KEY = os.getenv("MNOTIFY_API_KEY", "")


# MOOLRE PAYMENT
MOOLRE_API_URL = os.getenv("MOOLRE_API_URL", "")
MOOLRE_PRIVATE_KEY = os.getenv("MOOLRE_PRIVATE_KEY", "")
MOOLRE_PUBLIC_KEY = os.getenv("MOOLRE_PUBLIC_KEY", "")
MOOLRE_USERNAME = os.getenv("MOOLRE_USERNAME", "")
MOORLE_ACCOUNT_NUMBER = os.getenv("MOORLE_ACCOUNT_NUMBER", "")
MOOLRE_SMS_API_KEY = os.getenv("MOOLRE_SMS_API_KEY", "")
MOOLRE_SMS_SENDER_ID = os.getenv("MOOLRE_SMS_SENDER_ID", "")

# AWS S3 SETTINGS
USE_S3 = as_bool(os.getenv("USE_S3", default="False"))

if USE_S3:
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

    # S3 static settings
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

    # S3 media settings
    AWS_DEFAULT_ACL = None  # Disable ACLs for newer S3 buckets
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False

    # Media files configuration
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # Optional: Configure S3 for better file organization
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_S3_SIGNATURE_VERSION = "s3v4"

    # Optional: Use S3 for static files as well (uncomment if needed)
    # STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    # STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

    # Configure STORAGES for Django 5.1+ compatibility
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


# EMAIL URL
AWS_EMAIL_URL = os.getenv("AWS_EMAIL_URL", "")
