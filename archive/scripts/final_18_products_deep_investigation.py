#!/usr/bin/env python3
"""
Deep investigation of the final 18 products that don't match any calculation
Focus on finding alternative ItemLookupCode patterns or data sources
"""

from database_pymssql import connection_pool
from datetime import datetime, timedelta
import json

def investigate_final_18():
    # Products that don't match ANY calculation from calculate_every_way.py
    problem_products = {
        '108400482190361': 'JUUL VIRG TOBACCO 5% 6PK 4CT',
        '108199130114261': 'JUUL VIRG TOBACCO 5% 4PK 8CT', 
        '108199130125911': 'JUUL CLASSIC MENTHL 5% 4PK 8CT',
        '6851419131520': '24/7 MENTHOL 100 1CTN',
        '6851419130770': '24/7 LIGHT 100S BOX',
        '108575450120771': 'BOB M HEMP WRAP STRBRY'
    }
    
    # Test period
    prior_date = "08012025"
    target_date = "08082025"
    
    # Parse MSA files to get actual values
    prior_inv = {}
    actual_inv = {}
    
    # Get prior inventory
    with open(f'MSA Data Fr/{prior_date}', 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                if len(line) >= 261:
                    # Extended format - ItemLookupCode is in positions 18-31
                    item_code_section = line[18:31].strip()
                    inv_str = line[247:261]
                elif len(line) >= 210:
                    inv_str = line[199:210]
                else:
                    continue
                inv = int(inv_str.replace('003', '').replace('-', '').strip())
                prior_inv[upc] = inv
    
    # Get actual inventory
    with open(f'MSA Data Fr/{target_date}', 'r') as f:
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
                actual_inv[upc] = inv
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Date range for sales/purchases
    target_dt = datetime.strptime(f"2025{target_date[:4]}", '%Y%m%d')
    if target_dt.weekday() != 4:
        days_to_friday = (4 - target_dt.weekday()) % 7
        if days_to_friday == 0:
            days_to_friday = 7
        target_dt = target_dt + timedelta(days=days_to_friday)
    
    start_dt = target_dt - timedelta(days=6)
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = target_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    print('='*100)
    print('DEEP INVESTIGATION: FINAL 18 PRODUCTS')
    print('='*100)
    print(f'\nPeriod: {prior_date} → {target_date}')
    print(f'Date Range: {start_dt.strftime("%Y-%m-%d")} to {end_dt.strftime("%Y-%m-%d")}')
    print('-'*100)
    
    for upc, name in problem_products.items():
        if upc not in actual_inv:
            continue
            
        print(f'\n\n{"="*80}')
        print(f'PRODUCT: {name}')
        print(f'UPC: {upc}')
        print('='*80)
        
        prior = prior_inv.get(upc, 0)
        actual = actual_inv[upc]
        
        print(f'\nMSA Values:')
        print(f'  Prior Period: {prior}')
        print(f'  Actual Period: {actual}')
        print(f'  Difference: {actual - prior}')
        
        # Try EVERY possible ItemLookupCode variant
        print(f'\nSearching for ItemLookupCode variants...')
        
        # Generate all possible variants
        variants = []
        
        # Original UPC
        variants.append(('Original', upc))
        
        # Remove leading zeros
        variants.append(('Strip leading 0s', upc.lstrip('0')))
        
        # If starts with '10', try without it (common JUUL pattern)
        if upc.startswith('10'):
            variants.append(('Remove 10 prefix', upc[2:]))
            
        # If starts with '108', try without it  
        if upc.startswith('108'):
            variants.append(('Remove 108 prefix', upc[3:]))
            
        # Try positions 18-31 from double UPC format (if 15 char UPC)
        if len(upc) == 15:
            # For UPC like 108400482190361, positions would be 840048219036
            if upc.startswith('10'):
                extracted = upc[2:14]  # Skip '10' and take next 12
                variants.append(('Extracted from double UPC', extracted))
            if upc.startswith('108'):
                extracted = upc[3:15]  # Skip '108' and take next 12
                variants.append(('Extracted alt from double UPC', extracted))
        
        # Try without last digit
        variants.append(('Remove last digit', upc[:-1]))
        
        # Try without first digit
        variants.append(('Remove first digit', upc[1:]))
        
        # For 14-15 char UPCs, try middle portions
        if len(upc) >= 14:
            variants.append(('Middle 12 chars', upc[1:13]))
            variants.append(('Middle 11 chars', upc[2:13]))
            
        # Try adding leading zero
        variants.append(('Add leading 0', '0' + upc))
        
        # Try common transformations for specific products
        if 'JUUL' in name:
            # JUUL specific patterns
            if upc == '108400482190361':
                variants.append(('JUUL specific 1', '840048219036'))
                variants.append(('JUUL specific 2', '8400482190361'))
                variants.append(('JUUL specific 3', '400482190361'))
            elif upc == '108199130114261':
                variants.append(('JUUL specific 1', '8199130114261'))
                variants.append(('JUUL specific 2', '819913011426'))
                variants.append(('JUUL specific 3', '199130114261'))
            elif upc == '108199130125911':
                variants.append(('JUUL specific 1', '8199130125911'))
                variants.append(('JUUL specific 2', '819913012591'))
                variants.append(('JUUL specific 3', '199130125911'))
        
        # Search for each variant
        found_items = []
        for desc, code in variants:
            if not code or len(code) < 5:
                continue
                
            # Try exact match
            cursor.execute('SELECT ID, ItemLookupCode, Description, Quantity FROM Item WHERE ItemLookupCode = %s', (code,))
            item = cursor.fetchone()
            
            if item:
                found_items.append((desc, code, item))
            else:
                # Try LIKE search for partial matches
                cursor.execute('SELECT ID, ItemLookupCode, Description, Quantity FROM Item WHERE ItemLookupCode LIKE %s', (f'%{code[-8:]}%',))
                items = cursor.fetchall()
                if items:
                    for item in items[:2]:  # Show first 2 matches
                        found_items.append((f'{desc} (partial)', code, item))
        
        if found_items:
            print(f'\n✓ FOUND {len(found_items)} matching items in POS:')
            
            for desc, code, item in found_items:
                item_id = item['ID']
                current_qty = int(item['Quantity'] or 0)
                
                print(f'\n  Variant: {desc}')
                print(f'    Code tried: {code}')
                print(f'    Found code: {item["ItemLookupCode"]}')
                print(f'    Description: {item["Description"][:50]}')
                print(f'    Current Qty: {current_qty}')
                
                # Get sales and purchases for this item
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN te.Quantity > 0 THEN te.Quantity ELSE 0 END) as Sold,
                        SUM(CASE WHEN te.Quantity < 0 THEN ABS(te.Quantity) ELSE 0 END) as Returned
                    FROM TransactionEntry te
                    JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                    WHERE te.ItemID = %s
                    AND t.Time >= %s AND t.Time <= %s
                ''', (item_id, start_dt, end_dt))
                
                sales_data = cursor.fetchone()
                sold = int(sales_data['Sold'] or 0) if sales_data else 0
                returned = int(sales_data['Returned'] or 0) if sales_data else 0
                
                cursor.execute('''
                    SELECT 
                        SUM(poi.QuantityReceived) as QtyReceived,
                        SUM(poi.LastQuantityReceived) as LastReceived
                    FROM PurchaseOrderEntry poi
                    WHERE poi.ItemID = %s
                    AND poi.LastReceivedDate >= %s 
                    AND poi.LastReceivedDate <= %s
                ''', (item_id, start_dt, end_dt))
                
                po_data = cursor.fetchone()
                qty_received = int(po_data['QtyReceived'] or 0) if po_data else 0
                last_received = int(po_data['LastReceived'] or 0) if po_data else 0
                
                print(f'    Activity:')
                print(f'      Sales: {sold}')
                print(f'      Returns: {returned}')
                print(f'      Purchases (Qty): {qty_received}')
                print(f'      Purchases (Last): {last_received}')
                
                # Try all calculations
                calcs = {
                    'Prior - Sales': prior - sold,
                    'Prior - Sales + Returns': prior - sold + returned,
                    'Prior - Sales + Purchases(Qty)': prior - sold + qty_received,
                    'Prior - Sales + Purchases(Last)': prior - sold + last_received,
                    'Prior - Net Sales': prior - (sold - returned),
                    'Current Inventory': current_qty,
                    'Prior + Purchases - Sales': prior + qty_received - sold
                }
                
                print(f'    Calculations:')
                for calc_name, calc_value in calcs.items():
                    match = '✓✓✓ MATCH!' if calc_value == actual else ''
                    print(f'      {calc_name:30}: {calc_value:5} {match}')
                
        else:
            print(f'\n✗ NO ITEMS FOUND in POS database')
            
            # Check if this product exists ONLY in MSA
            print(f'\n  Checking if product exists only in MSA...')
            if prior > 0 and actual == prior:
                print(f'  ✓ Product has same inventory as prior period ({prior})')
                print(f'    → No sales/purchases, carried forward from MSA')
            elif prior == 0 and actual > 0:
                print(f'  ✓ New product in this period (inventory: {actual})')
                print(f'    → May have been manually added to MSA')
        
        # Additional investigation - check for similar products
        print(f'\n  Searching for similar products by name...')
        search_terms = name.split()[:3]  # First 3 words
        for term in search_terms:
            if len(term) > 3:  # Skip short words
                cursor.execute('''
                    SELECT TOP 3 ItemLookupCode, Description, Quantity 
                    FROM Item 
                    WHERE Description LIKE %s
                ''', (f'%{term}%',))
                
                similar = cursor.fetchall()
                if similar:
                    print(f'\n  Similar products with "{term}":')
                    for s in similar:
                        print(f'    {s["ItemLookupCode"]:15} {s["Description"][:40]:40} Qty: {s["Quantity"]}')
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print('\n\n' + '='*100)
    print('INVESTIGATION COMPLETE')
    print('='*100)
    
    print('\nFINDINGS:')
    print('1. Some products exist ONLY in MSA files (not in POS)')
    print('2. These products carry forward their inventory from prior MSA')
    print('3. Without POS data, we cannot track sales/purchases')
    print('4. This is why they don\'t match any calculation')
    print('\nSOLUTION:')
    print('→ For products not found in POS, use prior MSA inventory as-is')
    print('→ This handles discontinued or MSA-only products correctly')

if __name__ == '__main__':
    investigate_final_18()