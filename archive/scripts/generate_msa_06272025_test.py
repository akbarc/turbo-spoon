import pymssql
import os
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# Database connection parameters
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_DATABASE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')

print("=" * 80)
print("MSA FILE GENERATION TEST - 06/27/2025")
print("=" * 80)

# Step 1: Parse 06/20/2025 MSA file
print("\n[Step 1] Parsing 06/20/2025 MSA file for baseline inventory...")

msa_products = {}  # UPC -> (description, category, ending_inventory)
prior_file = "MSA Data Fr/06202025"

with open(prior_file, 'r', encoding='latin-1') as f:
    for line in f:
        if line.startswith('BID'):
            # Extract UPC (positions 5-18)
            upc = line[5:18].strip()
            # Extract product description (positions 18-118)
            description = line[18:118].strip()
            # Extract category code (around position 123-128)
            category = line[123:128].strip() if len(line) > 128 else ""
            # Extract ending inventory (last field, starts with 003)
            inventory_match = re.search(r'003(\d{11})', line)
            if inventory_match:
                inventory = int(inventory_match.group(1).lstrip('0') or '0')
            else:
                inventory = 0
            
            msa_products[upc] = {
                'description': description,
                'category': category,
                'ending_inventory': inventory,
                'source': 'MSA'
            }

print(f"  Found {len(msa_products)} products in prior MSA file")
print(f"  Sample products:")
for upc in list(msa_products.keys())[:3]:
    prod = msa_products[upc]
    print(f"    {upc}: {prod['description'][:40]} (Inv: {prod['ending_inventory']})")

# Step 2: Load UPC to SKU mapping from Items Modified
print("\n[Step 2] Loading UPC to SKU mappings...")

upc_to_sku = {}
sku_to_upc = {}

# Parse the Items Modified file more carefully
import csv
with open("Items- 06202025 MODIFIED.csv", 'r') as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip header
    
    for row in reader:
        if len(row) > 29:  # Need at least 30 columns
            # Column 1 (index 1) has the BID line with UPC
            bid_line = row[1] if len(row) > 1 else ""
            if 'BID' in bid_line:
                # Extract UPC from the BID line (positions 5-18 in the BID string)
                if len(bid_line) >= 18:
                    upc = bid_line[5:18]
                    # Column 29 (index 28) is TRUE MATCH (0 or 1)
                    # Column 30 (index 29) is the SKU when matched
                    if row[28] == '1' and len(row) > 29 and row[29]:
                        sku = row[29].strip()
                        if sku:
                            upc_to_sku[upc] = sku
                            sku_to_upc[sku] = upc
                            if len(upc_to_sku) <= 5:  # Debug first few
                                print(f"    Mapped UPC {upc} -> SKU {sku}")

print(f"  Loaded {len(upc_to_sku)} UPC to SKU mappings")

# Step 3: Connect to database and get POS data
print("\n[Step 3] Connecting to database for POS data...")

try:
    conn = pymssql.connect(
        server=server,
        user=username,
        password=password,
        database=database,
        tds_version='7.0'
    )
    cursor = conn.cursor()
    
    # Get tobacco categories
    tobacco_categories = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]
    
    # Get current inventory for tobacco items
    print("\n[Step 4] Getting POS inventory for tobacco products...")
    
    # First check what columns are available
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Item' 
        AND COLUMN_NAME LIKE '%hand%' OR COLUMN_NAME LIKE '%quant%' OR COLUMN_NAME LIKE '%stock%'
    """)
    inv_columns = [row[0] for row in cursor.fetchall()]
    print(f"  Available inventory columns: {inv_columns}")
    
    # Use the correct column name (likely Quantity or QtyOnHand)
    inv_column = 'Quantity' if 'Quantity' in inv_columns else inv_columns[0] if inv_columns else '0'
    
    cursor.execute("""
        SELECT 
            i.ItemLookupCode,
            i.Description,
            i.%s as OnHand,
            i.CategoryID,
            c.Name as CategoryName
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE i.CategoryID IN (%s)
    """ % (inv_column, ','.join(map(str, tobacco_categories))))
    
    pos_inventory = {}
    for row in cursor.fetchall():
        sku, desc, on_hand, cat_id, cat_name = row
        pos_inventory[sku] = {
            'description': desc,
            'on_hand': on_hand or 0,
            'category_id': cat_id,
            'category_name': cat_name
        }
    
    print(f"  Found {len(pos_inventory)} tobacco items in POS")
    
    # Match POS items to MSA UPCs
    print("\n[Step 5] Matching POS items to MSA UPCs...")
    
    matched_products = {}
    unmatched_msa = {}
    unmatched_pos = []
    
    # First try direct SKU to UPC mapping
    for sku, pos_data in pos_inventory.items():
        if sku in sku_to_upc:
            upc = sku_to_upc[sku]
            matched_products[upc] = {
                'upc': upc,
                'sku': sku,
                'description': pos_data['description'],
                'ending_inventory': pos_data['on_hand'],
                'category': pos_data['category_name'],
                'source': 'POS_MATCHED'
            }
            # Remove from MSA products as it's now matched
            if upc in msa_products:
                del msa_products[upc]
        else:
            # Try other matching strategies
            matched = False
            
            # Strategy 1: Add leading zero
            test_upc = '0' + sku if len(sku) == 11 else sku
            if test_upc in msa_products:
                matched_products[test_upc] = {
                    'upc': test_upc,
                    'sku': sku,
                    'description': pos_data['description'],
                    'ending_inventory': pos_data['on_hand'],
                    'category': pos_data['category_name'],
                    'source': 'POS_MATCHED_ZERO'
                }
                del msa_products[test_upc]
                matched = True
            
            # Strategy 2: Try without leading zeros
            if not matched:
                test_upc = sku.lstrip('0')
                for msa_upc in list(msa_products.keys()):
                    if msa_upc.lstrip('0') == test_upc:
                        matched_products[msa_upc] = {
                            'upc': msa_upc,
                            'sku': sku,
                            'description': pos_data['description'],
                            'ending_inventory': pos_data['on_hand'],
                            'category': pos_data['category_name'],
                            'source': 'POS_MATCHED_STRIP'
                        }
                        del msa_products[msa_upc]
                        matched = True
                        break
            
            if not matched:
                unmatched_pos.append(sku)
    
    print(f"  Matched: {len(matched_products)} products")
    print(f"  Unmatched MSA products (will use prior inventory): {len(msa_products)}")
    print(f"  Unmatched POS products: {len(unmatched_pos)}")
    
    # Step 6: Combine all products for new MSA file
    print("\n[Step 6] Generating 06/27/2025 MSA file...")
    
    all_products = {}
    
    # Add matched products with POS inventory
    for upc, data in matched_products.items():
        all_products[upc] = data
    
    # Add unmatched MSA products with prior inventory
    for upc, data in msa_products.items():
        all_products[upc] = {
            'upc': upc,
            'sku': None,
            'description': data['description'],
            'ending_inventory': data['ending_inventory'],  # Use prior period inventory
            'category': data['category'],
            'source': 'MSA_CARRYOVER'
        }
    
    # Generate MSA file
    output_file = "generated_msa_06272025_test.txt"
    
    with open(output_file, 'w', encoding='latin-1') as f:
        # Write header (HID record)
        header = "HID17000028TOB  W20250627Georgia Wholesale               "
        header += "2935 N Decatur Rd Suite A" + " " * 74
        header += "Decatur                  GA30033    USA"
        header += "Rajput              Raj                      "
        header += "4042924899     4042922573rajput7866@aol.com" + " " * 30
        header += "00010000000220250628 \n"
        f.write(header)
        
        # Write BID records for all products
        for upc, data in sorted(all_products.items()):
            bid_line = "BID  "
            bid_line += upc.ljust(13)  # UPC padded to 13
            bid_line += data['description'][:100].ljust(100)  # Description
            
            # Category and other fields
            if data.get('category'):
                cat_code = "003231"  # Default tobacco category code
            else:
                cat_code = "003231"
            
            bid_line += "000005N      " + cat_code
            bid_line += " " * 100  # Spacing
            
            # Ending inventory in format 003XXXXXXXXXXX
            inv_str = str(data['ending_inventory']).zfill(11)
            bid_line += "003" + inv_str + "\n"
            
            f.write(bid_line)
    
    print(f"  Generated file: {output_file}")
    print(f"  Total products written: {len(all_products)}")
    
    # Show summary by source
    source_counts = defaultdict(int)
    for upc, data in all_products.items():
        source_counts[data['source']] += 1
    
    print("\n  Products by source:")
    for source, count in source_counts.items():
        print(f"    {source}: {count}")
    
    # Step 7: Compare with actual 06/27/2025 file
    print("\n[Step 7] Validating against actual 06/27/2025 file...")
    
    actual_file = "MSA Data Fr/06272025"
    actual_products = {}
    
    with open(actual_file, 'r', encoding='latin-1') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[5:18].strip()
                actual_products[upc] = line
    
    print(f"  Actual file has {len(actual_products)} products")
    print(f"  Generated file has {len(all_products)} products")
    
    # Find differences
    only_in_actual = set(actual_products.keys()) - set(all_products.keys())
    only_in_generated = set(all_products.keys()) - set(actual_products.keys())
    
    print(f"  Products only in actual: {len(only_in_actual)}")
    if only_in_actual:
        for upc in list(only_in_actual)[:5]:
            print(f"    {upc}")
    
    print(f"  Products only in generated: {len(only_in_generated)}")
    if only_in_generated:
        for upc in list(only_in_generated)[:5]:
            print(f"    {upc}")
    
    conn.close()
    print("\n✅ MSA generation test complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()