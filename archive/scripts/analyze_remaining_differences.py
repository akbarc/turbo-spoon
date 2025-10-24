#!/usr/bin/env python3
"""
Analyze the remaining 22% BID differences to find patterns and root causes
"""

from database_pymssql import connection_pool
from datetime import datetime

def analyze_bid_differences():
    gen_file = 'generated_msa_08082025_perfect_bid.txt'
    act_file = 'MSA Data Fr/08082025'
    
    gen_bids = {}
    act_bids = {}
    
    # Parse generated
    with open(gen_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                gen_bids[upc] = line.rstrip()
    
    # Parse actual
    with open(act_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                act_bids[upc] = line.rstrip()
    
    print("="*70)
    print("ANALYZING REMAINING 22% BID DIFFERENCES")
    print("="*70)
    
    # Categorize differences
    inventory_mismatches = []
    perfect_matches = []
    
    for upc in act_bids:
        if upc in gen_bids:
            gen_line = gen_bids[upc]
            act_line = act_bids[upc]
            
            if gen_line == act_line:
                perfect_matches.append(upc)
            else:
                # Extract inventory values
                gen_inv = None
                act_inv = None
                
                if len(gen_line) >= 261 and len(act_line) >= 261:
                    # Extended format
                    gen_inv = gen_line[247:261]
                    act_inv = act_line[247:261]
                elif len(gen_line) >= 210 and len(act_line) >= 210:
                    # Standard format
                    gen_inv = gen_line[199:210]
                    act_inv = act_line[199:210]
                
                if gen_inv and act_inv:
                    try:
                        gen_val = int(gen_inv.replace('-', '').replace('003', ''))
                        act_val = int(act_inv.replace('-', '').replace('003', ''))
                        diff = act_val - gen_val
                        
                        # Extract product name
                        name = ''
                        if len(act_line) > 78:
                            # Check for double UPC format
                            if act_line[18:30].strip() and act_line[18:30].strip()[0].isdigit():
                                name = act_line[30:78].strip()
                            else:
                                name = act_line[18:78].strip()
                        
                        inventory_mismatches.append({
                            'upc': upc,
                            'name': name,
                            'gen_inv': gen_val,
                            'act_inv': act_val,
                            'diff': diff
                        })
                    except:
                        pass
    
    print(f"\nTotal BIDs analyzed: {len(act_bids)}")
    print(f"Perfect matches: {len(perfect_matches)} ({100*len(perfect_matches)/len(act_bids):.1f}%)")
    print(f"Inventory mismatches: {len(inventory_mismatches)} ({100*len(inventory_mismatches)/len(act_bids):.1f}%)")
    
    # Analyze patterns in mismatches
    print("\n" + "="*70)
    print("PATTERNS IN INVENTORY MISMATCHES")
    print("="*70)
    
    # Group by difference size
    small_diff = [m for m in inventory_mismatches if abs(m['diff']) <= 5]
    medium_diff = [m for m in inventory_mismatches if 5 < abs(m['diff']) <= 20]
    large_diff = [m for m in inventory_mismatches if abs(m['diff']) > 20]
    
    print(f"\nBy difference size:")
    print(f"  Small (±5): {len(small_diff)} products")
    print(f"  Medium (6-20): {len(medium_diff)} products")
    print(f"  Large (>20): {len(large_diff)} products")
    
    # Show examples of each
    print("\n### SMALL DIFFERENCES (±5) - Likely timing issues ###")
    for m in sorted(small_diff, key=lambda x: abs(x['diff']))[:5]:
        print(f"  {m['upc']}: Gen={m['gen_inv']:4}, Act={m['act_inv']:4}, Diff={m['diff']:+3} | {m['name'][:35]}")
    
    print("\n### MEDIUM DIFFERENCES (6-20) - May be returns/adjustments ###")
    for m in sorted(medium_diff, key=lambda x: abs(x['diff']))[:5]:
        print(f"  {m['upc']}: Gen={m['gen_inv']:4}, Act={m['act_inv']:4}, Diff={m['diff']:+3} | {m['name'][:35]}")
    
    print("\n### LARGE DIFFERENCES (>20) - Need investigation ###")
    for m in sorted(large_diff, key=lambda x: abs(x['diff']), reverse=True)[:10]:
        print(f"  {m['upc']}: Gen={m['gen_inv']:4}, Act={m['act_inv']:4}, Diff={m['diff']:+4} | {m['name'][:35]}")
    
    # Check specific patterns
    print("\n" + "="*70)
    print("CHECKING SPECIFIC PATTERNS")
    print("="*70)
    
    # Products where we show 0 but MSA shows inventory
    zero_in_gen = [m for m in inventory_mismatches if m['gen_inv'] == 0 and m['act_inv'] > 0]
    print(f"\nProducts with 0 in generated but >0 in actual: {len(zero_in_gen)}")
    for m in zero_in_gen[:5]:
        print(f"  {m['upc']}: Act={m['act_inv']:4} | {m['name'][:35]}")
    
    # Products where MSA shows 0 but we show inventory
    zero_in_act = [m for m in inventory_mismatches if m['act_inv'] == 0 and m['gen_inv'] > 0]
    print(f"\nProducts with 0 in actual but >0 in generated: {len(zero_in_act)}")
    for m in zero_in_act[:5]:
        print(f"  {m['upc']}: Gen={m['gen_inv']:4} | {m['name'][:35]}")
    
    return inventory_mismatches

def check_specific_products(mismatches):
    """Deep dive into specific products with large differences"""
    
    print("\n" + "="*70)
    print("DEEP DIVE INTO SPECIFIC PRODUCTS")
    print("="*70)
    
    # Get top 3 products with largest differences
    large_diffs = sorted(mismatches, key=lambda x: abs(x['diff']), reverse=True)[:3]
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    end_dt = datetime(2025, 8, 8, 23, 59, 59)
    
    for product in large_diffs:
        upc = product['upc']
        
        # Try to find the ItemLookupCode
        possible_codes = [
            upc.lstrip('0'),
            upc.lstrip(' ').lstrip('0'),
            upc[-13:] if len(upc) > 13 and upc[-1] == '0' else upc,
            upc[:-1] if upc.endswith('0') else upc
        ]
        
        item_code = None
        for code in possible_codes:
            cursor.execute('SELECT ItemLookupCode FROM Item WHERE ItemLookupCode = %s', code)
            result = cursor.fetchone()
            if result:
                item_code = result['ItemLookupCode']
                break
        
        if item_code:
            print(f"\n### {product['name'][:40]} ###")
            print(f"UPC: {upc}, ItemCode: {item_code}")
            print(f"MSA shows: {product['act_inv']}, We show: {product['gen_inv']}, Diff: {product['diff']:+d}")
            
            # Get current inventory
            cursor.execute('SELECT Quantity FROM Item WHERE ItemLookupCode = %s', item_code)
            result = cursor.fetchone()
            current = result['Quantity'] if result else 0
            
            # Sales after period
            cursor.execute('''
                SELECT COUNT(*) as TransCount, SUM(te.Quantity) as TotalQty
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                JOIN Item i ON te.ItemID = i.ID
                WHERE i.ItemLookupCode = %s AND t.Time > %s
            ''', (item_code, end_dt))
            result = cursor.fetchone()
            sales_after = result['TotalQty'] if result and result['TotalQty'] else 0
            trans_after = result['TransCount'] if result else 0
            
            # Sales during period
            cursor.execute('''
                SELECT COUNT(*) as TransCount, SUM(te.Quantity) as TotalQty
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                JOIN Item i ON te.ItemID = i.ID
                WHERE i.ItemLookupCode = %s 
                AND t.Time >= '2025-08-02' AND t.Time <= %s
            ''', (item_code, end_dt))
            result = cursor.fetchone()
            sales_during = result['TotalQty'] if result and result['TotalQty'] else 0
            trans_during = result['TransCount'] if result else 0
            
            # Check for returns
            cursor.execute('''
                SELECT COUNT(*) as ReturnCount, SUM(te.Quantity) as ReturnQty
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                JOIN Item i ON te.ItemID = i.ID
                WHERE i.ItemLookupCode = %s 
                AND t.Time >= '2025-08-02'
                AND te.Quantity < 0
            ''', item_code)
            result = cursor.fetchone()
            returns = abs(result['ReturnQty']) if result and result['ReturnQty'] else 0
            
            print(f"\nInventory calculation:")
            print(f"  Current stock: {current:.0f}")
            print(f"  + Sales after 08/08: {sales_after:.0f} ({trans_after} transactions)")
            print(f"  = Calculated: {current + sales_after:.0f}")
            print(f"  vs MSA: {product['act_inv']}")
            print(f"\nActivity during period (08/02-08/08):")
            print(f"  Sales: {sales_during:.0f} units in {trans_during} transactions")
            print(f"  Returns: {returns:.0f} units")
    
    cursor.close()
    connection_pool.return_connection(conn)

def find_itemlookupcode_issues():
    """Check if ItemLookupCode extraction is working correctly"""
    
    print("\n" + "="*70)
    print("CHECKING ITEMLOOKUPCODE EXTRACTION")
    print("="*70)
    
    # Check products with double UPC format
    act_file = 'MSA Data Fr/08082025'
    
    double_upc_products = []
    with open(act_file, 'r') as f:
        for line in f:
            if line.startswith('BID') and len(line) > 30:
                if line[18:30].strip() and line[18:30].strip()[0].isdigit():
                    upc = line[3:18].strip()
                    item_code = line[18:30].strip()
                    double_upc_products.append((upc, item_code))
    
    print(f"Found {len(double_upc_products)} products with double UPC format")
    
    # Sample check
    print("\nSample products with double UPC:")
    for upc, item_code in double_upc_products[:10]:
        print(f"  UPC: {upc}, ItemCode: {item_code}")

if __name__ == '__main__':
    mismatches = analyze_bid_differences()
    check_specific_products(mismatches)
    find_itemlookupcode_issues()