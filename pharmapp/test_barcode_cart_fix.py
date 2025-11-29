#!/usr/bin/env python3
"""
Test script to verify barcode scanner automatically adds items to cart in dispensing
"""

import os
import django
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
# Override ALLOWED_HOSTS for testing
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
django.setup()

from django.test import Client, TestCase
from django.urls import reverse
from store.models import Item, Cart
from userauth.models import User, Profile

class BarcodeScannerTest(TestCase):
    """Test barcode scanner functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Generate unique mobile number
        unique_mobile = f'test{uuid.uuid4().hex[:8]}'
        
        # Create test user with proper profile
        self.user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4().hex[:8]}',
            email=f'test_{uuid.uuid4().hex[:8]}@example.com',
            password='testpass123',
            mobile=unique_mobile
        )
        # Create profile with required fields
        self.profile, created = Profile.objects.get_or_create(
            user=self.user,
            defaults={'user_type': 'Pharmacist'}
        )
        
        # Create test item with barcode
        self.test_item = Item.objects.create(
            name='Test Medication',
            brand='Test Brand',
            dosage_form='Tablet',
            unit='Pcs',
            price=10.50,
            stock=100,
            barcode='680577895232'  # Using the barcode from the log
        )
        
        self.client = Client()
        # Use mobile for login since that's the USERNAME_FIELD
        self.client.login(mobile=self.user.mobile, password='testpass123')
    
    def tearDown(self):
        """Clean up test data"""
        Cart.objects.filter(user=self.user).delete()
        self.test_item.delete()
        self.profile.delete()  # Delete profile first (OneToOne relationship)
        self.user.delete()
    
    def test_dispense_page_loads(self):
        """Test that dispense page loads successfully"""
        response = self.client.get(reverse('store:dispense'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Scan')
        self.assertContains(response, 'barcode')
    
    def test_search_item_by_barcode(self):
        """Test searching for item by barcode"""
        response = self.client.get(
            reverse('store:dispense_search_items'),
            {'q': '680577895232'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Medication')
        self.assertContains(response, 'Test Brand')
    
    def test_search_item_by_name(self):
        """Test searching for item by name"""
        response = self.client.get(
            reverse('store:dispense_search_items'),
            {'q': 'Test Medication'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Medication')
        self.assertContains(response, 'add-to-cart-form')
    
    def test_add_to_cart_from_dispense(self):
        """Test adding item to cart from dispense page"""
        # Initial cart should be empty
        self.assertEqual(Cart.objects.filter(user=self.user, status='active').count(), 0)
        
        # Add item to cart
        response = self.client.post(
            reverse('store:add_to_cart', args=[self.test_item.id]),
            {
                'quantity': 5,
                'unit': 'Pcs',
                'from_dispense': 'true'
            }
        )
        
        # Verify item was added to cart
        cart_items = Cart.objects.filter(user=self.user, status='active')
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().item, self.test_item)
        self.assertEqual(cart_items.first().quantity, 5)
    
    def test_cart_summary_widget_update(self):
        """Test that cart summary widget is updated when adding from dispense"""
        # Add item to cart with HTMX headers
        response = self.client.post(
            reverse('store:add_to_cart', args=[self.test_item.id]),
            {
                'quantity': 3,
                'unit': 'Pcs',
                'from_dispense': 'true'
            },
            HTTP_HX_REQUEST='true'
        )
        
        # Verify the response contains cart summary data
        self.assertEqual(response.status_code, 200)
        # Check for cart summary elements (not necessarily with specific variable names)
        self.assertContains(response, 'item in cart')
        self.assertContains(response, 'Total:')
    
    def test_barcode_not_found(self):
        """Test behavior when barcode is not found"""
        response = self.client.get(
            reverse('store:dispense_search_items'),
            {'q': '999999999999'}  # Non-existent barcode
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'add-to-cart-form')
        self.assertContains(response, 'No items found')

def run_manual_test_instructions():
    """Print manual testing instructions"""
    print("""
🧪 MANUAL TESTING INSTRUCTIONS FOR BARCODE SCANNER FIX
=====================================================

1. Start the server:
   python manage.py runserver

2. Login to the system:
   http://127.0.0.1:8000

3. Navigate to dispensing:
   http://127.0.0.1:8000/dispense/

4. Open browser console (F12) to watch logs

5. Click the "Scan" button next to search

6. Click "Start Camera" and allow camera permission

7. Scan a barcode for an item in your database

8. EXPECTED BEHAVIOR AFTER FIX:
   ✅ Barcode is scanned
   ✅ Search input is filled with item name
   ✅ Search results appear automatically
   ✅ Add to Cart button is clicked automatically
   ✅ Item is added to cart without manual interaction
   ✅ Cart summary widget updates
   ✅ Success notification appears

9. Console should show:
   [Barcode Scanner] Scanned: [barcode]
   [Dispense] Search input filled with: [item name]
   [Dispense] HTMX search triggered
   [Dispense] Found add-to-cart form for item: [item name]
   [Dispense] Submitting add-to-cart form...

10. Check the cart summary widget to confirm item was added

If any step fails, check the console for error messages.
""")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--manual':
        run_manual_test_instructions()
    else:
        # Run automated tests
        import unittest
        unittest.main(argv=[''], exit=False, verbosity=2)
