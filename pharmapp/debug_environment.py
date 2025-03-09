import os
import sys
import django

print("=== Environment Debug Information ===")
print(f"Current Directory: {os.getcwd()}")
print(f"Python Version: {sys.version}")
print(f"Django Version: {django.get_version()}")
print("\nPython Path:")
for path in sys.path:
    print(f"  - {path}")
print("\nDirectory Contents:")
for item in os.listdir():
    print(f"  - {item}")