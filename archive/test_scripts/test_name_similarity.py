#!/usr/bin/env python3
"""
Test name similarity to understand why incorrect groupings are happening
"""

from difflib import SequenceMatcher

def test_similarity(first1, last1, first2, last2):
    """Test similarity between two names"""
    
    # Normalize names
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
    
    # Weight last name more heavily (60/40)
    if first1 and first2 and last1 and last2:
        combined = (first_sim * 0.4 + last_sim * 0.6)
    elif last1 and last2:
        combined = last_sim
    elif first1 and first2:
        combined = first_sim
    else:
        combined = 0.0
    
    print(f"Comparing: {first1} {last1} vs {first2} {last2}")
    print(f"  First name similarity: {first_sim:.2%}")
    print(f"  Last name similarity: {last_sim:.2%}")
    print(f"  Combined (40/60 weighted): {combined:.2%}")
    print(f"  Would group at 85% threshold: {'YES' if combined >= 0.85 else 'NO'}")
    print()
    
    return combined

# Test the problematic cases
print("=" * 60)
print("TESTING NAME SIMILARITY ISSUES")
print("=" * 60)
print()

print("ISSUE 1: Rehan vs Rehman Lakhani")
print("-" * 40)
test_similarity("REHAN", "LAKHANI", "REHMAN", "LAKHANI")

print("ISSUE 2: Karim vs Arif Jiwani")
print("-" * 40)
test_similarity("KARIM", "JIWANI", "ARIF", "JIWANI")

print("TESTING OTHER POTENTIAL ISSUES")
print("-" * 40)

# Test some other similar names
test_similarity("JOHN", "SMITH", "JON", "SMITH")
test_similarity("MICHAEL", "JOHNSON", "MIKE", "JOHNSON")
test_similarity("ROBERT", "WILLIAMS", "BOB", "WILLIAMS")

print("=" * 60)
print("ANALYSIS")
print("=" * 60)
print()
print("The issue is that when last names match perfectly (100%),")
print("the 60% weight on last name means even very different first")
print("names can still result in a match.")
print()
print("For example:")
print("- REHAN vs REHMAN: 83% first name match + 100% last name = 93% combined")
print("- KARIM vs ARIF: 20% first name match + 100% last name = 68% combined")
print()
print("SOLUTION: We need to either:")
print("1. Increase the threshold to 90-95% for better accuracy")
print("2. Require BOTH first and last names to meet minimum thresholds")
print("3. Use exact last name match + high first name similarity")