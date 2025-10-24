import os
os.environ['TDSVER'] = '7.0'
import pymssql
import time
from datetime import datetime, timedelta
import csv
import json
import sys
from openai import OpenAI
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

print('╔════════════════════════════════════════════════════════════════╗', flush=True)
print('║   MASTER CATEGORIZATION - PARALLEL AI-POWERED (15-MIN MODE)   ║', flush=True)
print('║          Complete Database - 12-Month Sales Filter            ║', flush=True)
print('╚════════════════════════════════════════════════════════════════╝', flush=True)
print(flush=True)
print('⚡ PARALLEL PROCESSING:', flush=True)
print('  • 30 concurrent API workers', flush=True)
print('  • Target: ~20x faster than sequential', flush=True)
print('  • Est. completion: 12-15 minutes', flush=True)
print(flush=True)

# Initialize OpenAI client
try:
    client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')
    print('✅ OpenAI client initialized', flush=True)
except Exception as e:
    print(f'❌ OpenAI initialization error: {e}', flush=True)
    sys.exit(1)

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 300,
    'login_timeout': 30
}

# Calculate date range for last 12 months
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

print(f'Analysis Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}', flush=True)
print(flush=True)

# Main categories
MAIN_CATEGORIES = [
    "Tobacco Products", "Tobacco Accessories", "Vaping & E-Cigarettes",
    "Food & Snacks", "Candy & Gum", "Health & Wellness",
    "Personal Care & Beauty", "Household & Cleaning", "General Merchandise",
    "Automotive", "Beverages", "Specialty Products"
]

# Brand standardization dictionary
brand_standardization = {
    'MARLBORO': ['MARLBORO', 'MARLBORO CIGARETTES', 'MARLBRO', 'MARBORO'],
    'NEWPORT': ['NEWPORT', 'NEWPORTS', 'NEWPORT CIGARETTES'],
    'LAY': ["LAY", "LAY'S", "LAYS", "LAYS CHIPS"],
    'DORITOS': ['DORITOS', 'DORITO'],
    'REDBULL': ['RED BULL', 'REDBULL'],
}

def standardize_brand(brand):
    """Standardize brand names to avoid variations"""
    if not brand or brand.upper() in ['UNKNOWN', 'ERROR', 'UNSPECIFIED', 'GENERIC']:
        return brand
    brand_upper = brand.upper().strip()
    for standard, variants in brand_standardization.items():
        if brand_upper in [v.upper() for v in variants]:
            return standard
    return brand

def standardize_size(size):
    """Standardize size formats"""
    if not size or size.upper() in ['UNKNOWN', 'UNSPECIFIED']:
        return size
    size = size.strip()
    replacements = {
        'OZ': 'oz', 'ML': 'ml', 'CT': 'count',
        'PK': 'pack', 'LB': 'lb', 'G': 'g', 'MG': 'mg',
    }
    for old, new in replacements.items():
        size = size.replace(f' {old}', new).replace(f'{old}', new)
    return size

# Step 1: Fetch items
print('Step 1: Fetching items with 12-month sales history...', flush=True)

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

query_items = f"""
SELECT DISTINCT
    i.ID as ItemID, i.ItemLookupCode, i.Description,
    i.Price, i.Cost, i.Quantity as OnHand,
    c.Name as CurrentCategory, d.Name as Department,
    s.SupplierName, i.LastReceived, i.LastSold
FROM Item i
LEFT JOIN Category c ON i.CategoryID = c.ID
LEFT JOIN Department d ON i.DepartmentID = d.ID
LEFT JOIN Supplier s ON i.SupplierID = s.ID
INNER JOIN (
    SELECT DISTINCT te.ItemID
    FROM [Transaction] t
    INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= '{start_date.strftime('%Y-%m-%d')}'
      AND t.Time < '{end_date.strftime('%Y-%m-%d')}'
      AND te.TransactionNumber > 0
) AS SoldItems ON i.ID = SoldItems.ItemID
WHERE i.Inactive = 0
ORDER BY c.Name, i.Description
"""

start_time = time.time()
cursor.execute(query_items)
items = cursor.fetchall()
elapsed = time.time() - start_time

print(f'✅ Found {len(items):,} items with sales in last 12 months', flush=True)
print(f'   Query time: {elapsed:.1f}s', flush=True)
print(flush=True)

# Step 2: Get sales data (batch query)
print('Step 2: Getting 12-month sales data (OPTIMIZED - Single batch query)...', flush=True)

query_sales_batch = f"""
SELECT
    te.ItemID,
    SUM(te.Quantity) as TotalQtySold,
    SUM(te.Price * te.Quantity) as TotalRevenue
FROM [Transaction] t
INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
WHERE t.Time >= '{start_date.strftime('%Y-%m-%d')}'
  AND t.Time < '{end_date.strftime('%Y-%m-%d')}'
  AND te.TransactionNumber > 0
  AND te.ItemID IN ({','.join(str(item['ItemID']) for item in items)})
GROUP BY te.ItemID
"""

start_time = time.time()
cursor.execute(query_sales_batch)
sales_data = cursor.fetchall()
elapsed = time.time() - start_time

sales_lookup = {row['ItemID']: row for row in sales_data}

for item in items:
    sales = sales_lookup.get(item['ItemID'], {'TotalQtySold': 0, 'TotalRevenue': 0})
    item['TotalQtySold_12mo'] = sales['TotalQtySold'] or 0
    item['TotalRevenue_12mo'] = sales['TotalRevenue'] or 0
    item['MonthlyAvgQty'] = round((sales['TotalQtySold'] or 0) / 12, 2)
    item['MonthlyAvgRevenue'] = round((sales['TotalRevenue'] or 0) / 12, 2)

cursor.close()
conn.close()

print(f'✅ Sales data collected for {len(sales_data):,} items in {elapsed:.1f}s', flush=True)
print(flush=True)

# Step 3: Parallel AI processing
print('Step 3: PARALLEL AI-powered categorization with 30 concurrent workers...', flush=True)
print(f'Processing {len(items)} items', flush=True)
print(flush=True)

# Thread-safe counters
processed_lock = threading.Lock()
processed_count = 0
error_count = 0

def analyze_item_with_ai(item_data):
    """Use OpenAI API to extract brand, categories, product type, and size."""
    idx, item = item_data
    description = item['Description']
    current_category = item['CurrentCategory'] or ''

    # Category hint
    category_hint = ""
    if current_category:
        cat_upper = current_category.upper()
        if 'CIGARETTE' in cat_upper or 'CIGAR' in cat_upper or 'TOBACCO' in cat_upper:
            category_hint = "This is likely a tobacco product."
        elif 'ECIG' in cat_upper or 'VAPE' in cat_upper or 'ELECTRONIC' in cat_upper:
            category_hint = "This is likely a vaping/e-cigarette product."
        elif 'FOOD' in cat_upper or 'CANDY' in cat_upper or 'SNACK' in cat_upper:
            category_hint = "This is likely a food or snack product."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""You are a product categorization expert for a convenience store chain.

Analyze the product description and extract the following in JSON format:
{{
  "brand": "Brand name (e.g., MARLBORO, BIC, DORITOS) - use EXACT brand name in UPPERCASE. If truly unknown/unbranded, use 'UNSPECIFIED'. If generic/store brand, use 'GENERIC'. Do not guess.",
  "main_category": "Choose ONE from: {', '.join(MAIN_CATEGORIES)}",
  "subcategory": "Specific subcategory (e.g., Premium Cigarettes, Disposable Vapes, Salty Snacks, Energy Drinks)",
  "product_type": "Exact product type with key details (e.g., 'Menthol Cigarette Box', 'Disposable Lighter', 'Tortilla Chips')",
  "size": "Package size with units (e.g., '20 count', '750ml', '2.5 oz') - extract from description. If not specified, use 'UNSPECIFIED'. Do not guess."
}}

CONSISTENCY RULES:
- Brand names must be UPPERCASE and standardized (MARLBORO not Marlboro or marlboro)
- Sizes must include units (oz, ml, count, pack, etc.)
- Use 'UNSPECIFIED' only when truly unknown, not as a guess
- Be specific but not too granular (don't create 50 subcategories)
- Use common industry terminology

{category_hint}"""},
                {"role": "user", "content": f"Analyze this product: {description}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=10
        )

        result = json.loads(response.choices[0].message.content)

        # Apply post-processing standardization
        result['brand'] = standardize_brand(result.get('brand', 'UNSPECIFIED'))
        result['size'] = standardize_size(result.get('size', 'UNSPECIFIED'))

        return (idx, result, None)
    except Exception as e:
        return (idx, None, str(e))

# Process items in parallel
start_time = time.time()
results = {}
MAX_WORKERS = 30  # 30 concurrent API calls

print(f'Launching {MAX_WORKERS} parallel workers...', flush=True)
print(flush=True)

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Submit all tasks
    futures = {executor.submit(analyze_item_with_ai, (idx, item)): idx for idx, item in enumerate(items)}

    # Process completed tasks
    for future in as_completed(futures):
        idx, result, error = future.result()

        with processed_lock:
            processed_count += 1

            if error:
                error_count += 1
                # Fallback values
                items[idx]['Brand'] = "ERROR"
                items[idx]['MainCategory'] = "Other"
                items[idx]['Subcategory'] = "Uncategorized"
                items[idx]['ProductType'] = "Unknown"
                items[idx]['Size'] = ""
            else:
                items[idx]['Brand'] = result['brand']
                items[idx]['MainCategory'] = result['main_category']
                items[idx]['Subcategory'] = result['subcategory']
                items[idx]['ProductType'] = result['product_type']
                items[idx]['Size'] = result['size']

            # Show progress every 100 items
            if processed_count % 100 == 0 or processed_count == len(items):
                elapsed = time.time() - start_time
                items_per_sec = processed_count / elapsed if elapsed > 0 else 0
                remaining = (len(items) - processed_count) / items_per_sec if items_per_sec > 0 else 0
                print(f'  [{processed_count:>4}/{len(items)}] {(processed_count/len(items)*100):>5.1f}% | {items_per_sec:>5.1f} items/s | ETA: {remaining/60:>4.1f}m | Errors: {error_count}', flush=True)

elapsed = time.time() - start_time

print(flush=True)
print(f'✅ PARALLEL AI analysis complete!', flush=True)
print(f'   Total items: {len(items):,}', flush=True)
print(f'   Processed successfully: {processed_count - error_count:,}', flush=True)
print(f'   Errors: {error_count}', flush=True)
print(f'   Total time: {elapsed/60:.1f} minutes ({len(items) / elapsed:.1f} items/sec)', flush=True)
print(flush=True)

# Show brand and category breakdowns
brands = Counter(item['Brand'] for item in items)
categories = Counter(item['MainCategory'] for item in items)
subcategories = Counter(item['Subcategory'] for item in items)

print('TOP 20 BRANDS:', flush=True)
print('─' * 60, flush=True)
for brand, count in brands.most_common(20):
    print(f'{brand:<35} {count:>5} items', flush=True)

print(flush=True)
print('MAIN CATEGORIES:', flush=True)
print('─' * 60, flush=True)
for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    print(f'{cat:<35} {count:>5} items', flush=True)

print(flush=True)
print('TOP 20 SUBCATEGORIES:', flush=True)
print('─' * 60, flush=True)
for subcat, count in subcategories.most_common(20):
    print(f'{subcat:<35} {count:>5} items', flush=True)

print(flush=True)

# Step 4: Export to CSV
output_file = '/Users/akbarchranya/georgiadashboard/gadash108/master_product_catalog.csv'

print(f'Step 4: Exporting to master catalog CSV...', flush=True)

export_data = []
for item in items:
    export_data.append({
        'ItemID': item['ItemID'],
        'ItemLookupCode': item['ItemLookupCode'],
        'Description': item['Description'],
        'CurrentCategory': item['CurrentCategory'] or '',
        'MainCategory': item['MainCategory'],
        'Subcategory': item['Subcategory'],
        'ProductType': item['ProductType'],
        'Brand': item['Brand'],
        'Size': item['Size'],
        'Price': round(item['Price'] or 0, 2),
        'Cost': round(item['Cost'] or 0, 2),
        'OnHand': round(item['OnHand'] or 0, 2),
        'MonthlyAvgQty': item['MonthlyAvgQty'],
        'MonthlyAvgRevenue': round(item['MonthlyAvgRevenue'], 2),
        'TotalQtySold_12mo': round(item['TotalQtySold_12mo'], 2),
        'TotalRevenue_12mo': round(item['TotalRevenue_12mo'], 2),
        'CurrentSupplier': item['SupplierName'] or '',
        'LastReceived': item['LastReceived'].strftime('%Y-%m-%d') if item['LastReceived'] else '',
        'LastSold': item['LastSold'].strftime('%Y-%m-%d') if item['LastSold'] else '',
        'GrossMargin': round(((item['Price'] - item['Cost']) / item['Price'] * 100) if item['Price'] else 0, 1)
    })

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    if export_data:
        writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
        writer.writeheader()
        writer.writerows(export_data)

print(f'✅ Export complete: {output_file}', flush=True)
print(f'   Total items exported: {len(export_data):,}', flush=True)
print(flush=True)

# Summary statistics
print('═' * 70, flush=True)
print('FINAL SUMMARY', flush=True)
print('═' * 70, flush=True)
print(f'Total Items Categorized:  {len(items):>10,}', flush=True)
print(f'Total Brands Identified:  {len(brands):>10}', flush=True)
print(f'Total Main Categories:    {len(categories):>10}', flush=True)
print(f'Total Subcategories:      {len(subcategories):>10}', flush=True)
print(f'Processing Time:          {elapsed/60:>10.1f} minutes', flush=True)
print(f'Average Speed:            {len(items) / elapsed:>10.1f} items/sec', flush=True)
print('═' * 70, flush=True)
print(flush=True)
print('✅ PARALLEL AI-powered categorization complete!', flush=True)
print(f'✅ Master file ready to use as overlay: {output_file}', flush=True)
