#!/usr/bin/env python3
"""
Improved MSA file generator with better accuracy
- Includes new products added during the period
- Maintains complete customer roster
- Better fixed-width parsing
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys

# Import the existing database module
from database_pymssql import connection_pool

# Tobacco category IDs from POS
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

def parse_msa_file(filepath):
    """Parse MSA file with improved fixed-width handling"""
    records = {
        'header': None,
        'bids': [],
        'sids': [],  # Keep ALL customers
        'purs': []
    }
    
    print(f"Parsing MSA file: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
                
            record_type = line[:3]
            
            if record_type == 'HID':
                records['header'] = line.rstrip('\r\n')
            elif record_type == 'BID':
                # Improved BID parsing with exact positions
                bid_data = {
                    'raw': line.rstrip('\r\n'),
                    'upc': line[3:18].strip(),
                    'name': line[18:78].strip(),
                    'quantity': line[199:210].strip() if len(line) > 210 else '0'
                }
                records['bids'].append(bid_data)
            elif record_type == 'SID':
                # Keep ALL customer records
                records['sids'].append(line.rstrip('\r\n'))
            elif record_type == 'PUR':
                records['purs'].append(line.rstrip('\r\n'))
    
    print(f"Found {len(records['bids'])} BID records")
    print(f"Found {len(records['sids'])} SID records")
    print(f"Found {len(records['purs'])} PUR records")
    
    return records

def load_all_tobacco_items():
    """Load ALL tobacco items from POS, including recently added"""
    print("Loading all tobacco items from POS...")
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
    query = f"""
    SELECT DISTINCT
        ItemLookupCode,
        Description,
        CategoryID,
        Quantity,
        ID as ItemID,
        DateCreated,
        LastReceived
    FROM Item
    WHERE CategoryID IN ({category_list})
    ORDER BY ItemLookupCode
    """
    
    cursor.execute(query)
    items = cursor.fetchall()
    
    print(f"Loaded {len(items)} tobacco items from POS")
    
    sku_lookup = {item['ItemLookupCode']: item for item in items}
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    return sku_lookup, items

def find_new_products_since(prior_date, sku_lookup):
    """Find products added to POS since the prior MSA date"""
    print(f"Finding products added since {prior_date}")
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Convert date string to datetime
    prior_datetime = datetime.strptime(prior_date, '%Y%m%d')
    
    category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
    # Only get products CREATED after prior date, not just received
    # This avoids counting restocked items as new
    query = f"""
    SELECT 
        ItemLookupCode,
        Description,
        CategoryID,
        Quantity,
        ID as ItemID,
        DateCreated,
        LastReceived
    FROM Item
    WHERE CategoryID IN ({category_list})
    AND DateCreated > %s
    AND Quantity > 0  -- Only include items with current inventory
    ORDER BY ItemLookupCode
    """
    
    cursor.execute(query, prior_datetime)
    new_items = cursor.fetchall()
    
    print(f"Found {len(new_items)} products created since {prior_date}")
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    return new_items

def create_upc_from_sku(sku):
    """Create a full UPC from SKU by padding with zeros"""
    # MSA UPCs are typically 15 digits, left-padded with zeros
    return '0' + sku.zfill(14) if len(sku) < 15 else sku[:15]

def match_upc_to_sku_improved(msa_upc, sku_lookup):
    """
    Improved UPC to SKU matching
    - Try exact match first
    - Try removing leading zeros
    - Try substring matching
    """
    if not msa_upc:
        return None
    
    upc_clean = msa_upc.strip()
    
    # Exact match
    if upc_clean in sku_lookup:
        return upc_clean
    
    # Try without leading zeros
    upc_no_zeros = upc_clean.lstrip('0')
    if upc_no_zeros in sku_lookup:
        return upc_no_zeros
    
    # Try substring matching from beginning
    for length in range(3, len(upc_clean) + 1):
        substring = upc_clean[:length]
        if substring in sku_lookup:
            return substring
        
        # Also try without leading zeros
        substring_no_zeros = substring.lstrip('0')
        if substring_no_zeros in sku_lookup:
            return substring_no_zeros
    
    return None

def build_comprehensive_upc_mapping(msa_records, sku_lookup, new_items):
    """Build UPC mapping including new products"""
    mapping = {}
    unmapped = []
    
    print("Building comprehensive UPC to SKU mapping...")
    
    # Map existing MSA products
    for bid in msa_records['bids']:
        upc = bid['upc']
        matched_sku = match_upc_to_sku_improved(upc, sku_lookup)
        
        if matched_sku:
            mapping[upc] = matched_sku
        else:
            unmapped.append(bid)
    
    # Add mappings for new products
    new_product_bids = []
    for item in new_items:
        sku = item['ItemLookupCode']
        # Check if this SKU is already mapped
        if sku not in mapping.values():
            # Create UPC for this new product
            upc = create_upc_from_sku(sku)
            mapping[upc] = sku
            
            # Create a BID record for this new product
            new_bid = {
                'upc': upc,
                'name': item['Description'][:60],  # Limit to 60 chars
                'quantity': str(int(item['Quantity'])) if item['Quantity'] else '0',
                'new': True,
                'sku': sku
            }
            new_product_bids.append(new_bid)
    
    print(f"Mapped {len(mapping)} UPCs to SKUs")
    print(f"Added {len(new_product_bids)} new products")
    print(f"Unmapped products: {len(unmapped)}")
    
    return mapping, unmapped, new_product_bids

def transform_customer_id(customer_id):
    """Transform customer ID using 8-digit rule"""
    if not customer_id:
        return None
    
    # Convert to string and pad to 8 digits
    cust_str = str(customer_id).zfill(8)
    
    # If starts with 0, rotate to end
    if cust_str.startswith('0'):
        cust_str = cust_str[1:] + '0'
    
    return cust_str

def get_sales_data(start_date, end_date, upc_mapping, sku_lookup):
    """Get sales data for the week with improved query"""
    print(f"Getting sales data from {start_date} to {end_date}")
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Get all SKUs we're interested in
    sku_list = list(set(upc_mapping.values()))
    if not sku_list:
        print("No SKUs to query")
        return {}
    
    # Get ItemIDs for our SKUs
    item_ids = []
    for sku in sku_list:
        if sku in sku_lookup and 'ItemID' in sku_lookup[sku]:
            item_ids.append(sku_lookup[sku]['ItemID'])
    
    if not item_ids:
        print("No ItemIDs found for SKUs")
        return {}
    
    item_id_placeholders = ','.join(['%s'] * len(item_ids))
    
    # Include returns (negative quantities) in the query
    query = f"""
    SELECT 
        t.CustomerID,
        i.ItemLookupCode,
        SUM(te.Quantity) as TotalQuantity,
        COUNT(*) as TransactionCount
    FROM TransactionEntry te
    INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    WHERE t.Time >= %s AND t.Time <= %s
    AND te.ItemID IN ({item_id_placeholders})
    AND t.Status = 0  -- Only completed transactions
    GROUP BY t.CustomerID, i.ItemLookupCode
    HAVING SUM(te.Quantity) != 0  -- Exclude net-zero transactions
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
                    # Use absolute value for sales (negative = returns)
                    sales[customer_id][upc] += abs(row['TotalQuantity'])
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print(f"Found sales for {len(sales)} customers")
    
    return sales

def calculate_ending_inventory(prior_bid, sales_data, upc_mapping):
    """Calculate ending inventory with improved logic"""
    upc = prior_bid['upc']
    
    # Parse prior quantity safely
    try:
        prior_qty = int(prior_bid['quantity']) if prior_bid['quantity'] else 0
    except (ValueError, TypeError):
        prior_qty = 0
    
    # If product is mapped to POS
    if upc in upc_mapping:
        # Sum all sales for this UPC
        total_sales = 0
        for customer_sales in sales_data.values():
            if upc in customer_sales:
                total_sales += customer_sales[upc]
        
        # New inventory = prior - sales (ensure non-negative)
        new_qty = max(0, prior_qty - int(total_sales))
        return new_qty
    else:
        # Unmapped product - carry forward unchanged
        return prior_qty

def format_bid_record(bid_data, new_quantity):
    """Format a BID record with proper fixed-width layout"""
    if 'raw' in bid_data:
        # Update existing record
        line = bid_data['raw']
        qty_str = str(new_quantity).zfill(11)
        # Ensure line is long enough
        if len(line) < 210:
            line = line.ljust(210)
        new_line = line[:199] + qty_str + line[210:]
        return new_line.rstrip()
    else:
        # Create new BID record for new product
        bid = 'BID'
        bid += bid_data['upc'].ljust(15)
        bid += bid_data['name'].ljust(60)
        bid += ' ' * 124  # Padding fields
        bid += str(new_quantity).zfill(11)
        bid += ' ' * 290  # Remaining padding to match format
        return bid

def format_pur_record(customer_id, upc, quantity, date_str):
    """Format a PUR record with improved layout"""
    pur = 'PUR'
    pur += customer_id.ljust(15)
    pur += upc.ljust(15)
    pur += ' ' * 50  # Spacing before quantity
    pur += str(int(quantity)).zfill(11)
    # Add price fields (placeholder)
    pur += '00000029.0000200000000.00'  # Standard price format
    return pur

def generate_improved_msa_file(prior_records, sales_data, upc_mapping, new_product_bids, output_file, target_date):
    """Generate MSA file with improved accuracy"""
    print(f"Generating improved MSA file: {output_file}")
    
    with open(output_file, 'w') as f:
        # Update header with new date
        if prior_records['header']:
            # Find and replace the date in the header
            header = prior_records['header']
            # The date appears after "TOB W" in format YYYYMMDD
            old_date = header[21:29] if len(header) > 29 else '20250801'
            header = header.replace(old_date, target_date)
            f.write(header + '\n')
        
        # Process existing BID records
        for bid in prior_records['bids']:
            new_qty = calculate_ending_inventory(bid, sales_data, upc_mapping)
            bid_line = format_bid_record(bid, new_qty)
            f.write(bid_line + '\n')
        
        # Add new product BID records
        for new_bid in new_product_bids:
            # Get current inventory from POS
            bid_line = format_bid_record(new_bid, int(new_bid['quantity']))
            f.write(bid_line + '\n')
        
        # Write ALL SID records from prior file (maintain customer roster)
        for sid in prior_records['sids']:
            f.write(sid + '\n')
        
        # Write PUR records for all sales
        for customer_id, customer_sales in sorted(sales_data.items()):
            for upc, quantity in sorted(customer_sales.items()):
                if quantity > 0:
                    pur_line = format_pur_record(customer_id, upc, quantity, target_date)
                    f.write(pur_line + '\n')
    
    print(f"MSA file generated: {output_file}")

def validate_improved(generated_file, actual_file):
    """Validate with improved metrics"""
    print("\n=== VALIDATION RESULTS ===")
    
    if not os.path.exists(actual_file):
        print(f"Actual file not found: {actual_file}")
        return
    
    generated = parse_msa_file(generated_file)
    actual = parse_msa_file(actual_file)
    
    print(f"\nRecord counts:")
    print(f"{'Type':<10} {'Generated':<12} {'Actual':<12} {'Difference':<12} {'Accuracy %':<12}")
    print("-" * 58)
    
    # BID records
    bid_diff = len(actual['bids']) - len(generated['bids'])
    bid_accuracy = (1 - abs(bid_diff) / len(actual['bids'])) * 100 if actual['bids'] else 0
    print(f"{'BIDs':<10} {len(generated['bids']):<12} {len(actual['bids']):<12} {bid_diff:<12} {bid_accuracy:.1f}%")
    
    # SID records
    sid_diff = len(actual['sids']) - len(generated['sids'])
    sid_accuracy = (1 - abs(sid_diff) / len(actual['sids'])) * 100 if actual['sids'] else 0
    print(f"{'SIDs':<10} {len(generated['sids']):<12} {len(actual['sids']):<12} {sid_diff:<12} {sid_accuracy:.1f}%")
    
    # PUR records
    pur_diff = len(actual['purs']) - len(generated['purs'])
    pur_accuracy = (1 - abs(pur_diff) / len(actual['purs'])) * 100 if actual['purs'] else 0
    print(f"{'PURs':<10} {len(generated['purs']):<12} {len(actual['purs']):<12} {pur_diff:<12} {pur_accuracy:.1f}%")
    
    # Overall accuracy
    overall_accuracy = (bid_accuracy + sid_accuracy + pur_accuracy) / 3
    print(f"\nOverall Accuracy: {overall_accuracy:.1f}%")
    
    # Check for missing products
    generated_upcs = {bid['upc'] for bid in generated['bids']}
    actual_upcs = {bid['upc'] for bid in actual['bids']}
    
    missing_in_generated = actual_upcs - generated_upcs
    extra_in_generated = generated_upcs - actual_upcs
    
    if missing_in_generated:
        print(f"\nProducts in actual but not generated: {len(missing_in_generated)}")
        if len(missing_in_generated) <= 5:
            for upc in missing_in_generated:
                print(f"  - {upc}")
    
    if extra_in_generated:
        print(f"\nProducts in generated but not actual: {len(extra_in_generated)}")
        if len(extra_in_generated) <= 5:
            for upc in extra_in_generated:
                print(f"  - {upc}")

def main():
    """Main function with command line arguments"""
    if len(sys.argv) > 1:
        # Allow command line usage
        prior_date = sys.argv[1]  # Format: MMDDYYYY
        target_date = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # Default to 08/08/2025 example
        prior_date = "08012025"
        target_date = "08082025"
    
    # File paths
    prior_msa_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_improved.txt"
    actual_file = f"MSA Data Fr/{target_date}"
    
    # Convert dates to proper format
    prior_date_str = "2025" + prior_date[:4]  # YYYYMMDD
    target_date_str = "2025" + target_date[:4]  # YYYYMMDD
    
    # Calculate date range (Saturday to Friday)
    target_datetime = datetime.strptime(target_date_str, '%Y%m%d')
    # MSA week runs Saturday to Friday
    # If target is Friday, go back 6 days to Saturday
    # For 08/08/2025 (Friday), we want 08/02/2025 (Saturday) to 08/08/2025 (Friday)
    if target_datetime.weekday() == 4:  # Friday
        start_datetime = target_datetime - timedelta(days=6)
    else:
        # Find the previous Saturday
        days_since_saturday = (target_datetime.weekday() + 2) % 7
        start_datetime = target_datetime - timedelta(days=days_since_saturday)
    end_datetime = target_datetime
    
    start_date = start_datetime.strftime('%Y-%m-%d')
    end_date = end_datetime.strftime('%Y-%m-%d 23:59:59')
    
    print(f"Generating MSA for {target_date_str} using prior from {prior_date_str}")
    print(f"Sales period: {start_date} to {end_date}")
    
    # Step 1: Parse prior MSA file
    print("\nSTEP 1: Parsing prior MSA file...")
    prior_records = parse_msa_file(prior_msa_file)
    
    # Step 2: Load all POS items
    print("\nSTEP 2: Loading POS items...")
    sku_lookup, all_items = load_all_tobacco_items()
    
    # Step 3: Find new products
    print("\nSTEP 3: Finding new products...")
    new_items = find_new_products_since(prior_date_str, sku_lookup)
    
    # Step 4: Build comprehensive UPC mapping
    print("\nSTEP 4: Building UPC mapping...")
    upc_mapping, unmapped, new_product_bids = build_comprehensive_upc_mapping(
        prior_records, sku_lookup, new_items
    )
    
    # Step 5: Get sales data
    print("\nSTEP 5: Getting sales data...")
    sales_data = get_sales_data(start_date, end_date, upc_mapping, sku_lookup)
    
    # Step 6: Generate MSA file
    print("\nSTEP 6: Generating MSA file...")
    generate_improved_msa_file(
        prior_records, sales_data, upc_mapping, new_product_bids, 
        output_file, target_date_str
    )
    
    # Step 7: Validate
    print("\nSTEP 7: Validating...")
    validate_improved(output_file, actual_file)
    
    print("\n✅ Generation complete!")

if __name__ == "__main__":
    main()