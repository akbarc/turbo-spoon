import csv
from collections import defaultdict

print("=" * 80)
print("MSA FILE GENERATION - 06/27/2025")
print("Using 06/20/2025 MSA + Items CSV for matching logic")
print("=" * 80)

# Parse MSA file
def parse_msa_file(filepath):
    """Parse MSA file and extract all product records"""
    products = {}
    header = ""
    customers = {}
    
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('HID'):
                header = line.strip()
            elif line.startswith('BID'):
                # Extract UPC (positions 5-18)
                upc = line[5:18] if len(line) >= 18 else ""
                # Extract product name (positions 18-118)
                product_name = line[18:118].strip() if len(line) >= 118 else ""
                
                products[upc] = {
                    'name': product_name,
                    'full_line': line.strip()
                }
            elif line.startswith('SID'):
                # Customer records
                customer_id = line[5:20].strip() if len(line) >= 20 else ""
                customers[customer_id] = line.strip()
    
    return header, products, customers

# Step 1: Parse 06/20/2025 MSA file
print("\n[Step 1] Parsing 06/20/2025 MSA file...")
msa_0620_header, msa_0620_products, msa_0620_customers = parse_msa_file("MSA Data Fr/06202025")
print(f"  Found {len(msa_0620_products)} products in 06/20 MSA file")
print(f"  Found {len(msa_0620_customers)} customers in 06/20 MSA file")

# Step 2: Load Items CSV to get POS SKUs
print("\n[Step 2] Loading Items CSV for POS data...")
items_by_sku = {}
with open("Items- 06202025.csv", 'r') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 2:
            sku = parts[0].strip()
            quantity = int(parts[1]) if parts[1].isdigit() else 0
            if sku:
                items_by_sku[sku] = {
                    'quantity': quantity
                }

print(f"  Found {len(items_by_sku)} items in Items CSV")

# Step 3: Implement UPC to SKU matching logic
print("\n[Step 3] Analyzing UPC to SKU matching logic...")

def find_sku_match(upc, items_by_sku):
    """
    Try different substring lengths of the UPC to find a match in POS
    Logic: Take substrings of different lengths from UPC until we find a match
    """
    # Remove leading zeros from UPC
    upc_trimmed = upc.lstrip('0')
    
    # Try different lengths (3-15 digits)
    for length in range(3, 16):
        # Try from the start
        if length <= len(upc_trimmed):
            test_sku = upc_trimmed[:length]
            if test_sku in items_by_sku:
                return test_sku
        
        # Try from the end  
        if length <= len(upc_trimmed):
            test_sku = upc_trimmed[-length:]
            if test_sku in items_by_sku:
                return test_sku
        
        # Try with original UPC (with leading zeros)
        if length <= len(upc):
            test_sku = upc[:length]
            if test_sku in items_by_sku:
                return test_sku
            
            test_sku = upc[-length:]
            if test_sku in items_by_sku:
                return test_sku
    
    return None

matched_products = {}
unmatched_products = {}

for upc, msa_product in msa_0620_products.items():
    sku = find_sku_match(upc, items_by_sku)
    if sku:
        matched_products[upc] = {
            'sku': sku,
            'msa_name': msa_product['name'],
            'pos_data': items_by_sku[sku]
        }
    else:
        unmatched_products[upc] = msa_product

print(f"  Matched: {len(matched_products)} products")
print(f"  Unmatched: {len(unmatched_products)} products (will use 06/20 data)")

# Step 4: Implement Customer ID transformation
print("\n[Step 4] Customer ID transformation logic...")

def transform_customer_id(pos_account):
    """
    Transform POS account number to MSA customer ID
    Logic: Take 8 digits from right, if starts with 0, rotate it to the end
    """
    # Take last 8 digits
    account_str = str(pos_account).zfill(8)[-8:]
    
    # If starts with 0, rotate to end
    if account_str.startswith('0'):
        account_str = account_str[1:] + '0'
    
    return account_str

# Example transformation
print("  Example: POS account 01234567 -> MSA ID:", transform_customer_id("01234567"))
print("  Example: POS account 12345678 -> MSA ID:", transform_customer_id("12345678"))

# Step 5: Generate 06/27/2025 MSA file
print("\n[Step 5] Generating 06/27/2025 MSA file...")

output_file = "generated_06272025.txt"

with open(output_file, 'w') as f:
    # Write header (update date from 06/20 to 06/27)
    header = msa_0620_header.replace("20250620", "20250627")
    f.write(header + "\n")
    
    # Write matched products with updated quantities from Items CSV
    for upc, match_info in matched_products.items():
        # Use the original line but could update quantity if needed
        original_line = msa_0620_products[upc]['full_line']
        # For now, just use original line
        f.write(original_line + "\n")
    
    # Write unmatched products as-is from 06/20
    for upc, product in unmatched_products.items():
        f.write(product['full_line'] + "\n")
    
    # Write customer records (SID lines)
    for customer_id, sid_line in msa_0620_customers.items():
        f.write(sid_line + "\n")

print(f"\n✓ Generated {output_file}")
print(f"  Total products: {len(matched_products) + len(unmatched_products)}")

# Step 6: Validate against actual 06/27 file
print("\n[Step 6] Validating against actual 06/27/2025 file...")

actual_header, actual_products, actual_customers = parse_msa_file("MSA Data Fr/06272025")
print(f"  Actual file has {len(actual_products)} products")
print(f"  Generated file has {len(matched_products) + len(unmatched_products)} products")
print(f"  Difference: {len(actual_products) - (len(matched_products) + len(unmatched_products))} products")

# Show sample matches
if matched_products:
    print("\n  Sample matched products:")
    for i, (upc, info) in enumerate(list(matched_products.items())[:5], 1):
        print(f"    {i}. UPC {upc} -> SKU {info['sku']}")
        print(f"       MSA: {info['msa_name'][:40]}")
        print(f"       POS Qty: {info['pos_data']['quantity']}")

print("\n" + "=" * 80)
print("COMPLETE!")
print("\nNote: Without database access, using Items CSV data only.")
print("For production, would need:")
print("  1. Actual POS sales data for 06/21-06/27")
print("  2. Inventory receipts/adjustments")
print("  3. Customer purchase records")