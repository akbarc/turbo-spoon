#!/usr/bin/env python3
"""
Complete POS to MSA transformer
1. Transforms POS data using the rules
2. Adds products from prior MSA that aren't in POS
3. Ensures proper customer ID transformation
"""

import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

def extract_upc_from_bid(bid_line):
    """Extract the single UPC from a BID record"""
    if not bid_line.startswith('BID'):
        return None
    
    content = bid_line[3:].lstrip()
    match = re.match(r'(\d+)', content)
    if match:
        doubled_upc = match.group(1)
        if len(doubled_upc) % 2 == 0:
            half_len = len(doubled_upc) // 2
            first_half = doubled_upc[:half_len]
            second_half = doubled_upc[half_len:]
            if first_half == second_half:
                return first_half
    return None

def parse_msa_file(filepath):
    """Parse an MSA file completely"""
    records = {
        'HID': [],
        'SID': {},  # customer_id -> record
        'BID': {},  # upc -> record
        'PUR': [],
        'TOT': []
    }
    
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            line = line.rstrip('\r\n')
            
            if line.startswith('HID'):
                records['HID'].append(line)
            elif line.startswith('SID'):
                # Extract customer ID (position 3-27)
                customer_id = line[3:27].strip()
                records['SID'][customer_id] = line
            elif line.startswith('BID'):
                upc = extract_upc_from_bid(line)
                if upc:
                    records['BID'][upc] = line
            elif line.startswith('PUR'):
                records['PUR'].append(line)
            elif line.startswith('TOT'):
                records['TOT'].append(line)
    
    return records

def complete_pos_to_msa(items_csv, sales_csv, week_date, prior_msa_file=None):
    """
    Complete transformation: POS data + prior MSA fallback
    """
    
    print(f"\n{'='*70}")
    print(f"COMPLETE POS TO MSA TRANSFORMATION")
    print(f"Week: {week_date}")
    print(f"{'='*70}")
    
    # Load prior MSA if available
    prior_records = {}
    if prior_msa_file and os.path.exists(prior_msa_file):
        print(f"\nLoading prior MSA: {prior_msa_file}")
        prior_records = parse_msa_file(prior_msa_file)
        print(f"  Prior has {len(prior_records['BID'])} products, {len(prior_records['SID'])} customers")
    
    # Initialize MSA records
    msa = {
        'HID': [],
        'SID': {},
        'BID': {},
        'PUR': [],
        'TOT': []
    }
    
    # Create/copy HID record
    if prior_records.get('HID'):
        hid = prior_records['HID'][0]
        # Update date in HID record
        if 'W' in hid:
            idx = hid.index('W')
            hid = hid[:idx+1] + week_date + hid[idx+9:]
        msa['HID'].append(hid)
    else:
        # Generate new HID
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
    
    # Process POS Items -> BID records
    print(f"\nProcessing POS items from {items_csv}...")
    
    pos_items = {}
    with open(items_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                pos_upc = row[0].strip()
                quantity = int(row[1])
                pos_items[pos_upc] = quantity
    
    print(f"  Loaded {len(pos_items)} POS items")
    
    # Transform POS items to BID records
    pos_upcs_transformed = set()
    
    for pos_upc, quantity in pos_items.items():
        # Apply transformation rules
        # Try different patterns to match with prior MSA
        candidates = [
            pos_upc,
            pos_upc + '0',  # Add trailing 0 (primary transformation)
            pos_upc.lstrip('0'),  # Remove leading zeros
            pos_upc.zfill(13),  # Pad to 13 digits
        ]
        
        matched = False
        for candidate in candidates:
            if candidate in prior_records.get('BID', {}):
                # Use the BID record from prior MSA
                bid_line = prior_records['BID'][candidate]
                
                # Update inventory if needed
                # The inventory is at the end in format 003XXXXXXXXX
                if '003' in bid_line:
                    # Find and replace inventory
                    inv_match = re.search(r'003[-\d]+', bid_line)
                    if inv_match:
                        old_inv = inv_match.group()
                        new_inv = f"003{quantity:011d}"
                        bid_line = bid_line.replace(old_inv, new_inv)
                
                msa['BID'][candidate] = bid_line
                pos_upcs_transformed.add(candidate)
                matched = True
                break
        
        if not matched:
            # Create new BID record for unmapped item
            msa_upc = pos_upc + '0'  # Apply primary transformation
            doubled_upc = msa_upc + msa_upc
            
            bid = f"BID  {doubled_upc}"
            bid += "PRODUCT" + " "*43  # Placeholder description
            bid += " "*100
            bid += f"003{quantity:011d}"  # Inventory
            
            msa['BID'][msa_upc] = bid
            pos_upcs_transformed.add(msa_upc)
    
    print(f"  Transformed {len(pos_upcs_transformed)} POS items to BID records")
    
    # Add products from prior MSA that aren't in POS
    if prior_records.get('BID'):
        print(f"\nAdding products from prior MSA not in POS...")
        added_from_prior = 0
        
        for upc, bid_line in prior_records['BID'].items():
            if upc not in pos_upcs_transformed:
                # This product wasn't in POS, add from prior
                msa['BID'][upc] = bid_line
                added_from_prior += 1
        
        print(f"  Added {added_from_prior} products from prior MSA")
    
    # Process POS Sales -> PUR records
    print(f"\nProcessing POS sales from {sales_csv}...")
    
    # First, collect all unique customers from sales
    pos_customers = set()
    sales_data = []
    
    with open(sales_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                pos_customer = row[0].strip()
                pos_upc = row[1].strip()
                quantity = int(row[2])
                price = float(row[3])
                
                pos_customers.add(pos_customer)
                sales_data.append({
                    'customer': pos_customer,
                    'upc': pos_upc,
                    'qty': quantity,
                    'price': price
                })
    
    print(f"  Loaded {len(sales_data)} sales from {len(pos_customers)} customers")
    
    # Build customer mapping and copy SID records
    print(f"\nProcessing customers...")
    
    # Copy all SID records from prior MSA
    if prior_records.get('SID'):
        msa['SID'] = prior_records['SID'].copy()
        print(f"  Copied {len(msa['SID'])} customers from prior MSA")
    
    # Check if any POS customers need to be added
    for pos_customer in pos_customers:
        # Transform customer ID: add trailing 0
        msa_customer = pos_customer + '0'
        
        # Check if this customer exists in SID records
        if msa_customer not in msa['SID'] and prior_records.get('SID'):
            # Try to find a close match in prior SID
            for sid_id, sid_record in prior_records['SID'].items():
                if pos_customer in sid_id or sid_id.startswith(pos_customer):
                    # Found a match, use this SID record
                    msa['SID'][msa_customer] = sid_record
                    break
    
    # Generate PUR records from sales
    print(f"\nGenerating PUR records...")
    
    for sale in sales_data:
        # Apply transformations
        msa_customer = sale['customer'] + '0'  # Add trailing 0
        msa_upc = sale['upc'].zfill(14)  # Pad to 14 digits
        
        # Create PUR record
        pur = f"PUR{msa_customer:<24}"
        pur += f"{msa_upc:<60}"
        pur += " "*30
        
        # Format quantity and price
        qty_str = f"{sale['qty']:011.4f}".replace('.', '')
        pur += f"001{qty_str}"
        
        price_str = f"{sale['price']:011.2f}".replace('.', '')
        pur += f"002{price_str}"
        
        msa['PUR'].append(pur)
    
    print(f"  Generated {len(msa['PUR'])} PUR records")
    
    # Generate TOT record
    # Copy format from prior if available, otherwise generate
    if prior_records.get('TOT'):
        tot = prior_records['TOT'][0]
        # Update counts in TOT record if it has them
        # This varies by MSA format
        msa['TOT'].append(tot)
    else:
        tot = "TOT"
        tot += f"{len(msa['BID']):010d}"
        tot += f"{len(msa['SID']):010d}"
        tot += f"{len(msa['PUR']):010d}"
        tot += " "*200
        msa['TOT'].append(tot)
    
    # Convert dict BID/SID to lists for writing
    final_msa = {
        'HID': msa['HID'],
        'SID': list(msa['SID'].values()),
        'BID': list(msa['BID'].values()),
        'PUR': msa['PUR'],
        'TOT': msa['TOT']
    }
    
    print(f"\n{'='*70}")
    print(f"TRANSFORMATION COMPLETE")
    print(f"{'='*70}")
    print(f"Final MSA records:")
    print(f"  HID: {len(final_msa['HID'])}")
    print(f"  SID: {len(final_msa['SID'])} customers")
    print(f"  BID: {len(final_msa['BID'])} products")
    print(f"    - From POS: {len(pos_upcs_transformed)}")
    print(f"    - From prior MSA: {len(final_msa['BID']) - len(pos_upcs_transformed)}")
    print(f"  PUR: {len(final_msa['PUR'])} sales (all from POS)")
    print(f"  TOT: {len(final_msa['TOT'])}")
    
    return final_msa

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
    """Test with 08/01/2025 POS data"""
    
    # Use actual POS data
    items_csv = 'archive/data_exports/test_Items- 08012025.csv'
    sales_csv = 'archive/data_exports/test_Sales - 08012025.csv'
    week_date = '08012025'
    
    # Use prior week (07/25) for products not in POS
    prior_msa = 'MSA Data Fr/07252025'
    
    # Transform
    msa_records = complete_pos_to_msa(
        items_csv=items_csv,
        sales_csv=sales_csv,
        week_date=week_date,
        prior_msa_file=prior_msa
    )
    
    # Write output
    output_file = 'complete_pos_generated_08012025.txt'
    generated_size = write_msa_file(msa_records, output_file)
    
    # Compare with actual
    actual_file = f'MSA Data Fr/{week_date}'
    if os.path.exists(actual_file):
        actual_size = os.path.getsize(actual_file)
        
        print(f"\n{'='*70}")
        print("COMPARISON WITH ACTUAL MSA")
        print(f"{'='*70}")
        
        print(f"File sizes:")
        print(f"  Actual:    {actual_size:,} bytes")
        print(f"  Generated: {generated_size:,} bytes")
        print(f"  Match: {actual_size == generated_size}")
        
        # Count records
        print(f"\nRecord counts:")
        
        actual_counts = {}
        with open(actual_file, 'r', encoding='latin-1') as f:
            for line in f:
                for record_type in ['HID', 'SID', 'BID', 'PUR', 'TOT']:
                    if line.startswith(record_type):
                        actual_counts[record_type] = actual_counts.get(record_type, 0) + 1
                        break
        
        print(f"{'Type':<10} {'Actual':<10} {'Generated':<10} {'Match':<10}")
        print("-"*40)
        
        for record_type in ['HID', 'SID', 'BID', 'PUR', 'TOT']:
            actual = actual_counts.get(record_type, 0)
            generated = len(msa_records[record_type])
            match = "✓" if actual == generated else "✗"
            print(f"{record_type:<10} {actual:<10} {generated:<10} {match:<10}")
        
        # Calculate accuracy
        total_actual = sum(actual_counts.values())
        total_generated = sum(len(msa_records[t]) for t in ['HID', 'SID', 'BID', 'PUR', 'TOT'])
        accuracy = 100 * min(total_actual, total_generated) / max(total_actual, total_generated)
        
        print(f"\nOverall accuracy: {accuracy:.1f}%")

if __name__ == "__main__":
    main()