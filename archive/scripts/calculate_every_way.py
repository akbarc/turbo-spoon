#!/usr/bin/env python3
"""
Calculate inventory for problem products EVERY possible way to find the pattern
"""

from database_pymssql import connection_pool
from datetime import datetime, timedelta
import json

def calculate_every_possible_way():
    # Test across ALL periods to find the pattern
    test_periods = [
        ("06202025", "06272025"),
        ("06272025", "07042025"),
        ("07042025", "07112025"),
        ("07112025", "07182025"),
        ("07182025", "07252025"),
        ("07252025", "08012025"),
        ("08012025", "08082025")
    ]
    
    # Known problem products
    problem_products = [
        '108400482190361',  # JUUL VIRG TOBACCO 5% 6PK 4CT
        '108199130114261',  # JUUL VIRG TOBACCO 5% 4PK 8CT
        '108199130125911',  # JUUL CLASSIC MENTHL 5% 4PK 8CT
        '6851419131520',    # 24/7 MENTHOL 100 1CTN
        '6851419130770',    # 24/7 LIGHT 100S BOX
        '0790831595090',    # JOB 1.5 50CT
        '108575450120771',  # BOB M HEMP WRAP STRBRY
        '701375001860',     # BLK & MLD CGR 5PKS
    ]
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Load UPC mapping
    with open('upc_to_itemcode_mapping.json', 'r') as f:
        upc_mapping = json.load(f)
    
    print('='*100)
    print('CALCULATING EVERY POSSIBLE WAY FOR PROBLEM PRODUCTS')
    print('='*100)
    
    all_results = {}
    
    for prior_date, target_date in test_periods:
        print(f'\n\nPERIOD: {prior_date} → {target_date}')
        print('-'*100)
        
        prior_file = f'MSA Data Fr/{prior_date}'
        actual_file = f'MSA Data Fr/{target_date}'
        
        # Parse MSA files
        prior_inv = {}
        actual_inv = {}
        product_names = {}
        
        # Get prior inventory
        try:
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
        except:
            continue
        
        # Get actual inventory
        with open(actual_file, 'r') as f:
            for line in f:
                if line.startswith('BID'):
                    upc = line[3:18].strip()
                    
                    # Get name
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
                    actual_inv[upc] = inv
                    product_names[upc] = name
        
        # Calculate date range
        target_dt = datetime.strptime(f"2025{target_date[:4]}", '%Y%m%d')
        if target_dt.weekday() != 4:
            days_to_friday = (4 - target_dt.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            target_dt = target_dt + timedelta(days=days_to_friday)
        
        start_dt = target_dt - timedelta(days=6)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = target_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Analyze each problem product
        for upc in problem_products:
            if upc not in actual_inv:
                continue
            
            prior = prior_inv.get(upc, 0)
            actual = actual_inv[upc]
            name = product_names.get(upc, 'Unknown')[:30]
            
            # Get all possible ItemLookupCodes
            possible_codes = [
                upc,
                upc_mapping.get(upc, ''),
                upc.lstrip('0'),
                upc[:-1] if upc.endswith('0') else '',
                upc + '0',
                '0' + upc,
            ]
            possible_codes = [c for c in possible_codes if c]
            
            # Try each code
            results = {
                'prior': prior,
                'actual': actual,
                'name': name
            }
            
            for code in possible_codes:
                if not code:
                    continue
                
                # Find item
                cursor.execute('SELECT ID, Quantity FROM Item WHERE ItemLookupCode = %s', (code,))
                item = cursor.fetchone()
                
                if item:
                    item_id = item['ID']
                    current_qty = int(item['Quantity'] or 0)
                    
                    # Method 1: Current inventory
                    results[f'current_{code[:6]}'] = current_qty
                    
                    # Method 2: Sales during period
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
                    
                    # Method 3: Purchases during period
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
                    
                    # Method 4: Activity AFTER period (for point-in-time)
                    cursor.execute('''
                        SELECT SUM(te.Quantity) as SoldAfter
                        FROM TransactionEntry te
                        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                        WHERE te.ItemID = %s
                        AND t.Time > %s
                        AND te.Quantity > 0
                    ''', (item_id, end_dt))
                    
                    after_data = cursor.fetchone()
                    sold_after = int(after_data['SoldAfter'] or 0) if after_data else 0
                    
                    cursor.execute('''
                        SELECT SUM(poi.LastQuantityReceived) as ReceivedAfter
                        FROM PurchaseOrderEntry poi
                        WHERE poi.ItemID = %s
                        AND poi.LastReceivedDate > %s
                    ''', (item_id, end_dt))
                    
                    po_after = cursor.fetchone()
                    received_after = int(po_after['ReceivedAfter'] or 0) if po_after else 0
                    
                    # Store all data
                    results['sold'] = sold
                    results['returned'] = returned
                    results['qty_received'] = qty_received
                    results['last_received'] = last_received
                    results['sold_after'] = sold_after
                    results['received_after'] = received_after
                    
                    # Calculate all possible ways
                    results['calc1_prior_minus_sold'] = prior - sold
                    results['calc2_prior_minus_sold_plus_returned'] = prior - sold + returned
                    results['calc3_prior_minus_sold_plus_received'] = prior - sold + qty_received
                    results['calc4_prior_minus_sold_plus_last_received'] = prior - sold + last_received
                    results['calc5_prior_minus_net_sales'] = prior - (sold - returned)
                    results['calc6_pit_current_plus_after'] = current_qty + sold_after - received_after
                    results['calc7_prior_plus_received_minus_sold'] = prior + qty_received - sold
                    results['calc8_prior_plus_last_minus_sold'] = prior + last_received - sold
                    
                    # Check if any calculation matches
                    for key, value in results.items():
                        if key.startswith('calc') and value == actual:
                            results['MATCH'] = f'{key} = {value}'
                            break
                    
                    break  # Found item, stop trying codes
            
            # Store results
            key = f'{target_date}_{upc}'
            all_results[key] = results
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    # Analyze patterns
    print('\n\n' + '='*100)
    print('PATTERN ANALYSIS')
    print('='*100)
    
    # Group by product
    by_product = {}
    for key, results in all_results.items():
        upc = key.split('_')[1]
        if upc not in by_product:
            by_product[upc] = []
        by_product[upc].append(results)
    
    # Find which calculation works for each product
    for upc, periods in by_product.items():
        print(f'\n{upc}:')
        
        # Check which calculations match
        calc_matches = {}
        for period in periods:
            if 'MATCH' in period:
                calc_name = period['MATCH'].split(' = ')[0]
                if calc_name not in calc_matches:
                    calc_matches[calc_name] = 0
                calc_matches[calc_name] += 1
        
        if calc_matches:
            print(f'  Matching calculations:')
            for calc, count in sorted(calc_matches.items(), key=lambda x: x[1], reverse=True):
                print(f'    {calc}: {count} periods')
        else:
            print(f'  NO MATCHING CALCULATION FOUND')
            
            # Show sample data
            if periods:
                p = periods[-1]  # Most recent
                print(f'    Prior: {p.get("prior", 0)}')
                print(f'    Actual: {p.get("actual", 0)}')
                print(f'    Sold: {p.get("sold", 0)}')
                print(f'    Returned: {p.get("returned", 0)}')
                print(f'    Received: {p.get("qty_received", 0)}')
                print(f'    Last Received: {p.get("last_received", 0)}')
                
                # Check for patterns
                diff = p.get("actual", 0) - p.get("prior", 0)
                print(f'    Actual - Prior = {diff}')
                
                # Check if it's a multiple of something
                if diff != 0:
                    for mult in [5, 10, 12, 20, 24, 25, 50, 100]:
                        if diff % mult == 0:
                            print(f'    Difference is multiple of {mult}: {diff} = {diff//mult} × {mult}')
                            break
    
    # Final analysis
    print('\n' + '='*100)
    print('FINAL INSIGHTS')
    print('='*100)
    
    # Check if there's a consistent pattern
    no_match_products = []
    for upc, periods in by_product.items():
        has_match = any('MATCH' in p for p in periods)
        if not has_match:
            no_match_products.append(upc)
    
    if no_match_products:
        print(f'\nProducts with NO matching calculation: {len(no_match_products)}')
        for upc in no_match_products:
            if periods := by_product.get(upc):
                p = periods[-1]
                print(f'  {upc}: {p.get("name", "Unknown")[:30]}')
        
        print('\nThese products may have:')
        print('  1. Data in a different table we haven\'t checked')
        print('  2. Manual adjustments stored elsewhere')
        print('  3. Different calculation rules')

if __name__ == '__main__':
    calculate_every_possible_way()