#!/usr/bin/env python
"""
Script to set up session security features for the pharmacy application.
Run this script after updating the session security configuration.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("Setting up session security for PharmApp...")
    print("=" * 50)
    
    try:
        # Run the setup command
        call_command('setup_session_security')
        
        print("\n" + "=" * 50)
        print("Setup completed successfully!")
        print("\nIMPORTANT NOTES:")
        print("1. All existing user sessions have been cleared for security")
        print("2. Users will need to log in again")
        print("3. Sessions are now properly isolated between users")
        print("4. Cache is using database backend for better security")
        print("\nYou can now start the Django development server.")
        
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)
