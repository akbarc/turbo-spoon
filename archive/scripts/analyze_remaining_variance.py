#!/usr/bin/env python3
"""
Analyze the remaining 0.8-5% variance to find patterns
"""

from database_pymssql import connection_pool
from datetime import datetime
import json

def analyze_all_periods_variance():
    """Analyze variance across all periods to find patterns"""
    
    test_periods = [
        ("06202025", "06272025", 93.9),
        ("06272025", "07042025", 95.1),
        ("07042025", "07112025", 95.1),
        ("07112025", "07182025", 97.1),
        ("07182025", "07252025", 95.7),
        ("07252025", "08012025", 98.8),
        ("08012025", "08082025", 99.2)
    ]
    
    all_mismatches = []
    
    for prior_date, target_date, accuracy in test_periods:
        print(f"\n{'='*70}")
        print(f"ANALYZING {target_date} (Accuracy: {accuracy:.1f}%)")
        print('='*70)
        
        gen_file = f"test_{target_date}_optimized.txt"
        act_file = f"MSA Data Fr/{target_date}"
        
        # Parse files
        gen_inv = {}
        act_inv = {}
        act_products = {}
        
        try:
            with open(gen_file, 'r') as f:
                for line in f:
                    if line.startswith('BID'):
                        upc = line[3:18].strip()
                        if len(line) >= 261:
                            inv_str = line[247:261]
                        elif len(line) >= 210:
                            inv_str = line[199:210]
                        else:
                            continue
                        inv = int(inv_str.replace('003', '').replace('-', '').strip())
                        gen_inv[upc] = inv
        except FileNotFoundError:
            print(f"  Generated file not found, regenerating...")
            import os
            os.system(f"python3 msa_generator_100_optimized.py {prior_date} {target_date} > /dev/null 2>&1")
            with open(gen_file, 'r') as f:
                for line in f:
                    if line.startswith('BID'):
                        upc = line[3:18].strip()
                        if len(line) >= 261:
                            inv_str = line[247:261]
                        elif len(line) >= 210:
                            inv_str = line[199:210]
                        else:
                            continue
                        inv = int(inv_str.replace('003', '').replace('-', '').strip())
                        gen_inv[upc] = inv
        
        with open(act_file, 'r') as f:
            for line in f:
                if line.startswith('BID'):
                    upc = line[3:18].strip()
                    
                    # Get product name
                    if len(line) > 78:
                        name = line[18:78].strip()
                        # Clean up double UPC format
                        if len(name) > 13 and name[:13].isdigit():
                            name = name[13:].strip()
                    else:
                        name = line[18:].strip()
                    
                    if len(line) >= 261:
                        inv_str = line[247:261]
                    elif len(line) >= 210:
                        inv_str = line[199:210]
                    else:
                        continue
                    inv = int(inv_str.replace('003', '').replace('-', '').strip())
                    act_inv[upc] = inv
                    act_products[upc] = name
        
        # Find mismatches
        period_mismatches = []
        for upc in act_inv:
            if upc in gen_inv and gen_inv[upc] != act_inv[upc]:
                mismatch = {
                    'period': target_date,
                    'upc': upc,
                    'name': act_products[upc][:40],
                    'generated': gen_inv[upc],
                    'actual': act_inv[upc],
                    'diff': act_inv[upc] - gen_inv[upc]
                }
                period_mismatches.append(mismatch)
                all_mismatches.append(mismatch)
        
        print(f"Found {len(period_mismatches)} mismatches")
        
        # Analyze patterns for this period
        if period_mismatches:
            # Group by difference magnitude
            small_diff = [m for m in period_mismatches if 0 < abs(m['diff']) <= 5]
            medium_diff = [m for m in period_mismatches if 5 < abs(m['diff']) <= 20]
            large_diff = [m for m in period_mismatches if abs(m['diff']) > 20]
            
            print(f"  Small differences (1-5): {len(small_diff)}")
            print(f"  Medium differences (6-20): {len(medium_diff)}")
            print(f"  Large differences (>20): {len(large_diff)}")
    
    # Analyze patterns across all periods
    print("\n" + "="*70)
    print("PATTERN ANALYSIS ACROSS ALL PERIODS")
    print("="*70)
    
    # Find products that consistently have mismatches
    from collections import defaultdict
    product_frequency = defaultdict(list)
    
    for mismatch in all_mismatches:
        key = (mismatch['upc'], mismatch['name'])
        product_frequency[key].append({
            'period': mismatch['period'],
            'diff': mismatch['diff']
        })
    
    # Products with most frequent mismatches
    frequent_mismatches = [(k, v) for k, v in product_frequency.items() if len(v) >= 3]
    frequent_mismatches.sort(key=lambda x: len(x[1]), reverse=True)
    
    print(f"\n1. PRODUCTS WITH CONSISTENT MISMATCHES (≥3 periods):")
    print(f"   Found {len(frequent_mismatches)} products")
    
    for (upc, name), occurrences in frequent_mismatches[:10]:
        avg_diff = sum(o['diff'] for o in occurrences) / len(occurrences)
        print(f"\n   {name}")
        print(f"   UPC: {upc}")
        print(f"   Mismatches in {len(occurrences)}/7 periods, Avg diff: {avg_diff:+.1f}")
        details = ', '.join(f"{o['period'][-7:]}({o['diff']:+d})" for o in occurrences[:3])
        print(f"   Details: {details}")
    
    # Analyze by product name patterns
    print("\n2. PATTERNS BY PRODUCT TYPE:")
    
    product_types = defaultdict(list)
    for mismatch in all_mismatches:
        name = mismatch['name'].upper()
        
        # Categorize by keywords
        if 'BACKWOOD' in name:
            ptype = 'BACKWOODS'
        elif 'GRABBA' in name or 'LEAF' in name:
            ptype = 'LEAF/WRAPS'
        elif 'VELO' in name or 'ZYN' in name or 'ROGUE' in name:
            ptype = 'NICOTINE POUCHES'
        elif 'JUUL' in name or 'VUSE' in name or 'NJOY' in name:
            ptype = 'VAPE'
        elif 'SWISHER' in name or 'WHITE OWL' in name or 'GAME' in name:
            ptype = 'CIGARS'
        elif 'NEWPORT' in name or 'MARLBORO' in name or 'CAMEL' in name:
            ptype = 'CIGARETTES'
        elif 'GRIZZLY' in name or 'COPENHAGEN' in name or 'SKOAL' in name:
            ptype = 'CHEWING TOBACCO'
        elif 'RAW' in name or 'PAPER' in name or 'WRAP' in name:
            ptype = 'ROLLING PAPERS'
        else:
            ptype = 'OTHER'
        
        product_types[ptype].append(mismatch)
    
    for ptype, mismatches in sorted(product_types.items(), key=lambda x: len(x[1]), reverse=True):
        if len(mismatches) >= 10:
            avg_diff = sum(abs(m['diff']) for m in mismatches) / len(mismatches)
            print(f"\n   {ptype}: {len(mismatches)} mismatches")
            print(f"      Average absolute difference: {avg_diff:.1f}")
            
            # Show examples
            examples = sorted(mismatches, key=lambda x: abs(x['diff']), reverse=True)[:3]
            for ex in examples:
                print(f"      - {ex['name'][:30]:30} Diff:{ex['diff']:+4}")
    
    # Check for specific UPC patterns
    print("\n3. UPC PATTERN ANALYSIS:")
    
    upc_patterns = defaultdict(list)
    for mismatch in all_mismatches:
        upc = mismatch['upc']
        # Check UPC prefix (manufacturer code)
        prefix = upc.lstrip()[:6] if upc.lstrip() else 'UNKNOWN'
        upc_patterns[prefix].append(mismatch)
    
    # Show top manufacturer codes with issues
    top_prefixes = sorted(upc_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    
    print("\n   Top UPC prefixes with mismatches:")
    for prefix, mismatches in top_prefixes:
        if len(mismatches) >= 5:
            # Try to identify manufacturer
            sample_names = list(set(m['name'][:20] for m in mismatches[:5]))
            print(f"   {prefix}: {len(mismatches)} mismatches")
            print(f"      Products: {', '.join(sample_names[:3])}")
    
    # Check for inventory adjustment patterns
    print("\n4. INVENTORY ADJUSTMENT PATTERNS:")
    
    # Products that always increase
    always_increase = []
    always_decrease = []
    
    for (upc, name), occurrences in product_frequency.items():
        if len(occurrences) >= 3:
            if all(o['diff'] > 0 for o in occurrences):
                always_increase.append((upc, name, occurrences))
            elif all(o['diff'] < 0 for o in occurrences):
                always_decrease.append((upc, name, occurrences))
    
    if always_increase:
        print(f"\n   Products that ALWAYS have more in MSA than calculated ({len(always_increase)}):")
        for upc, name, occs in always_increase[:5]:
            avg_increase = sum(o['diff'] for o in occs) / len(occs)
            print(f"      {name[:35]:35} Avg: +{avg_increase:.1f}")
            print(f"         Likely: Manual inventory additions or untracked purchases")
    
    if always_decrease:
        print(f"\n   Products that ALWAYS have less in MSA than calculated ({len(always_decrease)}):")
        for upc, name, occs in always_decrease[:5]:
            avg_decrease = sum(o['diff'] for o in occs) / len(occs)
            print(f"      {name[:35]:35} Avg: {avg_decrease:.1f}")
            print(f"         Likely: Shrinkage, damages, or untracked removals")
    
    # Final summary
    print("\n" + "="*70)
    print("KEY FINDINGS:")
    print("="*70)
    
    total_mismatches = len(all_mismatches)
    unique_products = len(product_frequency)
    
    print(f"Total mismatches across all periods: {total_mismatches}")
    print(f"Unique products with mismatches: {unique_products}")
    print(f"Products with recurring issues: {len(frequent_mismatches)}")
    
    # Clean up test files
    import os
    for _, target_date, _ in test_periods:
        test_file = f"test_{target_date}_optimized.txt"
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == '__main__':
    analyze_all_periods_variance()