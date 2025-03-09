import os
import sys
from pathlib import Path

def simple_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return [b"Hello, World!"]

try:
    # Add the project root directory to Python path
    BASE_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(BASE_DIR))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
    
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    print("WSGI application loaded successfully!")
except Exception as e:
    print(f"Failed to load WSGI application: {e}")
    print("\nTraceback:")
    import traceback
    traceback.print_exc()
    print("\nFalling back to simple WSGI app")
    application = simple_app
