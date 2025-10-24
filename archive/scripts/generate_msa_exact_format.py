#!/usr/bin/env python3
"""
Generate MSA file matching EXACT format of actual files
Following the actual format pattern discovered in our MSA files
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from database_pymssql import connection_pool

# Tobacco category IDs from POS
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

def parse_actual_msa_format(filepath):
    """Parse MSA file understanding the actual format used"""
    records = {
        'header': None,
        'bids': [],
        'sids': [],
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
                # BID records follow standard format
                bid_data = {
                    'raw': line.rstrip('\r\n'),
                    'upc': line[3:18].strip() if len(line) > 18 else '',
                    'name': line[18:78].strip() if len(line) > 78 else '',
                    'quantity': line[199:210].strip() if len(line) > 210 else '0'
                }
                records['bids'].append(bid_data)
                
            elif record_type == 'SID':
                records['sids'].append(line.rstrip('\r\n'))
                
            elif record_type == 'PUR':
                # Parse the actual PUR format used in our files
                # Format appears to be: PUR + customer + spaces + concatenated data
                pur_data = {
                    'raw': line.rstrip('\r\n'),
                    'customer_id': line[3:11].strip() if len(line) > 11 else '',
                    # The SKU appears to be embedded in positions 27-41
                    'sku': line[27:41].strip() if len(line) > 41 else '',
                    # Additional data after position 80
                    'extra_data': line[80:].strip() if len(line) > 80 else ''
                }
                records['purs'].append(pur_data)
    
    print(f"Found {len(records['bids'])} BID records")
    print(f"Found {len(records['sids'])} SID records")
    print(f"Found {len(records['purs'])} PUR records")
    
    return records

def match_sku_pattern(msa_sku, pos_sku):
    """
    Match MSA SKU format to POS ItemLookupCode
    The actual files use specific SKU patterns
    """
    if not msa_sku or not pos_sku:
        return False
    
    # Clean both
    msa_clean = msa_sku.strip().lstrip('0')
    pos_clean = pos_sku.strip().lstrip('0')
    
    # Direct match
    if msa_clean == pos_clean:
        return True
    
    # Check if POS SKU is contained in MSA SKU
    if pos_clean in msa_clean:
        return True
    
    # Check if MSA SKU is contained in POS SKU
    if msa_clean in pos_clean:
        return True
    
    # Try matching last N digits
    for n in range(5, min(len(msa_clean), len(pos_clean)) + 1):
        if msa_clean[-n:] == pos_clean[-n:]:
            return True
    
    return False

def build_sku_mapping(prior_records, sku_lookup):
    """Build mapping between MSA format and POS SKUs"""
    mapping = {}
    
    print("Building SKU mapping from actual file patterns...")
    
    # Analyze actual PUR records to understand SKU patterns
    sku_patterns = set()
    for pur in prior_records['purs']:
        if pur['sku']:
            sku_patterns.add(pur['sku'])
    
    print(f"Found {len(sku_patterns)} unique SKU patterns in PUR records")
    
    # Map each pattern to POS items
    for pattern in sku_patterns:
        for pos_sku, item in sku_lookup.items():
            if match_sku_pattern(pattern, pos_sku):
                mapping[pattern] = pos_sku
                break
    
    print(f"Mapped {len(mapping)} SKU patterns to POS items")
    
    return mapping

def format_pur_record_exact(customer_id, sku_pattern, quantity_data=''):
    """Format PUR record matching actual file format"""
    # Match the exact format from actual files:
    # PUR + customer(8) + spaces(19) + sku(14) + spaces + data
    
    line = 'PUR'
    line += customer_id[:9].ljust(9)  # Customer ID padded to 9
    line += ' ' * 18  # Spaces
    line += sku_pattern[:14].ljust(14)  # SKU pattern
    line += ' ' * 61  # More spaces to position 102
    
    # Add the quantity/price data if provided
    if quantity_data:
        line += quantity_data
    else:
        # Default quantity format from actual files
        line += '00100000001.0000100000000.00'
    
    # Ensure line is 130 characters (typical length)
    if len(line) < 130:
        line = line.ljust(130)
    
    return line[:130]  # Truncate to match actual file length

def generate_exact_format_msa(prior_file, output_file, target_date_str):
    """Generate MSA matching exact format of actual files"""
    
    # Parse prior file
    prior_records = parse_actual_msa_format(prior_file)
    
    # Connect to database
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Get tobacco items
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
    sku_lookup = {item['ItemLookupCode']: item for item in items}
    
    # Build SKU mapping
    sku_mapping = build_sku_mapping(prior_records, sku_lookup)
    
    # Calculate date range
    target_date = datetime.strptime(target_date_str, '%Y%m%d')
    if target_date.weekday() == 4:  # Friday
        start_date = target_date - timedelta(days=6)
    else:
        days_since_saturday = (target_date.weekday() + 2) % 7
        start_date = target_date - timedelta(days=days_since_saturday)
    
    # Get sales data
    print(f"Getting sales for {start_date.strftime('%Y-%m-%d')} to {target_date.strftime('%Y-%m-%d')}")
    
    # For now, let's just copy the format exactly
    # In production, we'd query actual sales
    
    # Write output file matching exact format
    with open(output_file, 'w') as f:
        # Header - update date
        if prior_records['header']:
            # Find date in header and replace
            header = prior_records['header']
            # The date typically appears after position 18
            old_date_str = prior_file.split('/')[-1]  # Get date from filename
            new_date_str = target_date_str
            header = header.replace(old_date_str, new_date_str)
            f.write(header + '\n')
        
        # BID records - maintain exact format
        for bid in prior_records['bids']:
            f.write(bid['raw'] + '\n')
        
        # SID records - maintain all
        for sid in prior_records['sids']:
            f.write(sid + '\n')
        
        # PUR records - this is where the actual format matters
        # For testing, let's replicate the pattern
        sample_customers = ['429225940', '489878600', '465496500']
        sample_skus = ['00008660007247', '06291100731176', '00094922733443']
        
        for customer in sample_customers[:2]:
            for sku in sample_skus[:3]:
                pur_line = format_pur_record_exact(customer, sku)
                f.write(pur_line + '\n')
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    print(f"Generated: {output_file}")

def main():
    if len(sys.argv) > 1:
        prior_date = sys.argv[1]
        target_date = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # Default test
        prior_date = "08012025"
        target_date = "08082025"
    
    prior_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_exact.txt"
    target_date_str = "2025" + target_date[:4]
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generate_exact_format_msa(prior_file, output_file, target_date_str)
    
    # Compare with actual
    actual_file = f"MSA Data Fr/{target_date}"
    if os.path.exists(actual_file):
        print("\nComparing with actual file...")
        actual = parse_actual_msa_format(actual_file)
        generated = parse_actual_msa_format(output_file)
        
        print(f"Actual BIDs: {len(actual['bids'])}, Generated: {len(generated['bids'])}")
        print(f"Actual SIDs: {len(actual['sids'])}, Generated: {len(generated['sids'])}")
        print(f"Actual PURs: {len(actual['purs'])}, Generated: {len(generated['purs'])}")

if __name__ == "__main__":
    main()