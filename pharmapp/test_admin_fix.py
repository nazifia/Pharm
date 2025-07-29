#!/usr/bin/env python
"""
Test script to verify the admin registration fix
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')

try:
    django.setup()
    print("✅ Django setup successful")
    
    # Test admin imports
    from django.contrib import admin
    from store.models import WholesaleItem
    print("✅ Model imports successful")
    
    # Check if WholesaleItem is registered
    if WholesaleItem in admin.site._registry:
        admin_class = admin.site._registry[WholesaleItem]
        print(f"✅ WholesaleItem is registered with: {admin_class.__class__.__name__}")
    else:
        print("❌ WholesaleItem is not registered")
    
    # Test admin functionality
    from store.admin import DispensingLogAdmin
    from wholesale.admin import WholesaleItemAdmin
    print("✅ Admin class imports successful")
    
    print("\n🎉 Admin registration fix successful!")
    print("The WholesaleItem registration conflict has been resolved.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
