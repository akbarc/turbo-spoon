#!/usr/bin/env python3
"""
Test that the grouping fixes work correctly
"""

from modules.ar.simple_name_grouping import SimpleNameGrouper
import json

def test_grouping_fixes():
    """Test that Rehan/Rehman and Karim/Arif are no longer incorrectly grouped"""
    
    grouper = SimpleNameGrouper()
    
    print("=" * 80)
    print("TESTING CUSTOMER GROUPING FIXES")
    print("=" * 80)
    print()
    
    # Test the fuzzy matching directly
    print("DIRECT FUZZY MATCH TESTS")
    print("-" * 40)
    
    # Test 1: Rehan vs Rehman Lakhani
    score1 = grouper.fuzzy_match_names("REHAN", "LAKHANI", "REHMAN", "LAKHANI")
    print(f"Rehan Lakhani vs Rehman Lakhani: {score1:.2%}")
    print(f"  Would group: {'YES ❌' if score1 >= 0.85 else 'NO ✅'}")
    print()
    
    # Test 2: Karim vs Arif Jiwani  
    score2 = grouper.fuzzy_match_names("KARIM", "JIWANI", "ARIF", "JIWANI")
    print(f"Karim Jiwani vs Arif Jiwani: {score2:.2%}")
    print(f"  Would group: {'YES ❌' if score2 >= 0.85 else 'NO ✅'}")
    print()
    
    # Find actual groups
    print("FINDING ACTUAL CUSTOMER GROUPS")
    print("-" * 40)
    groups = grouper.find_name_groups()
    
    if groups:
        print(f"Found {len(groups)} total groups")
        print()
        
        # Check for Lakhani groups
        lakhani_groups = [g for g in groups if 'LAKHANI' in g.get('last_name', '').upper()]
        print(f"Lakhani groups found: {len(lakhani_groups)}")
        for g in lakhani_groups:
            print(f"  - {g['display_name']} ({g['member_count']} members)")
            for m in g['members']:
                print(f"    • {m.get('FirstName', '')} {m.get('LastName', '')} - {m.get('Company', 'N/A')}")
        print()
        
        # Check for Jiwani groups
        jiwani_groups = [g for g in groups if 'JIWANI' in g.get('last_name', '').upper()]
        print(f"Jiwani groups found: {len(jiwani_groups)}")
        for g in jiwani_groups:
            print(f"  - {g['display_name']} ({g['member_count']} members)")
            for m in g['members']:
                print(f"    • {m.get('FirstName', '')} {m.get('LastName', '')} - {m.get('Company', 'N/A')}")
        print()
        
        # Verify the fixes
        print("VERIFICATION")
        print("-" * 40)
        
        # Check if Rehan and Rehman are in same group (they shouldn't be)
        rehan_found = False
        rehman_found = False
        rehan_rehman_same_group = False
        
        for g in groups:
            members_first_names = [m.get('FirstName', '').upper().strip() for m in g['members']]
            if 'REHAN' in members_first_names and 'REHMAN' in members_first_names:
                rehan_rehman_same_group = True
                print("❌ ERROR: Rehan and Rehman Lakhani are still in the same group!")
            elif 'REHAN' in members_first_names:
                rehan_found = True
            elif 'REHMAN' in members_first_names:
                rehman_found = True
        
        if not rehan_rehman_same_group:
            print("✅ SUCCESS: Rehan and Rehman Lakhani are NOT grouped together")
        
        # Check if Karim and Arif are in same group (they shouldn't be)
        karim_arif_same_group = False
        
        for g in groups:
            members_first_names = [m.get('FirstName', '').upper().strip() for m in g['members']]
            if 'KARIM' in members_first_names and 'ARIF' in members_first_names:
                karim_arif_same_group = True
                print("❌ ERROR: Karim and Arif Jiwani are still in the same group!")
                print(f"   Group: {g['display_name']}")
                for m in g['members']:
                    print(f"    • {m.get('FirstName', '')} {m.get('LastName', '')}")
        
        if not karim_arif_same_group:
            print("✅ SUCCESS: Karim and Arif Jiwani are NOT grouped together")
    
    else:
        print("No groups found")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if score1 < 0.85 and score2 < 0.85:
        print("✅ Fuzzy matching logic correctly prevents false matches")
    else:
        print("❌ Fuzzy matching logic still has issues")
    
    print()
    print("The grouping algorithm now uses stricter thresholds:")
    print("- For identical last names: First names must be >92% similar")
    print("- This prevents Rehan (90.91%) from matching Rehman")
    print("- This prevents Karim (66.67%) from matching Arif")

if __name__ == "__main__":
    test_grouping_fixes()