"""Configuración principal de Kimün LMS."""

from pathlib import Path
from dotenv import load_dotenv
import os
import sys

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-me')

DEBUG = os.environ.get('DEBUG', 'True').lower() in {'1', 'true', 'yes', 'si'}

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = ['http://18.212.117.26']


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'usuarios',
    'cursos',
    'evaluaciones',
    'certificados',
    'reportes',
    'calendario',
    'tareas',
    'anuncios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'usuarios.middleware.DynamoDBAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kimun.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kimun.wsgi.application'


# Django exige una entrada de base de datos aunque la aplicación no use ORM.
# El backend ficticio impide abrir conexiones SQL de forma accidental.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',
    },
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'es-cl'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True

AUTH_USER_MODEL = 'usuarios.Usuario'

# Autenticación y sesiones 100 % NoSQL.
AUTHENTICATION_BACKENDS = [
    'usuarios.auth_backend.DynamoDBAuthBackend',
]
# Las sesiones firmadas viven en cookies y no requieren una tabla SQL.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'templates' / 'admin',
    BASE_DIR / 'kimun',
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'usuarios:login'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Configuración NoSQL (DynamoDB)
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'KimunData-Demo')
AWS_REGION_PRIMARY = os.environ.get('AWS_REGION_PRIMARY', 'us-east-1')
AWS_REGION_SECONDARY = os.environ.get('AWS_REGION_SECONDARY', 'us-west-2')

MEDIA_STORAGE_BACKEND = (
    'django_supabase_storage.SupabaseMediaStorage'
    if SUPABASE_URL and SUPABASE_KEY
    else 'django.core.files.storage.FileSystemStorage'
)

STORAGES = {
    'default': {
        'BACKEND': MEDIA_STORAGE_BACKEND,
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': [
                'heading', '|',
                'bold', 'italic', 'underline', 'strikethrough', '|',
                'link', '|',
                'bulletedList', 'numberedList', 'blockQuote', '|',
                'imageUpload', '|',
                'undo', 'redo',
            ],
        },
        'language': 'es',
        'image': {
            'toolbar': [
                'imageTextAlternative', '|',
                'imageStyle:alignLeft', 'imageStyle:alignCenter', 'imageStyle:alignRight', '|',
            ],
            'styles': [
                'alignLeft', 'alignCenter', 'alignRight',
            ],
        },
    },
}

CKEDITOR_5_FILE_UPLOAD_PERMISSION = 'authenticated'
CKEDITOR_5_MAX_FILE_SIZE = 5

# Ajustes de seguridad del despliegue actual.
if not DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    # SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

if 'test' in sys.argv:
    STORAGES['default']['BACKEND'] = 'django.core.files.storage.FileSystemStorage'
