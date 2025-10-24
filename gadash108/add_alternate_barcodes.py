import os
os.environ['TDSVER'] = '7.0'
import pymssql
import csv

print('╔════════════════════════════════════════════════════════════════╗')
print('║       ADDING ALTERNATE BARCODES TO MASTER CATALOG             ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 60,
    'login_timeout': 15
}

print('Step 1: Getting all alternate barcodes from Alias table...')

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

# Get all aliases for all items
cursor.execute('''
SELECT
    ItemID,
    COUNT(*) as AliasCount
FROM Alias
GROUP BY ItemID
''')

alias_counts = cursor.fetchall()
print(f'✅ Found {len(alias_counts):,} items with alternate barcodes')

# Now get the actual aliases
print('\\nStep 2: Fetching all alias barcodes...')

alias_lookup = {}
for i, row in enumerate(alias_counts):
    if (i + 1) % 100 == 0:
        print(f'  Progress: {i+1}/{len(alias_counts)}')

    item_id = row['ItemID']

    cursor.execute('''
    SELECT Alias
    FROM Alias
    WHERE ItemID = %s
    ORDER BY Alias
    ''', (item_id,))

    aliases = cursor.fetchall()
    alias_list = [a['Alias'] for a in aliases]

    alias_lookup[item_id] = {
        'barcodes': ' | '.join(alias_list),
        'count': len(alias_list)
    }

print(f'✅ Collected alternate barcodes for {len(alias_lookup):,} items')

cursor.close()
conn.close()

# Update the CSV
print('\\nStep 3: Updating master_product_catalog_ENHANCED.csv...')

with open('master_product_catalog_ENHANCED.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    items = list(reader)
    fieldnames = list(reader.fieldnames)

# Add new columns
if 'AlternateBarcodes' not in fieldnames:
    fieldnames.append('AlternateBarcodes')
if 'AlternateBarcodeCount' not in fieldnames:
    fieldnames.append('AlternateBarcodeCount')

# Add alias data
items_with_aliases = 0
total_aliases = 0

for item in items:
    item_id = int(item['ItemID'])
    if item_id in alias_lookup:
        item['AlternateBarcodes'] = alias_lookup[item_id]['barcodes']
        item['AlternateBarcodeCount'] = alias_lookup[item_id]['count']
        items_with_aliases += 1
        total_aliases += alias_lookup[item_id]['count']
    else:
        item['AlternateBarcodes'] = ''
        item['AlternateBarcodeCount'] = 0

# Write back
with open('master_product_catalog_ENHANCED.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(items)

print(f'✅ Updated {items_with_aliases:,} items with alternate barcodes')
print(f'   Total alternate barcodes added: {total_aliases:,}')
print(f'   Average per item: {total_aliases/items_with_aliases:.1f}')
print(f'   Total columns now: {len(fieldnames)}')
print()

# Show top items by barcode count
print('TOP 20 ITEMS BY ALTERNATE BARCODE COUNT:')
print('─' * 80)

sorted_items = sorted(items, key=lambda x: int(x.get('AlternateBarcodeCount', 0)), reverse=True)
for item in sorted_items[:20]:
    count = item.get('AlternateBarcodeCount', 0)
    if int(count) > 0:
        desc = item['Description'][:50]
        print(f'{desc:<50} → {count:>3} alt barcodes')

print()
print('✅ COMPLETE! Alternate barcodes added to master catalog')
print(f'   File: master_product_catalog_ENHANCED.csv')
print(f'   Total columns: {len(fieldnames)} (was 45, now 47)')
