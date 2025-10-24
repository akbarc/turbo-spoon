import pymssql
import csv

# Connect
conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=120
)

print("Querying September sales...")

# Simple aggregated query
query = """
SELECT 
    COALESCE(cat.Name, 'Uncategorized') as Category,
    COALESCE(pe.SubDescription3, 'NO_TAX') as TaxCode,
    CASE 
        WHEN pe.SubDescription3 LIKE '%23%' THEN 23
        WHEN pe.SubDescription3 LIKE '%25%' THEN 25
        WHEN pe.SubDescription3 LIKE '%10%' THEN 10
        WHEN pe.SubDescription3 LIKE '%07%' THEN 7
        WHEN pe.SubDescription3 LIKE '%05%' THEN 5
        ELSE 0 
    END as TaxRate,
    COUNT(*) as Transactions,
    SUM(te.Quantity) as Qty,
    AVG(te.Price) as AvgPrice,
    AVG(te.Cost) as AvgCost,
    SUM(te.Price * te.Quantity) as Revenue,
    SUM(te.Cost * te.Quantity) as COGS,
    SUM(COALESCE(pe.PriceC, 0)) as TaxAmount,
    SUM(te.Price * te.Quantity - te.Cost * te.Quantity - COALESCE(pe.PriceC, 0)) as GrossProfit
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
LEFT JOIN Category cat ON i.CategoryID = cat.ID
LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-09-01'
  AND te.TransactionTime < '2025-10-01'
GROUP BY cat.Name, pe.SubDescription3
ORDER BY SUM(te.Price * te.Quantity) DESC
"""

cursor = conn.cursor(as_dict=True)
cursor.execute(query)
rows = cursor.fetchall()

print(f"Got {len(rows)} category/tax combinations")

# Write CSV
with open('september_2025_sales.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Category', 'TaxCode', 'TaxRate%', 'Transactions', 'Quantity', 
                     'AvgPrice', 'AvgCost', 'Revenue', 'COGS', 'TaxAmount', 
                     'GrossProfit', 'GP%', 'Tax%'])
    
    for r in rows:
        gp_pct = (r['GrossProfit'] / r['Revenue'] * 100) if r['Revenue'] > 0 else 0
        tax_pct = (r['TaxAmount'] / r['Revenue'] * 100) if r['Revenue'] > 0 else 0
        
        writer.writerow([
            r['Category'],
            r['TaxCode'],
            r['TaxRate'],
            r['Transactions'],
            f"{r['Qty']:.2f}",
            f"{r['AvgPrice']:.2f}",
            f"{r['AvgCost']:.2f}",
            f"{r['Revenue']:.2f}",
            f"{r['COGS']:.2f}",
            f"{r['TaxAmount']:.2f}",
            f"{r['GrossProfit']:.2f}",
            f"{gp_pct:.2f}",
            f"{tax_pct:.2f}"
        ])

print("✅ Saved to september_2025_sales.csv")

# Quick summary
total_rev = sum(r['Revenue'] for r in rows)
total_gp = sum(r['GrossProfit'] for r in rows)
total_tax = sum(r['TaxAmount'] for r in rows)

print(f"\nRevenue:  ${total_rev:,.2f}")
print(f"GP:       ${total_gp:,.2f} ({total_gp/total_rev*100:.1f}%)")
print(f"Tax:      ${total_tax:,.2f}")

conn.close()
