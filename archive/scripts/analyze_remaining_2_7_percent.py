#!/usr/bin/env python3
"""
Detailed breakdown of the remaining 2.7% (138 products) inventory mismatches
"""

from database_pymssql import connection_pool
from datetime import datetime
import json

def analyze_remaining_mismatches():
    gen_file = 'generated_msa_08082025_100_percent.txt'
    act_file = 'MSA Data Fr/08082025'
    prior_file = 'MSA Data Fr/08012025'
    
    # Load UPC mapping
    with open('upc_to_itemcode_mapping.json', 'r') as f:
        upc_to_itemcode = json.load(f)
    
    # Parse all files
    gen_inv = {}
    act_inv = {}
    prior_inv = {}
    act_products = {}  # Store full product info
    
    # Parse generated
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
    
    # Parse actual
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
                act_products[upc] = {'name': name, 'inventory': inv}
    
    # Parse prior
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
    
    # Get database connection for analysis
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    start_dt = datetime(2025, 8, 2, 0, 0, 0)
    end_dt = datetime(2025, 8, 8, 23, 59, 59)
    
    # Analyze mismatches
    mismatches = []
    for upc in act_inv:
        if upc in gen_inv and gen_inv[upc] != act_inv[upc]:
            mismatch = {
                'upc': upc,
                'name': act_products[upc]['name'][:40],
                'prior': prior_inv.get(upc, 0),
                'generated': gen_inv[upc],
                'actual': act_inv[upc],
                'diff': act_inv[upc] - gen_inv[upc],
                'item_code': upc_to_itemcode.get(upc, ''),
                'sales': 0,
                'purchases': 0,
                'expected_change': 0,
                'actual_change': 0
            }
            
            # Calculate expected vs actual changes
            mismatch['expected_change'] = mismatch['generated'] - mismatch['prior']
            mismatch['actual_change'] = mismatch['actual'] - mismatch['prior']
            
            # Try to get sales/purchases from database
            item_code = mismatch['item_code']
            if item_code:
                # Get sales
                cursor.execute('''
                    SELECT SUM(te.Quantity) as TotalSold
                    FROM TransactionEntry te
                    JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                    JOIN Item i ON te.ItemID = i.ID
                    WHERE i.ItemLookupCode = %s
                    AND t.Time >= %s AND t.Time <= %s
                    AND te.Quantity > 0
                ''', (item_code, start_dt, end_dt))
                
                result = cursor.fetchone()
                if result and result['TotalSold']:
                    mismatch['sales'] = int(result['TotalSold'])
                
                # Get purchases
                cursor.execute('''
                    SELECT SUM(poi.LastQuantityReceived) as TotalReceived
                    FROM PurchaseOrderEntry poi
                    JOIN Item i ON poi.ItemID = i.ID
                    WHERE i.ItemLookupCode = %s
                    AND poi.LastReceivedDate >= %s 
                    AND poi.LastReceivedDate <= %s
                ''', (item_code, start_dt, end_dt))
                
                result = cursor.fetchone()
                if result and result['TotalReceived']:
                    mismatch['purchases'] = int(result['TotalReceived'])
            
            mismatches.append(mismatch)
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    # Categorize mismatches
    print("="*80)
    print("DETAILED BREAKDOWN OF REMAINING 2.7% (138 PRODUCTS)")
    print("="*80)
    
    # Category 1: Products not in prior MSA
    not_in_prior = [m for m in mismatches if m['prior'] == 0 and m['actual'] > 0]
    print(f"\n1. NOT IN PRIOR MSA (New products): {len(not_in_prior)} products")
    print("   These products weren't in the 08/01 MSA, so we have no baseline")
    for m in sorted(not_in_prior, key=lambda x: x['actual'], reverse=True)[:5]:
        print(f"   - {m['name']:40} Act:{m['actual']:4}")
    
    # Category 2: Zero in generated but have value in actual
    zero_gen = [m for m in mismatches if m['generated'] == 0 and m['actual'] > 0 and m['prior'] > 0]
    print(f"\n2. ZERO IN GENERATED (Had prior, no sales found): {len(zero_gen)} products")
    print("   These had prior inventory but we found no sales/purchases")
    for m in sorted(zero_gen, key=lambda x: x['actual'], reverse=True)[:5]:
        print(f"   - {m['name']:40} Prior:{m['prior']:4} Act:{m['actual']:4}")
        if m['item_code']:
            print(f"     ItemCode: {m['item_code']} (may be wrong)")
    
    # Category 3: Generated > Actual (we calculated too much inventory)
    over_calculated = [m for m in mismatches if m['generated'] > m['actual'] and m['actual'] > 0]
    print(f"\n3. OVER-CALCULATED (Gen > Act): {len(over_calculated)} products")
    print("   We show more inventory than MSA")
    for m in sorted(over_calculated, key=lambda x: abs(m['diff']), reverse=True)[:5]:
        print(f"   - {m['name']:40} Gen:{m['generated']:4} Act:{m['actual']:4} Diff:{m['diff']:+5}")
        print(f"     Prior:{m['prior']:4} Sales:{m['sales']:4} Purch:{m['purchases']:4}")
        calc_inv = m['prior'] - m['sales'] + m['purchases']
        print(f"     Formula: {m['prior']} - {m['sales']} + {m['purchases']} = {calc_inv} (vs Act:{m['actual']})")
    
    # Category 4: Generated < Actual (we calculated too little inventory)
    under_calculated = [m for m in mismatches if m['generated'] < m['actual'] and m['generated'] > 0]
    print(f"\n4. UNDER-CALCULATED (Gen < Act): {len(under_calculated)} products")
    print("   We show less inventory than MSA")
    for m in sorted(under_calculated, key=lambda x: abs(m['diff']), reverse=True)[:5]:
        print(f"   - {m['name']:40} Gen:{m['generated']:4} Act:{m['actual']:4} Diff:{m['diff']:+5}")
        print(f"     Prior:{m['prior']:4} Sales:{m['sales']:4} Purch:{m['purchases']:4}")
        calc_inv = m['prior'] - m['sales'] + m['purchases']
        print(f"     Formula: {m['prior']} - {m['sales']} + {m['purchases']} = {calc_inv} (vs Act:{m['actual']})")
    
    # Category 5: Actual is zero but we have inventory
    act_zero = [m for m in mismatches if m['actual'] == 0 and m['generated'] > 0]
    print(f"\n5. ACTUAL IS ZERO (Discontinued?): {len(act_zero)} products")
    for m in act_zero[:3]:
        print(f"   - {m['name']:40} Prior:{m['prior']:4} Gen:{m['generated']:4}")
    
    # Analysis of patterns
    print("\n" + "="*80)
    print("PATTERN ANALYSIS:")
    print("="*80)
    
    # Check if there's a systematic error
    total_diff = sum(m['diff'] for m in mismatches)
    print(f"\nTotal inventory difference: {total_diff:+d}")
    if abs(total_diff) > 100:
        print("  Large systematic difference suggests missing data source")
    
    # Check for specific product categories
    print("\nBy product type:")
    product_types = {}
    for m in mismatches:
        # Categorize by product name patterns
        name = m['name'].upper()
        if 'NEWPORT' in name:
            ptype = 'NEWPORT'
        elif 'BLK' in name or 'BLACK' in name:
            ptype = 'BLACK & MILD'
        elif 'MARLBORO' in name:
            ptype = 'MARLBORO'
        elif 'CAMEL' in name:
            ptype = 'CAMEL'
        elif '24/7' in name:
            ptype = '24/7'
        elif 'AMERICAN' in name:
            ptype = 'AMERICAN SPIRIT'
        else:
            ptype = 'OTHER'
        
        if ptype not in product_types:
            product_types[ptype] = []
        product_types[ptype].append(m)
    
    for ptype, products in sorted(product_types.items(), key=lambda x: len(x[1]), reverse=True):
        if len(products) > 2:
            total_diff = sum(p['diff'] for p in products)
            print(f"  {ptype:20} {len(products):3} products, Total diff: {total_diff:+6}")
    
    print("\n" + "="*80)
    print("LIKELY CAUSES:")
    print("="*80)
    print("1. Manual inventory adjustments in MSA not reflected in POS")
    print("2. Products added to MSA mid-week without prior baseline")
    print("3. Returns or damages processed differently in MSA vs POS")
    print("4. Some ItemLookupCode mappings may still be incorrect")
    print("5. MSA may have additional data sources beyond POS")
    
    return mismatches

if __name__ == '__main__':
    mismatches = analyze_remaining_mismatches()