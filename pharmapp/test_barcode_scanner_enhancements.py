#!/usr/bin/env python3
"""
Comprehensive test script for barcode scanner enhancements
Tests online/offline scanning and new item creation via barcode
"""

import os
import django
import uuid
import json
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
# Override ALLOWED_HOSTS for testing
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
django.setup()

from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from store.models import Item, WholesaleItem
from userauth.models import Profile

User = get_user_model()

class BarcodeScannerEnhancementTest(TestCase):
    """Test enhanced barcode scanner functionality"""
    
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
        
        # Create test item with barcode for existing tests
        self.test_item = Item.objects.create(
            name='Test Medication',
            brand='Test Brand',
            dosage_form='Tablet',
            unit='Pcs',
            price=Decimal('10.50'),
            cost=Decimal('8.00'),
            stock=100,
            barcode='680577895232'
        )
        
        self.client = Client()
        # Use mobile for login since that's the USERNAME_FIELD
        self.client.login(mobile=self.user.mobile, password='testpass123')
        
        # Test data for new items
        self.new_item_data = {
            'barcode': '1234567890123',
            'name': 'New Test Medication',
            'brand': 'New Test Brand',
            'dosage_form': 'Capsule',
            'unit': 'Caps',
            'cost': '15.00',
            'price': '20.00',
            'stock': 50,
            'exp_date': '2024-12-31',
            'barcode_type': 'UPC',
            'mode': 'retail'
        }
    
    def tearDown(self):
        """Clean up test data"""
        Item.objects.filter(user=self.user).delete()
        WholesaleItem.objects.filter(user=self.user).delete()
        self.profile.delete()
        self.user.delete()
    
    def test_barcode_lookup_existing_item(self):
        """Test looking up existing item by barcode"""
        response = self.client.post(
            reverse('api:barcode_lookup'),
            data=json.dumps({
                'barcode': '680577895232',
                'mode': 'retail'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['item']['name'], 'Test Medication')
        self.assertEqual(result['item']['barcode'], '680577895232')
    
    def test_barcode_lookup_nonexistent_item(self):
        """Test looking up non-existent item"""
        response = self.client.post(
            reverse('api:barcode_lookup'),
            data=json.dumps({
                'barcode': '999999999999',
                'mode': 'retail'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        result = response.json()
        self.assertEqual(result['status'], 'error')
        self.assertIn('Item not found', result['user_message'])
    
    def test_add_new_item_via_barcode(self):
        """Test adding new item via barcode API"""
        response = self.client.post(
            reverse('api:barcode_add_item'),
            data=json.dumps(self.new_item_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertIn('New retail item created successfully', result['message'])
        
        # Verify item was created in database
        created_item = Item.objects.get(barcode='1234567890123')
        self.assertEqual(created_item.name, 'New Test Medication')
        self.assertEqual(created_item.cost, Decimal('15.00'))
        self.assertEqual(created_item.stock, 50)
    
    def test_add_duplicate_barcode_fails(self):
        """Test that adding item with existing barcode fails"""
        duplicate_data = self.new_item_data.copy()
        duplicate_data['barcode'] = '680577895232'  # Existing barcode
        
        response = self.client.post(
            reverse('api:barcode_add_item'),
            data=json.dumps(duplicate_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 409)
        result = response.json()
        self.assertEqual(result['status'], 'error')
        self.assertIn('already assigned', result['user_message'])
    
    def test_add_item_missing_required_fields(self):
        """Test validation for missing required fields"""
        incomplete_data = {
            'barcode': '1234567890124',
            'name': 'Incomplete Item',
            # Missing cost and stock
            'mode': 'retail'
        }
        
        response = self.client.post(
            reverse('api:barcode_add_item'),
            data=json.dumps(incomplete_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertEqual(result['status'], 'error')
        self.assertIn('Missing required fields', result['user_message'])
    
    def test_batch_add_items(self):
        """Test batch adding multiple items"""
        batch_data = {
            'mode': 'retail',
            'items': [
                {
                    'barcode': '1111111111111',
                    'name': 'Batch Item 1',
                    'cost': '10.00',
                    'stock': 25
                },
                {
                    'barcode': '2222222222222',
                    'name': 'Batch Item 2',
                    'cost': '15.00',
                    'stock': 30
                }
            ]
        }
        
        response = self.client.post(
            reverse('api:barcode_batch_add_items'),
            data=json.dumps(batch_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['created_count'], 2)
        self.assertEqual(result['failed_count'], 0)
        
        # Verify items were created
        self.assertTrue(Item.objects.filter(barcode='1111111111111').exists())
        self.assertTrue(Item.objects.filter(barcode='2222222222222').exists())
    
    def test_batch_add_items_with_duplicates(self):
        """Test batch adding with duplicate barcodes in batch"""
        batch_data = {
            'mode': 'retail',
            'items': [
                {
                    'barcode': '3333333333333',
                    'name': 'Duplicate Item 1',
                    'cost': '10.00',
                    'stock': 25
                },
                {
                    'barcode': '3333333333333',  # Same barcode
                    'name': 'Duplicate Item 2',
                    'cost': '15.00',
                    'stock': 30
                }
            ]
        }
        
        response = self.client.post(
            reverse('api:barcode_batch_add_items'),
            data=json.dumps(batch_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['created_count'], 1)
        self.assertEqual(result['failed_count'], 1)
        self.assertIn('Duplicate barcode in this batch', result['failed_items'][0]['error'])
    
    def test_wholesale_barcode_lookup(self):
        """Test wholesale barcode lookup"""
        # Create wholesale item
        wholesale_item = WholesaleItem.objects.create(
            name='Wholesale Test Item',
            barcode='WHOLESALE123',
            price=Decimal('100.00'),
            cost=Decimal('80.00'),
            stock=200
        )
        
        response = self.client.post(
            reverse('api:barcode_lookup'),
            data=json.dumps({
                'barcode': 'WHOLESALE123',
                'mode': 'wholesale'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['item']['name'], 'Wholesale Test Item')
        
        wholesale_item.delete()
    
    def test_wholesale_add_item_via_barcode(self):
        """Test adding wholesale item via barcode"""
        wholesale_data = self.new_item_data.copy()
        wholesale_data['mode'] = 'wholesale'
        wholesale_data['barcode'] = 'WHOLESALENEW123'
        
        response = self.client.post(
            reverse('api:barcode_add_item'),
            data=json.dumps(wholesale_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertIn('New wholesale item created successfully', result['message'])
        
        # Verify wholesale item was created
        created_item = WholesaleItem.objects.get(barcode='WHOLESALENEW123')
        self.assertEqual(created_item.name, 'New Test Medication')
    
    def test_inventory_sync_create_item(self):
        """Test inventory sync for creating items"""
        sync_data = {
            'pendingActions': [
                {
                    'actionType': 'create_item',
                    'data': {
                        'barcode': 'SYNC123456',
                        'name': 'Sync Created Item',
                        'cost': '12.50',
                        'stock': 75,
                        'mode': 'retail'
                    }
                }
            ]
        }
        
        response = self.client.post(
            reverse('api:inventory_sync'),
            data=json.dumps(sync_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['synced_count'], 1)
        
        # Verify item was created
        created_item = Item.objects.get(barcode='SYNC123456')
        self.assertEqual(created_item.name, 'Sync Created Item')
    
    def test_inventory_sync_lookup_when_online(self):
        """Test inventory sync for queued barcode lookups"""
        sync_data = {
            'pendingActions': [
                {
                    'actionType': 'lookup_when_online',
                    'data': {
                        'barcode': '680577895232',  # Existing barcode
                        'mode': 'retail'
                    }
                }
            ]
        }
        
        response = self.client.post(
            reverse('api:inventory_sync'),
            data=json.dumps(sync_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['synced_count'], 1)
    
    def test_barcode_qr_code_support(self):
        """Test QR code format support"""
        # Create item with QR code
        qr_item = Item.objects.create(
            name='QR Test Item',
            barcode='PHARM-RETAIL-999',
            barcode_type='QR',
            price=Decimal('25.00'),
            cost=Decimal('20.00'),
            stock=40
        )
        
        response = self.client.post(
            reverse('api:barcode_lookup'),
            data=json.dumps({
                'barcode': 'PHARM-RETAIL-999',
                'mode': 'retail'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['item']['name'], 'QR Test Item')
        self.assertEqual(result['item']['barcode_type'], 'QR')
        
        qr_item.delete()
    
    def test_invalid_json_requests(self):
        """Test handling of invalid JSON requests"""
        # Test invalid JSON for lookup
        response = self.client.post(
            reverse('api:barcode_lookup'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test invalid JSON for add item
        response = self.client.post(
            reverse('api:barcode_add_item'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_decimal_field_validation(self):
        """Test decimal field validation in API"""
        invalid_decimal_data = self.new_item_data.copy()
        invalid_decimal_data['cost'] = 'invalid_decimal'
        invalid_decimal_data['barcode'] = 'INVALIDDEC123'
        
        response = self.client.post(
            reverse('api:barcode_add_item'),
            data=json.dumps(invalid_decimal_data),
            content_type='application/json'
        )
        
        # Should still succeed but Django will handle the validation
        self.assertEqual(response.status_code, 200)
        
        # Verify the item was created but with 0 cost due to invalid decimal
        created_item = Item.objects.get(barcode='INVALIDDEC123')
        self.assertEqual(created_item.cost, Decimal('0'))


def run_tests():
    """Run all barcode scanner enhancement tests"""
    import unittest
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(BarcodeScannerEnhancementTest)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n{'='*60}")
        print("FAILURES:")
        print(f"{'='*60}")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(f"{'-'*40}")
            print(traceback)
    
    if result.errors:
        print(f"\n{'='*60}")
        print("ERRORS:")
        print(f"{'='*60}")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(f"{'-'*40}")
            print(traceback)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Running Barcode Scanner Enhancement Tests...")
    print(f"{'='*60}")
    success = run_tests()
    
    if success:
        print(f"\n✅ All tests passed! Barcode scanner enhancements are working correctly.")
        exit(0)
    else:
        print(f"\n❌ Some tests failed. Please review the output above.")
        exit(1)
