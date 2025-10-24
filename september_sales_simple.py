"""
Generate CSV report of September 2025 sales by category with tax type details
Simplified approach - fetch raw data and aggregate in Python
"""
import pymssql
import csv
from collections import defaultdict
from datetime import datetime

# Database connection - using working credentials
conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    port=1433,
    tds_version='7.0',
    timeout=300,
    login_timeout=30
)

print("Connected to database successfully")

# Simpler query - just get raw data without complex aggregations
query = """
SELECT
    COALESCE(cat.Name, 'Uncategorized') as CategoryName,
    COALESCE(pe.SubDescription3, 'No Tax') as ExciseTaxType,
    te.TransactionNumber,
    te.Quantity,
    te.Price,
    te.Cost,
    COALESCE(pe.PriceC, 0) as ExciseTax
FROM TransactionEntry te WITH (NOLOCK)
INNER JOIN Item i WITH (NOLOCK) ON te.ItemID = i.ID
LEFT JOIN Category cat WITH (NOLOCK) ON i.CategoryID = cat.ID
LEFT JOIN PUExciseEntry pe WITH (NOLOCK) ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-09-01'
  AND te.TransactionTime < '2025-10-01'
  AND te.Quantity != 0
"""

print("Fetching September 2025 transaction data...")
print("This may take a minute or two...")
cursor = conn.cursor(as_dict=True)
cursor.execute(query)

# Aggregate in Python
aggregates = defaultdict(lambda: {
    'transactions': set(),
    'items_sold': 0,
    'total_quantity': 0,
    'total_revenue': 0,
    'total_cogs': 0,
    'total_excise': 0,
    'prices': [],
    'costs': []
})

print("Processing rows...")
row_count = 0
for row in cursor:
    row_count += 1
    if row_count % 10000 == 0:
        print(f"  Processed {row_count:,} rows...")

    key = (row['CategoryName'], row['ExciseTaxType'])
    agg = aggregates[key]

    agg['transactions'].add(row['TransactionNumber'])
    agg['items_sold'] += 1
    agg['total_quantity'] += row['Quantity']

    revenue = row['Price'] * row['Quantity']
    cogs = row['Cost'] * row['Quantity']
    excise = row['ExciseTax']

    agg['total_revenue'] += revenue
    agg['total_cogs'] += cogs
    agg['total_excise'] += excise
    agg['prices'].append(row['Price'])
    agg['costs'].append(row['Cost'])

print(f"Total rows processed: {row_count:,}")
print(f"Unique category/tax combinations: {len(aggregates)}")

# Extract tax rate from tax type
def get_tax_rate(tax_type):
    if '23' in tax_type:
        return 23
    elif '25' in tax_type:
        return 25
    elif '10' in tax_type:
        return 10
    elif '07' in tax_type or '7' in tax_type:
        return 7
    elif '05' in tax_type or '5' in tax_type:
        return 5
    return 0

# Write to CSV
output_file = '/Users/akbarchranya/georgiadashboard/september_2025_sales_by_category_tax.csv'
with open(output_file, 'w', newline='') as csvfile:
    fieldnames = [
        'CategoryName',
        'ExciseTaxType',
        'TaxRatePercent',
        'TransactionCount',
        'ItemsSold',
        'TotalQuantity',
        'TotalRevenue',
        'TotalCOGS',
        'TotalExciseTax',
        'GrossProfit',
        'GPMarginPercent',
        'AvgPrice',
        'AvgCost'
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Sort by category name and tax type
    sorted_keys = sorted(aggregates.keys())

    for key in sorted_keys:
        category_name, tax_type = key
        agg = aggregates[key]

        gross_profit = agg['total_revenue'] - agg['total_cogs'] - agg['total_excise']
        gp_margin = (gross_profit / agg['total_revenue'] * 100) if agg['total_revenue'] > 0 else 0
        avg_price = sum(agg['prices']) / len(agg['prices']) if agg['prices'] else 0
        avg_cost = sum(agg['costs']) / len(agg['costs']) if agg['costs'] else 0

        writer.writerow({
            'CategoryName': category_name,
            'ExciseTaxType': tax_type,
            'TaxRatePercent': f"{get_tax_rate(tax_type)}%",
            'TransactionCount': len(agg['transactions']),
            'ItemsSold': agg['items_sold'],
            'TotalQuantity': f"{agg['total_quantity']:.2f}",
            'TotalRevenue': f"${agg['total_revenue']:.2f}",
            'TotalCOGS': f"${agg['total_cogs']:.2f}",
            'TotalExciseTax': f"${agg['total_excise']:.2f}",
            'GrossProfit': f"${gross_profit:.2f}",
            'GPMarginPercent': f"{gp_margin:.2f}%",
            'AvgPrice': f"${avg_price:.2f}",
            'AvgCost': f"${avg_cost:.2f}"
        })

print(f"\nCSV report generated: {output_file}")
print(f"Total category/tax combinations: {len(aggregates)}")

# Print summary
print("\n=== SUMMARY ===")
total_revenue = sum(agg['total_revenue'] for agg in aggregates.values())
total_cogs = sum(agg['total_cogs'] for agg in aggregates.values())
total_excise = sum(agg['total_excise'] for agg in aggregates.values())
total_gp = total_revenue - total_cogs - total_excise
all_transactions = set()
for agg in aggregates.values():
    all_transactions.update(agg['transactions'])

print(f"Total Revenue: ${total_revenue:,.2f}")
print(f"Total COGS: ${total_cogs:,.2f}")
print(f"Total Excise Tax: ${total_excise:,.2f}")
print(f"Total Gross Profit: ${total_gp:,.2f}")
print(f"Total Transactions: {len(all_transactions):,}")
print(f"Overall GP Margin: {(total_gp/total_revenue*100):.2f}%")

# Close connection
cursor.close()
conn.close()
print("\nDone!")
