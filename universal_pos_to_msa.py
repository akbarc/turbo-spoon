#!/usr/bin/env python3
"""
Universal POS to MSA transformer
Applies the transformation rules to ANY POS data, not just mapped items
"""

import csv
import os
from datetime import datetime, timedelta

def transform_pos_to_msa(items_csv, sales_csv, week_date, template_msa=None):
    """
    Transform ANY POS CSV files to MSA format using the discovered rules:
    1. Customer ID: Add trailing '0'
    2. UPC: Pad to 14 digits with leading zeros
    3. Use template MSA for structure (HID, SID records)
    """
    
    print(f"\n{'='*70}")
    print(f"UNIVERSAL POS TO MSA TRANSFORMATION")
    print(f"Week: {week_date}")
    print(f"{'='*70}")
    
    print(f"\nInput files:")
    print(f"  Items: {items_csv}")
    print(f"  Sales: {sales_csv}")
    
    # Load template MSA for structure
    template_records = {}
    if template_msa and os.path.exists(template_msa):
        print(f"  Template: {template_msa}")
        with open(template_msa, 'r', encoding='latin-1') as f:
            template_records['HID'] = []
            template_records['SID'] = []
            for line in f:
                line = line.rstrip('\r\n')
                if line.startswith('HID'):
                    template_records['HID'].append(line)
                elif line.startswith('SID'):
                    template_records['SID'].append(line)
    
    # Initialize MSA records
    msa = {
        'HID': [],
        'SID': [],
        'BID': [],
        'PUR': [],
        'TOT': []
    }
    
    # Create HID record (use template or generate)
    if template_records.get('HID'):
        hid = template_records['HID'][0]
        # Update date in HID record
        # The date is typically at position after 'W'
        if 'W' in hid:
            idx = hid.index('W')
            # Replace the 8-digit date after W
            hid = hid[:idx+1] + week_date + hid[idx+9:]
        msa['HID'].append(hid)
    else:
        # Generate HID
        hid = f"HID17000028TOB  W{week_date}Georgia Wholesale" + " "*31
        hid += "2935 N Decatur Rd Suite A" + " "*89
        hid += "Decatur                  GA30033    USA"
        hid += "Rajput              Raj                      "
        hid += "4042924899     4042922573"
        hid += "rajput7866@aol.com" + " "*46
        
        week_dt = datetime.strptime(week_date, '%m%d%Y')
        next_day = week_dt + timedelta(days=1)
        hid += f"00010000000220{next_day.strftime('%y%m%d')} "
        msa['HID'].append(hid)
    
    # Get customer list (SID records) from template
    customers_in_sales = set()
    
    # First pass - identify all customers in sales
    with open(sales_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                pos_customer = row[0].strip()
                customers_in_sales.add(pos_customer)
    
    print(f"\nFound {len(customers_in_sales)} unique customers in sales")
    
    # Copy SID records from template
    if template_records.get('SID'):
        msa['SID'] = template_records['SID'].copy()
        print(f"Using {len(msa['SID'])} customers from template")
    
    # Process Items CSV -> BID records
    print(f"\nProcessing items...")
    
    items_by_upc = {}  # Track items for BID generation
    
    with open(items_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                pos_upc = row[0].strip()
                quantity = int(row[1])
                items_by_upc[pos_upc] = quantity
    
    print(f"  Loaded {len(items_by_upc)} items")
    
    # Generate BID records
    for pos_upc, quantity in items_by_upc.items():
        # Apply transformation: MSA UPC is doubled
        msa_upc = pos_upc + '0'  # Add trailing 0 as discovered
        doubled_upc = msa_upc + msa_upc  # Double it for BID format
        
        # Create BID record
        # Format: BID[spaces][doubled UPC][description][...][inventory]
        bid = f"BID  {doubled_upc}"
        
        # Add placeholder description (50 chars)
        bid += "PRODUCT" + " "*43
        
        # Add other fields (mostly spaces)
        bid += " "*100
        
        # Add inventory at end (003XXXXXXXXX format)
        inv_str = f"{quantity:011d}"
        bid += f"003{inv_str}"
        
        msa['BID'].append(bid)
    
    print(f"  Generated {len(msa['BID'])} BID records")
    
    # Process Sales CSV -> PUR records
    print(f"\nProcessing sales...")
    
    sales_count = 0
    with open(sales_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                pos_customer = row[0].strip()
                pos_upc = row[1].strip()
                quantity = int(row[2])
                price = float(row[3])
                
                # Apply transformations
                # 1. Customer: add trailing 0
                msa_customer = pos_customer + '0'
                
                # 2. UPC: pad to 14 digits with leading zeros
                msa_upc = pos_upc.zfill(14)
                
                # Create PUR record
                # Format: PUR[customer 24 chars][UPC 14 digits + spaces]...[quantity][price]
                pur = f"PUR{msa_customer:<24}"
                pur += f"{msa_upc:<60}"
                pur += " "*30
                
                # Format quantity (001 + 11 digits with 4 decimal places)
                qty_str = f"{quantity:011.4f}".replace('.', '')
                pur += f"001{qty_str}"
                
                # Format price (002 + 11 digits with 2 decimal places)
                price_str = f"{price:011.2f}".replace('.', '')
                pur += f"002{price_str}"
                
                msa['PUR'].append(pur)
                sales_count += 1
    
    print(f"  Generated {sales_count} PUR records")
    
    # Generate TOT record
    tot = "TOT"
    tot += f"{len(msa['BID']):010d}"  # BID count
    tot += f"{len(msa['SID']):010d}"  # SID count
    tot += f"{len(msa['PUR']):010d}"  # PUR count
    # Add more fields if needed based on actual format
    tot += " "*200  # Padding
    
    msa['TOT'].append(tot)
    
    print(f"\n{'='*70}")
    print(f"TRANSFORMATION COMPLETE")
    print(f"{'='*70}")
    print(f"Generated MSA records:")
    print(f"  HID: {len(msa['HID'])}")
    print(f"  SID: {len(msa['SID'])} customers")
    print(f"  BID: {len(msa['BID'])} products")
    print(f"  PUR: {len(msa['PUR'])} sales")
    print(f"  TOT: {len(msa['TOT'])}")
    
    return msa

def write_msa_file(msa_records, output_file):
    """Write MSA records to file"""
    with open(output_file, 'w', encoding='latin-1') as f:
        for record_type in ['HID', 'SID', 'BID', 'PUR', 'TOT']:
            for line in msa_records[record_type]:
                f.write(line + '\r\n')
    
    print(f"\nMSA file written to: {output_file}")
    size = os.path.getsize(output_file)
    print(f"File size: {size:,} bytes")
    return size

def main():
    """Test with actual POS data for 08/01/2025"""
    
    items_csv = 'archive/data_exports/test_Items- 08012025.csv'
    sales_csv = 'archive/data_exports/test_Sales - 08012025.csv'
    week_date = '08012025'
    template_msa = f'MSA Data Fr/{week_date}'
    
    # Transform POS to MSA
    msa_records = transform_pos_to_msa(
        items_csv=items_csv,
        sales_csv=sales_csv,
        week_date=week_date,
        template_msa=template_msa
    )
    
    # Write output
    output_file = 'universal_pos_generated_08012025.txt'
    generated_size = write_msa_file(msa_records, output_file)
    
    # Compare with actual
    if os.path.exists(template_msa):
        actual_size = os.path.getsize(template_msa)
        print(f"\nComparison:")
        print(f"  Actual MSA:    {actual_size:,} bytes")
        print(f"  Generated MSA: {generated_size:,} bytes")
        print(f"  Difference:    {abs(actual_size - generated_size):,} bytes")
        
        # Count records
        print(f"\nRecord count comparison:")
        for record_type in ['BID', 'PUR', 'SID']:
            with open(template_msa, 'r', encoding='latin-1') as f:
                actual_count = sum(1 for line in f if line.startswith(record_type))
            
            generated_count = len(msa_records[record_type])
            match = "✓" if actual_count == generated_count else "✗"
            print(f"  {record_type}: Actual={actual_count}, Generated={generated_count} {match}")

if __name__ == "__main__":
    main()