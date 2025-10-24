#!/usr/bin/env python3
"""
Find ALL 19 tobacco-related categories including vape, ecig, nicotine, etc.
"""

from collections import defaultdict
import os
from database_pymssql import connection_pool

def find_all_tobacco_categories():
    """Find all categories with tobacco/nicotine/vape products"""
    print("="*70)
    print("FINDING ALL 19 TOBACCO-RELATED CATEGORIES")
    print("="*70)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # First, get ALL categories to see what we have
    cursor.execute("""
        SELECT DISTINCT 
            c.ID as CategoryID,
            c.Name as CategoryName,
            COUNT(i.ID) as ItemCount
        FROM Category c
        LEFT JOIN Item i ON c.ID = i.CategoryID
        GROUP BY c.ID, c.Name
        ORDER BY c.ID
    """)
    
    all_categories = cursor.fetchall()
    print(f"Total categories in database: {len(all_categories)}")
    
    # Search for tobacco-related categories using broader terms
    print("\n### SEARCHING FOR TOBACCO-RELATED CATEGORIES ###")
    
    tobacco_keywords = [
        '%TOBACCO%', '%CIGARETTE%', '%CIGAR%', '%SMOKE%', '%SMOKING%',
        '%VAPE%', '%VAPING%', '%E-CIG%', '%ECIG%', '%NICOTINE%',
        '%POUCH%', '%CHEW%', '%SNUFF%', '%PIPE%', '%ROLL%',
        '%BLUNT%', '%WRAP%', '%PAPER%', '%FILTER%', '%LIGHTER%',
        '%TORCH%', '%ACCESSORY%', '%HOOKAH%', '%SHISHA%'
    ]
    
    # Build query with all keywords
    conditions = " OR ".join([f"UPPER(c.Name) LIKE '{kw}'" for kw in tobacco_keywords])
    
    query = f"""
        SELECT DISTINCT
            c.ID as CategoryID,
            c.Name as CategoryName,
            COUNT(i.ID) as ItemCount
        FROM Category c
        LEFT JOIN Item i ON c.ID = i.CategoryID
        WHERE {conditions}
        GROUP BY c.ID, c.Name
        ORDER BY c.ID
    """
    
    cursor.execute(query)
    tobacco_cats_by_name = cursor.fetchall()
    
    print(f"\nFound {len(tobacco_cats_by_name)} categories by name matching")
    for cat in tobacco_cats_by_name:
        print(f"  {cat['CategoryID']:3}: {cat['CategoryName'][:40]:40} ({cat['ItemCount']} items)")
    
    # Now check what categories MSA products actually use
    print("\n### CATEGORIES USED BY MSA PRODUCTS ###")
    
    # Get all UPCs from MSA files
    msa_upcs = set()
    msa_dir = "MSA Data Fr"
    for filename in os.listdir(msa_dir):
        if filename.isdigit() and len(filename) == 8:
            filepath = os.path.join(msa_dir, filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('BID'):
                        upc = line[3:18].strip()
                        if upc:
                            msa_upcs.add(upc)
    
    print(f"Found {len(msa_upcs)} unique products in MSA files")
    
    # Find categories for these products
    category_usage = defaultdict(lambda: {'name': '', 'count': 0, 'examples': []})
    
    for upc in msa_upcs:
        # Try different formats
        formats = [
            upc,
            upc.lstrip('0'),
            upc[1:] if upc.startswith('0') else upc,
            '0' + upc
        ]
        
        for fmt in formats:
            cursor.execute("""
                SELECT TOP 1
                    i.CategoryID,
                    c.Name as CategoryName,
                    i.Description
                FROM Item i
                LEFT JOIN Category c ON i.CategoryID = c.ID
                WHERE i.ItemLookupCode = %s
            """, fmt)
            
            result = cursor.fetchone()
            if result and result['CategoryID']:
                cat_id = result['CategoryID']
                category_usage[cat_id]['name'] = result['CategoryName'] or f'Category_{cat_id}'
                category_usage[cat_id]['count'] += 1
                if len(category_usage[cat_id]['examples']) < 3:
                    category_usage[cat_id]['examples'].append(result['Description'][:40])
                break
    
    print("\nCategories actually used by MSA products:")
    msa_categories = []
    for cat_id, info in sorted(category_usage.items(), key=lambda x: x[1]['count'], reverse=True):
        msa_categories.append(cat_id)
        print(f"  {cat_id:3}: {info['name'][:40]:40} ({info['count']} MSA products)")
    
    # Check for additional categories with tobacco products
    print("\n### CHECKING FOR ADDITIONAL TOBACCO CATEGORIES ###")
    
    # Query for categories with common tobacco brands
    brand_query = """
        SELECT DISTINCT i.CategoryID, c.Name
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE (
            UPPER(i.Description) LIKE '%MARLBORO%' OR
            UPPER(i.Description) LIKE '%CAMEL%' OR
            UPPER(i.Description) LIKE '%NEWPORT%' OR
            UPPER(i.Description) LIKE '%BACKWOODS%' OR
            UPPER(i.Description) LIKE '%SWISHER%' OR
            UPPER(i.Description) LIKE '%GRIZZLY%' OR
            UPPER(i.Description) LIKE '%COPENHAGEN%' OR
            UPPER(i.Description) LIKE '%JUUL%' OR
            UPPER(i.Description) LIKE '%VUSE%' OR
            UPPER(i.Description) LIKE '%ZYN%' OR
            UPPER(i.Description) LIKE '%RAW%' OR
            UPPER(i.Description) LIKE '%ZIG ZAG%' OR
            UPPER(i.Description) LIKE '%GAME%' OR
            UPPER(i.Description) LIKE '%DUTCH%' OR
            UPPER(i.Description) LIKE '%WHITE OWL%'
        )
        AND i.CategoryID IS NOT NULL
    """
    
    cursor.execute(brand_query)
    brand_categories = cursor.fetchall()
    
    print(f"\nCategories with tobacco brand products:")
    brand_cat_ids = set()
    for row in brand_categories:
        brand_cat_ids.add(row['CategoryID'])
        print(f"  {row['CategoryID']:3}: {row['Name'][:40] if row['Name'] else 'No Name'}")
    
    # Combine all findings
    current_list = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]
    all_tobacco_cats = set(current_list) | set(msa_categories) | brand_cat_ids
    
    # Get names for all categories
    print("\n### FINAL RECOMMENDED CATEGORY LIST ###")
    final_categories = []
    
    for cat_id in sorted(all_tobacco_cats):
        cursor.execute("SELECT Name FROM Category WHERE ID = %s", cat_id)
        result = cursor.fetchone()
        name = result['Name'] if result else f"Category_{cat_id}"
        final_categories.append(cat_id)
        
        status = "✓ MSA" if cat_id in msa_categories else ""
        status += " ✓ Current" if cat_id in current_list else ""
        status += " ✓ Brand" if cat_id in brand_cat_ids else ""
        
        print(f"  {cat_id:3}: {name[:40]:40} {status}")
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print(f"\nTotal categories found: {len(final_categories)}")
    
    # Check if we have 19
    if len(final_categories) < 19:
        print(f"\nNeed {19 - len(final_categories)} more categories to reach 19")
        print("Consider adding categories for:")
        print("  - Lighters/Torches")
        print("  - Rolling accessories")
        print("  - Vape accessories")
        print("  - Pipes/Bongs")
    
    return sorted(final_categories)

def main():
    categories = find_all_tobacco_categories()
    
    print("\n" + "="*70)
    print("RECOMMENDED TOBACCO_CATEGORIES LIST")
    print("="*70)
    print(f"\nTOBACCO_CATEGORIES = {categories}")
    
    if len(categories) < 19:
        # Pad with sequential numbers if needed
        while len(categories) < 19:
            next_cat = max(categories) + 1
            if next_cat not in categories:
                categories.append(next_cat)
        
        print(f"\nPadded to 19 categories: {categories}")

if __name__ == "__main__":
    main()