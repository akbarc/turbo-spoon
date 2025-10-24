import os
import csv
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

print('╔════════════════════════════════════════════════════════════════╗')
print('║        UPC LOOKUP & MASTER/SUB BARCODE STRUCTURE              ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

API_KEY = 'abb286e1762c2760f56d08bdb9c96b2d7128e61f10113cbc7693d37e473eb6f0'
API_URL = 'https://go-upc.com/api/v1/code/'

# Load existing catalog
print('Step 1: Loading master catalog...')
with open('master_product_catalog_ENHANCED.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    master_items = list(reader)

print(f'✅ Loaded {len(master_items):,} items')

# Collect all unique barcodes
print('\nStep 2: Collecting all unique barcodes...')
all_barcodes = set()
items_with_alternates = []
items_without_alternates = []

for item in master_items:
    primary_barcode = item['ItemLookupCode']
    alt_barcodes_str = item.get('AlternateBarcodes', '')
    alt_count = int(item.get('AlternateBarcodeCount', 0))

    # Add primary barcode
    all_barcodes.add(primary_barcode)

    if alt_count > 0:
        # Item has alternates - will become a master item
        alt_barcodes = alt_barcodes_str.split(' | ')
        all_barcodes.update(alt_barcodes)
        items_with_alternates.append({
            'item': item,
            'primary_barcode': primary_barcode,
            'alternate_barcodes': alt_barcodes
        })
    else:
        # Simple item, no alternates
        items_without_alternates.append(item)

print(f'✅ Found {len(all_barcodes):,} unique barcodes')
print(f'   Items with alternates: {len(items_with_alternates):,}')
print(f'   Items without alternates: {len(items_without_alternates):,}')

# UPC Lookup function
def lookup_upc(barcode):
    """Look up UPC data from go-upc.com API"""
    try:
        headers = {'Authorization': f'Bearer {API_KEY}'}
        response = requests.get(f'{API_URL}{barcode}', headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return (barcode, data, None)
        elif response.status_code == 404:
            return (barcode, None, 'Not found')
        else:
            return (barcode, None, f'HTTP {response.status_code}')
    except Exception as e:
        return (barcode, None, str(e))

# Step 3: Parallel UPC lookups
print(f'\nStep 3: Looking up {len(all_barcodes):,} barcodes from UPC database...')
print('(This will take ~10-15 minutes with parallel processing)')
print()

upc_data = {}
errors = []
not_found = []

MAX_WORKERS = 20  # Parallel API calls
processed = 0
start_time = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(lookup_upc, barcode): barcode for barcode in all_barcodes}

    for future in as_completed(futures):
        barcode, data, error = future.result()
        processed += 1

        if data:
            upc_data[barcode] = data
        elif error == 'Not found':
            not_found.append(barcode)
        else:
            errors.append({'barcode': barcode, 'error': error})

        # Progress update
        if processed % 100 == 0 or processed == len(all_barcodes):
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (len(all_barcodes) - processed) / rate if rate > 0 else 0
            print(f'  [{processed:>5}/{len(all_barcodes)}] {processed/len(all_barcodes)*100:>5.1f}% | {rate:>4.1f} /s | ETA: {remaining/60:>4.1f}m | Found: {len(upc_data)} | Not Found: {len(not_found)} | Errors: {len(errors)}')

elapsed = time.time() - start_time
print(f'\n✅ UPC lookup complete in {elapsed/60:.1f} minutes')
print(f'   Found: {len(upc_data):,}')
print(f'   Not found: {len(not_found):,}')
print(f'   Errors: {len(errors):,}')

# Step 4: Create Master/Sub structure
print('\nStep 4: Creating master/sub barcode structure...')

# Create MASTER table (items with alternate barcodes)
master_table = []
for entry in items_with_alternates:
    item = entry['item']
    primary = entry['primary_barcode']

    master_row = {
        # Original data
        **item,

        # Master/Sub structure
        'ItemType': 'MASTER',
        'MasterItemID': item['ItemID'],
        'PrimaryBarcode': primary,
        'AlternateCount': item['AlternateBarcodeCount'],

        # UPC data for primary barcode
        'UPC_Data_Available': 'Yes' if primary in upc_data else 'No',
    }

    # Add UPC data if available
    if primary in upc_data:
        upc = upc_data[primary]
        master_row['UPC_ProductName'] = upc.get('product', {}).get('name', '')
        master_row['UPC_Brand'] = upc.get('product', {}).get('brand', '')
        master_row['UPC_Category'] = upc.get('product', {}).get('category', '')
        master_row['UPC_Description'] = upc.get('product', {}).get('description', '')
    else:
        master_row['UPC_ProductName'] = ''
        master_row['UPC_Brand'] = ''
        master_row['UPC_Category'] = ''
        master_row['UPC_Description'] = ''

    master_table.append(master_row)

# Create SUB table (each alternate barcode)
sub_table = []
for entry in items_with_alternates:
    item = entry['item']
    master_id = item['ItemID']

    for alt_barcode in entry['alternate_barcodes']:
        sub_row = {
            # Link to master
            'MasterItemID': master_id,
            'MasterDescription': item['Description'],
            'Barcode': alt_barcode,
            'ItemType': 'SUB',

            # Inventory NOTE: Points to master, not split
            'InventoryNote': 'Shares inventory with master item',
            'OnHand_Master': item['OnHand'],

            # UPC data for this alternate barcode
            'UPC_Data_Available': 'Yes' if alt_barcode in upc_data else 'No',
        }

        # Add UPC data if available
        if alt_barcode in upc_data:
            upc = upc_data[alt_barcode]
            sub_row['UPC_ProductName'] = upc.get('product', {}).get('name', '')
            sub_row['UPC_Brand'] = upc.get('product', {}).get('brand', '')
            sub_row['UPC_Category'] = upc.get('product', {}).get('category', '')
            sub_row['UPC_Description'] = upc.get('product', {}).get('description', '')
            sub_row['UPC_Manufacturer'] = upc.get('product', {}).get('manufacturer', '')
            sub_row['UPC_Model'] = upc.get('product', {}).get('model', '')
            sub_row['UPC_Size'] = upc.get('product', {}).get('size', '')
            sub_row['UPC_Weight'] = upc.get('product', {}).get('weight', '')
            sub_row['UPC_ImageURL'] = upc.get('product', {}).get('image_url', '')
        else:
            sub_row['UPC_ProductName'] = ''
            sub_row['UPC_Brand'] = ''
            sub_row['UPC_Category'] = ''
            sub_row['UPC_Description'] = ''
            sub_row['UPC_Manufacturer'] = ''
            sub_row['UPC_Model'] = ''
            sub_row['UPC_Size'] = ''
            sub_row['UPC_Weight'] = ''
            sub_row['UPC_ImageURL'] = ''

        sub_table.append(sub_row)

print(f'✅ Created master/sub structure')
print(f'   Master items: {len(master_table):,}')
print(f'   Sub items: {len(sub_table):,}')

# Step 5: Save all data
print('\nStep 5: Saving data to files...')

# Save master items (with alternates) - ENHANCED with UPC data
master_file = 'master_items_with_upc.csv'
if master_table:
    with open(master_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=master_table[0].keys())
        writer.writeheader()
        writer.writerows(master_table)
    print(f'✅ Saved {master_file} ({len(master_table)} items)')

# Save sub items (alternate barcodes) - ENHANCED with UPC data
sub_file = 'sub_items_alternate_barcodes.csv'
if sub_table:
    with open(sub_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sub_table[0].keys())
        writer.writeheader()
        writer.writerows(sub_table)
    print(f'✅ Saved {sub_file} ({len(sub_table)} sub-items)')

# Save complete UPC database dump (JSON)
upc_file = 'upc_lookup_complete.json'
with open(upc_file, 'w', encoding='utf-8') as f:
    json.dump({
        'total_barcodes': len(all_barcodes),
        'found': len(upc_data),
        'not_found': not_found,
        'errors': errors,
        'data': upc_data
    }, f, indent=2)
print(f'✅ Saved {upc_file} (complete UPC data)')

# Save simple items (no alternates) - for reference
simple_file = 'simple_items_no_alternates.csv'
if items_without_alternates:
    # Add UPC data for simple items too
    for item in items_without_alternates:
        barcode = item['ItemLookupCode']
        if barcode in upc_data:
            upc = upc_data[barcode]
            item['UPC_ProductName'] = upc.get('product', {}).get('name', '')
            item['UPC_Brand'] = upc.get('product', {}).get('brand', '')
            item['UPC_Category'] = upc.get('product', {}).get('category', '')
        else:
            item['UPC_ProductName'] = ''
            item['UPC_Brand'] = ''
            item['UPC_Category'] = ''

    with open(simple_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=items_without_alternates[0].keys())
        writer.writeheader()
        writer.writerows(items_without_alternates)
    print(f'✅ Saved {simple_file} ({len(items_without_alternates)} items)')

print()
print('═' * 70)
print('FINAL SUMMARY')
print('═' * 70)
print(f'Total barcodes looked up:     {len(all_barcodes):>10,}')
print(f'UPC data found:                {len(upc_data):>10,} ({len(upc_data)/len(all_barcodes)*100:.1f}%)')
print(f'Not found in UPC DB:           {len(not_found):>10,}')
print(f'Errors:                        {len(errors):>10}')
print()
print(f'Master items (with alternates):{len(master_table):>10,}')
print(f'Sub items (alt barcodes):      {len(sub_table):>10,}')
print(f'Simple items (no alternates):  {len(items_without_alternates):>10,}')
print()
print('FILES CREATED:')
print(f'  • {master_file} - Master items with UPC data')
print(f'  • {sub_file} - Alternate barcodes with UPC data')
print(f'  • {simple_file} - Simple items (no alternates)')
print(f'  • {upc_file} - Complete UPC database (JSON)')
print()
print('✅ COMPLETE! All UPC data fetched and structured.')
print()
print('IMPORTANT NOTES:')
print('  • Inventory on SUB items points to MASTER (not split)')
print('  • All original data preserved in master items')
print('  • UPC data available for enrichment')
