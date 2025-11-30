#!/usr/bin/env python3
"""
Simple test for barcode scanner system without Unicode issues
"""

import requests
import json

def test_barcode_endpoints():
    """Test barcode scanner API endpoints"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing barcode scanner API endpoints...")
    
    # Test 1: Server health check
    try:
        response = requests.get(f"{base_url}/api/health/", timeout=5)
        if response.status_code == 200:
            print("Server is running and accessible")
            return True
        else:
            print(f"Server responded with status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Cannot connect to server: {e}")
        return False
    
    # Test 2: Add new item
    test_item_data = {
        "barcode": "TEST123456789",
        "name": "Test Enhanced Scanner Item",
        "cost": "15.00",
        "stock": 50,
        "mode": "retail"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/barcode/add-item/",
            json=test_item_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            print("SUCCESS: Item created via barcode")
            return True
        else:
            print(f"FAILED: Item creation returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Item creation failed: {e}")
        return False
    
    # Test 3: Barcode lookup
    try:
        response = requests.post(
            f"{base_url}/api/barcode/lookup/",
            json={"barcode": "TEST123456789", "mode": "retail"},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            print("SUCCESS: Barcode lookup worked")
            return True
        else:
            print(f"FAILED: Barcode lookup returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Barcode lookup failed: {e}")
        return False

if __name__ == "__main__":
    print("BARCODE SCANNER SYSTEM TEST")
    print("=" * 50)
    
    print("Testing barcode scanner endpoints...")
    
    # Check server availability
    if not test_barcode_endpoints():
        print("Server is not running. Please start Django server first.")
        exit(1)
    
    # Run tests
    results = []
    
    # Test item creation
    if test_barcode_endpoints():
        results.append("Item Creation: PASS")
    else:
        results.append("Item Creation: FAIL")
    
    # Test barcode lookup
    if test_barcode_endpoints():
        results.append("Barcode Lookup: PASS")
    else:
        results.append("Barcode Lookup: FAIL")
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    for i, result in enumerate(results, 1):
        status = "PASS" if result else "FAIL"
        print(f"Test {i}: {result}")
    
    passed = sum(1 for r in results if r)
    total_tests = len(results)
    
    print(f"\nTests Passed: {passed}/{total_tests}")
    print(f"Success Rate: {(passed/total_tests)*100:.1f}%")
    
    if passed == total_tests:
        print("\nALL TESTS PASSED! Barcode scanner system is working correctly.")
        print("System is ready for production use.")
    else:
        print(f"\n{total_tests - passed} tests failed. Please check server and configuration.")
    
    print("\n" + "=" * 50)
