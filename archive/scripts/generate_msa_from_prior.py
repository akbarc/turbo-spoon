#!/usr/bin/env python3
"""
Generate MSA files using modified CSV mappings and prior period data as fallback
Based on the work already done in the MODIFIED CSV files
"""

import csv
import re
from datetime import datetime, timedelta
from collections import defaultdict
import os

def load_modified_items_mapping(filepath):
    """Load the modified items CSV with MSA mappings"""
    items_mapping = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('TRUE MATCH') == '1':
                # Extract the BID record and the matching UPC
                bid_record = row.get('', '')  # The BID record is in the unnamed second column
                
                # Parse the BID record to get the UPC
                if bid_record.startswith('BID'):
                    # Extract the doubled UPC from the BID record
                    match = re.match(r'BID\s*(\d+)', bid_record[3:])
                    if match:
                        doubled_upc = match.group(1)
                        # The UPC is doubled, take first half
                        if len(doubled_upc) % 2 == 0:
                            msa_upc = doubled_upc[:len(doubled_upc)//2]
                        else:
                            msa_upc = doubled_upc
                        
                        # Find the matching POS UPC (look for non-zero match columns)
                        pos_upc = None
                        for col in ['3 Digit UPC', '4 Digit UPC', '5 Digit UPC', '6 Digit UPC', 
                                   '7 Digit UPC', '8 Digit UPC', '9 Digit UPC', '10 Digit UPC',
                                   '11 Digit UPC', '12 Digit UPC', '13 Digit UPC', '14 Digit UPC', '15 Digit UPC']:
                            if row.get(col):
                                # Check if this column has a match
                                match_col = col + ' MATCH'
                                if row.get(match_col) and float(row.get(match_col, 0)) > 0:
                                    pos_upc = row.get(col)
                                    break
                        
                        if pos_upc:
                            items_mapping[pos_upc] = {
                                'msa_upc': msa_upc,
                                'bid_record': bid_record
                            }
    
    return items_mapping

def load_modified_sales_mapping(filepath):
    """Load the modified sales CSV with MSA mappings"""
    sales_mapping = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Record Type') == 'PUR':
                sales_mapping.append({
                    'msa_customer': row.get('MSA Customer', ''),
                    'msa_sku': row.get('MSA SKU', ''),
                    'msa_record': row.get('MSA SALES RECORD', ''),
                    'pos_customer': row.get('POS CUSTOMER', ''),
                    'pos_sku': row.get('POS SKU', ''),
                    'pos_qty': row.get('POS QT', ''),
                    'pos_price': row.get('POS Price', '')
                })
    
    return sales_mapping

def parse_msa_file(filepath):
    """Parse an existing MSA file to extract all records"""
    records = {
        'HID': [],
        'SID': [],
        'BID': [],
        'PUR': [],
        'TOT': []
    }
    
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if line.startswith('HID'):
                records['HID'].append(line)
            elif line.startswith('SID'):
                records['SID'].append(line)
            elif line.startswith('BID'):
                records['BID'].append(line)
            elif line.startswith('PUR'):
                records['PUR'].append(line)
            elif line.startswith('TOT'):
                records['TOT'].append(line)
    
    return records

def generate_msa_for_week(target_date, prior_msa_file, items_mapping, sales_mapping, 
                          new_items_csv=None, new_sales_csv=None):
    """
    Generate MSA file for target week using prior period as fallback
    
    Args:
        target_date: The week date (e.g., '06272025')
        prior_msa_file: Path to the prior week's MSA file
        items_mapping: Mapping from modified items CSV
        sales_mapping: Mapping from modified sales CSV
        new_items_csv: Optional path to new week's items CSV
        new_sales_csv: Optional path to new week's sales CSV
    """
    
    # Load prior MSA as base
    prior_records = parse_msa_file(prior_msa_file)
    
    # Initialize new records with prior data
    new_records = {
        'HID': [],
        'SID': prior_records['SID'].copy(),  # Keep same customers
        'BID': [],
        'PUR': [],
        'TOT': []
    }
    
    # Update HID record with new date
    if prior_records['HID']:
        hid = prior_records['HID'][0]
        # Update the date in HID record (positions vary, need to find date pattern)
        # For now, keep as is and update manually if needed
        new_records['HID'] = [hid]
    
    # Process BID records
    bid_lookup = {}
    for bid_line in prior_records['BID']:
        # Extract UPC from BID record
        if bid_line.startswith('BID'):
            match = re.match(r'BID\s*(\d+)', bid_line[3:])
            if match:
                doubled_upc = match.group(1)
                if len(doubled_upc) % 2 == 0:
                    upc = doubled_upc[:len(doubled_upc)//2]
                else:
                    upc = doubled_upc
                bid_lookup[upc] = bid_line
    
    # If we have new items CSV, update inventory
    if new_items_csv and os.path.exists(new_items_csv):
        # Load new items and update BID records
        with open(new_items_csv, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    pos_upc = row[0].strip()
                    new_qty = row[1].strip()
                    
                    # Check if we have mapping for this UPC
                    if pos_upc in items_mapping:
                        msa_upc = items_mapping[pos_upc]['msa_upc']
                        if msa_upc in bid_lookup:
                            # Update the inventory in the BID record
                            bid_line = bid_lookup[msa_upc]
                            # Update inventory at the end (003XXXXXXX format)
                            # This is complex, for now keep as is
                            new_records['BID'].append(bid_line)
                        else:
                            # Use the BID record from mapping
                            new_records['BID'].append(items_mapping[pos_upc]['bid_record'])
    else:
        # No new items, use prior period BID records
        new_records['BID'] = prior_records['BID'].copy()
    
    # Process PUR records
    if new_sales_csv and os.path.exists(new_sales_csv):
        # Load new sales and create PUR records
        with open(new_sales_csv, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    pos_customer = row[0].strip()
                    pos_sku = row[1].strip()
                    pos_qty = row[2].strip()
                    pos_price = row[3].strip()
                    
                    # Find matching pattern in sales mapping
                    for mapping in sales_mapping:
                        if (mapping['pos_customer'] == pos_customer and 
                            mapping['pos_sku'] == pos_sku):
                            # Create PUR record
                            msa_customer = mapping['msa_customer']
                            msa_sku = mapping['msa_sku'].zfill(14)  # Pad to 14 digits
                            
                            # Format quantity and price
                            qty_str = f"00100000{int(float(pos_qty)):03d}.0000"
                            price_str = f"200000{float(pos_price):07.2f}".replace('.', '')
                            
                            pur_line = f"PUR{msa_customer:<24}{msa_sku:<60}{qty_str}{price_str}"
                            new_records['PUR'].append(pur_line)
                            break
    else:
        # No new sales, use prior period PUR records
        new_records['PUR'] = prior_records['PUR'].copy()
    
    # Generate TOT record (summary)
    total_bid = len(new_records['BID'])
    total_sid = len(new_records['SID'])
    total_pur = len(new_records['PUR'])
    
    # Create TOT record
    tot_line = f"TOT{total_bid:010d}{total_sid:010d}{total_pur:010d}"
    new_records['TOT'] = [tot_line]
    
    return new_records

def write_msa_file(records, output_path):
    """Write MSA records to file"""
    with open(output_path, 'w', encoding='latin-1') as f:
        # Write in order: HID, SID, BID, PUR, TOT
        for record_type in ['HID', 'SID', 'BID', 'PUR', 'TOT']:
            for line in records[record_type]:
                f.write(line + '\r\n')

def main():
    """Generate MSA for 06/27/2025 using 06/20/2025 as base"""
    
    print("Loading modified CSV mappings...")
    items_mapping = load_modified_items_mapping('Items- 06202025 MODIFIED.csv')
    sales_mapping = load_modified_sales_mapping('Sales - 06202025 MODIFIED.csv')
    
    print(f"Loaded {len(items_mapping)} item mappings")
    print(f"Loaded {len(sales_mapping)} sales mappings")
    
    # Generate MSA for 06/27/2025
    print("\nGenerating MSA for 06/27/2025...")
    
    # Since we don't have CSV files for 6/27, we'll use prior period data
    new_records = generate_msa_for_week(
        target_date='06272025',
        prior_msa_file='MSA Data Fr/06202025',
        items_mapping=items_mapping,
        sales_mapping=sales_mapping,
        new_items_csv=None,  # Don't have this
        new_sales_csv=None   # Don't have this
    )
    
    # Write to file
    output_path = 'generated_06272025.txt'
    write_msa_file(new_records, output_path)
    print(f"\nGenerated MSA file: {output_path}")
    
    # Compare with actual
    print("\nComparing with actual MSA file...")
    actual_records = parse_msa_file('MSA Data Fr/06272025')
    
    print(f"Generated: {len(new_records['BID'])} BID, {len(new_records['PUR'])} PUR")
    print(f"Actual:    {len(actual_records['BID'])} BID, {len(actual_records['PUR'])} PUR")

if __name__ == "__main__":
    main()