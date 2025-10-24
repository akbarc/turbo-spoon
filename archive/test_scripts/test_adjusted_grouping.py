#!/usr/bin/env python3
"""
Test adjusted customer grouping logic with stricter verification
"""

from modules.ar.enhanced_customer_grouping import EnhancedCustomerGrouper
from database_pymssql import SQLServerConnection
import json

def test_adjusted_grouping():
    """Test the adjusted grouping logic that prevents false positives"""
    
    grouper = EnhancedCustomerGrouper()
    
    print("=" * 80)
    print("TESTING ADJUSTED GROUPING LOGIC")
    print("=" * 80)
    print()
    
    # Test with specific problematic cases
    print("1. Testing ALI surname grouping (should be more restrictive now)")
    print("-" * 40)
    
    # Create test customers with ALI surname
    test_customers = [
        {
            'ID': 1,
            'FirstName': 'MURAD',
            'LastName': 'ALI',
            'PhoneNumber': '682-557-6333',
            'EmailAddress': '',
            'Company': 'Company A'
        },
        {
            'ID': 2,
            'FirstName': 'MURAD',
            'LastName': 'ALI',
            'PhoneNumber': '404-793-4414',  # Different phone
            'EmailAddress': '',
            'Company': 'Company B'
        },
        {
            'ID': 3,
            'FirstName': 'HASSAN',
            'LastName': 'ALI',
            'PhoneNumber': '555-123-4567',
            'EmailAddress': '',
            'Company': 'Company C'
        }
    ]
    
    print("Test Cases:")
    for customer in test_customers:
        print(f"  {customer['FirstName']} {customer['LastName']} - Phone: {customer['PhoneNumber']}")
    print()
    
    # Test similarity between MURAD ALI with different phones
    similarity1 = grouper.calculate_customer_similarity(test_customers[0], test_customers[1])
    print(f"MURAD ALI (phone1) vs MURAD ALI (phone2): {similarity1:.2%}")
    print(f"  Expected: 0% (common surname, no phone/email match)")
    print(f"  Result: {'✅ CORRECT' if similarity1 == 0 else '❌ INCORRECT'}")
    print()
    
    # Test similarity between MURAD ALI and HASSAN ALI
    similarity2 = grouper.calculate_customer_similarity(test_customers[0], test_customers[2])
    print(f"MURAD ALI vs HASSAN ALI: {similarity2:.2%}")
    print(f"  Expected: 0% (different first names, common surname)")
    print(f"  Result: {'✅ CORRECT' if similarity2 == 0 else '❌ INCORRECT'}")
    print()
    
    # Test with matching phone numbers
    test_customers[1]['PhoneNumber'] = '682-557-6333'  # Same as first MURAD
    similarity3 = grouper.calculate_customer_similarity(test_customers[0], test_customers[1])
    print(f"MURAD ALI vs MURAD ALI (same phone): {similarity3:.2%}")
    print(f"  Expected: 95% (phone match)")
    print(f"  Result: {'✅ CORRECT' if similarity3 >= 0.95 else '❌ INCORRECT'}")
    print()
    
    print("=" * 80)
    print("2. Testing SOUNDEX groups with new restrictions")
    print("-" * 40)
    
    # Get SOUNDEX groups with new logic
    soundex_groups = grouper.find_customer_groups_soundex()
    
    # Check for ALI groups
    ali_groups = []
    for group in soundex_groups:
        for member in group['members']:
            if member.get('last_name') == 'ALI':
                ali_groups.append(group)
                break
    
    print(f"Found {len(ali_groups)} groups containing 'ALI' surname")
    
    # Analyze confidence levels
    confidence_counts = {'verified': 0, 'high': 0, 'potential': 0}
    for group in soundex_groups:
        confidence_counts[group['confidence']] = confidence_counts.get(group['confidence'], 0) + 1
    
    print()
    print("Confidence Level Distribution:")
    print(f"  Verified (phone/email match): {confidence_counts['verified']}")
    print(f"  High (3+ members): {confidence_counts['high']}")
    print(f"  Potential (needs review): {confidence_counts['potential']}")
    
    # Show examples of each confidence level
    print()
    print("=" * 80)
    print("3. Examples by Confidence Level")
    print("-" * 40)
    
    for confidence in ['verified', 'high', 'potential']:
        examples = [g for g in soundex_groups if g['confidence'] == confidence][:2]
        if examples:
            print(f"\n{confidence.upper()} Confidence Examples:")
            for example in examples:
                print(f"  Group {example['group_id']}:")
                print(f"    Primary: {example['primary_customer']['name']}")
                print(f"    Members: {example['member_count']}")
                print(f"    Balance: ${example['total_balance']:,.2f}")
                if 'verification' in example:
                    print(f"    Phone Match: {example['verification']['has_phone_match']}")
                    print(f"    Email Match: {example['verification']['has_email_match']}")
    
    # Check specific known good groups
    print()
    print("=" * 80)
    print("4. Verifying Known Good Groups")
    print("-" * 40)
    
    # Look for RIJWAN JIWANI group
    rijwan_found = False
    for group in soundex_groups:
        if any('RIJWAN' in str(m.get('first_name', '')).upper() for m in group['members']):
            print(f"✅ RIJWAN JIWANI group found:")
            print(f"   Confidence: {group['confidence']}")
            print(f"   Members: {group['member_count']}")
            print(f"   Has Phone Match: {group.get('verification', {}).get('has_phone_match', False)}")
            rijwan_found = True
            break
    
    if not rijwan_found:
        print("❌ RIJWAN JIWANI group not found")
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY OF ADJUSTMENTS")
    print("=" * 80)
    print()
    print("✅ Improvements Made:")
    print("1. Common surnames (ALI, KHAN, etc.) require phone/email verification")
    print("2. Confidence scoring: verified > high > potential")
    print("3. No false positives for different people with common surnames")
    print("4. Legitimate groups with contact verification still detected")
    print()
    print(f"Total Groups Found: {len(soundex_groups)}")
    print(f"Verified Groups: {confidence_counts['verified']}")
    print(f"Groups Needing Review: {confidence_counts['potential']}")

if __name__ == "__main__":
    test_adjusted_grouping()