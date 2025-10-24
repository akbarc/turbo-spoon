#!/usr/bin/env python3
"""
Test SOUNDEX phonetic matching for customer grouping
"""

from modules.ar.enhanced_customer_grouping import EnhancedCustomerGrouper
import json

def test_soundex_grouping():
    """Test SOUNDEX phonetic matching"""
    
    grouper = EnhancedCustomerGrouper()
    
    print("=" * 80)
    print("TESTING SOUNDEX PHONETIC MATCHING")
    print("=" * 80)
    print()
    
    # Test SOUNDEX groups
    print("Finding customer groups using SOUNDEX phonetic matching...")
    soundex_groups = grouper.find_customer_groups_soundex()
    
    if soundex_groups:
        print(f"✅ Found {len(soundex_groups)} SOUNDEX groups")
        print()
        
        # Show top 5 groups
        print("Top 5 SOUNDEX Groups by Balance:")
        print("-" * 40)
        
        for i, group in enumerate(soundex_groups[:5], 1):
            print(f"\n{i}. {group['group_id']}")
            print(f"   Primary: {group['primary_customer']['name']}")
            print(f"   Members: {group['member_count']}")
            print(f"   Total Balance: ${group['total_balance']:,.2f}")
            print(f"   Confidence: {group['confidence']}")
            print(f"   Match Type: {group['match_type']}")
            
            # Show member names
            print("   Members:")
            for member in group['members'][:3]:
                print(f"     - {member['first_name']} {member['last_name']} (ID: {member['id']}, Balance: ${member['balance']:,.2f})")
            
            if len(group['members']) > 3:
                print(f"     ... and {len(group['members']) - 3} more")
    else:
        print("❌ No SOUNDEX groups found")
    
    print()
    print("=" * 80)
    print("COMPARING SOUNDEX VS FUZZY MATCHING")
    print("=" * 80)
    print()
    
    comparison = grouper.compare_matching_methods()
    
    if 'error' not in comparison:
        print("Method Comparison Results:")
        print(f"  SOUNDEX Groups: {comparison['soundex_groups_count']}")
        print(f"  Fuzzy Groups: {comparison['fuzzy_groups_count']}")
        print(f"  SOUNDEX Total Balance: ${comparison['soundex_total_balance']:,.2f}")
        print(f"  Fuzzy Total Balance: ${comparison['fuzzy_total_balance']:,.2f}")
        print()
        print(f"Customer Pair Matches:")
        print(f"  SOUNDEX pairs: {comparison['soundex_total_pairs']}")
        print(f"  Fuzzy pairs: {comparison['fuzzy_total_pairs']}")
        print(f"  Pairs found by both: {comparison['pairs_in_both']}")
        print(f"  Unique to SOUNDEX: {comparison['pairs_only_soundex']}")
        print(f"  Unique to Fuzzy: {comparison['pairs_only_fuzzy']}")
        
        if comparison['examples']['soundex_only']:
            print()
            print("Examples of pairs found ONLY by SOUNDEX:")
            for pair in comparison['examples']['soundex_only']:
                print(f"  - Customer {pair[0]} & {pair[1]}")
        
        if comparison['examples']['fuzzy_only']:
            print()
            print("Examples of pairs found ONLY by Fuzzy matching:")
            for pair in comparison['examples']['fuzzy_only']:
                print(f"  - Customer {pair[0]} & {pair[1]}")
    else:
        print(f"Error in comparison: {comparison['error']}")
    
    print()
    print("=" * 80)
    print("SPECIFIC EXAMPLES FROM YOUR DATA")
    print("=" * 80)
    print()
    
    # Test specific names from the provided data
    test_names = [
        ("AMIT", "BUDHWANI"),
        ("AMAN", "JIWANI"),
        ("MALIK", "KHERANI"),
        ("CHAND", "SHAIKH"),
        ("BARKAT", "DINANI")
    ]
    
    print("Looking for specific customer groups from your data...")
    
    for first_name, last_name in test_names:
        # Search in SOUNDEX groups
        found = False
        for group in soundex_groups:
            for member in group['members']:
                if (member['first_name'] and first_name.lower() in member['first_name'].lower() and
                    member['last_name'] and last_name.lower() in member['last_name'].lower()):
                    print(f"\n✅ Found {first_name} {last_name} in group {group['group_id']}")
                    print(f"   Group has {group['member_count']} members")
                    print(f"   Member IDs: {', '.join(str(m['id']) for m in group['members'])}")
                    found = True
                    break
            if found:
                break
        
        if not found:
            print(f"\n❌ {first_name} {last_name} not found in any SOUNDEX group")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_soundex_grouping()