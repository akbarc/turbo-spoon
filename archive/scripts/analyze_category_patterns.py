#!/usr/bin/env python3
"""
Analyze which categories are actually used in MSA files to fix the category list
"""

from collections import defaultdict
import os
from database_pymssql import connection_pool

def analyze_msa_product_categories():
    """Find which product categories appear in MSA files"""
    print("="*70)
    print("ANALYZING PRODUCT CATEGORIES IN MSA FILES")
    print("="*70)
    
    # Get all UPCs from MSA files
    msa_dir = "MSA Data Fr"
    all_msa_upcs = set()
    
    for filename in os.listdir(msa_dir):
        if filename.isdigit() and len(filename) == 8:
            filepath = os.path.join(msa_dir, filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('BID'):
                        upc = line[3:18].strip()
                        if upc:
                            all_msa_upcs.add(upc)
    
    print(f"Found {len(all_msa_upcs)} unique products in MSA files")
    
    # Connect to database and find categories
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # First, get all tobacco-related categories
    print("\n### CHECKING CURRENT CATEGORY LIST ###")
    current_categories = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]
    
    cursor.execute("""
        SELECT DISTINCT 
            c.ID as CategoryID,
            c.Name as CategoryName,
            COUNT(DISTINCT i.ItemLookupCode) as ItemCount
        FROM Category c
        LEFT JOIN Item i ON c.ID = i.CategoryID
        WHERE c.ID IN ({})
        GROUP BY c.ID, c.Name
        ORDER BY c.ID
    """.format(','.join(str(x) for x in current_categories)))
    
    print("\nCurrent categories being used:")
    for row in cursor.fetchall():
        print(f"  {row['CategoryID']:3}: {row['CategoryName'][:30]:30} - {row['ItemCount']} items")
    
    # Now find which categories MSA products actually belong to
    print("\n### FINDING ACTUAL MSA PRODUCT CATEGORIES ###")
    
    # Get categories for MSA products
    category_counts = defaultdict(lambda: {'name': '', 'count': 0, 'examples': []})
    
    for upc in all_msa_upcs:
        # Try different formats of the UPC
        formats = [
            upc,
            upc.lstrip('0'),
            upc[1:] if upc.startswith('0') else upc,
            '0' + upc,
            upc.rjust(14, '0')
        ]
        
        for fmt in formats:
            cursor.execute("""
                SELECT TOP 1
                    i.ItemLookupCode,
                    i.Description,
                    i.CategoryID,
                    c.Name as CategoryName
                FROM Item i
                LEFT JOIN Category c ON i.CategoryID = c.ID
                WHERE i.ItemLookupCode = %s
            """, fmt)
            
            result = cursor.fetchone()
            if result:
                cat_id = result['CategoryID']
                if cat_id:
                    category_counts[cat_id]['name'] = result['CategoryName'] or f'Category_{cat_id}'
                    category_counts[cat_id]['count'] += 1
                    if len(category_counts[cat_id]['examples']) < 3:
                        category_counts[cat_id]['examples'].append(result['Description'][:40])
                break
    
    # Display results
    print("\nCategories actually used by MSA products:")
    sorted_cats = sorted(category_counts.items(), key=lambda x: x[1]['count'], reverse=True)
    
    all_msa_categories = []
    for cat_id, info in sorted_cats:
        all_msa_categories.append(cat_id)
        print(f"\nCategory {cat_id}: {info['name'][:30]} ({info['count']} products)")
        for example in info['examples']:
            print(f"  - {example}")
    
    # Find missing categories
    missing_from_current = set(all_msa_categories) - set(current_categories)
    unused_in_current = set(current_categories) - set(all_msa_categories)
    
    print("\n### CATEGORY ANALYSIS RESULTS ###")
    if missing_from_current:
        print(f"\nCategories IN MSA but NOT in our list: {missing_from_current}")
        for cat_id in missing_from_current:
            cursor.execute("SELECT Name FROM Category WHERE ID = %s", cat_id)
            result = cursor.fetchone()
            if result:
                print(f"  {cat_id}: {result['Name']}")
    
    if unused_in_current:
        print(f"\nCategories in our list but NO MSA products: {unused_in_current}")
        for cat_id in unused_in_current:
            cursor.execute("SELECT Name FROM Category WHERE ID = %s", cat_id)
            result = cursor.fetchone()
            if result:
                print(f"  {cat_id}: {result['Name']} (keep for future products)")
    
    # Check all categories to find tobacco-related ones
    print("\n### SEARCHING ALL CATEGORIES FOR TOBACCO PRODUCTS ###")
    cursor.execute("""
        SELECT 
            c.ID as CategoryID,
            c.Name as CategoryName,
            COUNT(i.ID) as ItemCount
        FROM Category c
        LEFT JOIN Item i ON c.ID = i.CategoryID
        WHERE (
            UPPER(c.Name) LIKE '%TOBACCO%' OR
            UPPER(c.Name) LIKE '%CIGARETTE%' OR
            UPPER(c.Name) LIKE '%CIGAR%' OR
            UPPER(c.Name) LIKE '%SMOKE%' OR
            UPPER(c.Name) LIKE '%VAPE%' OR
            UPPER(c.Name) LIKE '%NICOTINE%' OR
            UPPER(c.Name) LIKE '%POUCH%' OR
            UPPER(c.Name) LIKE '%CHEW%' OR
            UPPER(c.Name) LIKE '%SNUFF%' OR
            UPPER(c.Name) LIKE '%PIPE%' OR
            UPPER(c.Name) LIKE '%ROLL%' OR
            UPPER(c.Name) LIKE '%BLUNT%'
        )
        GROUP BY c.ID, c.Name
        ORDER BY c.ID
    """)
    
    tobacco_categories = cursor.fetchall()
    if tobacco_categories:
        print("\nAll tobacco-related categories in database:")
        for row in tobacco_categories:
            status = "✓ IN LIST" if row['CategoryID'] in current_categories else "✗ MISSING"
            print(f"  {row['CategoryID']:3}: {row['CategoryName'][:30]:30} - {row['ItemCount']:4} items {status}")
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    # Return recommended category list
    return sorted(set(all_msa_categories) | set(current_categories))

def verify_new_products_in_categories():
    """Check if new products are being added to the right categories"""
    print("\n" + "="*70)
    print("VERIFYING NEW PRODUCT DETECTION")
    print("="*70)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Check recent products
    cursor.execute("""
        SELECT TOP 50
            i.ItemLookupCode,
            i.Description,
            i.CategoryID,
            c.Name as CategoryName,
            i.DateCreated,
            i.Quantity
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE i.DateCreated >= '2025-08-01'
        ORDER BY i.DateCreated DESC
    """)
    
    recent_products = cursor.fetchall()
    if recent_products:
        print("\nRecent products added (since 08/01/2025):")
        tobacco_cats = set()
        for row in recent_products[:20]:
            print(f"  {row['ItemLookupCode']:15} Cat {row['CategoryID']:3}: {row['Description'][:40]}")
            if row['CategoryID']:
                tobacco_cats.add(row['CategoryID'])
        
        print(f"\nCategories with new products: {sorted(tobacco_cats)}")
    
    cursor.close()
    connection_pool.return_connection(conn)

def main():
    print("Analyzing product categories to fix MSA generation...")
    print()
    
    # Analyze categories
    recommended_categories = analyze_msa_product_categories()
    
    # Verify new products
    verify_new_products_in_categories()
    
    print("\n" + "="*70)
    print("RECOMMENDED CATEGORY LIST")
    print("="*70)
    
    print(f"\nCurrent list: {[11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]}")
    print(f"Recommended: {recommended_categories}")
    
    print("\nUse this category list for accurate MSA generation:")
    print(f"TOBACCO_CATEGORIES = {recommended_categories}")

if __name__ == "__main__":
    main()