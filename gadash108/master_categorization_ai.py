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

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

print('╔════════════════════════════════════════════════════════════════╗', flush=True)
print('║     MASTER PRODUCT CATEGORIZATION - AI-POWERED ANALYSIS       ║', flush=True)
print('║              Complete Database - 12-Month Sales Filter        ║', flush=True)
print('╚════════════════════════════════════════════════════════════════╝', flush=True)
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

# MASTER CATEGORY STRUCTURE
MAIN_CATEGORIES = [
    "Tobacco Products",
    "Tobacco Accessories",
    "Vaping & E-Cigarettes",
    "Food & Snacks",
    "Candy & Gum",
    "Health & Wellness",
    "Personal Care & Beauty",
    "Household & Cleaning",
    "General Merchandise",
    "Automotive",
    "Beverages",
    "Specialty Products"
]

# Brand standardization lookup (will be built dynamically)
brand_standardization = {
    # Tobacco
    'MARLBORO': ['MARLBORO', 'MARLBORO CIGARETTES', 'MARLBRO', 'MARBOLO'],
    'NEWPORT': ['NEWPORT', 'NEWPORTS', 'NEWPORT CIGARETTES'],
    'CAMEL': ['CAMEL', 'CAMELS', 'CAMEL CIGARETTES'],
    'PALL MALL': ['PALL MALL', 'PALLMALL', 'PALL-MALL'],
    'L&M': ['L&M', 'L & M', 'LM'],
    'WINSTON': ['WINSTON', 'WINSTONS'],
    # Vaping
    'JUUL': ['JUUL', 'JUUL LABS', 'JUL'],
    'VUSE': ['VUSE', 'VUSE VAPOR'],
    'NJOY': ['NJOY', 'N-JOY'],
    # Food brands (from previous analysis)
    'PLANTERS': ['PLANTERS', 'PLANTER', 'PLANTERS PEANUTS'],
    'HOSTESS': ['HOSTESS', 'HOSTESS BRANDS'],
    'SLIM JIM': ['SLIM JIM', 'SLIMJIM', 'SLIM-JIM'],
    'JACK LINKS': ['JACK LINKS', 'JACK LINK', "JACK LINK'S"],
    'LAY': ['LAY', "LAY'S", 'LAYS'],
    'DORITOS': ['DORITOS', 'DORITO'],
    # Add more as discovered
}

print('Step 1: Fetching items with 12-month sales history...', flush=True)
print('(Only items that have sold in the last 12 months)', flush=True)
print(flush=True)

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

# Query to get items with sales in last 12 months
query_items = f"""
SELECT DISTINCT
    i.ID as ItemID,
    i.ItemLookupCode,
    i.Description,
    i.Price,
    i.Cost,
    i.Quantity as OnHand,
    c.Name as CurrentCategory,
    d.Name as Department,
    s.SupplierName,
    i.LastReceived,
    i.LastSold
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

# Step 2: Get 12-month sales data in batch
print('Step 2: Getting 12-month sales data (OPTIMIZED - Single batch query)...', flush=True)

query_sales_batch = f"""
SELECT
    te.ItemID,
    SUM(te.Quantity) as TotalQtySold,
    SUM(te.Price * te.Quantity) as TotalRevenue,
    COUNT(DISTINCT CAST(t.Time AS DATE)) as DaysSold
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

print(f'✅ Sales data collected for {len(sales_data):,} items in {elapsed:.1f}s', flush=True)
print(flush=True)

# Add sales data to items
for item in items:
    sales = sales_lookup.get(item['ItemID'], {'TotalQtySold': 0, 'TotalRevenue': 0, 'DaysSold': 0})
    item['TotalQtySold_12mo'] = sales['TotalQtySold'] or 0
    item['TotalRevenue_12mo'] = sales['TotalRevenue'] or 0
    item['MonthlyAvgQty'] = round((sales['TotalQtySold'] or 0) / 12, 2)
    item['MonthlyAvgRevenue'] = round((sales['TotalRevenue'] or 0) / 12, 2)

cursor.close()
conn.close()

# Step 3: AI-powered categorization with consistency enforcement
print('Step 3: AI-powered deep categorization with consistency checks...', flush=True)
print(f'Processing {len(items):,} items with OpenAI GPT-4o-mini', flush=True)
print(flush=True)

def standardize_brand(brand):
    """Standardize brand names to avoid variations"""
    if not brand or brand.upper() in ['UNKNOWN', 'ERROR', 'UNSPECIFIED', 'GENERIC']:
        return brand

    brand_upper = brand.upper().strip()

    # Check against known standardizations
    for standard, variants in brand_standardization.items():
        if brand_upper in [v.upper() for v in variants]:
            return standard

    return brand  # Return as-is if not in lookup

def standardize_size(size):
    """Standardize size formats"""
    if not size or size.upper() in ['UNKNOWN', 'UNSPECIFIED']:
        return size

    size = size.strip()

    # Common standardizations
    replacements = {
        'OZ': 'oz',
        'ML': 'ml',
        'CT': 'count',
        'PK': 'pack',
        'LB': 'lb',
        'G': 'g',
        'MG': 'mg',
    }

    for old, new in replacements.items():
        size = size.replace(f' {old}', new).replace(f'{old}', new)

    return size

def analyze_item_with_ai(description, current_category):
    """Use OpenAI API to extract brand, categories, product type, and size with consistency."""
    try:
        # Determine likely main category from current category for better prompting
        category_hint = ""
        if current_category:
            cat_upper = current_category.upper()
            if 'CIGARETTE' in cat_upper or 'CIGAR' in cat_upper or 'TOBACCO' in cat_upper:
                category_hint = "This is likely a tobacco product."
            elif 'ECIG' in cat_upper or 'VAPE' in cat_upper or 'ELECTRONIC' in cat_upper:
                category_hint = "This is likely a vaping/e-cigarette product."
            elif 'FOOD' in cat_upper or 'SNACK' in cat_upper:
                category_hint = "This is likely a food/snack product."
            elif 'CANDY' in cat_upper or 'GUM' in cat_upper:
                category_hint = "This is likely a candy/gum product."

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
            timeout=15
        )

        result = json.loads(response.choices[0].message.content)

        # Apply post-processing standardization
        result['brand'] = standardize_brand(result.get('brand', 'UNSPECIFIED'))
        result['size'] = standardize_size(result.get('size', 'UNSPECIFIED'))

        return result
    except Exception as e:
        # Return fallback data on error
        return {
            "brand": "ERROR",
            "main_category": "General Merchandise",
            "subcategory": "Uncategorized",
            "product_type": "Unknown",
            "size": "UNSPECIFIED"
        }

# Process items with progress tracking and checkpointing
processed = 0
errors = 0
start_time = time.time()
checkpoint_file = '/Users/akbarchranya/georgiadashboard/gadash108/categorization_checkpoint.json'

# Load checkpoint if exists
checkpoint_data = {}
if os.path.exists(checkpoint_file):
    try:
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
        print(f'📋 Loaded checkpoint with {len(checkpoint_data)} previously processed items', flush=True)
    except:
        pass

for idx, item in enumerate(items, 1):
    # Show progress every 50 items
    if idx % 50 == 0:
        elapsed = time.time() - start_time
        items_per_sec = idx / elapsed if elapsed > 0 else 0
        remaining = (len(items) - idx) / items_per_sec if items_per_sec > 0 else 0
        print(f'  [{idx:>5}/{len(items)}] {(idx/len(items)*100):>5.1f}% | {items_per_sec:>4.1f} items/s | ETA: {remaining/60:>5.1f}m | Errors: {errors}', flush=True)

    # Check if already in checkpoint
    item_key = str(item['ItemID'])
    if item_key in checkpoint_data:
        ai_result = checkpoint_data[item_key]
    else:
        # Analyze with AI
        try:
            ai_result = analyze_item_with_ai(item['Description'], item['CurrentCategory'])

            # Save to checkpoint every 100 items
            checkpoint_data[item_key] = ai_result
            if idx % 100 == 0:
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint_data, f)

        except Exception as e:
            # Fallback values
            ai_result = {
                "brand": "ERROR",
                "main_category": "General Merchandise",
                "subcategory": "Uncategorized",
                "product_type": "Unknown",
                "size": "UNSPECIFIED"
            }
            errors += 1

    item['Brand'] = ai_result.get('brand', 'UNSPECIFIED')
    item['MainCategory'] = ai_result.get('main_category', 'General Merchandise')
    item['Subcategory'] = ai_result.get('subcategory', 'Uncategorized')
    item['ProductType'] = ai_result.get('product_type', 'Unknown')
    item['Size'] = ai_result.get('size', 'UNSPECIFIED')
    processed += 1

    # Small delay every 50 items to respect API rate limits
    if idx % 50 == 0 and item_key not in checkpoint_data:
        time.sleep(0.5)

# Save final checkpoint
with open(checkpoint_file, 'w') as f:
    json.dump(checkpoint_data, f)

elapsed = time.time() - start_time

print(flush=True)
print(f'✅ AI analysis complete!', flush=True)
print(f'   Total items: {len(items):,}', flush=True)
print(f'   Processed successfully: {processed:,}', flush=True)
print(f'   Errors: {errors}', flush=True)
print(f'   Total time: {elapsed:.1f}s ({len(items) / elapsed:.1f} items/sec)', flush=True)
print(flush=True)

# Show analytics
brands = Counter(item['Brand'] for item in items)
main_cats = Counter(item['MainCategory'] for item in items)
subcats = Counter(item['Subcategory'] for item in items)

print('═' * 80, flush=True)
print('CATEGORIZATION SUMMARY', flush=True)
print('═' * 80, flush=True)
print(flush=True)

print('MAIN CATEGORIES:', flush=True)
print('─' * 80, flush=True)
for cat, count in sorted(main_cats.items(), key=lambda x: x[1], reverse=True):
    pct = (count / len(items) * 100) if items else 0
    print(f'{cat:<40} {count:>6,} items ({pct:>5.1f}%)', flush=True)

print(flush=True)
print('TOP 30 BRANDS:', flush=True)
print('─' * 80, flush=True)
for brand, count in brands.most_common(30):
    print(f'{brand:<40} {count:>6,} items', flush=True)

print(flush=True)
print('TOP 30 SUBCATEGORIES:', flush=True)
print('─' * 80, flush=True)
for subcat, count in subcats.most_common(30):
    print(f'{subcat:<40} {count:>6,} items', flush=True)

print(flush=True)

# Check for consistency issues
unspecified_brands = sum(1 for item in items if item['Brand'] in ['UNSPECIFIED', 'GENERIC', 'ERROR'])
unspecified_sizes = sum(1 for item in items if item['Size'] == 'UNSPECIFIED')

print('CONSISTENCY CHECK:', flush=True)
print('─' * 80, flush=True)
print(f'Items with UNSPECIFIED brand: {unspecified_brands:,} ({unspecified_brands/len(items)*100:.1f}%)', flush=True)
print(f'Items with UNSPECIFIED size:  {unspecified_sizes:,} ({unspecified_sizes/len(items)*100:.1f}%)', flush=True)
print(f'Total unique brands:          {len(brands):,}', flush=True)
print(f'Total unique subcategories:   {len(subcats):,}', flush=True)

print(flush=True)

# Export to master overlay file
output_file = '/Users/akbarchranya/georgiadashboard/gadash108/master_product_catalog.csv'

print(f'Step 4: Exporting master catalog overlay...', flush=True)

# Prepare data for export
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

# Write to CSV
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    if export_data:
        writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
        writer.writeheader()
        writer.writerows(export_data)

print(f'✅ Master catalog exported: {output_file}', flush=True)
print(f'   Total items: {len(export_data):,}', flush=True)
print(f'   Columns: {len(export_data[0].keys())}', flush=True)
print(flush=True)

# Final summary
print('═' * 80, flush=True)
print('FINAL SUMMARY', flush=True)
print('═' * 80, flush=True)
print(f'Total Items Analyzed:        {len(items):>10,}', flush=True)
print(f'Total Brands Identified:     {len(brands):>10,}', flush=True)
print(f'Total Main Categories:       {len(main_cats):>10}', flush=True)
print(f'Total Subcategories:         {len(subcats):>10}', flush=True)
print(f'Avg Monthly Revenue/Item:    ${sum(i["MonthlyAvgRevenue"] for i in items) / len(items):>10,.2f}', flush=True)
print(f'Processing Time:             {elapsed/60:>10,.1f} minutes', flush=True)
print('═' * 80, flush=True)
print(flush=True)
print('✅ Master categorization complete!', flush=True)
print(flush=True)
print('USAGE:', flush=True)
print('  This file can be used as an overlay/lookup table:', flush=True)
print(f'  - JOIN on ItemID or ItemLookupCode', flush=True)
print(f'  - Use in Power BI, Tableau, Excel', flush=True)
print(f'  - Update Item table with new categories', flush=True)
print(flush=True)
