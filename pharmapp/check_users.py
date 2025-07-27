#!/usr/bin/env python
"""
Script to check user credentials
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def check_users():
    print("Checking users...")
    print("=" * 50)
    
    users = User.objects.all()
    
    for user in users:
        print(f"Mobile: {user.mobile}")
        print(f"Username: {user.username}")
        print(f"Is superuser: {user.is_superuser}")
        print(f"Is active: {user.is_active}")
        print("-" * 30)

if __name__ == "__main__":
    check_users()
