#!/usr/bin/env python
"""
Simple test to verify GS1 barcode implementation works
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.gs1_parser import parse_barcode
from store.models import Item

def test_api():
    """Test the API with user's barcode"""
    import requests
    import json
    
    # Test data
    test_barcode = 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'
    
    # Test API endpoint
    data = {
        'barcode': test_barcode,
        'mode': 'retail'
    }
    
    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/barcode/lookup/',
            json=data,
            headers={'X-CSRFToken': 'test-token'}  # We'll need to get this properly
        )
        
        print("API Test Results:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # Check if GS1 was detected
            if result.get('lookup_type') == 'gs1_barcode':
                print("✅ GS1 barcode was correctly detected!")
                print(f"GTIN found: {result.get('item', {}).get('gtin', 'N/A')}")
                print(f"Batch: {result.get('item', {}).get('batch_number', 'N/A')}")
                
        else:
            print("❌ Failed or not a GS1 barcode")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_parser():
    """Test GS1 parser directly"""
    print("\n=== Testing GS1 Parser ===")
    
    test_barcode = 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'
    
    try:
        parsed = parse_barcode(test_barcode)
        
        print(f"✅ Parser Test Results:")
        print(f"Original: {parsed['original_barcode']}")
        print(f"Product Name: {parsed.get('product_name')}")
        print(f"GTIN: {parsed.get('gtin')}")
        print(f"Batch Number: {parsed.get('batch_number')}")
        print(f"Expiry Date: {parsed.get('expiry_date')}")
        print(f"Serial Number: {parsed.get('serial_number')}")
        print(f"Is GS1 Format: {parsed.get('is_gs1_format')}")
        print(f"Confidence: {parsed.get('confidence')}")
        
    except Exception as e:
        print(f"❌ Parser Error: {e}")

def main():
    print("PharmApp Barcode Scanner Enhancement Test")
    print("=" * 50)
    
    test_parser()
    print()
    test_api()
    print("=" * 50)

if __name__ == "__main__":
    main()
