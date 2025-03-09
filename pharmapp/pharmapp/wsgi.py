"""
WSGI config for pharmapp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Get the project base directory
BASE_DIR = Path(__file__).resolve().parent.parent
# Add the project directory to the Python path
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    import traceback
    print(f"Error loading WSGI application: {e}")
    traceback.print_exc()
    raise
