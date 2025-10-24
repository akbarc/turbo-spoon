#!/usr/bin/env python3
"""
Test script for Enhanced Customer Grouping with Fuzzy Name Matching
"""

from modules.ar.enhanced_customer_grouping import EnhancedCustomerGrouper
import json

def test_fuzzy_matching():
    """Test the fuzzy name matching capabilities"""
    
    grouper = EnhancedCustomerGrouper()
    
    # Test cases for fuzzy name matching
    test_cases = [
        # Exact match
        ("John", "Smith", "John", "Smith", "Exact match"),
        
        # Nickname variations
        ("Robert", "Johnson", "Bob", "Johnson", "Nickname match (Robert/Bob)"),
        ("William", "Brown", "Bill", "Brown", "Nickname match (William/Bill)"),
        ("Michael", "Davis", "Mike", "Davis", "Nickname match (Michael/Mike)"),
        
        # Swapped names
        ("Smith", "John", "John", "Smith", "Swapped first/last names"),
        
        # Initial matching
        ("J", "Smith", "John", "Smith", "Initial match"),
        ("John", "Smith", "J", "Smith", "Initial match reverse"),
        
        # Similar names
        ("Jon", "Smith", "John", "Smith", "Similar spelling"),
        ("Smith", "Jr", "Smith", "Sr", "Family variation"),
        
        # No match cases
        ("John", "Smith", "Jane", "Doe", "No match - different names"),
    ]
    
    print("=" * 80)
    print("ENHANCED FUZZY NAME MATCHING TEST")
    print("=" * 80)
    print()
    
    for first1, last1, first2, last2, description in test_cases:
        score = grouper.fuzzy_name_match(first1, last1, first2, last2)
        
        print(f"Test: {description}")
        print(f"  Name 1: {first1} {last1}")
        print(f"  Name 2: {first2} {last2}")
        print(f"  Match Score: {score:.2%}")
        
        if score >= 0.75:
            print(f"  ✅ MATCH FOUND (threshold: 75%)")
        else:
            print(f"  ❌ No match (below threshold)")
        print()
    
    print("=" * 80)
    print("TESTING CUSTOMER SIMILARITY CALCULATION")
    print("=" * 80)
    print()
    
    # Test customer similarity with full records
    customer1 = {
        'FirstName': 'Robert',
        'LastName': 'Johnson',
        'PhoneNumber': '(555) 123-4567',
        'EmailAddress': 'robert.johnson@email.com',
        'Company': 'Johnson Industries',
        'Address': '123 Main St'
    }
    
    customer2 = {
        'FirstName': 'Bob',
        'LastName': 'Johnson',
        'PhoneNumber': '555-123-4567',  # Same phone, different format
        'EmailAddress': 'bob.j@email.com',
        'Company': 'Johnson Ind',
        'Address': '123 Main Street'
    }
    
    similarity = grouper.calculate_customer_similarity(customer1, customer2)
    
    print("Customer 1:")
    print(json.dumps(customer1, indent=2))
    print()
    print("Customer 2:")
    print(json.dumps(customer2, indent=2))
    print()
    print(f"Overall Similarity Score: {similarity:.2%}")
    
    if similarity >= 0.75:
        print("✅ These customers would be grouped together")
    else:
        print("❌ These customers would NOT be grouped together")
    
    print()
    print("=" * 80)
    print("FINDING CUSTOMER GROUPS IN DATABASE")
    print("=" * 80)
    print()
    
    try:
        groups = grouper.find_customer_groups(min_similarity=0.75)
        
        if groups:
            print(f"Found {len(groups)} customer groups:")
            print()
            
            for i, group in enumerate(groups[:5], 1):  # Show first 5 groups
                print(f"Group {i}: {group['group_id']}")
                print(f"  Primary: {group['primary_customer']['name']}")
                print(f"  Members: {group['member_count']}")
                print(f"  Total Balance: ${group['total_balance']:,.2f}")
                print(f"  Confidence: {group['confidence']}")
                
                # Show member details
                for member in group['members'][:3]:  # Show first 3 members
                    print(f"    - {member['name']} (Balance: ${member['balance']:,.2f})")
                
                if len(group['members']) > 3:
                    print(f"    ... and {len(group['members']) - 3} more")
                print()
        else:
            print("No customer groups found in the database")
    except Exception as e:
        print(f"Error accessing database: {e}")
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_fuzzy_matching()