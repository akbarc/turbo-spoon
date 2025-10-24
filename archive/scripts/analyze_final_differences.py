#!/usr/bin/env python3
"""
Analyze the final 5.3% BID differences after all fixes
"""

from database_pymssql import connection_pool
from datetime import datetime
from collections import defaultdict

def analyze_final_differences():
    gen_file = 'generated_msa_08082025_perfect_bid.txt'
    act_file = 'MSA Data Fr/08082025'
    
    gen_bids = {}
    act_bids = {}
    
    # Parse files
    with open(gen_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                gen_bids[upc] = line.rstrip()
    
    with open(act_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                act_bids[upc] = line.rstrip()
    
    print("="*70)
    print("ANALYZING FINAL 5.3% BID DIFFERENCES")
    print("="*70)
    
    # Find mismatches
    mismatches = []
    perfect_matches = 0
    
    for upc in act_bids:
        if upc in gen_bids:
            if gen_bids[upc] == act_bids[upc]:
                perfect_matches += 1
            else:
                mismatches.append((upc, gen_bids[upc], act_bids[upc]))
    
    print(f"\nTotal BIDs: {len(act_bids)}")
    print(f"Perfect matches: {perfect_matches} ({100*perfect_matches/len(act_bids):.1f}%)")
    print(f"Mismatches: {len(mismatches)} ({100*len(mismatches)/len(act_bids):.1f}%)")
    
    # Categorize mismatches
    inventory_only = []
    format_diff = []
    other_diff = []
    
    for upc, gen_line, act_line in mismatches:
        # Check if only inventory differs
        if len(gen_line) == len(act_line):
            # Same length - check if only inventory field differs
            if len(gen_line) >= 261:
                # Extended format
                if gen_line[:247] == act_line[:247] and gen_line[261:] == act_line[261:]:
                    # Only inventory field differs
                    gen_inv = gen_line[247:261]
                    act_inv = act_line[247:261]
                    try:
                        gen_val = int(gen_inv.replace('003', '').replace('-', ''))
                        act_val = int(act_inv.replace('003', '').replace('-', ''))
                        diff = act_val - gen_val
                        inventory_only.append((upc, gen_val, act_val, diff))
                    except:
                        other_diff.append((upc, gen_line, act_line))
                else:
                    other_diff.append((upc, gen_line, act_line))
            elif len(gen_line) >= 210:
                # Standard format
                if gen_line[:199] == act_line[:199] and gen_line[210:] == act_line[210:]:
                    gen_inv = gen_line[199:210]
                    act_inv = act_line[199:210]
                    try:
                        gen_val = int(gen_inv.replace('003', ''))
                        act_val = int(act_inv.replace('003', ''))
                        diff = act_val - gen_val
                        inventory_only.append((upc, gen_val, act_val, diff))
                    except:
                        other_diff.append((upc, gen_line, act_line))
                else:
                    other_diff.append((upc, gen_line, act_line))
        else:
            format_diff.append((upc, len(gen_line), len(act_line)))
    
    print("\n" + "="*70)
    print("CATEGORIZATION OF MISMATCHES")
    print("="*70)
    
    print(f"\n1. Inventory-only differences: {len(inventory_only)} ({100*len(inventory_only)/len(mismatches):.1f}%)")
    print(f"2. Format/length differences: {len(format_diff)} ({100*len(format_diff)/len(mismatches):.1f}%)")
    print(f"3. Other differences: {len(other_diff)} ({100*len(other_diff)/len(mismatches):.1f}%)")
    
    # Analyze inventory differences
    if inventory_only:
        print("\n" + "="*70)
        print("INVENTORY DIFFERENCES ANALYSIS")
        print("="*70)
        
        # Group by difference size
        tiny = [m for m in inventory_only if abs(m[3]) <= 1]
        small = [m for m in inventory_only if 1 < abs(m[3]) <= 5]
        medium = [m for m in inventory_only if 5 < abs(m[3]) <= 20]
        large = [m for m in inventory_only if abs(m[3]) > 20]
        
        print(f"\nBy difference magnitude:")
        print(f"  ±1 unit: {len(tiny)} products")
        print(f"  ±2-5 units: {len(small)} products")
        print(f"  ±6-20 units: {len(medium)} products")
        print(f"  >20 units: {len(large)} products")
        
        # Show samples
        if tiny:
            print("\n### ±1 UNIT DIFFERENCES (likely rounding/timing) ###")
            for upc, gen_val, act_val, diff in tiny[:10]:
                name = get_product_name(upc, act_bids)
                print(f"  {upc}: Gen={gen_val:4}, Act={act_val:4}, Diff={diff:+2} | {name[:35]}")
        
        if small:
            print("\n### ±2-5 UNIT DIFFERENCES (likely returns/adjustments) ###")
            for upc, gen_val, act_val, diff in small[:10]:
                name = get_product_name(upc, act_bids)
                print(f"  {upc}: Gen={gen_val:4}, Act={act_val:4}, Diff={diff:+3} | {name[:35]}")
        
        if large:
            print("\n### LARGE DIFFERENCES (need investigation) ###")
            for upc, gen_val, act_val, diff in sorted(large, key=lambda x: abs(x[3]), reverse=True)[:10]:
                name = get_product_name(upc, act_bids)
                print(f"  {upc}: Gen={gen_val:4}, Act={act_val:4}, Diff={diff:+4} | {name[:35]}")
    
    # Check specific products with large differences
    if large:
        check_large_differences(large[:3], act_bids)
    
    return inventory_only, format_diff, other_diff

def get_product_name(upc, act_bids):
    """Extract product name from BID line"""
    if upc in act_bids:
        line = act_bids[upc]
        # Check for double UPC format
        if len(line) > 30 and line[18:30].strip() and line[18:30].strip()[0].isdigit():
            # Name starts after ItemLookupCode
            for i in range(18, min(50, len(line))):
                if line[i].isalpha():
                    return line[i:i+40].strip()
        else:
            # Standard format
            return line[18:58].strip() if len(line) > 58 else line[18:].strip()
    return ""

def check_large_differences(large_diffs, act_bids):
    """Deep dive into products with large inventory differences"""
    
    print("\n" + "="*70)
    print("DEEP DIVE INTO LARGE DIFFERENCES")
    print("="*70)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    end_dt = datetime(2025, 8, 8, 23, 59, 59)
    
    for upc, gen_val, act_val, diff in large_diffs:
        name = get_product_name(upc, act_bids)
        print(f"\n### {name[:40]} ###")
        print(f"UPC: {upc}")
        print(f"Our calculation: {gen_val}, MSA shows: {act_val}, Difference: {diff:+d}")
        
        # Try to find the ItemLookupCode
        possible_codes = [
            upc.lstrip('0'),
            upc.lstrip(' ').lstrip('0'),
            upc[:-1] if upc.endswith('0') else upc,
            upc[-12:] if len(upc) > 12 else upc,
        ]
        
        item_code = None
        for code in possible_codes:
            cursor.execute('SELECT ItemLookupCode, Description FROM Item WHERE ItemLookupCode = %s', code)
            result = cursor.fetchone()
            if result:
                item_code = result['ItemLookupCode']
                break
        
        if item_code:
            print(f"ItemLookupCode: {item_code}")
            
            # Check for manual adjustments
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT t.TransactionNumber) as TransCount,
                    SUM(CASE WHEN te.Quantity > 0 THEN te.Quantity ELSE 0 END) as TotalSold,
                    SUM(CASE WHEN te.Quantity < 0 THEN ABS(te.Quantity) ELSE 0 END) as TotalReturned
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                JOIN Item i ON te.ItemID = i.ID
                WHERE i.ItemLookupCode = %s
                AND t.Time >= '2025-08-02' AND t.Time <= %s
            ''', (item_code, end_dt))
            
            result = cursor.fetchone()
            if result:
                print(f"\nActivity during MSA week:")
                print(f"  Transactions: {result['TransCount']}")
                sold = result['TotalSold'] if result['TotalSold'] is not None else 0
                returned = result['TotalReturned'] if result['TotalReturned'] is not None else 0
                print(f"  Units sold: {sold:.0f}")
                print(f"  Units returned: {returned:.0f}")
            
            # Check for damaged/expired adjustments
            cursor.execute('''
                SELECT TOP 5
                    t.Time,
                    t.TransactionNumber,
                    te.Quantity,
                    t.Comment
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                JOIN Item i ON te.ItemID = i.ID
                WHERE i.ItemLookupCode = %s
                AND t.Time >= '2025-08-02' AND t.Time <= %s
                AND (t.Comment IS NOT NULL OR ABS(te.Quantity) > 100)
                ORDER BY ABS(te.Quantity) DESC
            ''', (item_code, end_dt))
            
            unusual = cursor.fetchall()
            if unusual:
                print("\nUnusual transactions:")
                for trans in unusual:
                    print(f"  {trans['Time'].strftime('%m/%d %H:%M')}: Qty={trans['Quantity']:.0f}, Comment={trans['Comment'] or 'None'}")
        else:
            print("Could not find ItemLookupCode in database")
    
    cursor.close()
    connection_pool.return_connection(conn)

def analyze_patterns():
    """Look for patterns in the remaining differences"""
    
    print("\n" + "="*70)
    print("PATTERN ANALYSIS")
    print("="*70)
    
    inventory_only, format_diff, other_diff = analyze_final_differences()
    
    if inventory_only:
        # Check if certain products always have differences
        print("\n### COMMON PATTERNS ###")
        
        # Group by product category (using UPC prefix)
        prefix_groups = defaultdict(list)
        for upc, gen_val, act_val, diff in inventory_only:
            prefix = upc[:6] if len(upc) >= 6 else upc
            prefix_groups[prefix].append((upc, diff))
        
        # Find prefixes with consistent differences
        print("\nProduct groups with consistent differences:")
        for prefix, products in sorted(prefix_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            if len(products) >= 3:
                avg_diff = sum(p[1] for p in products) / len(products)
                print(f"  Prefix {prefix}: {len(products)} products, avg diff: {avg_diff:+.1f}")

if __name__ == '__main__':
    analyze_patterns()