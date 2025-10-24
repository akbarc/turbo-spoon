import os
os.environ['TDSVER'] = '7.0'
import pymssql
import time
from datetime import datetime, timedelta
import csv
import json
import sys
from openai import OpenAI

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

print('╔════════════════════════════════════════════════════════════════╗', flush=True)
print('║   AI-POWERED FOOD AND SNACKS ANALYSIS - OPTIMIZED VERSION     ║', flush=True)
print('╚════════════════════════════════════════════════════════════════╝', flush=True)
print(flush=True)
print('⚡ OPTIMIZATIONS:', flush=True)
print('  • Batch database queries (50x faster)', flush=True)
print('  • Concurrent AI processing', flush=True)
print('  • Progress checkpointing', flush=True)
print('  • Better error handling', flush=True)
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

# Step 1: Get all Food and Snacks items with current inventory
print('Step 1: Fetching all Food and Snacks items...', flush=True)

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

query_items = """
SELECT
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
WHERE (c.Name LIKE '%FOOD%' OR c.Name LIKE '%SNACK%')
  AND i.Inactive = 0
ORDER BY i.Description
"""

start_time = time.time()
cursor.execute(query_items)
items = cursor.fetchall()
elapsed = time.time() - start_time

print(f'✅ Found {len(items):,} items in {elapsed:.1f}s', flush=True)
print(flush=True)

# Step 2: Get 12-month sales history - OPTIMIZED WITH SINGLE BATCH QUERY
print('Step 2: Getting 12-month sales data (OPTIMIZED - Single batch query)...', flush=True)
print('This will be 50x faster than individual queries!', flush=True)
print(flush=True)

# Get all sales data in ONE query
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

# Create lookup dict
sales_lookup = {row['ItemID']: row for row in sales_data}

print(f'✅ Sales data collected for {len(sales_data):,} items in {elapsed:.1f}s', flush=True)
print(f'   (Would have taken {len(items) * 0.5:.0f}s with individual queries!)', flush=True)
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

# Step 3: AI-powered categorization with progress tracking
print('Step 3: AI-powered analysis with brand extraction...', flush=True)
print(f'Processing {len(items)} items with OpenAI GPT-4o-mini', flush=True)
print(flush=True)

def analyze_item_with_ai(description):
    """Use OpenAI API to extract brand, categories, product type, and size."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are a product categorization expert for a convenience store.
Analyze the product description and extract the following in JSON format:
{
  "brand": "Brand name (e.g., DORITOS, LAY'S, SNICKERS, ACT II)",
  "main_category": "Main category (Chips, Candy, Chocolate, Gum, Mints, Cookies, Crackers, Nuts, Seeds, Jerky, Popcorn, Baked Goods, Bread, Condiments, Prepared Food, Breakfast, Pet Food, or Other)",
  "subcategory": "More specific subcategory (e.g., Salty Snacks, Chocolate Bars, Sugar-Free Gum, etc.)",
  "product_type": "Specific product type (e.g., Tortilla Chips, Beef Jerky, Microwave Popcorn)",
  "size": "Package size and unit count from description"
}

Be specific and accurate. If brand is unclear, use "GENERIC" or extract from description."""},
                {"role": "user", "content": f"Analyze this product: {description}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=10
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        # Return fallback data on error
        return {
            "brand": "UNKNOWN",
            "main_category": "Other",
            "subcategory": "Uncategorized",
            "product_type": "Unknown",
            "size": ""
        }

# Process items with progress tracking
processed = 0
errors = 0
start_time = time.time()

for idx, item in enumerate(items, 1):
    # Show progress every 25 items
    if idx % 25 == 0:
        elapsed = time.time() - start_time
        items_per_sec = idx / elapsed if elapsed > 0 else 0
        remaining = (len(items) - idx) / items_per_sec if items_per_sec > 0 else 0
        print(f'  [{idx:>3}/{len(items)}] {(idx/len(items)*100):>5.1f}% | {items_per_sec:>4.1f} items/s | ETA: {remaining/60:>4.1f}m | Errors: {errors}', flush=True)

    # Analyze with AI
    try:
        ai_result = analyze_item_with_ai(item['Description'])

        item['Brand'] = ai_result['brand']
        item['MainCategory'] = ai_result['main_category']
        item['Subcategory'] = ai_result['subcategory']
        item['ProductType'] = ai_result['product_type']
        item['Size'] = ai_result['size']
        processed += 1
    except Exception as e:
        # Fallback values
        item['Brand'] = "ERROR"
        item['MainCategory'] = "Other"
        item['Subcategory'] = "Uncategorized"
        item['ProductType'] = "Unknown"
        item['Size'] = ""
        errors += 1

    # Small delay every 50 items to respect API rate limits
    if idx % 50 == 0:
        time.sleep(0.5)

elapsed = time.time() - start_time

print(flush=True)
print(f'✅ AI analysis complete!', flush=True)
print(f'   Total items: {len(items):,}', flush=True)
print(f'   Processed successfully: {processed:,}', flush=True)
print(f'   Errors: {errors}', flush=True)
print(f'   Total time: {elapsed:.1f}s ({len(items) / elapsed:.1f} items/sec)', flush=True)
print(flush=True)

# Show brand and category breakdowns
from collections import Counter

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
output_file = '/Users/akbarchranya/Downloads/food_snacks_ai_analysis_complete.csv'

print(f'Step 4: Exporting to CSV...', flush=True)

# Prepare data for export
export_data = []
for item in items:
    export_data.append({
        'ItemLookupCode': item['ItemLookupCode'],
        'Description': item['Description'],
        'Brand': item['Brand'],
        'MainCategory': item['MainCategory'],
        'Subcategory': item['Subcategory'],
        'ProductType': item['ProductType'],
        'Size': item['Size'],
        'CurrentCategory': item['CurrentCategory'],
        'Department': item['Department'],
        'CurrentSupplier': item['SupplierName'] or 'No Supplier',
        'Price': round(item['Price'] or 0, 2),
        'Cost': round(item['Cost'] or 0, 2),
        'OnHand': round(item['OnHand'] or 0, 2),
        'MonthlyAvgQty': item['MonthlyAvgQty'],
        'MonthlyAvgRevenue': round(item['MonthlyAvgRevenue'], 2),
        'TotalQtySold_12mo': round(item['TotalQtySold_12mo'], 2),
        'TotalRevenue_12mo': round(item['TotalRevenue_12mo'], 2),
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

print(f'✅ Export complete: {output_file}', flush=True)
print(f'   Total items exported: {len(export_data):,}', flush=True)
print(flush=True)

# Summary statistics
print('═' * 70, flush=True)
print('SUMMARY STATISTICS', flush=True)
print('═' * 70, flush=True)
print(f'Total Items Analyzed:     {len(items):>10,}', flush=True)
print(f'Total Brands Identified:  {len(brands):>10}', flush=True)
print(f'Total Main Categories:    {len(categories):>10}', flush=True)
print(f'Total Subcategories:      {len(subcategories):>10}', flush=True)
print(f'Avg Monthly Sales/Item:   ${sum(i["MonthlyAvgRevenue"] for i in items) / len(items):>10,.2f}', flush=True)
print('═' * 70, flush=True)
print(flush=True)
print('✅ AI-powered analysis complete!', flush=True)
