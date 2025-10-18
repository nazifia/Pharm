#!/usr/bin/env python
"""
Generate a secure Django SECRET_KEY for production use.
Run this script to get a new secret key to use in your .env file.
"""
import secrets

def generate_django_secret_key(length=50):
    """Generate a Django-compatible SECRET_KEY"""
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))

if __name__ == '__main__':
    secret_key = generate_django_secret_key()
    print(f"Generated SECRET_KEY for production:")
    print(f"SECRET_KEY={secret_key}")
    print("\nAdd this to your .env file for production use.")
