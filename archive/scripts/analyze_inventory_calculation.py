#!/usr/bin/env python3
"""
Analyze how MSA calculates inventory by examining all factors
"""

from database_pymssql import connection_pool
from datetime import datetime
from collections import defaultdict

def analyze_inventory_calculation():
    """Deep dive into inventory calculation methodology"""
    
    # Test products with known differences
    test_products = [
        # Small differences (±1-5)
        ('810090981369', 'ZLAB 7GM 6CT STRAWBERRY', 1),
        ('784762072375', 'ZIG ZAG CIG DRGBERRY 3/99', 1),
        
        # Medium differences (6-20)
        ('731000320970', 'SKOAL XTRA R/BLND 5 CT', 4),
        
        # Large differences (>20)
        ('769577921186', 'LOOSE LEAF 20/2CT COOKIE N CRM', -220),
        ('860001473353', 'SEA PODS BASIC KIT SILVER 1CT', -99),
    ]
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # MSA period
    start_dt = datetime(2025, 8, 2, 0, 0, 0)  # Saturday
    end_dt = datetime(2025, 8, 8, 23, 59, 59)  # Friday
    
    print("="*70)
    print("COMPREHENSIVE INVENTORY CALCULATION ANALYSIS")
    print("="*70)
    print(f"MSA Period: {start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%m/%d %H:%M')}")
    
    for msa_upc, name, expected_diff in test_products:
        print(f"\n{'='*70}")
        print(f"{name}")
        print(f"MSA UPC: {msa_upc}")
        print("="*70)
        
        # Find ItemLookupCode
        possible_codes = [
            msa_upc.strip(),
            msa_upc.lstrip('0'),
            msa_upc[:-1] if msa_upc.endswith('0') else msa_upc,
            msa_upc.zfill(12),
            msa_upc.zfill(13),
            msa_upc.zfill(14),
        ]
        
        item_code = None
        item_id = None
        for code in possible_codes:
            cursor.execute('SELECT ID, ItemLookupCode, Description, Quantity FROM Item WHERE ItemLookupCode = %s', (code,))
            result = cursor.fetchone()
            if result:
                item_code = result['ItemLookupCode']
                item_id = result['ID']
                current_qty = int(result['Quantity'] or 0)
                print(f"Found ItemCode: {item_code}")
                print(f"Current Inventory: {current_qty}")
                break
        
        if not item_code:
            print("NOT FOUND IN DATABASE")
            continue
        
        # 1. SALES during period (positive quantity = sold)
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT t.TransactionNumber) as SalesTransCount,
                SUM(te.Quantity) as TotalSold
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE te.ItemID = %s
            AND t.Time >= %s AND t.Time <= %s
            AND te.Quantity > 0
        ''', (item_id, start_dt, end_dt))
        
        sales_result = cursor.fetchone()
        sales_count = sales_result['SalesTransCount'] or 0
        total_sold = int(sales_result['TotalSold'] or 0)
        
        print(f"\n1. SALES During Period:")
        print(f"   Transactions: {sales_count}")
        print(f"   Units Sold: {total_sold}")
        
        # 2. RETURNS during period (negative quantity in TransactionEntry)
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT t.TransactionNumber) as ReturnTransCount,
                SUM(ABS(te.Quantity)) as TotalReturned
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE te.ItemID = %s
            AND t.Time >= %s AND t.Time <= %s
            AND te.Quantity < 0
        ''', (item_id, start_dt, end_dt))
        
        return_result = cursor.fetchone()
        return_count = return_result['ReturnTransCount'] or 0
        total_returned = int(return_result['TotalReturned'] or 0)
        
        print(f"\n2. RETURNS During Period:")
        print(f"   Transactions: {return_count}")
        print(f"   Units Returned: {total_returned}")
        
        # 3. PURCHASE ORDERS received during period
        cursor.execute('''
            SELECT 
                COUNT(*) as POCount,
                SUM(poi.QuantityReceived) as TotalReceived,
                SUM(poi.LastQuantityReceived) as LastReceived
            FROM PurchaseOrderEntry poi
            WHERE poi.ItemID = %s
            AND poi.LastReceivedDate >= %s AND poi.LastReceivedDate <= %s
        ''', (item_id, start_dt, end_dt))
        
        po_result = cursor.fetchone()
        po_count = po_result['POCount'] or 0
        total_received = int(po_result['TotalReceived'] or 0)
        last_received = int(po_result['LastReceived'] or 0)
        
        print(f"\n3. PURCHASE ORDERS During Period:")
        print(f"   PO Count: {po_count}")
        print(f"   Total Received: {total_received}")
        print(f"   Last Received: {last_received}")
        
        # 4. INVENTORY ADJUSTMENTS (check InventoryTransferLog)
        cursor.execute('''
            SELECT 
                COUNT(*) as AdjustmentCount,
                SUM(Quantity) as TotalAdjustment
            FROM InventoryTransferLog
            WHERE ItemID = %s
            AND DateTransferred >= %s AND DateTransferred <= %s
        ''', (item_id, start_dt, end_dt))
        
        adj_result = cursor.fetchone()
        adj_count = adj_result['AdjustmentCount'] or 0
        total_adjustment = int(adj_result['TotalAdjustment'] or 0) if adj_result['TotalAdjustment'] else 0
        
        print(f"\n4. INVENTORY ADJUSTMENTS During Period:")
        print(f"   Adjustment Count: {adj_count}")
        print(f"   Total Adjustment: {total_adjustment}")
        
        # 5. Check for manual adjustments in Transaction comments
        cursor.execute('''
            SELECT TOP 5
                t.Time,
                t.TransactionNumber,
                te.Quantity,
                t.Comment,
                t.Total
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE te.ItemID = %s
            AND t.Time >= %s AND t.Time <= %s
            AND (t.Comment IS NOT NULL 
                OR t.Total = 0 
                OR ABS(te.Quantity) > 10)
            ORDER BY t.Time
        ''', (item_id, start_dt, end_dt))
        
        special_trans = cursor.fetchall()
        if special_trans:
            print(f"\n5. SPECIAL TRANSACTIONS (manual/zero-dollar/bulk):")
            for trans in special_trans:
                print(f"   {trans['Time'].strftime('%m/%d %H:%M')}: Qty={trans['Quantity']:3.0f}, Total=${trans['Total']:6.2f}, Comment={trans['Comment'] or 'None'}")
        
        # 6. Calculate what happened AFTER the MSA period
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN te.Quantity > 0 THEN te.Quantity ELSE 0 END) as SoldAfter,
                SUM(CASE WHEN te.Quantity < 0 THEN ABS(te.Quantity) ELSE 0 END) as ReturnedAfter
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE te.ItemID = %s
            AND t.Time > %s
        ''', (item_id, end_dt))
        
        after_result = cursor.fetchone()
        sold_after = int(after_result['SoldAfter'] or 0)
        returned_after = int(after_result['ReturnedAfter'] or 0)
        
        cursor.execute('''
            SELECT SUM(poi.LastQuantityReceived) as ReceivedAfter
            FROM PurchaseOrderEntry poi
            WHERE poi.ItemID = %s
            AND poi.LastReceivedDate > %s
        ''', (item_id, end_dt))
        
        po_after = cursor.fetchone()
        received_after = int(po_after['ReceivedAfter'] or 0)
        
        print(f"\n6. ACTIVITY AFTER MSA Period (for point-in-time calc):")
        print(f"   Sold After: {sold_after}")
        print(f"   Returned After: {returned_after}")
        print(f"   Received After: {received_after}")
        
        # 7. Calculate different inventory methods
        print(f"\n7. INVENTORY CALCULATIONS:")
        
        # Method 1: Current POS
        print(f"   A. Current POS: {current_qty}")
        
        # Method 2: Point-in-time (our current method)
        pit_inventory = current_qty + sold_after - returned_after - received_after
        print(f"   B. Point-in-time: {current_qty} + {sold_after} - {returned_after} - {received_after} = {pit_inventory}")
        
        # Method 3: Starting inventory + activity
        # Try to calculate starting inventory
        starting_inv = current_qty + total_sold - total_returned - total_received - total_adjustment
        ending_inv_method3 = starting_inv - total_sold + total_returned + total_received + total_adjustment
        print(f"   C. Activity-based: Start={starting_inv} - Sold={total_sold} + Returned={total_returned} + Received={total_received} + Adj={total_adjustment} = {ending_inv_method3}")
        
        # Method 4: Include all adjustments
        comprehensive = current_qty + sold_after - received_after
        if current_qty < 0:  # Handle negative inventory
            comprehensive = abs(current_qty)
        print(f"   D. Comprehensive: {comprehensive}")
        
        # Get actual MSA values
        print(f"\n8. MSA COMPARISON:")
        gen_file = 'generated_msa_08082025_perfect_bid.txt'
        act_file = 'MSA Data Fr/08082025'
        
        gen_inv = 0
        act_inv = 0
        
        with open(gen_file, 'r') as f:
            for line in f:
                if line.startswith('BID') and msa_upc in line:
                    if len(line) >= 261:
                        gen_inv_str = line[247:261]
                    elif len(line) >= 210:
                        gen_inv_str = line[199:210]
                    else:
                        continue
                    gen_inv = int(gen_inv_str.replace('003', '').replace('-', '').strip())
                    break
        
        with open(act_file, 'r') as f:
            for line in f:
                if line.startswith('BID') and msa_upc in line:
                    if len(line) >= 261:
                        act_inv_str = line[247:261]
                    elif len(line) >= 210:
                        act_inv_str = line[199:210]
                    else:
                        continue
                    act_inv = int(act_inv_str.replace('003', '').replace('-', '').strip())
                    break
        
        print(f"   Generated MSA: {gen_inv}")
        print(f"   Actual MSA: {act_inv}")
        print(f"   Difference: {act_inv - gen_inv:+d}")
        print(f"   Expected Diff: {expected_diff:+d}")
        
        # Check which method is closest
        print(f"\n9. WHICH METHOD IS CLOSEST TO MSA?")
        methods = [
            ('Current POS', current_qty),
            ('Point-in-time', pit_inventory),
            ('Activity-based', ending_inv_method3),
            ('Comprehensive', comprehensive),
            ('Absolute if negative', abs(current_qty) if current_qty < 0 else current_qty),
        ]
        
        for method_name, value in methods:
            diff = act_inv - value
            print(f"   {method_name:20}: {value:4} (diff: {diff:+4})")
    
    cursor.close()
    connection_pool.return_connection(conn)

if __name__ == '__main__':
    analyze_inventory_calculation()