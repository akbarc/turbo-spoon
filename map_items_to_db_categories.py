import pymssql
import os
from dotenv import load_dotenv
import csv
from collections import Counter

# Load environment variables
load_dotenv()

# Database connection parameters
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_DATABASE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')

print(f"Connecting to database: {database} on server: {server}")

try:
    # Connect to database
    conn = pymssql.connect(
        server=server,
        user=username,
        password=password,
        database=database,
        tds_version='7.0'
    )
    cursor = conn.cursor()
    
    # First, get all items from Items CSV
    print("\nReading Items- 06202025.csv...")
    items_barcodes = set()
    items_categories = {}
    
    with open('Items- 06202025.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                barcode = row[0].strip()
                category_id = row[1].strip()
                items_barcodes.add(barcode)
                items_categories[barcode] = category_id
    
    print(f"Found {len(items_barcodes)} unique barcodes in Items CSV")
    
    # Now also check MSA files for barcodes
    print("\nChecking MSA generated files...")
    msa_files = [
        'generated_msa_08082025.txt',
        'final_msa_08082025.txt',
        'complete_pos_generated_08012025.txt',
        'pos_generated_08012025.txt'
    ]
    
    msa_barcodes = set()
    for filename in msa_files:
        if os.path.exists(filename):
            print(f"  Reading {filename}...")
            with open(filename, 'r') as f:
                for line in f:
                    # MSA format has barcode in specific position
                    if len(line) > 20:
                        barcode = line[7:20].strip()
                        if barcode and barcode.isdigit():
                            msa_barcodes.add(barcode)
    
    print(f"Found {len(msa_barcodes)} unique barcodes in MSA files")
    
    # Combine all barcodes
    all_barcodes = items_barcodes.union(msa_barcodes)
    print(f"\nTotal unique barcodes to check: {len(all_barcodes)}")
    
    # Now check which categories these items belong to in the database
    print("\n" + "="*60)
    print("Checking database for these items...")
    
    # Get all tables that might contain product information
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        AND (TABLE_NAME LIKE '%item%' OR TABLE_NAME LIKE '%product%' OR TABLE_NAME LIKE '%inventory%')
        ORDER BY TABLE_NAME
    """)
    
    tables = cursor.fetchall()
    print(f"\nFound these product-related tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check Item table (most likely the correct one)
    print("\n" + "="*60)
    print("Checking Item table structure...")
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Item'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = [row[0] for row in cursor.fetchall()]
    print(f"Item table columns: {', '.join(columns[:10])}...")
    
    # Find items and their categories
    barcode_list = list(all_barcodes)
    category_distribution = Counter()
    found_items = []
    
    # Process in batches to avoid query size limits
    batch_size = 500
    for i in range(0, len(barcode_list), batch_size):
        batch = barcode_list[i:i+batch_size]
        batch_str = "','".join(batch)
        
        query = f"""
            SELECT 
                i.ItemLookupCode as Barcode,
                i.Description,
                i.CategoryID,
                c.Name as CategoryName
            FROM Item i
            LEFT JOIN Category c ON i.CategoryID = c.ID
            WHERE i.ItemLookupCode IN ('{batch_str}')
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        for barcode, desc, cat_id, cat_name in results:
            found_items.append((barcode, desc, cat_id, cat_name))
            if cat_id:
                category_distribution[cat_name if cat_name else f"Category_{cat_id}"] += 1
    
    print(f"\nFound {len(found_items)} items in database")
    
    # Show category distribution
    print("\n" + "="*60)
    print("CATEGORIES USED IN ITEMS CSV & MSA FILES:")
    print("="*60)
    
    sorted_categories = sorted(category_distribution.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nTotal categories used: {len(sorted_categories)}")
    print("-"*60)
    for cat_name, count in sorted_categories:
        print(f"{cat_name:30} - {count:5} items")
    
    # Save detailed mapping
    output_file = 'Items_MSA_Category_Mapping.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Barcode', 'Description', 'Category_ID', 'Category_Name', 'Items_CSV_Category'])
        
        for barcode, desc, cat_id, cat_name in found_items:
            items_cat = items_categories.get(barcode, 'N/A')
            writer.writerow([barcode, desc, cat_id, cat_name, items_cat])
    
    print(f"\nDetailed mapping saved to: {output_file}")
    
    # Check which categories from the full list are NOT used
    cursor.execute("SELECT ID, Name FROM Category ORDER BY ID")
    all_db_categories = cursor.fetchall()
    
    used_category_names = set(cat[0] for cat in sorted_categories)
    unused_categories = []
    
    for cat_id, cat_name in all_db_categories:
        if cat_name not in used_category_names:
            unused_categories.append((cat_id, cat_name))
    
    print("\n" + "="*60)
    print("CATEGORIES NOT USED IN ITEMS/MSA:")
    print("="*60)
    for cat_id, cat_name in unused_categories:
        print(f"ID {cat_id:3}: {cat_name}")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()