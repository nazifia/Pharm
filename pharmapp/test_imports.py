import os
import sys
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Try imports
print("Testing imports...")

try:
    print("1. Testing Django import...")
    import django
    print(f"Django version: {django.get_version()}")

    print("\n2. Testing settings import...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
    from django.conf import settings
    print("Settings imported successfully")

    print("\n3. Testing WSGI import...")
    from pharmapp.wsgi import application
    print("WSGI application imported successfully")

except Exception as e:
    print(f"\nError occurred: {e}")
    import traceback
    traceback.print_exc()