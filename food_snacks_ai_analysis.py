import os
os.environ['TDSVER'] = '7.0'
import pymssql
import time
from datetime import datetime, timedelta
import csv
import json
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 300,
    'login_timeout': 30
}

print('╔════════════════════════════════════════════════════════════════╗')
print('║   AI-POWERED FOOD AND SNACKS ANALYSIS WITH BRAND EXTRACTION   ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

# Calculate date range for last 12 months
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

print(f'Analysis Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
print()

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

# Step 1: Get all Food and Snacks items with current inventory
print('Step 1: Fetching all Food and Snacks items...')
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

print(f'✅ Found {len(items):,} items in {elapsed:.1f}s')
print()

# Step 2: Get 12-month sales history for each item
print('Step 2: Getting 12-month sales data...')
print('(This may take a few minutes)')
print()

for idx, item in enumerate(items, 1):
    if idx % 50 == 0:
        print(f'  Processing item {idx}/{len(items)}...')

    # Get sales data for past 12 months
    query_sales = f"""
    SELECT
        SUM(te.Quantity) as TotalQtySold,
        SUM(te.Price * te.Quantity) as TotalRevenue,
        COUNT(DISTINCT CAST(t.Time AS DATE)) as DaysSold
    FROM [Transaction] t
    INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE te.ItemID = {item['ItemID']}
      AND t.Time >= '{start_date.strftime('%Y-%m-%d')}'
      AND t.Time < '{end_date.strftime('%Y-%m-%d')}'
      AND te.TransactionNumber > 0
    """

    cursor.execute(query_sales)
    sales = cursor.fetchone()

    # Calculate monthly average
    item['TotalQtySold_12mo'] = sales['TotalQtySold'] or 0
    item['TotalRevenue_12mo'] = sales['TotalRevenue'] or 0
    item['MonthlyAvgQty'] = round((sales['TotalQtySold'] or 0) / 12, 2)
    item['MonthlyAvgRevenue'] = round((sales['TotalRevenue'] or 0) / 12, 2)

print()
print(f'✅ Sales data collected for {len(items):,} items')
print()

# Step 3: AI-powered categorization and brand extraction
print('Step 3: Using OpenAI to analyze each item...')
print('(Extracting brand, category, subcategory, product type)')
print()

def analyze_item_with_ai(description):
    """
    Use OpenAI API to intelligently extract:
    - Brand name
    - Main category
    - Subcategory
    - Product type
    - Size/quantity
    """
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
            temperature=0.1
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f'    ⚠️  API Error: {str(e)[:50]}')
        # Fallback
        return {
            "brand": "UNKNOWN",
            "main_category": "Other",
            "subcategory": "Uncategorized",
            "product_type": "Unknown",
            "size": ""
        }

# Process items in batches to show progress
for idx, item in enumerate(items, 1):
    if idx % 10 == 0:
        print(f'  Analyzing item {idx}/{len(items)}... ({(idx/len(items)*100):.1f}%)')

    # Analyze with AI
    ai_result = analyze_item_with_ai(item['Description'])

    # Add AI results to item
    item['Brand'] = ai_result['brand']
    item['MainCategory'] = ai_result['main_category']
    item['Subcategory'] = ai_result['subcategory']
    item['ProductType'] = ai_result['product_type']
    item['Size'] = ai_result['size']

    # Small delay to respect API rate limits
    if idx % 50 == 0:
        time.sleep(1)

print()
print(f'✅ AI analysis complete for {len(items):,} items')
print()

# Show brand and category breakdowns
from collections import Counter

brands = Counter(item['Brand'] for item in items)
categories = Counter(item['MainCategory'] for item in items)
subcategories = Counter(item['Subcategory'] for item in items)

print('TOP 20 BRANDS:')
print('─' * 60)
for brand, count in brands.most_common(20):
    print(f'{brand:<35} {count:>5} items')

print()
print('MAIN CATEGORIES:')
print('─' * 60)
for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    print(f'{cat:<35} {count:>5} items')

print()
print('TOP 20 SUBCATEGORIES:')
print('─' * 60)
for subcat, count in subcategories.most_common(20):
    print(f'{subcat:<35} {count:>5} items')

print()

# Step 4: Export to CSV
output_file = '/Users/akbarchranya/Downloads/food_snacks_ai_analysis_complete.csv'

print(f'Step 4: Exporting to CSV...')

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

print(f'✅ Export complete: {output_file}')
print(f'   Total items exported: {len(export_data):,}')
print()

# Summary statistics
print('═' * 70)
print('SUMMARY STATISTICS')
print('═' * 70)
print(f'Total Items Analyzed:     {len(items):>10,}')
print(f'Total Brands Identified:  {len(brands):>10}')
print(f'Total Main Categories:    {len(categories):>10}')
print(f'Total Subcategories:      {len(subcategories):>10}')
print(f'Avg Monthly Sales/Item:   ${sum(i["MonthlyAvgRevenue"] for i in items) / len(items):>10,.2f}')
print('═' * 70)
print()
print('✅ AI-powered analysis complete!')

cursor.close()
conn.close()
