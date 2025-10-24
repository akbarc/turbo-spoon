import pymssql
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

print("=" * 80)
print("MSA FILE GENERATION - 06/27/2025")
print("Using 06/20/2025 MSA + POS Data")
print("=" * 80)

# Database connection
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_NAME', 'RMH')
username = os.getenv('DB_USER', 'sa')
password = os.getenv('DB_PASSWORD', '')

# Function to build BID line
def build_bid_line(upc, product_name, quantity):
    """Build a BID line in MSA format"""
    # Pad UPC to 13 digits
    upc_padded = upc.zfill(13)
    
    # Pad product name to 100 characters
    name_padded = product_name[:100].ljust(100)
    
    # Format quantity (simplified - actual format is complex)
    qty_str = str(int(quantity)).zfill(10)
    
    # Build the line (simplified version)
    bid_line = f"BID  {upc_padded}{name_padded}000005N      003231                                                                                                 003{qty_str}00000"
    
    return bid_line

# Parse MSA file
def parse_msa_file(filepath):
    """Parse MSA file and extract all product records"""
    products = {}
    header = ""
    
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('HID'):
                header = line.strip()
            elif line.startswith('BID'):
                # Extract UPC (positions 5-18)
                upc = line[5:18] if len(line) >= 18 else ""
                # Extract product name (positions 18-118)
                product_name = line[18:118].strip() if len(line) >= 118 else ""
                # Extract quantity (look for pattern like "003" followed by numbers)
                # Typically around position 200+
                quantity_section = line[200:250] if len(line) >= 250 else ""
                
                # Parse quantity - look for numbers after "003"
                quantity = 0
                if "003" in quantity_section:
                    idx = quantity_section.find("003")
                    qty_str = quantity_section[idx+3:idx+13].strip()
                    # Extract numeric part
                    qty_num = ''.join(c for c in qty_str if c.isdigit())
                    if qty_num:
                        quantity = int(qty_num)
                
                products[upc] = {
                    'name': product_name,
                    'quantity': quantity,
                    'full_line': line.strip()
                }
    
    return header, products

# Step 1: Parse 06/20/2025 MSA file
print("\n[Step 1] Parsing 06/20/2025 MSA file...")
msa_0620_header, msa_0620_products = parse_msa_file("MSA Data Fr/06202025")
print(f"  Found {len(msa_0620_products)} products in 06/20 MSA file")

# Step 2: Connect to database and get POS items
print("\n[Step 2] Connecting to database...")
conn = pymssql.connect(server=server, database=database, user=username, password=password)
cursor = conn.cursor(as_dict=True)

# Get all tobacco category IDs
tobacco_categories = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

# Get all POS items with their lookup codes
print("\n[Step 3] Getting POS items...")
cursor.execute("""
    SELECT 
        ItemLookupCode,
        Description,
        Quantity,
        CategoryID
    FROM Item
    WHERE CategoryID IN (%s)
""" % ','.join(map(str, tobacco_categories)))

pos_items = {}
for row in cursor.fetchall():
    pos_items[row['ItemLookupCode']] = {
        'description': row['Description'],
        'quantity': row['Quantity'] or 0,
        'category': row['CategoryID']
    }

print(f"  Found {len(pos_items)} tobacco items in POS")

# Step 4: Implement UPC to SKU matching logic
print("\n[Step 4] Matching MSA UPCs to POS SKUs...")

def find_sku_match(upc, pos_items):
    """
    Try different substring lengths of the UPC to find a match in POS
    Based on the Items Modified file logic - it tests 3-15 digit substrings
    """
    # Remove leading zeros from UPC for matching
    upc_trimmed = upc.lstrip('0')
    
    # Try different lengths from both ends
    for length in range(3, min(len(upc_trimmed) + 1, 16)):
        # Try from the start
        test_sku = upc_trimmed[:length]
        if test_sku in pos_items:
            return test_sku
        
        # Try from the end
        test_sku = upc_trimmed[-length:]
        if test_sku in pos_items:
            return test_sku
        
        # Try with the original UPC (with leading zeros)
        test_sku = upc[:length]
        if test_sku in pos_items:
            return test_sku
        
        test_sku = upc[-length:]
        if test_sku in pos_items:
            return test_sku
    
    return None

matched_products = {}
unmatched_products = {}

for upc, msa_product in msa_0620_products.items():
    sku = find_sku_match(upc, pos_items)
    if sku:
        matched_products[upc] = {
            'sku': sku,
            'msa_name': msa_product['name'],
            'pos_name': pos_items[sku]['description'],
            'pos_quantity': pos_items[sku]['quantity'],
            'msa_0620_quantity': msa_product['quantity']
        }
    else:
        unmatched_products[upc] = msa_product

print(f"  Matched: {len(matched_products)} products")
print(f"  Unmatched: {len(unmatched_products)} products (will use 06/20 quantities)")

# Step 5: Get sales data for 06/21-06/27
print("\n[Step 5] Getting sales data for 06/21-06/27...")

cursor.execute("""
    SELECT 
        i.ItemLookupCode,
        SUM(te.Quantity) as TotalSold
    FROM TransactionEntry te
    JOIN Item i ON te.ItemID = i.ID
    JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE i.CategoryID IN (%s)
    AND t.Time >= '2025-06-21'
    AND t.Time < '2025-06-28'
    GROUP BY i.ItemLookupCode
""" % ','.join(map(str, tobacco_categories)))

sales_by_sku = {}
for row in cursor.fetchall():
    sales_by_sku[row['ItemLookupCode']] = row['TotalSold'] or 0

print(f"  Found sales for {len(sales_by_sku)} items")

# Step 6: Calculate 06/27 ending inventory
print("\n[Step 6] Calculating 06/27 ending inventory...")

msa_0627_products = {}

# For matched products: use POS quantity (or calculate as 06/20 - sales if needed)
for upc, match_info in matched_products.items():
    sku = match_info['sku']
    # Use current POS quantity as ending inventory
    ending_quantity = match_info['pos_quantity']
    
    # Build BID line
    bid_line = build_bid_line(upc, match_info['msa_name'], ending_quantity)
    msa_0627_products[upc] = bid_line

# For unmatched products: carry forward 06/20 quantity
for upc, product in unmatched_products.items():
    # Use the full line from 06/20 but update the date if needed
    msa_0627_products[upc] = product['full_line']

# Step 7: Generate MSA file
print("\n[Step 7] Generating 06/27/2025 MSA file...")

output_file = "generated_06272025_final.txt"

with open(output_file, 'w') as f:
    # Write header (update date from 06/20 to 06/27)
    header = msa_0620_header.replace("20250620", "20250627")
    f.write(header + "\n")
    
    # Write all BID lines
    for upc in sorted(msa_0627_products.keys()):
        f.write(msa_0627_products[upc] + "\n")

print(f"\n✓ Generated {output_file}")
print(f"  Total products: {len(msa_0627_products)}")

# Step 8: Validate against actual 06/27 file
print("\n[Step 8] Validating against actual 06/27/2025 file...")

actual_header, actual_products = parse_msa_file("MSA Data Fr/06272025")
print(f"  Actual file has {len(actual_products)} products")
print(f"  Generated file has {len(msa_0627_products)} products")
print(f"  Difference: {len(actual_products) - len(msa_0627_products)} products")

# Show sample matches
print("\n  Sample matched products:")
for i, (upc, info) in enumerate(list(matched_products.items())[:5], 1):
    print(f"    {i}. UPC {upc} -> SKU {info['sku']}")
    print(f"       {info['msa_name'][:50]}")

conn.close()
print("\n" + "=" * 80)
print("COMPLETE!")