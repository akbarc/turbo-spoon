#!/usr/bin/env python3
"""
Analyze MULTICAT transformation process
Compare input CSVs with MSA output to understand exact rules
"""

import csv
import re
from collections import defaultdict, Counter

def load_items_csv(filepath):
    """Load items/inventory CSV"""
    items = {}
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                upc = row[0].strip()
                qty = int(row[1])
                items[upc] = qty
    return items

def load_sales_csv(filepath):
    """Load sales CSV"""
    sales = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                sales.append({
                    'customer_id': row[0].strip(),
                    'upc': row[1].strip(),
                    'quantity': int(row[2]),
                    'price': float(row[3])
                })
    return sales

def parse_msa_file(filepath):
    """Parse MSA output file"""
    records = {
        'HID': [],
        'BID': [],
        'SID': [],
        'PUR': [],
        'TOT': []
    }
    
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            line = line.rstrip('\n')
            if len(line) < 3:
                continue
            
            record_type = line[:3]
            
            if record_type == 'BID':
                # Extract UPC from BID record
                # Looking at the pattern, UPC starts after spaces
                parts = line[3:].lstrip()
                if parts:
                    # UPC appears to be duplicated
                    upc_end = parts.find(' ')
                    if upc_end > 0:
                        upc = parts[:upc_end]
                    else:
                        # Try to extract first continuous digit sequence
                        match = re.match(r'(\d+)', parts)
                        upc = match.group(1) if match else parts[:20]
                    
                    # Get inventory from end (003XXXXXXXXXX pattern)
                    inv_match = re.search(r'003(\d+)$', line)
                    inventory = 0
                    if inv_match:
                        inv_str = inv_match.group(1)
                        # Handle negative
                        if '-' in inv_str:
                            inventory = -int(inv_str.replace('-', '').lstrip('0') or '0')
                        else:
                            inventory = int(inv_str.lstrip('0') or '0')
                    
                    records['BID'].append({
                        'upc': upc,
                        'inventory': inventory,
                        'raw': line
                    })
            
            elif record_type == 'SID':
                # Extract customer ID
                customer_id = line[3:30].strip()
                records['SID'].append({
                    'customer_id': customer_id,
                    'raw': line
                })
            
            elif record_type == 'PUR':
                # Extract customer, UPC, quantity, price
                customer_id = line[3:30].strip()
                upc = line[30:60].strip() if len(line) > 30 else ""
                
                # Parse quantity and price from end
                qty = 0
                price = 0.0
                if len(line) > 90:
                    data = line[90:]
                    # Look for 001 (quantity)
                    if '001' in data:
                        idx = data.index('001')
                        qty_str = data[idx+3:idx+14]
                        try:
                            qty = int(float(qty_str))
                        except:
                            pass
                    # Look for 002 (price)
                    if '002' in data:
                        idx = data.index('002')
                        price_str = data[idx+3:idx+14]
                        try:
                            price = float(price_str)
                        except:
                            pass
                
                records['PUR'].append({
                    'customer_id': customer_id,
                    'upc': upc,
                    'quantity': qty,
                    'price': price,
                    'raw': line
                })
            
            else:
                records[record_type].append({'raw': line})
    
    return records

def compare_data():
    """Compare input CSVs with MSA output"""
    
    print("="*70)
    print("MULTICAT TRANSFORMATION ANALYSIS")
    print("="*70)
    
    # Load input data
    items = load_items_csv('Items- 06202025.csv')
    sales = load_sales_csv('Sales - 06202025.csv')
    
    print(f"\nINPUT DATA:")
    print(f"  Items CSV: {len(items)} products")
    print(f"  Sales CSV: {len(sales)} transactions")
    
    # Parse MSA output
    msa = parse_msa_file('MSA Data Fr/06202025')
    
    print(f"\nMSA OUTPUT:")
    print(f"  BID records: {len(msa['BID'])}")
    print(f"  SID records: {len(msa['SID'])}")
    print(f"  PUR records: {len(msa['PUR'])}")
    
    # Compare products
    print("\n" + "="*70)
    print("PRODUCT/INVENTORY COMPARISON")
    print("="*70)
    
    # Get UPCs from each source
    csv_upcs = set(items.keys())
    msa_upcs = set(bid['upc'] for bid in msa['BID'])
    
    print(f"\nUPCs in Items CSV: {len(csv_upcs)}")
    print(f"UPCs in MSA BID: {len(msa_upcs)}")
    
    # Find differences
    only_in_csv = csv_upcs - msa_upcs
    only_in_msa = msa_upcs - csv_upcs
    
    print(f"\nOnly in CSV (not in MSA): {len(only_in_csv)}")
    if only_in_csv:
        for upc in list(only_in_csv)[:5]:
            print(f"  {upc}: qty={items[upc]}")
    
    print(f"\nOnly in MSA (not in CSV): {len(only_in_msa)}")
    if only_in_msa:
        for upc in list(only_in_msa)[:5]:
            bid = next((b for b in msa['BID'] if b['upc'] == upc), None)
            print(f"  {upc}: inv={bid['inventory'] if bid else 'N/A'}")
    
    # Check inventory matches
    print("\n" + "="*70)
    print("INVENTORY QUANTITY COMPARISON")
    print("="*70)
    
    matches = 0
    mismatches = []
    
    for bid in msa['BID']:
        upc = bid['upc']
        if upc in items:
            csv_qty = items[upc]
            msa_qty = bid['inventory']
            if csv_qty == msa_qty:
                matches += 1
            else:
                mismatches.append((upc, csv_qty, msa_qty))
    
    print(f"\nInventory matches: {matches}")
    print(f"Inventory mismatches: {len(mismatches)}")
    
    if mismatches:
        print("\nSample mismatches (UPC, CSV qty, MSA qty):")
        for upc, csv_qty, msa_qty in mismatches[:10]:
            print(f"  {upc}: CSV={csv_qty}, MSA={msa_qty}, Diff={msa_qty-csv_qty}")
    
    # Compare sales
    print("\n" + "="*70)
    print("SALES COMPARISON")
    print("="*70)
    
    # Group sales by customer and UPC
    csv_sales_map = defaultdict(list)
    for sale in sales:
        key = (sale['customer_id'], sale['upc'])
        csv_sales_map[key].append(sale)
    
    msa_sales_map = defaultdict(list)
    for pur in msa['PUR']:
        key = (pur['customer_id'], pur['upc'])
        msa_sales_map[key].append(pur)
    
    print(f"\nUnique sales combinations:")
    print(f"  CSV: {len(csv_sales_map)} customer-product pairs")
    print(f"  MSA: {len(msa_sales_map)} customer-product pairs")
    
    # Check customer IDs
    csv_customers = set(s['customer_id'] for s in sales)
    msa_customers = set(p['customer_id'] for p in msa['PUR'])
    msa_sid_customers = set(s['customer_id'] for s in msa['SID'])
    
    print(f"\nCustomers:")
    print(f"  In Sales CSV: {len(csv_customers)}")
    print(f"  In MSA PUR: {len(msa_customers)}")
    print(f"  In MSA SID: {len(msa_sid_customers)}")
    
    # Check for customer ID transformations
    print("\nCustomer ID format analysis:")
    
    # Sample some customer IDs to see transformation
    for csv_cust in list(csv_customers)[:5]:
        # Look for this customer in MSA
        found_in_pur = False
        for msa_cust in msa_customers:
            if csv_cust in msa_cust or msa_cust in csv_cust:
                print(f"  CSV: {csv_cust} → MSA: {msa_cust}")
                found_in_pur = True
                break
        if not found_in_pur:
            print(f"  CSV: {csv_cust} → NOT FOUND in MSA")
    
    # Check UPC transformations
    print("\n" + "="*70)
    print("UPC TRANSFORMATION PATTERNS")
    print("="*70)
    
    # Look for patterns in how UPCs are transformed
    csv_sales_upcs = set(s['upc'] for s in sales)
    msa_pur_upcs = set(p['upc'] for p in msa['PUR'])
    
    print(f"\nUPCs in sales:")
    print(f"  CSV: {len(csv_sales_upcs)} unique")
    print(f"  MSA: {len(msa_pur_upcs)} unique")
    
    # Check if leading zeros are added
    for csv_upc in list(csv_sales_upcs)[:10]:
        found = False
        for msa_upc in msa_pur_upcs:
            if csv_upc in msa_upc or msa_upc.lstrip('0') == csv_upc:
                if csv_upc != msa_upc:
                    print(f"  {csv_upc} → {msa_upc} (padded with {len(msa_upc)-len(csv_upc)} zeros)")
                found = True
                break
        if not found:
            print(f"  {csv_upc} → NOT FOUND")

if __name__ == "__main__":
    compare_data()