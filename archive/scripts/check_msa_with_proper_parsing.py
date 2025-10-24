import pymssql
import os
from dotenv import load_dotenv
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
    
    # Get all MSA files from MSA Data Fr folder
    msa_folder = "MSA Data Fr"
    msa_dates = ["06202025", "06272025", "07042025", "07112025", "07182025", "07252025", "08012025", "08082025"]
    
    all_msa_barcodes = set()
    all_msa_barcodes_stripped = set()
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
                    # MSA format: BID lines contain the barcode
                    if line.startswith('BID'):
                        # Barcode is at positions 5-17 (13 digits, padded with zeros)
                        barcode_padded = line[5:18].strip()
                        if barcode_padded:
                            all_msa_barcodes.add(barcode_padded)
                            # Also store the stripped version (remove leading zeros)
                            barcode_stripped = barcode_padded.lstrip('0')
                            if barcode_stripped:  # Only add if not empty after stripping
                                all_msa_barcodes_stripped.add(barcode_stripped)
                                barcodes_in_file.add(barcode_stripped)
            
            file_barcode_counts[date] = len(barcodes_in_file)
            print(f"  Found {len(barcodes_in_file)} unique barcodes (after removing padding)")
    
    print(f"\n{'='*60}")
    print(f"Total unique barcodes across all MSA files:")
    print(f"  Padded: {len(all_msa_barcodes)}")
    print(f"  Without padding: {len(all_msa_barcodes_stripped)}")
    print("="*60)
    
    # Show sample of barcodes
    print("\nSample barcodes (first 10):")
    for i, barcode in enumerate(list(all_msa_barcodes_stripped)[:10]):
        print(f"  {barcode}")
    
    # Now check which categories these items belong to in the database
    print("\n" + "="*60)
    print("Checking database for category distribution...")
    
    # First, get ALL items from database to handle variable length barcodes
    cursor.execute("""
        SELECT 
            i.ItemLookupCode as Barcode,
            i.Description,
            i.CategoryID,
            c.Name as CategoryName
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE i.CategoryID IN (
            SELECT ID FROM Category 
            WHERE Name LIKE '%CIG%' OR Name LIKE '%TOB%' OR Name LIKE '%BLUNT%' 
            OR Name LIKE '%NICOTINE%' OR Name LIKE '%ECIG%' OR Name LIKE 'LT-%'
            OR Name LIKE 'T7%' OR Name = 'LIGHTERS'
        )
    """)
    
    db_items = cursor.fetchall()
    print(f"Found {len(db_items)} tobacco-related items in database")
    
    # Create lookup dictionary with stripped barcodes
    db_barcode_lookup = {}
    for barcode, desc, cat_id, cat_name in db_items:
        if barcode:
            # Store with the barcode as-is (could be 3-15 digits)
            db_barcode_lookup[barcode] = (desc, cat_id, cat_name)
    
    # Match MSA barcodes with database
    category_distribution = Counter()
    matched_items = []
    unmatched_barcodes = []
    
    for msa_barcode in all_msa_barcodes_stripped:
        matched = False
        # Try to match directly
        if msa_barcode in db_barcode_lookup:
            desc, cat_id, cat_name = db_barcode_lookup[msa_barcode]
            matched_items.append((msa_barcode, desc, cat_id, cat_name))
            if cat_name:
                category_distribution[cat_name] += 1
            matched = True
        else:
            # Try with different lengths (in case of partial matches)
            for db_barcode in db_barcode_lookup:
                if db_barcode == msa_barcode or db_barcode.lstrip('0') == msa_barcode:
                    desc, cat_id, cat_name = db_barcode_lookup[db_barcode]
                    matched_items.append((msa_barcode, desc, cat_id, cat_name))
                    if cat_name:
                        category_distribution[cat_name] += 1
                    matched = True
                    break
        
        if not matched:
            unmatched_barcodes.append(msa_barcode)
    
    print(f"\nMatched {len(matched_items)} items with database")
    print(f"Unmatched {len(unmatched_barcodes)} items not found in database")
    
    # Show category distribution
    print("\n" + "="*60)
    print("CATEGORIES USED ACROSS ALL MSA FILES:")
    print("="*60)
    
    sorted_categories = sorted(category_distribution.items(), key=lambda x: x[1], reverse=True)
    
    if sorted_categories:
        print(f"\nTotal categories used: {len(sorted_categories)}")
        print("-"*60)
        for cat_name, count in sorted_categories:
            print(f"{cat_name:30} - {count:5} items")
        
        # Get category IDs for reference
        print("\n" + "="*60)
        print("CATEGORY IDs FOR MSA CATEGORIES:")
        print("="*60)
        
        category_names = [cat[0] for cat in sorted_categories]
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
    else:
        print("\nNo categories matched - checking why...")
        print("\nSample of unmatched MSA barcodes (first 20):")
        for barcode in unmatched_barcodes[:20]:
            print(f"  {barcode}")
        
        print("\nSample of database barcodes (first 20):")
        for barcode in list(db_barcode_lookup.keys())[:20]:
            print(f"  {barcode}")
    
    # Save detailed report
    output_file = 'MSA_Category_Analysis_Corrected.txt'
    with open(output_file, 'w') as f:
        f.write("MSA CATEGORY ANALYSIS (WITH PROPER BARCODE PARSING)\n")
        f.write("="*60 + "\n\n")
        
        f.write("File Summary:\n")
        f.write("-"*40 + "\n")
        for date, count in file_barcode_counts.items():
            f.write(f"{date}: {count} unique barcodes\n")
        
        f.write(f"\nTotal unique barcodes (without padding): {len(all_msa_barcodes_stripped)}\n")
        f.write(f"Matched with database: {len(matched_items)}\n")
        f.write(f"Not found in database: {len(unmatched_barcodes)}\n")
        
        if sorted_categories:
            f.write("\n" + "="*60 + "\n")
            f.write("CATEGORIES USED IN MSA:\n")
            f.write("-"*60 + "\n")
            for cat_name, count in sorted_categories:
                f.write(f"{cat_name:30} - {count:5} items\n")
        
        if unmatched_barcodes[:50]:
            f.write("\n" + "="*60 + "\n")
            f.write("SAMPLE OF UNMATCHED BARCODES (first 50):\n")
            f.write("-"*60 + "\n")
            for barcode in unmatched_barcodes[:50]:
                f.write(f"{barcode}\n")
    
    print(f"\nDetailed report saved to: {output_file}")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()