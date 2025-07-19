#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.models import DispensingLog
from userauth.models import User

def fix_povidone_return():
    """Create a return entry for the povidone iodine that was already returned"""
    
    # Get the user
    try:
        user = User.objects.get(username='superuser')
    except User.DoesNotExist:
        user = User.objects.first()
    
    print(f"Using user: {user.username}")
    
    # Find the povidone iodine dispensed entry
    povidone_dispensed = DispensingLog.objects.filter(
        name__icontains='povidone',
        status='Dispensed'
    ).first()
    
    if povidone_dispensed:
        print(f"Found dispensed povidone entry: ID {povidone_dispensed.id}")
        print(f"Name: {povidone_dispensed.name}")
        print(f"Quantity: {povidone_dispensed.quantity}")
        print(f"Amount: {povidone_dispensed.amount}")
        
        # Create a return entry for the povidone iodine
        return_entry = DispensingLog.objects.create(
            user=user,
            name=povidone_dispensed.name,
            unit=povidone_dispensed.unit,
            quantity=povidone_dispensed.quantity,  # Assuming full return
            amount=povidone_dispensed.amount,      # Same amount as dispensed
            status='Returned'
        )
        
        print(f'Created return entry: ID {return_entry.id}')
        
        # Verify the has_returns property now works
        print(f'Dispensed entry now has returns: {povidone_dispensed.has_returns}')
        
    else:
        print("No dispensed povidone iodine entry found")

if __name__ == '__main__':
    fix_povidone_return()
