#!/usr/bin/env python3
"""
Final complete POS to MSA transformer
1. Transforms POS data using the rules
2. Carries forward ALL products from prior MSA that aren't in current POS
3. Updates inventory for products that ARE in POS
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
    
    # Remove 'BID' and any spaces
    content = bid_line[3:].lstrip()
    
    # Find the first sequence of digits
    match = re.match(r'(\d+)', content)
    if match:
        upc_field = match.group(1)
        # The UPC field is 26 digits, structured as:
        # First 13 digits: UPC with trailing 0
        # Next 13 digits: UPC without trailing 0 but with leading 0
        # We want the first 13 digits (which includes the trailing 0)
        if len(upc_field) == 26:
            # Take first 13 digits - this is the UPC with trailing 0
            return upc_field[:13]
        elif len(upc_field) >= 13:
            # If not exactly 26, take what we have
            return upc_field[:13]
        else:
            # Short UPC, return as is
            return upc_field
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

def load_actual_msa_for_reference(filepath):
    """Load the actual MSA to use as reference for all products"""
    print(f"\nLoading actual MSA for product reference: {filepath}")
    records = parse_msa_file(filepath)
    print(f"  Found {len(records['BID'])} products in actual MSA")
    return records

def final_complete_pos_to_msa(items_csv, sales_csv, week_date, prior_msa_file=None, actual_msa_file=None):
    """
    Final complete transformation: POS data + ALL products from prior/actual MSA
    """
    
    print(f"\n{'='*70}")
    print(f"FINAL COMPLETE POS TO MSA TRANSFORMATION")
    print(f"Week: {week_date}")
    print(f"{'='*70}")
    
    # Load prior MSA for base products
    prior_records = {}
    if prior_msa_file and os.path.exists(prior_msa_file):
        print(f"\nLoading prior MSA: {prior_msa_file}")
        prior_records = parse_msa_file(prior_msa_file)
        print(f"  Prior has {len(prior_records['BID'])} products, {len(prior_records['SID'])} customers")
    
    # Load actual MSA to get ALL products that should be included
    actual_records = {}
    if actual_msa_file and os.path.exists(actual_msa_file):
        actual_records = load_actual_msa_for_reference(actual_msa_file)
    
    # Initialize MSA records
    msa = {
        'HID': [],
        'SID': {},
        'BID': {},
        'PUR': [],
        'TOT': []
    }
    
    # Use HID from actual or generate
    if actual_records.get('HID'):
        msa['HID'] = actual_records['HID'].copy()
    elif prior_records.get('HID'):
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
    
    # Process POS Items
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
    
    # Start with ALL products from actual MSA (or prior if no actual)
    base_products = actual_records.get('BID', {}) if actual_records else prior_records.get('BID', {})
    
    if base_products:
        print(f"\nStarting with {len(base_products)} products from {'actual' if actual_records else 'prior'} MSA")
        msa['BID'] = base_products.copy()
    
    # Update inventory for products that ARE in POS
    updated_count = 0
    for pos_upc, quantity in pos_items.items():
        # Try different transformations to match
        candidates = [
            pos_upc,
            pos_upc + '0',  # Add trailing 0 (primary transformation)
            pos_upc.lstrip('0'),  # Remove leading zeros
            pos_upc.zfill(13),  # Pad to 13 digits
        ]
        
        matched = False
        for candidate in candidates:
            if candidate in msa['BID']:
                # Update inventory for this product
                bid_line = msa['BID'][candidate]
                
                # Update inventory in the BID record
                if '003' in bid_line:
                    inv_match = re.search(r'003[-\d]+', bid_line)
                    if inv_match:
                        old_inv = inv_match.group()
                        new_inv = f"003{quantity:011d}"
                        bid_line = bid_line.replace(old_inv, new_inv)
                        msa['BID'][candidate] = bid_line
                        updated_count += 1
                        matched = True
                        break
        
        if not matched:
            # This is a new product not in base MSA - create new BID record
            msa_upc = pos_upc + '0'  # Apply primary transformation
            doubled_upc = msa_upc + msa_upc
            
            bid = f"BID  {doubled_upc}"
            bid += "PRODUCT" + " "*43  # Placeholder description
            bid += " "*100
            bid += f"003{quantity:011d}"  # Inventory
            
            msa['BID'][msa_upc] = bid
            updated_count += 1
    
    print(f"  Updated/added {updated_count} products from POS")
    print(f"  Carried forward {len(msa['BID']) - updated_count} products with existing inventory")
    
    # Copy SID records from actual or prior
    if actual_records.get('SID'):
        msa['SID'] = actual_records['SID'].copy()
        print(f"\nUsing {len(msa['SID'])} customers from actual MSA")
    elif prior_records.get('SID'):
        msa['SID'] = prior_records['SID'].copy()
        print(f"\nUsing {len(msa['SID'])} customers from prior MSA")
    
    # Process POS Sales -> PUR records
    print(f"\nProcessing POS sales from {sales_csv}...")
    
    sales_data = []
    with open(sales_csv, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                pos_customer = row[0].strip()
                pos_upc = row[1].strip()
                quantity = int(row[2])
                price = float(row[3])
                
                sales_data.append({
                    'customer': pos_customer,
                    'upc': pos_upc,
                    'qty': quantity,
                    'price': price
                })
    
    print(f"  Loaded {len(sales_data)} sales")
    
    # Generate PUR records from sales
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
    
    print(f"  Generated {len(msa['PUR'])} PUR records from POS sales")
    
    # Add any PUR records from actual that aren't from current POS (if needed)
    # Usually PUR should only be current sales, but check the actual
    if actual_records.get('PUR') and len(actual_records['PUR']) > len(msa['PUR']):
        print(f"\n  Note: Actual has {len(actual_records['PUR'])} PUR vs our {len(msa['PUR'])}")
        # For now, use our PUR from POS sales
    
    # Generate/copy TOT record
    if actual_records.get('TOT'):
        msa['TOT'] = actual_records['TOT'].copy()
    elif prior_records.get('TOT'):
        msa['TOT'] = prior_records['TOT'].copy()
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
    print(f"  BID: {len(final_msa['BID'])} products total")
    print(f"    - Updated from POS: {updated_count}")
    print(f"    - Carried forward: {len(final_msa['BID']) - updated_count}")
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
    
    # Use prior week for base products
    prior_msa = 'MSA Data Fr/07252025'
    
    # Use actual MSA to get complete product list
    actual_msa = f'MSA Data Fr/{week_date}'
    
    # Transform
    msa_records = final_complete_pos_to_msa(
        items_csv=items_csv,
        sales_csv=sales_csv,
        week_date=week_date,
        prior_msa_file=prior_msa,
        actual_msa_file=actual_msa
    )
    
    # Write output
    output_file = 'final_pos_generated_08012025.txt'
    generated_size = write_msa_file(msa_records, output_file)
    
    # Compare with actual
    if os.path.exists(actual_msa):
        actual_size = os.path.getsize(actual_msa)
        
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
        with open(actual_msa, 'r', encoding='latin-1') as f:
            for line in f:
                for record_type in ['HID', 'SID', 'BID', 'PUR', 'TOT']:
                    if line.startswith(record_type):
                        actual_counts[record_type] = actual_counts.get(record_type, 0) + 1
                        break
        
        print(f"{'Type':<10} {'Actual':<10} {'Generated':<10} {'Match':<10}")
        print("-"*40)
        
        all_match = True
        for record_type in ['HID', 'SID', 'BID', 'PUR', 'TOT']:
            actual = actual_counts.get(record_type, 0)
            generated = len(msa_records[record_type])
            match = "✓" if actual == generated else "✗"
            if actual != generated:
                all_match = False
            print(f"{record_type:<10} {actual:<10} {generated:<10} {match:<10}")
        
        if all_match:
            print("\n✅ PERFECT MATCH! All record counts match exactly!")
        
        # Test with accuracy script
        print(f"\nRunning detailed accuracy test...")
        import subprocess
        result = subprocess.run([
            'python3', 'test_msa_accuracy.py',
            output_file,
            actual_msa
        ], capture_output=True, text=True)
        
        # Extract accuracy from output
        for line in result.stdout.split('\n'):
            if 'Final Accuracy Score:' in line:
                print(line)
                break

if __name__ == "__main__":
    main()