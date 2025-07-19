#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.models import DispensingLog
from userauth.models import User

def test_return_logic():
    """Test the return tracking logic"""
    
    # Get the user (using the correct User model)
    try:
        user = User.objects.get(username='superuser')
    except User.DoesNotExist:
        user = User.objects.first()  # Get any user if superuser doesn't exist
    
    print(f"Using user: {user.username}")
    
    # Create a test return entry for ARTEMETHER/LUMEFANTRINE
    return_entry = DispensingLog.objects.create(
        user=user,
        name='ARTEMETHER/LUMEFANTRINE',
        unit='Pack',
        quantity=1.0,
        amount=1500.0,
        status='Returned'
    )
    
    print(f'Created return entry: ID {return_entry.id}')
    
    # Now test the has_returns property
    artemether_logs = DispensingLog.objects.filter(
        name__icontains='ARTEMETHER', 
        status='Dispensed'
    ).order_by('created_at')
    
    print('\nARTEMETHER/LUMEFANTRINE dispensed entries after creating return:')
    for log in artemether_logs:
        print(f'ID: {log.id}, Status: {log.status}, Has Returns: {log.has_returns}')
    
    # Check all ARTEMETHER entries
    all_artemether = DispensingLog.objects.filter(name__icontains='ARTEMETHER').order_by('created_at')
    print(f'\nAll ARTEMETHER entries ({all_artemether.count()} total):')
    for log in all_artemether:
        print(f'ID: {log.id}, Status: {log.status}, Quantity: {log.quantity}, Created: {log.created_at}')

if __name__ == '__main__':
    test_return_logic()
