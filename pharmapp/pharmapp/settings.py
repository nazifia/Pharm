import os
import shutil
from django.contrib import messages

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-745$ysi)dtow@&h&g9%um@8m-7#8)xkva&4r1q4vx_mpg3pg&3'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# ALLOWED_HOSTS = []
ALLOWED_HOSTS = ['localhost', '127.0.0.1']


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
    'store',
    'userauth',
    'customer',
    'wholesale',
    'supplier',
    'corsheaders',  # Make sure this is here
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # This should be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Add custom offline middleware
    'pharmapp.middleware.OfflineMiddleware',
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

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'pharmapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


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
MEDIA_ROOT = BASE_DIR /'media'

AUTH_USER_MODEL = 'userauth.User'



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


# Bootstrap Messages class configuration
MESSAGE_TAGS = {
    messages.SUCCESS: 'success',
    messages.INFO: 'info',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}



# Set session to expire after 10 minutes (300 seconds) of inactivity
SESSION_COOKIE_AGE = 1200  # 10 minutes in seconds
SESSION_SAVE_EVERY_REQUEST = True  # Reset the session expiration time on each request



# Authentication settings
LOGIN_URL = 'store:index'  # Update this to match your login URL pattern
LOGIN_REDIRECT_URL = 'store:index'
LOGOUT_REDIRECT_URL = 'store:index'

# def copy_index_html(sender, **kwargs):
#     """Copy capacitor_index.html to staticfiles/index.html after collectstatic"""
#     source = os.path.join(BASE_DIR, 'templates', 'capacitor_index.html')
#     dest = os.path.join(BASE_DIR, 'staticfiles', 'index.html')
#     if os.path.exists(source):
#         shutil.copy2(source, dest)

# from django.core.signals import static_files_copied
# static_files_copied.connect(copy_index_html)
