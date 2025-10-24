#!/usr/bin/env python3
"""
Analyze what MULTICAT is actually reporting as inventory
"""

from database_pymssql import connection_pool
from datetime import datetime

def analyze_multicat_logic():
    """Figure out MULTICAT's inventory logic"""
    
    print("=" * 80)
    print("ANALYZING MULTICAT INVENTORY LOGIC")
    print("=" * 80)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Test products with known MSA values
    test_products = [
        ('609249902429', 'ZYN 6MG SPEARMINT', 63),
        ('609249914422', 'ZYN 6MG SMOOTH', 54),
        ('609249901422', 'ZYN 6MG PEPPERMINT', 125),
        ('609249923226', 'ZYN 6MG MENTHOL', 51),
        ('609249900425', 'ZYN 6MG COOL MINT', 83),
    ]
    
    print("\nComparing Real MSA values with POS database:\n")
    print(f"{'Product':<30} {'MSA Val':>8} {'POS Qty':>8} {'Ratio':>8}")
    print("-" * 60)
    
    for item_code, name, msa_value in test_products:
        cursor.execute("""
            SELECT Quantity, Price, Cost
            FROM Item
            WHERE ItemLookupCode = %s
        """, (item_code,))
        
        result = cursor.fetchone()
        if result:
            pos_qty = result['Quantity']
            ratio = pos_qty / msa_value if msa_value > 0 else 0
            print(f"{name:<30} {msa_value:>8} {pos_qty:>8.0f} {ratio:>8.2f}")
    
    # Check if the pack size field might be involved
    print("\n" + "=" * 80)
    print("CHECKING PACK SIZE FIELD:")
    print("-" * 40)
    
    # Look at the BID line structure for pack size
    with open('MSA Data Fr/08082025', 'r', encoding='utf-8', errors='ignore') as f:
        line_count = 0
        for line in f:
            if line.startswith('BID') and line_count < 5:
                # Extract pack size field (around position 131-136)
                pack_size = line[131:137].strip()
                name = line[29:89].strip()
                inv_value = line[250:260].strip()
                print(f"Product: {name[:30]:<30}")
                print(f"  Pack size field: '{pack_size}'")
                print(f"  Inventory value: {inv_value}")
                line_count += 1
    
    # Check quantity on hand for all ZYN products
    print("\n" + "=" * 80)
    print("ALL ZYN PRODUCTS IN DATABASE:")
    print("-" * 40)
    
    cursor.execute("""
        SELECT ItemLookupCode, Description, Quantity, DepartmentID
        FROM Item
        WHERE Description LIKE '%ZYN%'
        ORDER BY Description
    """)
    
    print(f"{'Code':<15} {'Description':<40} {'Qty':>8}")
    print("-" * 65)
    for row in cursor.fetchall():
        print(f"{row['ItemLookupCode']:<15} {row['Description'][:40]:<40} {row['Quantity']:>8.0f}")
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print("\n" + "=" * 80)
    print("HYPOTHESIS:")
    print("-" * 40)
    print("The MSA inventory values appear to be:")
    print("1. NOT cumulative inventory tracking")
    print("2. Possibly current POS quantity but divided by ~10")
    print("3. Or manually entered values in MULTICAT")
    print("4. The erratic pattern (0, -54, 0, 63) suggests manual updates")

if __name__ == '__main__':
    analyze_multicat_logic()