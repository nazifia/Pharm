#!/usr/bin/env python3
"""
Test script for the new dynamic dispensing functionality
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.models import Item, Cart

class TestDynamicDispensing(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create test items
        self.item1 = Item.objects.create(
            name='Paracetamol',
            brand='Test Brand',
            dosage_form='Tablet',
            unit='Tab',
            price=50.00,
            stock=100
        )
        
        self.item2 = Item.objects.create(
            name='Amoxicillin',
            brand='Another Brand',
            dosage_form='Capsule',
            unit='Caps',
            price=75.00,
            stock=50
        )
        
        # Login the user
        self.client.login(username='testuser', password='testpass123')
    
    def test_dispense_page_loads(self):
        """Test that the dispense page loads correctly"""
        response = self.client.get(reverse('store:dispense'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dispense Items')
        self.assertContains(response, 'cart-summary-widget')
    
    def test_dynamic_search_endpoint(self):
        """Test the new dynamic search endpoint"""
        response = self.client.get(
            reverse('store:dispense_search_items'),
            {'q': 'para'},
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paracetamol')
    
    def test_add_to_cart_with_htmx(self):
        """Test adding items to cart via HTMX"""
        response = self.client.post(
            reverse('store:add_to_cart', args=[self.item1.id]),
            {
                'quantity': 2,
                'unit': 'Tab',
                'from_dispense': 'true'
            },
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that item was added to cart
        cart_item = Cart.objects.filter(user=self.user, item=self.item1).first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 2)
    
    def test_cart_summary_update(self):
        """Test that cart summary updates correctly"""
        # Add item to cart first
        Cart.objects.create(
            user=self.user,
            item=self.item1,
            quantity=3,
            price=self.item1.price,
            unit='Tab'
        )
        
        # Get dispense page
        response = self.client.get(reverse('store:dispense'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3 items in cart')

def run_tests():
    """Run the tests"""
    print("Running Dynamic Dispensing Tests...")
    
    # Import Django test runner
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run specific test
    failures = test_runner.run_tests(['__main__.TestDynamicDispensing'])
    
    if failures:
        print(f"❌ {failures} test(s) failed")
        return False
    else:
        print("✅ All tests passed!")
        return True

if __name__ == '__main__':
    run_tests()
