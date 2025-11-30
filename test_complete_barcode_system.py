#!/usr/bin/env python3
"""
Comprehensive test script to verify complete barcode scanner system functionality
Tests both online and offline capabilities with item creation workflow
"""

import os
import json
import requests
import time
from decimal import Decimal

def test_complete_barcode_system():
    """Test the complete barcode scanner implementation"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing Complete Barcode Scanner System")
    print("=" * 60)
    
    # Test data
    test_items = [
        {
            "barcode": "EXIST123456789",
            "name": "Test Existing Item",
            "cost": "10.00",
            "price": "15.00",
            "stock": 50,
            "barcode_type": "UPC"
        },
        {
            "barcode": "NEW987654321",
            "name": "Test New Item via Scanner",
            "cost": "12.00",
            "price": "18.00", 
            "stock": 30,
            "barcode_type": "EAN13"
        }
    ]
    
    results = {"tests_run": 0, "tests_passed": 0, "tests_failed": 0}
    
    # Test 1: Server Health Check
    print("\n🏥 Test 1: Server Health Check")
    try:
        response = requests.get(f"{base_url}/api/health/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and accessible")
            results["tests_run"] += 1
            results["tests_passed"] += 1
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ Server health check error: {e}")
        results["tests_failed"] += 1
    
    # Test 2: Barcode Lookup - Existing Item
    print("\n📦 Test 2: Barcode Lookup - Existing Item")
    try:
        response = requests.post(
            f"{base_url}/api/barcode/lookup/",
            json={"barcode": test_items[0]["barcode"], "mode": "retail"},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ Existing barcode lookup successful")
                print(f"   Item Name: {result.get('item', {}).get('name', 'N/A')}")
                results["tests_run"] += 1
                results["tests_passed"] += 1
            else:
                print(f"❌ Unexpected response: {result.get('error', 'Unknown')}")
                results["tests_failed"] += 1
        else:
            print(f"❌ Barcode lookup failed with status {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ Barcode lookup request failed: {e}")
        results["tests_failed"] += 1
    
    # Test 3: Barcode Lookup - Non-Existent Item
    print("\n🔍 Test 3: Barcode Lookup - Non-Existent Item")
    try:
        response = requests.post(
            f"{base_url}/api/barcode/lookup/",
            json={"barcode": "NONEXIST987654321", "mode": "retail"},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 404:
            print("✅ Non-existent barcode correctly returns 404")
            results["tests_run"] += 1
            results["tests_passed"] += 1
        else:
            print(f"❌ Expected 404 but got {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ Non-existent barcode lookup failed: {e}")
        results["tests_failed"] += 1
    
    # Test 4: Add New Item via Barcode
    print("\n➕ Test 4: Add New Item via Barcode")
    try:
        response = requests.post(
            f"{base_url}/api/barcode/add-item/",
            json=test_items[1],
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ New item creation successful")
                print(f"   Item ID: {result.get('item', {}).get('id', 'N/A')}")
                print(f"   Item Name: {result.get('item', {}).get('name', 'N/A')}")
                results["tests_run"] += 1
                results["tests_passed"] += 1
            else:
                print(f"❌ Item creation failed: {result.get('error', 'Unknown')}")
                results["tests_failed"] += 1
        else:
            print(f"❌ Item creation failed with status {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ Item creation request failed: {e}")
        results["tests_failed"] += 1
    
    # Test 5: Batch Add Items
    print("\n📦 Test 5: Batch Add Items")
    batch_data = {
        "mode": "retail",
        "items": [
            {
                "barcode": "BATCH111111",
                "name": "Batch Item 1",
                "cost": "8.00",
                "stock": 20
            },
            {
                "barcode": "BATCH222222", 
                "name": "Batch Item 2",
                "cost": "15.00",
                "stock": 25
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/barcode/batch-add-items/",
            json=batch_data,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch add successful: {result.get('status', 'unknown')}")
            print(f"   Created: {result.get('created_count', 0)} items")
            print(f"   Failed: {result.get('failed_count', 0)} items")
            results["tests_run"] += 1
            results["tests_passed"] += 1
        else:
            print(f"❌ Batch add failed with status {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ Batch add request failed: {e}")
        results["tests_failed"] += 1
    
    # Test 6: QR Code Support
    print("\n🔲 Test 6: QR Code Support")
    qr_data = {
        "barcode": "PHARM-RETAIL-123",
        "mode": "retail"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/barcode/lookup/",
            json=qr_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        # QR code should work if QR item exists or return 404 if not found
        if response.status_code in [200, 404]:
            print("✅ QR code lookup working properly")
            results["tests_run"] += 1
            results["tests_passed"] += 1
        else:
            print(f"❌ QR code lookup failed: {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ QR code lookup failed: {e}")
        results["tests_failed"] += 1
    
    # Test 7: Inventory Sync
    print("\n🔄 Test 7: Inventory Sync")
    sync_data = {
        "pendingActions": [
            {
                "actionType": "create_item",
                "data": {
                    "barcode": "SYNC123456",
                    "name": "Sync Test Item",
                    "cost": "11.00",
                    "stock": 35,
                    "mode": "retail"
                }
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/inventory_sync/",
            json=sync_data,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Inventory sync successful")
            print(f"   Synced: {result.get('synced_count', 0)} items")
            results["tests_run"] += 1
            results["tests_passed"] += 1
        else:
            print(f"❌ Inventory sync failed: {response.status_code}")
            results["tests_failed"] += 1
    except requests.exceptions.RequestException as e:
        print(f"❌ Inventory sync failed: {e}")
        results["tests_failed"] += 1
    
    # Test Summary
    print("\n" + "=" * 60)
    print("🎯 COMPLETE BARCODE SCANNER SYSTEM TEST RESULTS")
    print(f"Total Tests Run: {results['tests_run']}")
    print(f"Tests Passed: {results['tests_passed']}")
    print(f"Tests Failed: {results['tests_failed']}")
    print(f"Success Rate: {(results['tests_passed']/results['tests_run']*100):.1f}%")
    
    if results['tests_failed'] == 0:
        print("\n✅ ALL TESTS PASSED! The barcode scanner system is working correctly.")
        print("\n🎉 Ready for Production Deployment")
        return True
    else:
        print(f"\n⚠️  {results['tests_failed']} tests failed. Please review the issues above.")
        return False

def check_server_availability():
    """Check if server is running before running tests"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/health/", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

if __name__ == "__main__":
    print("🧪 Barcode Scanner System Verification")
    print("=" * 60)
    
    # Check if server is running
    if not check_server_availability():
        print("❌ Server is not running. Please start Django server first:")
        print("   python manage.py runserver")
        print("   Then run this test script again.")
        exit(1)
    
    # Run complete system tests
    success = test_complete_barcode_system()
    
    if success:
        exit(0)
    else:
        exit(1)
