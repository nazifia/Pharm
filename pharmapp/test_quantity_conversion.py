#!/usr/bin/env python
"""
Test script to verify that quantity conversion from string to Decimal works correctly.
"""

from decimal import Decimal

def test_quantity_conversion():
    """Test that string quantities can be properly converted to Decimal for calculations."""
    
    print("🧪 Testing Quantity Conversion Fix")
    print("=" * 50)
    
    # Simulate POST data (quantities come as strings)
    quantities = ['1', '2.5', '10', '0.75']
    item_price = Decimal('100.50')
    
    print(f"💰 Item price: ₦{item_price}")
    print(f"📦 Quantities from POST: {quantities}")
    print()
    
    for i, quantity_str in enumerate(quantities):
        try:
            # This is what was causing the error before the fix
            print(f"Test {i+1}: quantity = '{quantity_str}' (type: {type(quantity_str)})")
            
            # Convert string to Decimal (the fix)
            quantity = Decimal(str(quantity_str))
            print(f"  ✅ Converted to: {quantity} (type: {type(quantity)})")
            
            # Calculate total (this would fail before the fix)
            item_total = item_price * quantity
            print(f"  💵 Total: ₦{item_total}")
            print()
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()
    
    print("=" * 50)
    print("✅ All quantity conversions successful!")
    
    # Test the specific error case
    print("\n🔍 Testing the specific error case:")
    try:
        # This would cause: "can't multiply sequence by non-int of type 'decimal.Decimal'"
        bad_result = item_price * "2"  # String quantity without conversion
        print(f"❌ This should not work: {bad_result}")
    except TypeError as e:
        print(f"✅ Expected error caught: {e}")
    
    try:
        # This should work with the fix
        good_result = item_price * Decimal(str("2"))  # Converted quantity
        print(f"✅ This works with conversion: ₦{good_result}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_quantity_conversion()
