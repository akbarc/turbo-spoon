#!/usr/bin/env python3
"""
Generate MSA file for 06/27/2025 using dynamic UPC matching and POS data
"""

from datetime import datetime
from collections import defaultdict
import os
import sys

# Import the existing database module
from database_pymssql import connection_pool

# Tobacco category IDs from POS
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

def parse_msa_file(filepath):
    """Parse MSA file and extract BID, SID, and PUR records"""
    records = {
        'header': None,
        'bids': [],
        'sids': [],
        'purs': []
    }
    
    print(f"Parsing MSA file: {filepath}")
    
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip():
                continue
                
            record_type = line[:3]
            
            if record_type == 'HID':
                records['header'] = line.rstrip('\n')
            elif record_type == 'BID':
                # Parse BID record
                bid_data = {
                    'raw': line.rstrip('\n'),
                    'upc': line[3:18].strip(),  # UPC is positions 4-18
                    'name': line[18:78].strip(),  # Product name
                    'quantity': line[199:210].strip()  # Quantity field
                }
                records['bids'].append(bid_data)
            elif record_type == 'SID':
                records['sids'].append(line.rstrip('\n'))
            elif record_type == 'PUR':
                records['purs'].append(line.rstrip('\n'))
    
    print(f"Found {len(records['bids'])} BID records")
    print(f"Found {len(records['sids'])} SID records")
    print(f"Found {len(records['purs'])} PUR records")
    
    return records

def load_pos_items():
    """Load all tobacco items from POS database"""
    print("Connecting to POS database...")
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Get all tobacco items with their SKUs
    category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
    query = f"""
    SELECT DISTINCT
        ItemLookupCode,
        Description,
        CategoryID,
        Quantity,
        ID as ItemID
    FROM Item
    WHERE CategoryID IN ({category_list})
    ORDER BY ItemLookupCode
    """
    
    cursor.execute(query)
    items = cursor.fetchall()
    
    print(f"Loaded {len(items)} tobacco items from POS")
    
    # Create SKU lookup dictionary
    sku_lookup = {item['ItemLookupCode']: item for item in items}
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    return sku_lookup

def match_upc_to_sku(msa_upc, sku_lookup):
    """
    Match MSA UPC to POS SKU using substring logic
    Try substrings from beginning: 3, 4, 5... up to full length
    """
    if not msa_upc:
        return None
    
    # Clean the UPC
    upc_clean = msa_upc.strip()
    
    # First try exact match
    if upc_clean in sku_lookup:
        return upc_clean
    
    # Try substring matching from beginning
    for length in range(3, len(upc_clean) + 1):
        substring = upc_clean[:length]
        if substring in sku_lookup:
            return substring
    
    return None

def build_upc_to_sku_mapping(msa_records, sku_lookup):
    """Build mapping of MSA UPCs to POS SKUs"""
    mapping = {}
    unmapped = []
    
    print("Building UPC to SKU mapping...")
    
    for bid in msa_records['bids']:
        upc = bid['upc']
        matched_sku = match_upc_to_sku(upc, sku_lookup)
        
        if matched_sku:
            mapping[upc] = matched_sku
        else:
            unmapped.append(bid)
    
    print(f"Mapped {len(mapping)} UPCs to SKUs")
    print(f"Unmapped products: {len(unmapped)}")
    
    return mapping, unmapped

def transform_customer_id(customer_id):
    """
    Transform customer ID using 8-digit rule:
    - If starts with 0, rotate to end
    - Ensure 8 digits total
    """
    if not customer_id:
        return None
    
    # Convert to string and pad to 8 digits
    cust_str = str(customer_id).zfill(8)
    
    # If starts with 0, rotate to end
    if cust_str.startswith('0'):
        cust_str = cust_str[1:] + '0'
    
    return cust_str

def get_sales_data(start_date, end_date, upc_mapping, sku_lookup):
    """Get sales data for the week"""
    print(f"Getting sales data from {start_date} to {end_date}")
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Get all SKUs we're interested in
    sku_list = list(set(upc_mapping.values()))
    if not sku_list:
        print("No SKUs to query")
        return {}
    
    # Build IN clause for SKUs - need to get ItemIDs for these SKUs
    sku_placeholders = ','.join(['%s'] * len(sku_list))
    
    # First get ItemIDs for our SKUs
    item_ids = []
    for sku in sku_list:
        if sku in sku_lookup and 'ItemID' in sku_lookup[sku]:
            item_ids.append(sku_lookup[sku]['ItemID'])
    
    if not item_ids:
        print("No ItemIDs found for SKUs")
        return {}
    
    item_id_placeholders = ','.join(['%s'] * len(item_ids))
    
    query = f"""
    SELECT 
        t.CustomerID,
        i.ItemLookupCode,
        SUM(te.Quantity) as TotalQuantity
    FROM TransactionEntry te
    INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    WHERE t.Time >= %s AND t.Time <= %s
    AND te.ItemID IN ({item_id_placeholders})
    GROUP BY t.CustomerID, i.ItemLookupCode
    """
    
    params = [start_date, end_date] + item_ids
    cursor.execute(query, params)
    
    # Process sales data
    sales = defaultdict(lambda: defaultdict(float))
    
    for row in cursor:
        customer_id = transform_customer_id(row['CustomerID'])
        if customer_id:
            # Find all UPCs that map to this SKU
            for upc, sku in upc_mapping.items():
                if sku == row['ItemLookupCode']:
                    sales[customer_id][upc] += row['TotalQuantity']
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print(f"Found sales for {len(sales)} customers")
    
    return sales

def calculate_ending_inventory(prior_bid, sales_data, upc_mapping):
    """Calculate ending inventory for a product"""
    upc = prior_bid['upc']
    prior_qty = int(prior_bid['quantity']) if prior_bid['quantity'] else 0
    
    # If product is mapped to POS
    if upc in upc_mapping:
        # Sum all sales for this UPC across all customers
        total_sales = 0
        for customer_sales in sales_data.values():
            if upc in customer_sales:
                total_sales += customer_sales[upc]
        
        # New inventory = prior - sales
        new_qty = max(0, prior_qty - int(total_sales))
        return new_qty
    else:
        # Unmapped product - carry forward unchanged
        return prior_qty

def format_bid_record(bid_data, new_quantity):
    """Format a BID record with updated quantity"""
    # Start with the raw line
    line = bid_data['raw']
    
    # Replace the quantity field (positions 199-210)
    qty_str = str(new_quantity).zfill(11)  # 11 digits with leading zeros
    
    # Reconstruct the line with new quantity
    new_line = line[:199] + qty_str + line[210:]
    
    return new_line.rstrip('\n')

def format_sid_record(customer_id, customer_name=""):
    """Format a SID record for a customer"""
    # SID format: 'SID' + customer_id (padded) + customer_name (padded)
    sid = 'SID'
    sid += customer_id.ljust(15)  # Customer ID field
    sid += customer_name.ljust(60)  # Customer name field
    sid += ' ' * 425  # Padding to match original format
    return sid

def format_pur_record(customer_id, upc, quantity, date_str):
    """Format a PUR record for a sale"""
    pur = 'PUR'
    pur += customer_id.ljust(15)  # Customer ID
    pur += upc.ljust(15)  # UPC
    pur += str(int(quantity)).zfill(11)  # Quantity (11 digits)
    pur += date_str  # Date (YYYYMMDD)
    pur += ' ' * 456  # Padding
    return pur

def generate_msa_file(prior_records, sales_data, upc_mapping, output_file):
    """Generate the new MSA file"""
    print(f"Generating MSA file: {output_file}")
    
    with open(output_file, 'w') as f:
        # Write updated header (change date from 20250620 to 20250627)
        if prior_records['header']:
            header = prior_records['header'].replace('20250620', '20250627')
            f.write(header + '\n')
        
        # Process and write BID records with updated quantities
        for bid in prior_records['bids']:
            new_qty = calculate_ending_inventory(bid, sales_data, upc_mapping)
            bid_line = format_bid_record(bid, new_qty)
            f.write(bid_line + '\n')
        
        # Write SID records for customers with purchases
        customers_with_sales = set(sales_data.keys())
        for customer_id in sorted(customers_with_sales):
            sid_line = format_sid_record(customer_id)
            f.write(sid_line + '\n')
        
        # Write PUR records for all sales
        for customer_id, customer_sales in sorted(sales_data.items()):
            for upc, quantity in sorted(customer_sales.items()):
                if quantity > 0:
                    pur_line = format_pur_record(customer_id, upc, quantity, '20250627')
                    f.write(pur_line + '\n')
    
    print(f"MSA file generated: {output_file}")

def validate_against_actual(generated_file, actual_file):
    """Validate generated file against actual"""
    print("\nValidating against actual file...")
    
    if not os.path.exists(actual_file):
        print(f"Actual file not found: {actual_file}")
        return
    
    # Parse both files
    generated = parse_msa_file(generated_file)
    actual = parse_msa_file(actual_file)
    
    print(f"\nComparison:")
    print(f"Generated BIDs: {len(generated['bids'])}")
    print(f"Actual BIDs: {len(actual['bids'])}")
    print(f"Generated SIDs: {len(generated['sids'])}")
    print(f"Actual SIDs: {len(actual['sids'])}")
    print(f"Generated PURs: {len(generated['purs'])}")
    print(f"Actual PURs: {len(actual['purs'])}")
    
    # Check for missing products
    generated_upcs = {bid['upc'] for bid in generated['bids']}
    actual_upcs = {bid['upc'] for bid in actual['bids']}
    
    missing_in_generated = actual_upcs - generated_upcs
    extra_in_generated = generated_upcs - actual_upcs
    
    if missing_in_generated:
        print(f"\nProducts in actual but not generated: {len(missing_in_generated)}")
        for upc in list(missing_in_generated)[:10]:
            print(f"  - {upc}")
    
    if extra_in_generated:
        print(f"\nProducts in generated but not actual: {len(extra_in_generated)}")
        for upc in list(extra_in_generated)[:10]:
            print(f"  - {upc}")

def main():
    # File paths
    prior_msa_file = "MSA Data Fr/06202025"
    output_file = "generated_msa_06272025.txt"
    actual_file = "MSA Data Fr/06272025"
    
    # Step 1: Parse prior MSA file
    print("STEP 1: Parsing prior MSA file...")
    prior_records = parse_msa_file(prior_msa_file)
    
    # Step 2: Load POS items
    print("\nSTEP 2: Loading POS items...")
    sku_lookup = load_pos_items()
    
    # Step 3: Build UPC to SKU mapping
    print("\nSTEP 3: Building UPC to SKU mapping...")
    upc_mapping, unmapped = build_upc_to_sku_mapping(prior_records, sku_lookup)
    
    # Step 4: Get sales data for the week
    print("\nSTEP 4: Getting sales data...")
    start_date = '2025-06-21'
    end_date = '2025-06-27 23:59:59'
    sales_data = get_sales_data(start_date, end_date, upc_mapping, sku_lookup)
    
    # Step 5 & 6: Generate MSA file (inventory calculation happens during generation)
    print("\nSTEP 5&6: Generating MSA file with updated inventories...")
    generate_msa_file(prior_records, sales_data, upc_mapping, output_file)
    
    # Step 7: Validate against actual
    print("\nSTEP 7: Validating...")
    validate_against_actual(output_file, actual_file)
    
    print("\nGeneration complete!")

if __name__ == "__main__":
    main()