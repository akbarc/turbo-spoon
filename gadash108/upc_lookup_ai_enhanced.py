import os
import csv
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

print('╔════════════════════════════════════════════════════════════════╗')
print('║   UPC LOOKUP + AI MERGE + VERIFICATION (PARALLEL)             ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

API_KEY = 'abb286e1762c2760f56d08bdb9c96b2d7128e61f10113cbc7693d37e473eb6f0'
API_URL = 'https://go-upc.com/api/v1/code/'

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

# Load existing catalog
print('Step 1: Loading master catalog...')
with open('master_product_catalog_ENHANCED.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    master_items = list(reader)

print(f'✅ Loaded {len(master_items):,} items')

# Collect all unique barcodes
print('\nStep 2: Collecting all unique barcodes...')
all_barcodes = set()
barcode_to_items = {}  # Map barcode to item(s)

for item in master_items:
    primary_barcode = item['ItemLookupCode']
    alt_barcodes_str = item.get('AlternateBarcodes', '')

    all_barcodes.add(primary_barcode)
    if primary_barcode not in barcode_to_items:
        barcode_to_items[primary_barcode] = []
    barcode_to_items[primary_barcode].append(item)

    if alt_barcodes_str:
        alt_barcodes = alt_barcodes_str.split(' | ')
        all_barcodes.update(alt_barcodes)

print(f'✅ Found {len(all_barcodes):,} unique barcodes')

# UPC Lookup function
def lookup_upc(barcode):
    """Look up UPC data from go-upc.com API"""
    try:
        headers = {'Authorization': f'Bearer {API_KEY}'}
        response = requests.get(f'{API_URL}{barcode}', headers=headers, timeout=10)

        if response.status_code == 200:
            return (barcode, response.json(), None)
        elif response.status_code == 404:
            return (barcode, None, 'Not found')
        else:
            return (barcode, None, f'HTTP {response.status_code}')
    except Exception as e:
        return (barcode, None, str(e))

# Step 3: Parallel UPC lookups
print(f'\nStep 3: Looking up {len(all_barcodes):,} barcodes from UPC database...')
print('(This will take ~10-15 minutes with 50 parallel workers)')
print()

upc_data = {}
not_found = []
errors = []

MAX_UPC_WORKERS = 50
processed = 0
start_time = time.time()

with ThreadPoolExecutor(max_workers=MAX_UPC_WORKERS) as executor:
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

        if processed % 100 == 0 or processed == len(all_barcodes):
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (len(all_barcodes) - processed) / rate if rate > 0 else 0
            print(f'  [{processed:>5}/{len(all_barcodes)}] {processed/len(all_barcodes)*100:>5.1f}% | {rate:>4.1f} /s | ETA: {remaining/60:>4.1f}m | Found: {len(upc_data)}')

print(f'\n✅ UPC lookup complete in {time.time() - start_time:.1f}s')
print(f'   Found: {len(upc_data):,} | Not found: {len(not_found):,} | Errors: {len(errors)}')

# Step 4: AI-powered data merging and verification
print(f'\nStep 4: AI-powered data merging and verification...')
print(f'Processing {len(master_items):,} items with 40 parallel AI workers')
print()

def ai_merge_and_verify(item_data):
    """Use AI to intelligently merge our data with UPC data and verify"""
    idx, item = item_data

    primary_barcode = item['ItemLookupCode']
    our_data = {
        'description': item['Description'],
        'brand': item.get('Brand', ''),
        'category': item.get('MainCategory', ''),
        'subcategory': item.get('Subcategory', ''),
        'size': item.get('Size', ''),
        'price': item.get('Price', '')
    }

    # Get UPC data if available
    upc_info = {}
    if primary_barcode in upc_data:
        upc = upc_data[primary_barcode]
        product = upc.get('product', {})
        upc_info = {
            'name': product.get('name', ''),
            'brand': product.get('brand', ''),
            'category': product.get('category', ''),
            'description': product.get('description', ''),
            'size': product.get('size', ''),
            'manufacturer': product.get('manufacturer', ''),
            'model': product.get('model', ''),
            'image_url': product.get('image_url', '')
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are a product data specialist. Merge and verify product data from two sources.

Return JSON with these fields:
{
  "verified_brand": "Best brand name (prefer UPC if available, otherwise our data)",
  "verified_name": "Best product name (combine our description + UPC name)",
  "verified_size": "Best size (prefer UPC if specific, otherwise our data)",
  "verified_category": "Best category match",
  "data_quality": "EXCELLENT/GOOD/FAIR/POOR",
  "issues": "List any data conflicts or problems",
  "recommendations": "Suggestions for data improvement"
}

Rules:
- Prefer UPC data when more detailed/accurate
- Keep our brand if UPC brand is missing
- Combine descriptions for best clarity
- Flag any major conflicts
- Rate data quality based on completeness and consistency
"""},
                {"role": "user", "content": f"""Our data: {json.dumps(our_data)}
UPC data: {json.dumps(upc_info)}

Merge and verify this product data."""}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            timeout=10
        )

        result = json.loads(response.choices[0].message.content)
        return (idx, result, None)

    except Exception as e:
        return (idx, None, str(e))

# Process with AI
ai_results = {}
ai_errors = 0
MAX_AI_WORKERS = 40

start_time = time.time()
processed = 0

with ThreadPoolExecutor(max_workers=MAX_AI_WORKERS) as executor:
    futures = {executor.submit(ai_merge_and_verify, (idx, item)): idx for idx, item in enumerate(master_items)}

    for future in as_completed(futures):
        idx, result, error = future.result()
        processed += 1

        if result:
            ai_results[idx] = result
        else:
            ai_errors += 1

        if processed % 100 == 0 or processed == len(master_items):
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (len(master_items) - processed) / rate if rate > 0 else 0
            print(f'  [{processed:>5}/{len(master_items)}] {processed/len(master_items)*100:>5.1f}% | {rate:>4.1f} /s | ETA: {remaining/60:>4.1f}m | Errors: {ai_errors}')

print(f'\n✅ AI processing complete in {time.time() - start_time:.1f}s')

# Step 5: Create consolidated master file
print('\nStep 5: Creating consolidated master file with all data...')

consolidated_data = []
master_items_data = []
sub_items_data = []
simple_items_data = []

for idx, item in enumerate(master_items):
    primary_barcode = item['ItemLookupCode']
    alt_count = int(item.get('AlternateBarcodeCount', 0))

    # Get UPC data
    upc_product = {}
    if primary_barcode in upc_data:
        upc_product = upc_data[primary_barcode].get('product', {})

    # Get AI verification
    ai_verify = ai_results.get(idx, {})

    # Build consolidated row with ALL data
    row = {
        **item,  # All original data

        # AI Verified/Merged data
        'AI_VerifiedBrand': ai_verify.get('verified_brand', ''),
        'AI_VerifiedName': ai_verify.get('verified_name', ''),
        'AI_VerifiedSize': ai_verify.get('verified_size', ''),
        'AI_VerifiedCategory': ai_verify.get('verified_category', ''),
        'AI_DataQuality': ai_verify.get('data_quality', ''),
        'AI_Issues': ai_verify.get('issues', ''),
        'AI_Recommendations': ai_verify.get('recommendations', ''),

        # UPC Database data
        'UPC_ProductName': upc_product.get('name', ''),
        'UPC_Brand': upc_product.get('brand', ''),
        'UPC_Category': upc_product.get('category', ''),
        'UPC_Description': upc_product.get('description', ''),
        'UPC_Manufacturer': upc_product.get('manufacturer', ''),
        'UPC_Model': upc_product.get('model', ''),
        'UPC_Size': upc_product.get('size', ''),
        'UPC_Weight': upc_product.get('weight', ''),
        'UPC_ImageURL': upc_product.get('image_url', ''),
        'UPC_DataAvailable': 'Yes' if primary_barcode in upc_data else 'No',
    }

    consolidated_data.append(row)

    # Separate into master/sub/simple
    if alt_count > 0:
        # Master item
        master_row = {**row, 'ItemType': 'MASTER'}
        master_items_data.append(master_row)

        # Create sub-items for alternates
        alt_barcodes = item.get('AlternateBarcodes', '').split(' | ')
        for alt_barcode in alt_barcodes:
            upc_alt = {}
            if alt_barcode in upc_data:
                upc_alt = upc_data[alt_barcode].get('product', {})

            sub_row = {
                'MasterItemID': item['ItemID'],
                'MasterDescription': item['Description'],
                'Barcode': alt_barcode,
                'ItemType': 'SUB',
                'OnHand_Master': item['OnHand'],
                'InventoryNote': 'Shares inventory with master',
                'UPC_ProductName': upc_alt.get('name', ''),
                'UPC_Brand': upc_alt.get('brand', ''),
                'UPC_ImageURL': upc_alt.get('image_url', ''),
            }
            sub_items_data.append(sub_row)
    else:
        # Simple item
        simple_items_data.append({**row, 'ItemType': 'SIMPLE'})

# Step 6: Save all files
print('\nStep 6: Saving all files...')

# 1. CONSOLIDATED MASTER FILE (everything)
consolidated_file = 'MASTER_CONSOLIDATED_ALL_DATA.csv'
with open(consolidated_file, 'w', newline='', encoding='utf-8') as f:
    if consolidated_data:
        writer = csv.DictWriter(f, fieldnames=consolidated_data[0].keys())
        writer.writeheader()
        writer.writerows(consolidated_data)
print(f'✅ {consolidated_file} - ALL DATA ({len(consolidated_data):,} items, {len(consolidated_data[0].keys())} columns)')

# 2. Master items (with alternates)
master_file = 'master_items_with_upc_ai.csv'
if master_items_data:
    with open(master_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=master_items_data[0].keys())
        writer.writeheader()
        writer.writerows(master_items_data)
    print(f'✅ {master_file} ({len(master_items_data):,} items)')

# 3. Sub items (alternates)
sub_file = 'sub_items_alternate_barcodes_upc.csv'
if sub_items_data:
    with open(sub_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sub_items_data[0].keys())
        writer.writeheader()
        writer.writerows(sub_items_data)
    print(f'✅ {sub_file} ({len(sub_items_data):,} sub-items)')

# 4. Simple items
simple_file = 'simple_items_no_alternates_upc_ai.csv'
if simple_items_data:
    with open(simple_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=simple_items_data[0].keys())
        writer.writeheader()
        writer.writerows(simple_items_data)
    print(f'✅ {simple_file} ({len(simple_items_data):,} items)')

# 5. Complete UPC database
upc_file = 'upc_lookup_complete.json'
with open(upc_file, 'w', encoding='utf-8') as f:
    json.dump({
        'total_barcodes': len(all_barcodes),
        'found': len(upc_data),
        'not_found': not_found,
        'errors': errors,
        'data': upc_data
    }, f, indent=2)
print(f'✅ {upc_file} (complete UPC JSON)')

# Data quality report
print('\n' + '═' * 70)
print('DATA QUALITY REPORT')
print('═' * 70)

quality_counts = {}
for result in ai_results.values():
    quality = result.get('data_quality', 'UNKNOWN')
    quality_counts[quality] = quality_counts.get(quality, 0) + 1

for quality, count in sorted(quality_counts.items(), key=lambda x: x[1], reverse=True):
    pct = count / len(master_items) * 100
    print(f'{quality:<15} {count:>5,} items ({pct:>5.1f}%)')

print()
print('═' * 70)
print('FINAL SUMMARY')
print('═' * 70)
print(f'Total items processed:         {len(master_items):>10,}')
print(f'UPC data found:                {len(upc_data):>10,} ({len(upc_data)/len(all_barcodes)*100:.1f}%)')
print(f'AI verifications complete:     {len(ai_results):>10,}')
print()
print(f'Master items (with alternates):{len(master_items_data):>10,}')
print(f'Sub items (alt barcodes):      {len(sub_items_data):>10,}')
print(f'Simple items (no alternates):  {len(simple_items_data):>10,}')
print()
print('FILES CREATED:')
print(f'  🌟 {consolidated_file} - MASTER FILE (all data)')
print(f'  📦 {master_file} - Master items')
print(f'  🔗 {sub_file} - Alternate barcodes')
print(f'  📄 {simple_file} - Simple items')
print(f'  💾 {upc_file} - UPC database (JSON)')
print()
print('✅ COMPLETE! All data merged, verified, and consolidated.')
