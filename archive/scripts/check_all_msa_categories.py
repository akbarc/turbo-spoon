import pymssql
import os
from dotenv import load_dotenv
from collections import Counter
import glob

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
    
    # Get all MSA files from MSA Data Fr folder
    msa_folder = "MSA Data Fr"
    msa_dates = ["06202025", "06272025", "07042025", "07112025", "07182025", "07252025", "08012025", "08082025"]
    
    all_msa_barcodes = set()
    file_barcode_counts = {}
    
    print("\nReading MSA files from 'MSA Data Fr' folder...")
    print("="*60)
    
    for date in msa_dates:
        file_path = os.path.join(msa_folder, date)
        if os.path.exists(file_path):
            print(f"\nReading {date}...")
            barcodes_in_file = set()
            
            with open(file_path, 'r') as f:
                for line in f:
                    # MSA format: positions 8-20 contain the barcode (13 digits)
                    if len(line) > 20:
                        barcode = line[7:20].strip()
                        if barcode and barcode.isdigit():
                            barcodes_in_file.add(barcode)
                            all_msa_barcodes.add(barcode)
            
            file_barcode_counts[date] = len(barcodes_in_file)
            print(f"  Found {len(barcodes_in_file)} unique barcodes")
    
    print(f"\n{'='*60}")
    print(f"Total unique barcodes across all MSA files: {len(all_msa_barcodes)}")
    print("="*60)
    
    # Now check which categories these items belong to in the database
    print("\nChecking database for category distribution...")
    
    barcode_list = list(all_msa_barcodes)
    category_distribution = Counter()
    found_items = []
    missing_barcodes = []
    
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
        
        found_barcodes = set()
        for barcode, desc, cat_id, cat_name in results:
            found_items.append((barcode, desc, cat_id, cat_name))
            found_barcodes.add(barcode)
            if cat_id:
                category_distribution[cat_name if cat_name else f"Category_{cat_id}"] += 1
        
        # Track missing barcodes
        for barcode in batch:
            if barcode not in found_barcodes:
                missing_barcodes.append(barcode)
    
    print(f"\nFound {len(found_items)} items in database")
    print(f"Missing {len(missing_barcodes)} items not in database")
    
    # Show category distribution
    print("\n" + "="*60)
    print("CATEGORIES USED ACROSS ALL MSA FILES:")
    print("="*60)
    
    sorted_categories = sorted(category_distribution.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nTotal categories used: {len(sorted_categories)}")
    print("-"*60)
    for cat_name, count in sorted_categories:
        print(f"{cat_name:30} - {count:5} items")
    
    # Get category IDs for reference
    print("\n" + "="*60)
    print("CATEGORY IDs FOR MSA CATEGORIES:")
    print("="*60)
    
    category_names = [cat[0] for cat in sorted_categories]
    if category_names:
        cat_name_list = "','".join(category_names)
        cursor.execute(f"""
            SELECT ID, Name, Code
            FROM Category
            WHERE Name IN ('{cat_name_list}')
            ORDER BY ID
        """)
        
        cat_results = cursor.fetchall()
        for cat_id, cat_name, cat_code in cat_results:
            print(f"ID {cat_id:3}: {cat_name:30} (Code: {cat_code})")
    
    # Check which categories are NOT used in MSA
    cursor.execute("SELECT ID, Name FROM Category ORDER BY ID")
    all_db_categories = cursor.fetchall()
    
    used_category_names = set(cat[0] for cat in sorted_categories)
    unused_categories = []
    
    for cat_id, cat_name in all_db_categories:
        if cat_name not in used_category_names:
            unused_categories.append((cat_id, cat_name))
    
    print("\n" + "="*60)
    print("CATEGORIES NOT USED IN ANY MSA FILE:")
    print("="*60)
    for cat_id, cat_name in unused_categories:
        print(f"ID {cat_id:3}: {cat_name}")
    
    # Save detailed report
    output_file = 'Complete_MSA_Category_Analysis.txt'
    with open(output_file, 'w') as f:
        f.write("COMPLETE MSA CATEGORY ANALYSIS\n")
        f.write("="*60 + "\n\n")
        
        f.write("File Summary:\n")
        f.write("-"*40 + "\n")
        for date, count in file_barcode_counts.items():
            f.write(f"{date}: {count} unique barcodes\n")
        
        f.write(f"\nTotal unique barcodes: {len(all_msa_barcodes)}\n")
        f.write(f"Found in database: {len(found_items)}\n")
        f.write(f"Not in database: {len(missing_barcodes)}\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("CATEGORIES USED IN MSA:\n")
        f.write("-"*60 + "\n")
        for cat_name, count in sorted_categories:
            f.write(f"{cat_name:30} - {count:5} items\n")
        
        if missing_barcodes[:20]:
            f.write("\n" + "="*60 + "\n")
            f.write("SAMPLE OF MISSING BARCODES (first 20):\n")
            f.write("-"*60 + "\n")
            for barcode in missing_barcodes[:20]:
                f.write(f"{barcode}\n")
    
    print(f"\nDetailed report saved to: {output_file}")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()