#!/usr/bin/env python3
"""
Deep dive into the final 40 products with variance
Check if MSA formula works for them or if there's another pattern
"""

from database_pymssql import connection_pool
from datetime import datetime
import json

def deep_dive_final_40():
    # Load the 40 products with mismatches
    gen_file = 'generated_msa_08082025_final.txt'
    act_file = 'MSA Data Fr/08082025'
    prior_file = 'MSA Data Fr/08012025'
    
    gen_inv = {}
    act_inv = {}
    act_products = {}
    prior_inv = {}
    
    # Parse generated file
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
    
    # Parse actual file
    with open(act_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                
                # Get product name
                if len(line) > 78:
                    name = line[18:78].strip()
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
    
    # Parse prior MSA file
    with open(prior_file, 'r') as f:
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
                prior_inv[upc] = inv
    
    # Find the 40 mismatches
    mismatches = []
    for upc in act_inv:
        if upc in gen_inv and gen_inv[upc] != act_inv[upc]:
            mismatches.append({
                'upc': upc,
                'name': act_products[upc][:50],
                'prior': prior_inv.get(upc, 0),
                'gen': gen_inv[upc],
                'act': act_inv[upc],
                'diff': act_inv[upc] - gen_inv[upc]
            })
    
    print('='*80)
    print(f'DEEP DIVE: FINAL 40 PRODUCTS WITH VARIANCE')
    print('='*80)
    
    # Group by patterns
    from collections import defaultdict, Counter
    
    # 1. Check if MSA formula (Prior - Sales + Purchases) would work
    print('\n1. CHECKING MSA FORMULA FOR THESE PRODUCTS:')
    print('-'*80)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    start_dt = datetime(2025, 8, 2, 0, 0, 0)
    end_dt = datetime(2025, 8, 8, 23, 59, 59)
    
    formula_works = []
    formula_fails = []
    
    # Load UPC mapping
    with open('upc_to_itemcode_mapping.json', 'r') as f:
        upc_mapping = json.load(f)
    
    for m in mismatches:
        upc = m['upc']
        prior = m['prior']
        actual = m['act']
        
        # Get ItemLookupCode
        item_code = upc_mapping.get(upc, upc)
        
        # Try to find in POS
        cursor.execute('SELECT ID FROM Item WHERE ItemLookupCode = %s', (item_code,))
        item = cursor.fetchone()
        
        if not item and item_code != upc:
            # Try UPC directly
            cursor.execute('SELECT ID FROM Item WHERE ItemLookupCode = %s', (upc,))
            item = cursor.fetchone()
        
        sales = 0
        purchases = 0
        
        if item:
            item_id = item['ID']
            
            # Get sales during period
            cursor.execute('''
                SELECT SUM(te.Quantity) as TotalSold
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE te.ItemID = %s
                AND t.Time >= %s AND t.Time <= %s
                AND te.Quantity > 0
            ''', (item_id, start_dt, end_dt))
            
            result = cursor.fetchone()
            sales = int(result['TotalSold'] or 0) if result else 0
            
            # Get purchases
            cursor.execute('''
                SELECT SUM(poi.LastQuantityReceived) as TotalReceived
                FROM PurchaseOrderEntry poi
                WHERE poi.ItemID = %s
                AND poi.LastReceivedDate >= %s 
                AND poi.LastReceivedDate <= %s
            ''', (item_id, start_dt, end_dt))
            
            result = cursor.fetchone()
            purchases = int(result['TotalReceived'] or 0) if result else 0
        
        # Calculate using MSA formula
        calculated = prior - sales + purchases
        
        # Check if it matches actual
        if calculated == actual:
            formula_works.append(m)
        else:
            m['calculated'] = calculated
            m['sales'] = sales
            m['purchases'] = purchases
            m['formula_diff'] = actual - calculated
            formula_fails.append(m)
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print(f'MSA Formula (Prior - Sales + Purchases):')
    print(f'  ✓ Works for: {len(formula_works)} products')
    print(f'  ✗ Fails for: {len(formula_fails)} products')
    
    # 2. Analyze the products where formula fails
    if formula_fails:
        print('\n2. PRODUCTS WHERE FORMULA FAILS:')
        print('-'*80)
        
        # Group by the adjustment amount needed
        adjustments = defaultdict(list)
        for m in formula_fails:
            adj = m['formula_diff']
            adjustments[adj].append(m)
        
        # Find common adjustments
        common_adj = sorted(adjustments.items(), key=lambda x: len(x[1]), reverse=True)
        
        print('Common adjustment patterns:')
        for adj, products in common_adj[:5]:
            if len(products) >= 2:
                print(f'  Adjustment of {adj:+4}: {len(products)} products')
                for p in products[:2]:
                    print(f'    - {p["name"][:35]:35} (Prior:{p["prior"]:4} Sales:{p["sales"]:3} → Act:{p["act"]:4})')
    
    # 3. Check for pack size patterns
    print('\n3. PACK SIZE / CASE PATTERNS:')
    print('-'*80)
    
    # Common pack sizes in tobacco
    pack_sizes = [5, 10, 12, 15, 20, 24, 25, 30, 50]
    
    pack_patterns = defaultdict(list)
    for m in mismatches:
        diff = abs(m['diff'])
        for pack in pack_sizes:
            if diff % pack == 0 and diff >= pack:
                multiplier = diff // pack
                pack_patterns[pack].append({
                    'product': m,
                    'multiplier': multiplier
                })
                break
    
    for pack_size, products in sorted(pack_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        if len(products) >= 2:
            print(f'Pack size {pack_size}: {len(products)} products')
            for p in products[:2]:
                m = p['product']
                mult = p['multiplier']
                print(f'  {m["name"][:35]:35} Diff: {m["diff"]:+4} = {mult} × {pack_size}')
    
    # 4. Check UPC patterns in detail
    print('\n4. UPC PATTERN ANALYSIS:')
    print('-'*80)
    
    # Group by exact UPC characteristics
    upc_patterns = defaultdict(list)
    for m in mismatches:
        upc = m['upc'].strip()
        
        # Characteristics
        chars = []
        if len(upc) == 13:
            chars.append('13_digit')
        elif len(upc) == 14:
            chars.append('14_digit')
        elif len(upc) == 15:
            chars.append('15_digit')
        
        if upc.startswith('0'):
            chars.append('starts_0')
        
        if upc.endswith('0'):
            chars.append('ends_0')
        
        pattern = '_'.join(chars) if chars else 'other'
        upc_patterns[pattern].append(m)
    
    for pattern, products in sorted(upc_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        if products:
            avg_diff = sum(abs(p['diff']) for p in products) / len(products)
            print(f'{pattern:20}: {len(products):2} products, Avg diff: {avg_diff:5.1f}')
    
    # 5. Check if actual MSA values follow a pattern
    print('\n5. ACTUAL MSA VALUES PATTERN:')
    print('-'*80)
    
    # Check if actual values are multiples of something
    multiples = defaultdict(list)
    for m in mismatches:
        act = m['act']
        if act > 0:
            for base in [5, 10, 12, 24, 25]:
                if act % base == 0:
                    multiples[base].append(m)
                    break
    
    for base, products in sorted(multiples.items(), key=lambda x: len(x[1]), reverse=True):
        if len(products) >= 3:
            print(f'Multiple of {base:2}: {len(products)} products')
            examples = ', '.join(str(p['act']) for p in products[:5])
            print(f'  Examples: {examples}')
    
    # 6. Look for specific product characteristics
    print('\n6. PRODUCT NAME PATTERNS:')
    print('-'*80)
    
    name_patterns = defaultdict(list)
    for m in mismatches:
        name = m['name'].upper()
        
        # Check for count indicators
        if '/5CT' in name or ' 5CT' in name:
            name_patterns['5_count'].append(m)
        elif '/10CT' in name or ' 10CT' in name:
            name_patterns['10_count'].append(m)
        elif '/20CT' in name or ' 20CT' in name:
            name_patterns['20_count'].append(m)
        elif '/24CT' in name or ' 24CT' in name:
            name_patterns['24_count'].append(m)
        elif '/25CT' in name or ' 25CT' in name:
            name_patterns['25_count'].append(m)
        
        # Check for pack indicators
        if '5PK' in name or '5/PK' in name:
            name_patterns['5_pack'].append(m)
        elif '10PK' in name or '10/PK' in name:
            name_patterns['10_pack'].append(m)
    
    for pattern, products in sorted(name_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        if products:
            print(f'{pattern:15}: {len(products)} products')
            for p in products[:2]:
                print(f'  {p["name"][:40]:40} Diff: {p["diff"]:+4}')
    
    # 7. Final pattern summary
    print('\n' + '='*80)
    print('DISCOVERED PATTERNS:')
    print('='*80)
    
    # The +24 pattern
    exactly_24 = [m for m in mismatches if m['diff'] == 24]
    if exactly_24:
        print(f'\n1. THE "+24" PATTERN: {len(exactly_24)} products')
        print('   All have exactly +24 difference')
        print('   Products:')
        for m in exactly_24[:5]:
            print(f'     - {m["name"][:40]}')
        
        # Check if they're all the same type
        upcs = [m['upc'][:5] for m in exactly_24]
        from collections import Counter
        upc_counts = Counter(upcs)
        if len(upc_counts) == 1:
            print(f'   ALL have same UPC prefix: {list(upc_counts.keys())[0]}')
        
        print('   LIKELY: Case quantity adjustment (24-pack standard)')
    
    # Products with no sales/purchases but different inventory
    no_activity = [m for m in formula_fails if m['sales'] == 0 and m['purchases'] == 0 and m['prior'] != m['act']]
    if no_activity:
        print(f'\n2. MANUAL ADJUSTMENTS: {len(no_activity)} products')
        print('   Changed without any sales/purchases')
        for m in no_activity[:3]:
            print(f'     - {m["name"][:35]:35} Prior:{m["prior"]:4} → Act:{m["act"]:4} ({m["act"]-m["prior"]:+4})')
        print('   LIKELY: Physical count adjustments')
    
    # Products that went to specific values
    went_to_zero = [m for m in mismatches if m['act'] == 0]
    went_to_round = [m for m in mismatches if m['act'] > 0 and m['act'] % 10 == 0]
    
    if went_to_zero:
        print(f'\n3. ZEROED OUT: {len(went_to_zero)} products')
        print('   Set to 0 inventory (discontinued?)')
    
    if went_to_round:
        print(f'\n4. ROUND NUMBERS: {len(went_to_round)} products')
        print('   Inventory set to round numbers (manual counts?)')
        examples = ', '.join(str(m['act']) for m in went_to_round[:5])
        print(f'   Examples: {examples}')

if __name__ == '__main__':
    deep_dive_final_40()