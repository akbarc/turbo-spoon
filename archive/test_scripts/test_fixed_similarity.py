#!/usr/bin/env python3
"""
Test the fixed name similarity logic
"""

from difflib import SequenceMatcher

def test_new_logic(first1, last1, first2, last2):
    """Test the new, more strict matching logic"""
    
    # Normalize (simulating normalize_name function)
    first1 = (first1 or '').strip().upper()
    first2 = (first2 or '').strip().upper()
    last1 = (last1 or '').strip().upper()
    last2 = (last2 or '').strip().upper()
    
    # Calculate similarities
    first_sim = 0
    if first1 and first2:
        first_sim = SequenceMatcher(None, first1, first2).ratio()
    
    last_sim = 0
    if last1 and last2:
        last_sim = SequenceMatcher(None, last1, last2).ratio()
    
    # Apply new strict logic
    result = 0.0
    if first1 and first2 and last1 and last2:
        # First names must be at least 92% similar
        # Last names must be at least 95% similar
        if first_sim < 0.92 or last_sim < 0.95:
            result = 0.0
        else:
            # Weight last name more heavily (60/40)
            result = (first_sim * 0.4 + last_sim * 0.6)
    elif last1 and last2:
        # For last name only matching, require 95%
        result = last_sim if last_sim >= 0.95 else 0.0
    elif first1 and first2:
        # For first name only matching, require 92%
        result = first_sim if first_sim >= 0.92 else 0.0
    
    print(f"Comparing: {first1} {last1} vs {first2} {last2}")
    print(f"  First name similarity: {first_sim:.2%}")
    print(f"  Last name similarity: {last_sim:.2%}")
    print(f"  Result score: {result:.2%}")
    print(f"  Would group at 85% threshold: {'YES ✅' if result >= 0.85 else 'NO ❌'}")
    print()
    
    return result >= 0.85

# Test the problematic cases
print("=" * 60)
print("TESTING FIXED NAME MATCHING LOGIC")
print("=" * 60)
print()

print("PREVIOUSLY INCORRECT MATCHES (Should now be NO)")
print("-" * 40)
rehan_rehman = test_new_logic("REHAN", "LAKHANI", "REHMAN", "LAKHANI")
karim_arif = test_new_logic("KARIM", "JIWANI", "ARIF", "JIWANI")

print("VALID MATCHES (Should still be YES)")
print("-" * 40)
# Test exact matches
test_new_logic("JOHN", "SMITH", "JOHN", "SMITH")
# Test with minor variations (typos, spacing)
test_new_logic("MICHAEL", "JOHNSON", "MICHAEL", "JOHNSON")
# Test very similar names that should match
test_new_logic("MOHAMMED", "ALI", "MOHAMMAD", "ALI")

print("EDGE CASES")
print("-" * 40)
# Should NOT match - different people
test_new_logic("JOHN", "SMITH", "JON", "SMITH")
test_new_logic("ROBERT", "WILLIAMS", "BOB", "WILLIAMS")

print("=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print()
if not rehan_rehman and not karim_arif:
    print("✅ SUCCESS: Both problematic groupings are now fixed!")
    print("   - Rehan and Rehman Lakhani will NOT be grouped")
    print("   - Karim and Arif Jiwani will NOT be grouped")
else:
    print("❌ ISSUE: Some problems remain:")
    if rehan_rehman:
        print("   - Rehan/Rehman still matching")
    if karim_arif:
        print("   - Karim/Arif still matching")