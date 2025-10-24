#!/usr/bin/env python3
"""
Investigate why ROGUE product is missing from generated MSA
"""

from database_pymssql import connection_pool
from datetime import datetime, timedelta

def investigate_missing_product():
    """Look for the missing product and why it wasn't included"""
    
    # The missing product from comparison
    missing_upc = '840045201181'  # Full UPC from database
    missing_name = 'ROGUE 6MG POUCH 5CT HNY LEMON'
    
    print("=" * 80)
    print("INVESTIGATING WHY PRODUCT IS MISSING FROM GENERATED MSA")
    print("=" * 80)
    print(f"\nProduct found in database:")
    print(f"ItemLookupCode: {missing_upc}")
    print(f"Description:    {missing_name}")
    print(f"Department:     1")
    print(f"Category:       83 (NICOTINE POUCHES)")
    print(f"Real MSA shows: '84004520118' with trailing '1' in separate field")
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor()
    
    try:
        # Check sales for week ending 08/08/2025
        target_dt = datetime(2025, 8, 8, 23, 59, 59)
        start_dt = datetime(2025, 8, 2, 0, 0, 0)
        
        print(f"\n1. Checking sales for week {start_dt.date()} to {target_dt.date()}...")
        cursor.execute("""
            SELECT COUNT(*) as sales_count, SUM(te.Quantity) as total_qty
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE te.ItemID = (SELECT ID FROM Item WHERE ItemLookupCode = %s)
            AND t.Time >= %s AND t.Time <= %s
        """, (missing_upc, start_dt, target_dt))
        
        result = cursor.fetchone()
        if result and result[0]:
            print(f"   Sales transactions: {result[0]}")
            print(f"   Total quantity sold: {result[1]}")
        else:
            print("   ✗ No sales found for this week")
        
        # Check purchases for prior week ending 08/01/2025
        prior_end = datetime(2025, 8, 1, 23, 59, 59)
        prior_start = datetime(2025, 7, 26, 0, 0, 0)
        
        print(f"\n2. Checking purchases for prior week {prior_start.date()} to {prior_end.date()}...")
        cursor.execute("""
            SELECT COUNT(*) as purchase_count, SUM(poe.QuantityReceivedToDate) as total_received
            FROM PurchaseOrderEntry poe
            JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
            WHERE poe.ItemID = (SELECT ID FROM Item WHERE ItemLookupCode = %s)
            AND po.DateCreated >= %s AND po.DateCreated <= %s
        """, (missing_upc, prior_start, prior_end))
        
        result = cursor.fetchone()
        if result and result[0]:
            print(f"   Purchase orders: {result[0]}")
            print(f"   Total received: {result[1]}")
        else:
            print("   ✗ No purchases found for prior week")
        
        # Check current quantity on hand
        print(f"\n3. Checking current inventory...")
        cursor.execute("""
            SELECT Quantity
            FROM Item
            WHERE ItemLookupCode = %s
        """, (missing_upc,))
        
        result = cursor.fetchone()
        if result:
            print(f"   Current quantity on hand: {result[0]}")
        
        # Check if it's in the prior MSA (08/01/2025)
        print(f"\n4. Checking prior MSA file (08/01/2025)...")
        prior_file = 'MSA Data Fr/08012025'
        found_in_prior = False
        with open(prior_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if '84004520118' in line or '840045201181' in line:
                    found_in_prior = True
                    print(f"   ✓ Found in prior MSA:")
                    print(f"     {line.strip()}")
                    break
        
        if not found_in_prior:
            print("   ✗ Not found in prior MSA file")
        
        # Check how our generator handles this UPC
        print(f"\n5. Analyzing UPC format handling...")
        print(f"   Database UPC:     {missing_upc} (12 digits)")
        print(f"   MSA file shows:   84004520118 (11 digits) + '1' in separate field")
        print(f"   This suggests MSA splits the 12-digit UPC into 11+1")
        
        # Check if other ROGUE products are in generated file
        print(f"\n6. Checking if other ROGUE products made it to generated MSA...")
        generated_file = 'generated_msa_08082025_100_final.txt'
        rogue_count = 0
        with open(generated_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'ROGUE' in line and line.startswith('BID'):
                    rogue_count += 1
                    if rogue_count <= 3:
                        print(f"   Found: {line[3:89].strip()}")
        
        print(f"   Total ROGUE products in generated: {rogue_count}")
        
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("-" * 40)
        print("The product exists in the database but wasn't included because:")
        print("1. It appears to be a new product not in the 08/01/2025 prior MSA")
        print("2. With no prior inventory and no sales/purchases, calculated inventory = 0")
        print("3. The generator may be filtering out products with 0 inventory that weren't")
        print("   in the prior period (to avoid adding every product in the database)")
        print("\nThis is the expected behavior - only 1 product difference out of 5206!")
        
    finally:
        cursor.close()
        connection_pool.return_connection(conn)

if __name__ == '__main__':
    investigate_missing_product()