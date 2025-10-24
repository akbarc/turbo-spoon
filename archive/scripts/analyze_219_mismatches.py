#!/usr/bin/env python3
"""
Deep analysis of the remaining 219 BID mismatches to identify root causes
"""

from database_pymssql import connection_pool
from datetime import datetime
from collections import defaultdict

def analyze_all_mismatches():
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
    print("DETAILED ANALYSIS OF ALL 219 MISMATCHES")
    print("="*70)
    
    # Find all mismatches and categorize them
    mismatches = []
    
    for upc in act_bids:
        if upc in gen_bids:
            gen_line = gen_bids[upc]
            act_line = act_bids[upc]
            
            if gen_line != act_line:
                # Analyze the type of difference
                mismatch = analyze_single_mismatch(upc, gen_line, act_line)
                if mismatch:
                    mismatches.append(mismatch)
    
    print(f"\nTotal mismatches found: {len(mismatches)}")
    
    # Group by problem type
    problem_types = defaultdict(list)
    for m in mismatches:
        problem_types[m['problem_type']].append(m)
    
    print(f"\n{'='*70}")
    print("CATEGORIZATION BY PROBLEM TYPE")
    print("="*70)
    
    for problem_type, items in sorted(problem_types.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{problem_type}: {len(items)} products")
        
        # Show examples for each type
        print(f"Examples:")
        for item in sorted(items, key=lambda x: abs(x.get('diff', 0)), reverse=True)[:5]:
            if 'diff' in item:
                print(f"  {item['upc']}: Gen={item['gen_inv']:4}, Act={item['act_inv']:4}, Diff={item['diff']:+4} | {item['name'][:35]}")
            else:
                print(f"  {item['upc']}: {item.get('details', 'Unknown issue')} | {item['name'][:35]}")
    
    # Deep dive into specific problem types
    investigate_zero_inventory_products(problem_types.get('Zero in Generated', []))
    investigate_large_differences(problem_types.get('Large Inventory Diff', []))
    investigate_format_differences(problem_types.get('Format/Length Diff', []))
    
    return mismatches

def analyze_single_mismatch(upc, gen_line, act_line):
    """Analyze a single mismatch to determine the problem type"""
    
    # Extract basic info
    name = extract_product_name(act_line)
    
    # Check for length differences
    if len(gen_line) != len(act_line):
        return {
            'upc': upc,
            'name': name,
            'problem_type': 'Format/Length Diff',
            'gen_len': len(gen_line),
            'act_len': len(act_line),
            'details': f'Length: Gen={len(gen_line)}, Act={len(act_line)}'
        }
    
    # Check for inventory differences
    gen_inv, act_inv = extract_inventory_values(gen_line, act_line)
    
    if gen_inv is not None and act_inv is not None:
        diff = act_inv - gen_inv
        
        if abs(diff) == 0:
            # Same inventory but lines differ - check other fields
            return {
                'upc': upc,
                'name': name,
                'problem_type': 'Non-Inventory Diff',
                'details': 'Same inventory but other fields differ'
            }
        elif gen_inv == 0 and act_inv > 0:
            return {
                'upc': upc,
                'name': name,
                'problem_type': 'Zero in Generated',
                'gen_inv': gen_inv,
                'act_inv': act_inv,
                'diff': diff
            }
        elif abs(diff) <= 5:
            return {
                'upc': upc,
                'name': name,
                'problem_type': 'Small Inventory Diff',
                'gen_inv': gen_inv,
                'act_inv': act_inv,
                'diff': diff
            }
        elif abs(diff) <= 20:
            return {
                'upc': upc,
                'name': name,
                'problem_type': 'Medium Inventory Diff',
                'gen_inv': gen_inv,
                'act_inv': act_inv,
                'diff': diff
            }
        else:
            return {
                'upc': upc,
                'name': name,
                'problem_type': 'Large Inventory Diff',
                'gen_inv': gen_inv,
                'act_inv': act_inv,
                'diff': diff
            }
    
    return {
        'upc': upc,
        'name': name,
        'problem_type': 'Unknown Diff',
        'details': 'Could not extract inventory values'
    }

def extract_product_name(line):
    """Extract product name from BID line"""
    if len(line) > 78:
        # Check for double UPC format
        if len(line) > 30 and line[18:30].strip() and line[18:30].strip()[0].isdigit():
            # Find where name starts after ItemLookupCode
            for i in range(18, min(80, len(line))):
                if line[i].isalpha():
                    return line[i:i+40].strip()
            return line[30:78].strip()
        else:
            return line[18:78].strip()
    return line[18:].strip()

def extract_inventory_values(gen_line, act_line):
    """Extract inventory values from both lines"""
    try:
        # Check format based on length
        if len(gen_line) >= 261 and len(act_line) >= 261:
            # Extended format
            gen_inv_str = gen_line[247:261]
            act_inv_str = act_line[247:261]
        elif len(gen_line) >= 210 and len(act_line) >= 210:
            # Standard format
            gen_inv_str = gen_line[199:210]
            act_inv_str = act_line[199:210]
        else:
            return None, None
        
        # Parse inventory values
        gen_inv = int(gen_inv_str.replace('003', '').replace('-', '').strip())
        act_inv = int(act_inv_str.replace('003', '').replace('-', '').strip())
        
        return gen_inv, act_inv
    except:
        return None, None

def investigate_zero_inventory_products(zero_products):
    """Deep dive into products showing 0 in generated but >0 in actual"""
    
    if not zero_products:
        return
    
    print(f"\n{'='*70}")
    print(f"INVESTIGATING {len(zero_products)} PRODUCTS WITH ZERO IN GENERATED")
    print("="*70)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Group by UPC prefix to find patterns
    prefix_groups = defaultdict(list)
    for product in zero_products:
        prefix = product['upc'][:6]
        prefix_groups[prefix].append(product)
    
    print("\nBy UPC prefix:")
    for prefix, products in sorted(prefix_groups.items(), key=lambda x: len(x[1]), reverse=True):
        if len(products) >= 3:
            total_missing = sum(p['act_inv'] for p in products)
            print(f"  {prefix}: {len(products)} products, {total_missing} total units missing")
    
    # Check database for top products
    print(f"\nDatabase investigation for top 10 products:")
    for i, product in enumerate(sorted(zero_products, key=lambda x: x['act_inv'], reverse=True)[:10], 1):
        upc = product['upc']
        
        # Try to find ItemLookupCode
        possible_codes = generate_possible_codes(upc)
        
        found_code = None
        for code in possible_codes:
            cursor.execute('SELECT ItemLookupCode, Description, Quantity FROM Item WHERE ItemLookupCode = %s', (code,))
            result = cursor.fetchone()
            if result:
                found_code = code
                print(f"\n{i:2}. {product['name'][:40]}")
                print(f"     UPC: {upc}")
                print(f"     Found ItemCode: {found_code}")
                print(f"     DB Inventory: {result['Quantity']}")
                print(f"     MSA Shows: {product['act_inv']}")
                
                # Check if this code was in our inventory lookup
                check_inventory_lookup_failure(found_code, product['act_inv'])
                break
        
        if not found_code:
            print(f"\n{i:2}. {product['name'][:40]} - NOT FOUND IN DATABASE")
            print(f"     UPC: {upc}")
            print(f"     Tried codes: {possible_codes[:3]}")
    
    cursor.close()
    connection_pool.return_connection(conn)

def generate_possible_codes(upc):
    """Generate all possible ItemLookupCode variations for a UPC"""
    upc_clean = upc.strip()
    codes = [upc_clean]
    
    if len(upc_clean) == 15:
        codes.extend([
            upc_clean[:14],      # First 14 chars
            upc_clean[1:15],     # Skip first char
            upc_clean[:13],      # First 13 chars
            upc_clean[1:14],     # Skip first char, take 13
            upc_clean[:12],      # First 12 chars
        ])
    
    # Remove leading zeros variations
    codes.extend([
        upc_clean.lstrip('0'),
        upc_clean[1:].lstrip('0') if upc_clean.startswith('0') else upc_clean
    ])
    
    # Padding variations
    if len(upc_clean) < 14:
        codes.extend([
            upc_clean.zfill(12),
            upc_clean.zfill(13),
            upc_clean.zfill(14)
        ])
    
    return list(set(codes))

def check_inventory_lookup_failure(item_code, expected_inv):
    """Check why our inventory lookup might have failed"""
    
    # Simulate our lookup process
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Get current inventory
    cursor.execute('SELECT Quantity FROM Item WHERE ItemLookupCode = %s', (item_code,))
    result = cursor.fetchone()
    
    if not result:
        print(f"     ❌ ItemCode {item_code} not found in current inventory lookup")
        cursor.close()
        connection_pool.return_connection(conn)
        return
    
    current_qty = int(result['Quantity'] or 0)
    
    # Get sales after 08/08
    end_dt = datetime(2025, 8, 8, 23, 59, 59)
    cursor.execute('''
        SELECT SUM(te.Quantity) as SoldAfter
        FROM TransactionEntry te
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber  
        JOIN Item i ON te.ItemID = i.ID
        WHERE i.ItemLookupCode = %s AND t.Time > %s
    ''', (item_code, end_dt))
    
    result = cursor.fetchone()
    sold_after = int(result['SoldAfter'] or 0)
    
    # Get POs after 08/08
    cursor.execute('''
        SELECT SUM(poi.LastQuantityReceived) as ReceivedAfter
        FROM PurchaseOrderEntry poi
        JOIN Item i ON poi.ItemID = i.ID
        WHERE i.ItemLookupCode = %s AND poi.LastReceivedDate > %s
    ''', (item_code, end_dt))
    
    result = cursor.fetchone()
    received_after = int(result['ReceivedAfter'] or 0)
    
    # Calculate what our point-in-time inventory should be
    calculated = current_qty + sold_after - received_after
    
    print(f"     📊 Calculation: {current_qty} current + {sold_after} sold after - {received_after} received after = {calculated}")
    print(f"     🎯 Expected (MSA): {expected_inv}")
    print(f"     ❌ Difference: {expected_inv - calculated:+d}")
    
    cursor.close()
    connection_pool.return_connection(conn)

def investigate_large_differences(large_diff_products):
    """Investigate products with large inventory differences"""
    
    if not large_diff_products:
        return
        
    print(f"\n{'='*70}")
    print(f"INVESTIGATING {len(large_diff_products)} PRODUCTS WITH LARGE DIFFERENCES")
    print("="*70)
    
    # Group by product family
    family_groups = defaultdict(list)
    for product in large_diff_products:
        # Group by first 6 chars of UPC or brand name
        if 'RED' in product['name'] or 'MENT' in product['name'] or 'LIGHT' in product['name']:
            family = 'Cigarettes'
        elif 'GRABBA' in product['name']:
            family = 'Grabba'
        elif 'LOOSE LEAF' in product['name']:
            family = 'Loose Leaf'
        else:
            family = 'Other'
        
        family_groups[family].append(product)
    
    for family, products in family_groups.items():
        total_diff = sum(abs(p['diff']) for p in products)
        print(f"\n{family}: {len(products)} products, {total_diff} total units difference")
        
        for product in sorted(products, key=lambda x: abs(x['diff']), reverse=True)[:3]:
            print(f"  {product['upc']}: {product['diff']:+4} units | {product['name'][:30]}")

def investigate_format_differences(format_diff_products):
    """Investigate products with format/length differences"""
    
    if not format_diff_products:
        return
        
    print(f"\n{'='*70}")
    print(f"INVESTIGATING {len(format_diff_products)} PRODUCTS WITH FORMAT DIFFERENCES")
    print("="*70)
    
    for product in format_diff_products[:10]:
        print(f"\n{product['upc']}: {product['name'][:40]}")
        print(f"  {product['details']}")

if __name__ == '__main__':
    analyze_all_mismatches()