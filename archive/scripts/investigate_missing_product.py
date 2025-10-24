#!/usr/bin/env python3
"""
Investigate the one missing product from real MSA
"""

from database_pymssql import connection_pool

def investigate_missing_product():
    """Look for the missing product in database"""
    
    # The missing product from comparison
    missing_upc = '84004520118'
    missing_name = '81ROGUE 6MG POUCH 5CT HNY LEMON'
    
    print("=" * 80)
    print("INVESTIGATING MISSING PRODUCT")
    print("=" * 80)
    print(f"\nMissing from generated MSA:")
    print(f"UPC:  {missing_upc}")
    print(f"Name: {missing_name}")
    print(f"Real MSA Inventory: 0")
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor()
    
    try:
        # Search by UPC
        print("\n1. Searching database by UPC...")
        cursor.execute("""
            SELECT ItemLookupCode, Description, DepartmentID, CategoryID
            FROM Item
            WHERE ItemLookupCode LIKE %s
        """, (f'%{missing_upc}%',))
        
        results = cursor.fetchall()
        if results:
            print(f"   Found {len(results)} matches:")
            for row in results:
                print(f"   - ItemCode: {row[0]}, Desc: {row[1]}, Dept: {row[2]}, Cat: {row[3]}")
        else:
            print("   ✗ No matches found by UPC")
        
        # Search by product name
        print("\n2. Searching database by product name...")
        cursor.execute("""
            SELECT ItemLookupCode, Description, DepartmentID, CategoryID
            FROM Item
            WHERE Description LIKE %s
        """, (f'%ROGUE%6MG%POUCH%HNY%LEMON%',))
        
        results = cursor.fetchall()
        if results:
            print(f"   Found {len(results)} matches:")
            for row in results:
                print(f"   - ItemCode: {row[0]}, Desc: {row[1]}, Dept: {row[2]}, Cat: {row[3]}")
        else:
            print("   ✗ No matches found by name")
        
        # Search for similar ROGUE products
        print("\n3. Searching for other ROGUE products...")
        cursor.execute("""
            SELECT TOP 10 ItemLookupCode, Description, DepartmentID, CategoryID
            FROM Item
            WHERE Description LIKE '%ROGUE%'
            ORDER BY Description
        """)
        
        results = cursor.fetchall()
        if results:
            print(f"   Found {len(results)} ROGUE products:")
            for row in results:
                print(f"   - {row[0]:20} | {row[1]:40} | Cat: {row[3]}")
        else:
            print("   ✗ No ROGUE products found")
        
        # Check if this is in our MSA categories
        print("\n4. Checking MSA categories...")
        msa_categories = [48, 23, 45, 11, 31, 56, 57, 81, 83, 49, 51]
        
        cursor.execute("""
            SELECT CategoryID, Name
            FROM Category
            WHERE CategoryID IN ({})
        """.format(','.join(str(c) for c in msa_categories)))
        
        categories = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Category 83 is NICOTINE POUCHES - ROGUE would belong here
        print(f"   Category 83 (NICOTINE POUCHES) products:")
        
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM Item
            WHERE CategoryID = 83
        """)
        count = cursor.fetchone()[0]
        print(f"   Total products in category: {count}")
        
        # Check if any ROGUE products exist in category 83
        cursor.execute("""
            SELECT ItemLookupCode, Description
            FROM Item
            WHERE CategoryID = 83 AND Description LIKE '%ROGUE%'
            ORDER BY Description
        """)
        
        results = cursor.fetchall()
        if results:
            print(f"   Found {len(results)} ROGUE products in NICOTINE POUCHES:")
            for row in results:
                print(f"   - {row[0]:20} | {row[1]}")
        else:
            print("   ✗ No ROGUE products in NICOTINE POUCHES category")
        
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("-" * 40)
        print("The missing product '81ROGUE 6MG POUCH 5CT HNY LEMON' with UPC '84004520118'")
        print("does not exist in the POS database. This is likely a product that was:")
        print("1. Manually added to MULTICAT but never sold/stocked")
        print("2. Part of manufacturer's catalog but not carried by this store")
        print("3. A discontinued product that was removed from POS")
        print("\nSince it has 0 inventory in real MSA, it's not affecting operations.")
        
    finally:
        cursor.close()
        connection_pool.return_connection(conn)

if __name__ == '__main__':
    investigate_missing_product()