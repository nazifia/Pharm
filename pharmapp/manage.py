#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    """Run administrative tasks."""
    try:
        # Add the project root directory to Python path
        BASE_DIR = Path(__file__).resolve().parent
        sys.path.insert(0, str(BASE_DIR))
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
        
        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            ) from exc
        
        execute_from_command_line(sys.argv)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
