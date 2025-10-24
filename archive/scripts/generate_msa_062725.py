import os
from datetime import datetime, timedelta
from collections import defaultdict
import csv

# First, let's parse the 06/20/2025 MSA file
def parse_msa_file(filepath):
    """Parse MSA file and extract all product records"""
    products = {}
    customers = {}
    purchases = []
    header = None
    
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            record_type = line[:3] if len(line) >= 3 else ""
            
            if record_type == 'HID':
                header = line
                print(f"Header found: Store info from positions 3-30: {line[3:30]}")
                
            elif record_type == 'BID':
                # Extract product info
                upc = line[5:18].strip()  # 13-digit UPC
                product_name = line[18:118].strip() if len(line) > 118 else line[18:].strip()
                
                # The quantity is in the last section - need to parse carefully
                if len(line) > 200:
                    quantity_section = line[200:].strip()
                    # Extract quantity - it's typically in format like "003000000000XX"
                    if quantity_section.startswith('003'):
                        qty_str = quantity_section[3:14]
                        quantity = int(qty_str) if qty_str.isdigit() else 0
                    else:
                        quantity = 0
                else:
                    quantity = 0
                
                products[upc] = {
                    'name': product_name,
                    'quantity': quantity,
                    'full_line': line.rstrip()
                }
                
            elif record_type == 'SID':
                # Customer record
                customer_id = line[3:30].strip()
                customer_name = line[30:80].strip() if len(line) > 80 else ""
                customers[customer_id] = customer_name
                
            elif record_type == 'PUR':
                # Purchase record
                customer = line[3:30].strip()
                upc = line[30:60].strip()
                # Parse quantity and price from the data section
                purchases.append({
                    'customer': customer,
                    'upc': upc,
                    'line': line.rstrip()
                })
    
    return header, products, customers, purchases

# Parse the 06/20/2025 file
print("Parsing MSA Data Fr/06202025...")
msa_0620_path = "MSA Data Fr/06202025"

header_0620, products_0620, customers_0620, purchases_0620 = parse_msa_file(msa_0620_path)

print(f"\nFound in 06/20/2025 MSA file:")
print(f"  - {len(products_0620)} products")
print(f"  - {len(customers_0620)} customers") 
print(f"  - {len(purchases_0620)} purchase records")

# Show sample products
print("\nSample products from 06/20/2025:")
for i, (upc, prod) in enumerate(list(products_0620.items())[:5]):
    print(f"  UPC: {upc} | {prod['name'][:40]} | Qty: {prod['quantity']}")

# Now let's check what POS data we have available
print("\n" + "="*60)
print("Checking available POS data files...")

# Check for sales files
sales_files = []
for f in os.listdir('.'):
    if 'sales' in f.lower() and '.csv' in f.lower():
        sales_files.append(f)
        
print(f"\nFound sales files: {sales_files}")

# Check for Items mapping file
items_file = "Items- 06202025 MODIFIED.csv"
if os.path.exists(items_file):
    print(f"✓ Found Items mapping file: {items_file}")
else:
    print(f"✗ Items mapping file not found")

print("\n" + "="*60)
print("QUESTIONS FOR YOU:")
print("="*60)
print("\n1. For the POS sales data for 06/21-06/27:")
print("   - Do we have daily sales files or one combined file?")
print("   - What format are the sales in? (CSV with customer_id, barcode, qty, price?)")
print("\n2. For inventory data:")
print("   - How do we get the Friday 06/27 ending inventory from POS?")
print("   - Is there an inventory table in the database we should query?")
print("\n3. For customer ID mapping:")
print("   - How do we convert POS customer account numbers to MSA SID format?")
print("   - Is there a specific formula or lookup table?")
print("\n4. For product categories:")
print("   - Should we only include the 15 tobacco categories we identified?")
print("   - How do we determine the category code for the BID records?")

print("\nPlease provide this information so we can continue!")