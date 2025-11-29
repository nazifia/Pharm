import os
import shutil
from django.contrib import messages
from decouple import config, Csv

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# Get SECRET_KEY from .env file (required - no default for security)
# Generate new key: python generate_secret_key.py
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
# Get DEBUG from environment variable or use development fallback
DEBUG = config('DEBUG', default='True', cast=bool)

# ALLOWED_HOSTS - get from environment or use development defaults
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver', cast=Csv())

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'whitenoise.runserver_nostatic',
    'django.contrib.humanize',
    'django_htmx',
    'crispy_forms',  # Legacy - still installed but unused (using simple HTML/CSS forms instead)
    'crispy_bootstrap5',  # Legacy - still installed but unused (using simple HTML/CSS forms instead)
    # 'channels',  # WebSocket support (disabled - not currently used)
    'store',
    'userauth',
    'customer',
    'wholesale',
    'supplier',
    'chat',
    'notebook',  # Add notebook app for note-taking functionality
    'corsheaders',  # Make sure this is here
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'pharmapp.no_cache_middleware.NoCacheMiddleware',  # Prevent HTML caching
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # Performance monitoring middleware (add early for accurate measurements)
    'pharmapp.performance_middleware.PerformanceMonitoringMiddleware',
    'pharmapp.performance_middleware.QueryCountMiddleware',
    # Re-enable essential middleware
    'pharmapp.middleware.ConnectionDetectionMiddleware',
    'pharmapp.middleware.OfflineMiddleware',
    'userauth.middleware.ActivityMiddleware',  # Add ActivityMiddleware to log user actions
    'userauth.middleware.RoleBasedAccessMiddleware',  # Add role-based access control
    'userauth.middleware.AutoLogoutMiddleware',  # Add auto-logout functionality
    # Session security middleware
    'userauth.session_middleware.SessionValidationMiddleware',  # Session validation for security
    'userauth.session_middleware.UserActivityTrackingMiddleware',  # Track user activity per session
    'userauth.session_middleware.SessionCleanupMiddleware',  # Clean up expired sessions
    # User isolation middleware (temporarily disabled for testing)
    # 'userauth.user_isolation_middleware.UserIsolationMiddleware',  # Ensure user data isolation
    # 'userauth.user_isolation_middleware.UserSessionIsolationMiddleware',  # Session isolation
    # 'userauth.user_isolation_middleware.UserActivityIsolationMiddleware',  # Activity isolation
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "capacitor://localhost",
    "http://localhost",
    "http://localhost:8000",
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
]

# Performance optimizations for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_MAX_AGE = 31536000  # 1 year for static files in production

ROOT_URLCONF = 'pharmapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.marquee_context',
                'userauth.context_processors.user_roles',
                'store.context_processors_performance.performance_metrics',
            ],
            # Performance optimizations
            'debug': DEBUG,  # Only enable template debug in development
            'string_if_invalid': '',
        },
    },
]

WSGI_APPLICATION = 'pharmapp.wsgi.application'
# ASGI_APPLICATION = 'pharmapp.asgi.application'

# Channel layers configuration for WebSocket support (temporarily disabled)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [('127.0.0.1', 6379)],
#         },
#     },
# }


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# Database settings are now optimized in the performance section below

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 2000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# Database routing settings
DATABASE_ROUTERS = ['pharmapp.routers.OfflineRouter']


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'userauth.User'

# Authentication backends
# AUTHENTICATION_BACKENDS = [
#     'userauth.backends.MobileBackend',  # Custom mobile authentication
#     'django.contrib.auth.backends.ModelBackend',  # Default backend as fallback
# ]



# Add to your settings.py for offline-mode
# PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static', 'js', 'sw.js')
PWA_APP_NAME = 'PharmApp'
PWA_APP_DESCRIPTION = "Pharmacy Management System"
PWA_APP_THEME_COLOR = '#4285f4'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Performance optimizations
# Database connection pool settings for better performance
# ===== DATABASE CONFIGURATION OPTIONS =====
# Option 1: SQLite (Default - Uncomment to use)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 60,  # Increased from 20 to 60 seconds for better concurrency
            'check_same_thread': False,
        },
        'CONN_MAX_AGE': 60,  # Reuse database connections for 60 seconds
    },
    'offline': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'offline.sqlite3',
        'OPTIONS': {
            'timeout': 60,  # Increased from 20 to 60 seconds for better concurrency
            'check_same_thread': False,
        },
        'CONN_MAX_AGE': 60,  # Reuse database connections for 60 seconds
    }
}

# Option 2: MySQL (Uncomment to use, Comment SQLite above)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': config('DB_NAME', default='pharmapp_db'),
#         'USER': config('DB_USER', default='pharmapp_user'),
#         'PASSWORD': config('DB_PASSWORD', default='your_mysql_password_here'),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='3306', cast=int),
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#         'CONN_MAX_AGE': 60,  # Reuse database connections for 60 seconds
#     },
#     'offline': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'offline.sqlite3',
#         'OPTIONS': {
#             'timeout': 20,
#             'check_same_thread': False,
#         },
#         'CONN_MAX_AGE': 60,  # Reuse database connections for 60 seconds
#     }
# }
# ===== END DATABASE CONFIGURATION OPTIONS =====

# File upload optimizations
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB in memory before writing to disk
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB


# Bootstrap Messages class configuration
MESSAGE_TAGS = {
    messages.SUCCESS: 'success',
    messages.INFO: 'info',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}



# Session Security Settings
SESSION_COOKIE_AGE = 1200  # 20 minutes in seconds
SESSION_SAVE_EVERY_REQUEST = True  # Reset the session expiration time on each request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Session expires when browser closes
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookies
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database sessions for better user isolation
# Note: SESSION_COOKIE_SECURE is set above based on DEBUG flag (True in production, False in development)

# Auto logout settings
AUTO_LOGOUT_DELAY = 20  # Auto logout after 20 minutes of inactivity

# Note: Security settings (XSS filter, content type nosniff, X-Frame-Options) are configured
# in the production security block above (lines 24-33) based on DEBUG flag



# Authentication settings
LOGIN_URL = 'store:index'  # Update this to match your login URL pattern
LOGIN_REDIRECT_URL = 'store:index'
LOGOUT_REDIRECT_URL = 'store:index'


# Allow more form fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# def copy_index_html(sender, **kwargs):
#     """Copy capacitor_index.html to staticfiles/index.html after collectstatic"""
#     source = os.path.join(BASE_DIR, 'templates', 'capacitor_index.html')
#     dest = os.path.join(BASE_DIR, 'staticfiles', 'index.html')
#     if os.path.exists(source):
#         shutil.copy2(source, dest)

# from django.core.signals import static_files_copied
# static_files_copied.connect(copy_index_html)
