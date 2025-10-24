#!/usr/bin/env python3
"""
Check if CSV UPCs need to be DOUBLED to match MSA
The BID records show doubled UPCs like: 60924990342600609249903426
"""

import csv
import re

def load_csv_items(filepath):
    """Load items from CSV"""
    items = {}
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                upc = row[0].strip()
                qty = int(row[1])
                items[upc] = qty
    return items

def extract_msa_doubled_upcs(filepath):
    """Extract doubled UPCs from MSA BID records"""
    doubled_upcs = set()
    single_upcs = set()
    
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            if line.startswith('BID'):
                # Skip 'BID  ' (5 chars)
                content = line[5:] if len(line) > 5 else ""
                
                # Find first number sequence (doubled UPC)
                match = re.match(r'^(\d+)', content)
                if match:
                    doubled = match.group(1)
                    doubled_upcs.add(doubled)
                    
                    # If it's even length, check if it's doubled
                    if len(doubled) % 2 == 0:
                        half_len = len(doubled) // 2
                        first_half = doubled[:half_len]
                        second_half = doubled[half_len:]
                        
                        if first_half == second_half:
                            single_upcs.add(first_half)
                        else:
                            # Not actually doubled, might be a long UPC
                            single_upcs.add(doubled)
    
    return doubled_upcs, single_upcs

def check_doubling_pattern():
    """Check if CSV UPCs match MSA when doubled"""
    
    print("="*70)
    print("CHECKING DOUBLED UPC PATTERN")
    print("="*70)
    
    # Load CSV items
    csv_items = load_csv_items('Items- 06202025.csv')
    print(f"\nCSV items: {len(csv_items)}")
    
    # Extract MSA UPCs
    msa_doubled, msa_single = extract_msa_doubled_upcs('MSA Data Fr/06202025')
    print(f"\nMSA doubled UPCs: {len(msa_doubled)}")
    print(f"MSA single UPCs: {len(msa_single)}")
    
    # Try matching with different patterns
    matched = []
    unmatched = []
    
    for csv_upc, qty in csv_items.items():
        found = False
        
        # Pattern 1: Double the CSV UPC
        doubled = csv_upc + csv_upc
        if doubled in msa_doubled:
            matched.append({
                'csv': csv_upc,
                'msa': doubled,
                'pattern': 'double_exact',
                'qty': qty
            })
            found = True
        
        # Pattern 2: CSV + '0' then double
        if not found:
            with_zero = csv_upc + '0'
            doubled_with_zero = with_zero + with_zero
            if doubled_with_zero in msa_doubled:
                matched.append({
                    'csv': csv_upc,
                    'msa': doubled_with_zero,
                    'pattern': 'add_0_then_double',
                    'qty': qty
                })
                found = True
        
        # Pattern 3: Check if CSV matches single UPC
        if not found and csv_upc in msa_single:
            matched.append({
                'csv': csv_upc,
                'msa': csv_upc,
                'pattern': 'single_match',
                'qty': qty
            })
            found = True
        
        # Pattern 4: CSV + '0' matches single
        if not found:
            with_zero = csv_upc + '0'
            if with_zero in msa_single:
                matched.append({
                    'csv': csv_upc,
                    'msa': with_zero,
                    'pattern': 'add_0_single',
                    'qty': qty
                })
                found = True
        
        if not found:
            unmatched.append((csv_upc, qty))
    
    print(f"\n" + "="*70)
    print("MATCHING RESULTS")
    print(f"="*70)
    
    match_rate = 100 * len(matched) / len(csv_items) if csv_items else 0
    print(f"\nMatched: {len(matched)}/{len(csv_items)} ({match_rate:.1f}%)")
    print(f"Unmatched: {len(unmatched)}")
    
    if matched:
        from collections import Counter
        pattern_counts = Counter(m['pattern'] for m in matched)
        print("\nMatching patterns:")
        for pattern, count in pattern_counts.most_common():
            print(f"  {pattern}: {count}")
        
        print("\nSample matches:")
        for m in matched[:10]:
            if m['pattern'] in ['double_exact', 'add_0_then_double']:
                print(f"  CSV: {m['csv']} → MSA: {m['msa'][:20]}... ({m['pattern']})")
            else:
                print(f"  CSV: {m['csv']} → MSA: {m['msa']} ({m['pattern']})")
    
    # Analyze unmatched
    if unmatched:
        print(f"\n" + "="*70)
        print("UNMATCHED ANALYSIS")
        print(f"="*70)
        
        with_inv = [(upc, qty) for upc, qty in unmatched if qty > 0]
        print(f"\nUnmatched with inventory: {len(with_inv)}")
        
        print("\nFirst 20 unmatched with inventory:")
        for upc, qty in with_inv[:20]:
            print(f"  {upc}: {qty} units")
            # Check if it exists in MSA in some other form
            for msa_upc in list(msa_single)[:100]:
                if upc[:8] in msa_upc or upc[-8:] in msa_upc:
                    print(f"    → Possible match in MSA: {msa_upc}")
                    break
    
    print(f"\n" + "="*70)
    print("CONCLUSION")
    print(f"="*70)
    
    if match_rate < 100:
        print(f"""
Only {match_rate:.1f}% match rate achieved!

The problem is clear:
1. MSA BID records use DOUBLED UPCs (e.g., 60924990342600609249903426)
2. Most CSV items do NOT match even when doubled
3. Only {len(matched)} out of {len(csv_items)} CSV items found in MSA

CRITICAL: {len(with_inv)} products with inventory are missing!

This means either:
1. The CSV and MSA files are from different time periods
2. MULTICAT is filtering out non-tobacco products
3. The CSV needs preprocessing before MULTICAT import
4. There's a configuration issue in MULTICAT
        """)
    else:
        print("✅ 100% match achieved with doubling pattern!")

if __name__ == "__main__":
    check_doubling_pattern()