#!/usr/bin/env python3
"""Test customer ID patterns from the correct file to understand the algorithm"""

import re

def analyze_customer_id_pattern():
    """Analyze the pattern of customer IDs in the correct file"""
    
    # Sample customer IDs from the correct file
    correct_ids = [
        "124662980", "203930900", "207790800", "209101900", "210569400",
        "232013900", "243571750", "246542900", "252356130", "252622600",
        "429225940", "489878600"  # From SID records we saw
    ]
    
    print("Analyzing Customer ID Patterns from Correct File:")
    print("=" * 60)
    
    for cust_id in correct_ids:
        print(f"\nCustomer ID: {cust_id}")
        print(f"  Length: {len(cust_id)}")
        print(f"  First digit: {cust_id[0]}")
        print(f"  Last digit: {cust_id[-1]}")
        
        # Check if it could be a phone number
        if len(cust_id) == 9:
            # Try different interpretations
            # Could be area code + 6 digits
            possible_phone1 = cust_id[:3] + "-" + cust_id[3:6] + "-" + cust_id[6:]
            print(f"  As phone (3-3-3): {possible_phone1}")
            
            # Could be prefix + 8 digits
            prefix = cust_id[0]
            eight_digits = cust_id[1:]
            print(f"  As prefix+8: {prefix} + {eight_digits}")
            
            # Check if last 7 digits could be a phone
            last_seven = cust_id[-7:]
            print(f"  Last 7 digits: {last_seven}")

def test_new_conversion(phone_number, customer_id=None):
    """Test new customer ID conversion logic"""
    
    if phone_number:
        # Remove all non-digits
        digits = re.sub(r'\D', '', str(phone_number))
        
        # Method 1: Take last 9 digits (no manipulation)
        if len(digits) >= 9:
            method1 = digits[-9:]
        else:
            method1 = digits.ljust(9, '0')
        
        # Method 2: Take last 10, drop first digit
        if len(digits) >= 10:
            method2 = digits[-10:][1:]  # Skip area code first digit
        else:
            method2 = digits.ljust(9, '0')
        
        # Method 3: Original but without '5' prefix
        if len(digits) >= 8:
            eight_digits = digits[-8:]
            if eight_digits[0] == '0':
                eight_digits = eight_digits[1:] + '0'
            method3 = eight_digits + '0'  # Add trailing 0 for 9 digits
        else:
            method3 = digits.ljust(9, '0')
        
        return method1, method2, method3
    elif customer_id:
        # Use customer ID directly, pad to 9 digits
        return str(customer_id).zfill(9), str(customer_id).zfill(9), str(customer_id).zfill(9)
    else:
        return "000000000", "000000000", "000000000"

print("\nTesting different conversion methods:")
print("=" * 60)

# Test with sample phone numbers
test_phones = [
    "4042924899",  # Company phone from HID
    "7705551234",  # Sample
    "4045551234",  # Sample
    "6785551234",  # Sample
    "4042922573",  # Fax number
]

for phone in test_phones:
    m1, m2, m3 = test_new_conversion(phone)
    print(f"\nPhone: {phone}")
    print(f"  Method 1 (last 9): {m1}")
    print(f"  Method 2 (skip 1st): {m2}")
    print(f"  Method 3 (8+0): {m3}")
    
    # Check if any match our target patterns
    if m1[0] in ['2', '4', '6', '7', '8']:
        print(f"  ✓ Method 1 matches pattern (starts with {m1[0]})")
    if m2[0] in ['2', '4', '6', '7', '8']:
        print(f"  ✓ Method 2 matches pattern (starts with {m2[0]})")

analyze_customer_id_pattern()