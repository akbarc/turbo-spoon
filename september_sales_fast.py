"""
Generate CSV report of September 2025 sales by category with tax type details
Optimized version with query hints and increased timeout
"""
import pymssql
import csv
from datetime import datetime

# Database connection - using working credentials with longer timeout
conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    port=1433,
    tds_version='7.0',
    timeout=300,  # Increased to 5 minutes
    login_timeout=30
)

print("Connected to database successfully")

# Optimized query with query hints and indexed access
query = """
SELECT
    COALESCE(cat.Name, 'Uncategorized') as CategoryName,
    COALESCE(pe.SubDescription3, 'No Tax') as ExciseTaxType,
    COUNT(DISTINCT te.TransactionNumber) as TransactionCount,
    COUNT(*) as ItemsSold,
    SUM(te.Quantity) as TotalQuantity,
    SUM(te.Price * te.Quantity) as TotalRevenue,
    SUM(te.Cost * te.Quantity) as TotalCOGS,
    SUM(COALESCE(pe.PriceC, 0)) as TotalExciseTax,
    SUM((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0)) as GrossProfit,
    AVG(te.Price) as AvgPrice,
    AVG(te.Cost) as AvgCost,
    CASE
        WHEN SUM(te.Price * te.Quantity) > 0
        THEN (SUM((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0)) / SUM(te.Price * te.Quantity)) * 100
        ELSE 0
    END as GPMarginPercent,
    CASE
        WHEN pe.SubDescription3 LIKE '%23%' THEN 23
        WHEN pe.SubDescription3 LIKE '%25%' THEN 25
        WHEN pe.SubDescription3 LIKE '%10%' THEN 10
        WHEN pe.SubDescription3 LIKE '%07%' THEN 7
        WHEN pe.SubDescription3 LIKE '%05%' THEN 5
        ELSE 0
    END as TaxRatePercent
FROM TransactionEntry te WITH (NOLOCK)
INNER JOIN Item i WITH (NOLOCK) ON te.ItemID = i.ID
LEFT JOIN Category cat WITH (NOLOCK) ON i.CategoryID = cat.ID
LEFT JOIN PUExciseEntry pe WITH (NOLOCK) ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-09-01'
  AND te.TransactionTime < '2025-10-01'
  AND te.Quantity != 0
GROUP BY cat.Name, pe.SubDescription3
ORDER BY cat.Name, pe.SubDescription3
OPTION (MAXDOP 4)
"""

print("Executing optimized query for September 2025 sales...")
print("This may take a few minutes for large datasets...")
cursor = conn.cursor(as_dict=True)
cursor.execute(query)
results = cursor.fetchall()

print(f"Retrieved {len(results)} rows")

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

    for row in results:
        writer.writerow({
            'CategoryName': row['CategoryName'],
            'ExciseTaxType': row['ExciseTaxType'],
            'TaxRatePercent': f"{row['TaxRatePercent']}%",
            'TransactionCount': row['TransactionCount'],
            'ItemsSold': row['ItemsSold'],
            'TotalQuantity': f"{row['TotalQuantity']:.2f}",
            'TotalRevenue': f"${row['TotalRevenue']:.2f}",
            'TotalCOGS': f"${row['TotalCOGS']:.2f}",
            'TotalExciseTax': f"${row['TotalExciseTax']:.2f}",
            'GrossProfit': f"${row['GrossProfit']:.2f}",
            'GPMarginPercent': f"{row['GPMarginPercent']:.2f}%",
            'AvgPrice': f"${row['AvgPrice']:.2f}",
            'AvgCost': f"${row['AvgCost']:.2f}"
        })

print(f"\nCSV report generated: {output_file}")
print(f"Total rows: {len(results)}")

# Print summary
print("\n=== SUMMARY ===")
total_revenue = sum(row['TotalRevenue'] for row in results)
total_cogs = sum(row['TotalCOGS'] for row in results)
total_excise = sum(row['TotalExciseTax'] for row in results)
total_gp = sum(row['GrossProfit'] for row in results)
total_transactions = sum(row['TransactionCount'] for row in results)

print(f"Total Revenue: ${total_revenue:,.2f}")
print(f"Total COGS: ${total_cogs:,.2f}")
print(f"Total Excise Tax: ${total_excise:,.2f}")
print(f"Total Gross Profit: ${total_gp:,.2f}")
print(f"Total Transactions: {total_transactions:,}")
print(f"Overall GP Margin: {(total_gp/total_revenue*100):.2f}%")

# Close connection
cursor.close()
conn.close()
print("\nDone!")
