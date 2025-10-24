import os
os.environ['TDSVER'] = '7.0'
import pymssql
import time
from datetime import datetime, timedelta
import csv

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
print('║    FOOD AND SNACKS COMPREHENSIVE ANALYSIS WITH RECATEGORIZATION║')
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

# Step 3: Manually recategorize items
print('Step 3: Manually recategorizing items...')
print('(Analyzing each item description for proper categorization)')
print()

def recategorize_item(description):
    """
    Manually recategorize items based on description keywords.
    This is a comprehensive categorization system for food and snacks.
    """
    desc_lower = description.lower() if description else ""

    # CHIPS & SALTY SNACKS
    if any(word in desc_lower for word in ['chip', 'chips', 'dorito', 'lay', 'cheeto', 'fritos', 'pringles', 'ruffles', 'tostitos']):
        return "Chips & Salty Snacks"

    # CANDY & CHOCOLATE
    if any(word in desc_lower for word in ['candy', 'chocolate', 'snickers', 'reese', 'm&m', 'kit kat', 'twix', 'skittles', 'starburst', 'hershey', 'milky way', 'butterf', 'gummy', 'gummi', 'sour patch']):
        return "Candy & Chocolate"

    # COOKIES & BAKED GOODS
    if any(word in desc_lower for word in ['cookie', 'oreo', 'chips ahoy', 'fig newton', 'brownie', 'cake', 'pastry', 'donut', 'danish']):
        return "Cookies & Baked Goods"

    # CRACKERS
    if any(word in desc_lower for word in ['cracker', 'ritz', 'wheat thin', 'triscuit', 'goldfish']):
        return "Crackers"

    # NUTS & SEEDS
    if any(word in desc_lower for word in ['nut', 'nuts', 'peanut', 'almond', 'cashew', 'pistachio', 'sunflower seed', 'trail mix']):
        return "Nuts & Seeds"

    # GUM & MINTS
    if any(word in desc_lower for word in ['gum', 'mint', 'breath', 'tic tac', 'altoid', 'mentos']):
        return "Gum & Mints"

    # JERKY & MEAT SNACKS
    if any(word in desc_lower for word in ['jerky', 'beef stick', 'slim jim', 'meat stick']):
        return "Jerky & Meat Snacks"

    # POPCORN
    if 'popcorn' in desc_lower:
        return "Popcorn"

    # PROTEIN/ENERGY BARS
    if any(word in desc_lower for word in ['protein bar', 'energy bar', 'granola bar', 'nature valley', 'cliff bar', 'quest bar']):
        return "Protein & Energy Bars"

    # BREAKFAST/CEREAL
    if any(word in desc_lower for word in ['cereal', 'oatmeal', 'granola', 'breakfast bar']):
        return "Breakfast & Cereal"

    # ICE CREAM & FROZEN
    if any(word in desc_lower for word in ['ice cream', 'frozen', 'popsicle', 'ice pop']):
        return "Ice Cream & Frozen"

    # PREPARED FOOD (Sandwiches, Hot Dogs, etc.)
    if any(word in desc_lower for word in ['sandwich', 'hot dog', 'pizza', 'taquito', 'burrito', 'wrap']):
        return "Prepared Food"

    # BREAD & BAKERY
    if any(word in desc_lower for word in ['bread', 'bun', 'roll', 'bagel', 'muffin']):
        return "Bread & Bakery"

    # CONDIMENTS & SAUCES
    if any(word in desc_lower for word in ['ketchup', 'mustard', 'mayo', 'sauce', 'salsa', 'dressing']):
        return "Condiments & Sauces"

    # Default category
    return "Other Food & Snacks"

# Apply recategorization
for item in items:
    item['NewCategory'] = recategorize_item(item['Description'])

print(f'✅ Recategorized {len(items):,} items')
print()

# Show category breakdown
from collections import Counter
category_counts = Counter(item['NewCategory'] for item in items)

print('NEW CATEGORY BREAKDOWN:')
print('─' * 60)
for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
    print(f'{cat:<35} {count:>5} items')

print()

# Step 4: Export to CSV
output_file = '/Users/akbarchranya/Downloads/food_snacks_recategorized_analysis.csv'

print(f'Step 4: Exporting to CSV...')

# Prepare data for export
export_data = []
for item in items:
    export_data.append({
        'ItemLookupCode': item['ItemLookupCode'],
        'Description': item['Description'],
        'CurrentCategory': item['CurrentCategory'],
        'NewCategory': item['NewCategory'],
        'Department': item['Department'],
        'Price': round(item['Price'] or 0, 2),
        'Cost': round(item['Cost'] or 0, 2),
        'OnHand': round(item['OnHand'] or 0, 2),
        'MonthlyAvgQty': item['MonthlyAvgQty'],
        'MonthlyAvgRevenue': round(item['MonthlyAvgRevenue'], 2),
        'TotalQtySold_12mo': round(item['TotalQtySold_12mo'], 2),
        'TotalRevenue_12mo': round(item['TotalRevenue_12mo'], 2),
        'CurrentSupplier': item['SupplierName'] or 'No Supplier',
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
print(f'Total New Categories:     {len(category_counts):>10}')
print(f'Avg Monthly Sales/Item:   ${sum(i["MonthlyAvgRevenue"] for i in items) / len(items):>10,.2f}')
print(f'Total Inventory Value:    ${sum((i["Cost"] or 0) * (i["OnHand"] or 0) for i in items):>10,.2f}')
print('═' * 70)
print()
print('✅ Analysis complete!')

cursor.close()
conn.close()
