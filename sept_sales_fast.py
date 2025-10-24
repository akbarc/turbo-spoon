import pymssql
import csv
from collections import defaultdict

conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=300
)

print("Fetching September transactions (this may take a minute)...")

# Get raw data - no aggregation in SQL
query = """
SELECT TOP 200000
    COALESCE(cat.Name, 'Uncategorized') as Category,
    COALESCE(pe.SubDescription3, 'NO_TAX') as TaxCode,
    te.Quantity,
    te.Price,
    te.Cost,
    COALESCE(pe.PriceC, 0) as TaxAmount
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
LEFT JOIN Category cat ON i.CategoryID = cat.ID
LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-09-01'
  AND te.TransactionTime < '2025-10-01'
ORDER BY te.TransactionTime DESC
"""

cursor = conn.cursor(as_dict=True)
cursor.execute(query)
rows = cursor.fetchall()
print(f"✅ Got {len(rows):,} transactions")

# Aggregate in Python
data = defaultdict(lambda: {
    'transactions': 0, 'qty': 0, 'prices': [], 'costs': [],
    'revenue': 0, 'cogs': 0, 'tax': 0
})

for r in rows:
    key = (r['Category'], r['TaxCode'])
    d = data[key]
    d['transactions'] += 1
    d['qty'] += r['Quantity']
    d['prices'].append(r['Price'])
    d['costs'].append(r['Cost'])
    d['revenue'] += r['Price'] * r['Quantity']
    d['cogs'] += r['Cost'] * r['Quantity']
    d['tax'] += r['TaxAmount']

# Calculate tax rates
def get_tax_rate(code):
    if '23' in code: return 23
    if '25' in code: return 25
    if '10' in code: return 10
    if '07' in code or '7' in code: return 7
    if '05' in code or '5' in code: return 5
    return 0

# Write CSV
results = []
for (cat, tax), d in data.items():
    avg_price = sum(d['prices']) / len(d['prices']) if d['prices'] else 0
    avg_cost = sum(d['costs']) / len(d['costs']) if d['costs'] else 0
    gp = d['revenue'] - d['cogs'] - d['tax']
    gp_pct = (gp / d['revenue'] * 100) if d['revenue'] > 0 else 0
    tax_pct = (d['tax'] / d['revenue'] * 100) if d['revenue'] > 0 else 0
    
    results.append({
        'cat': cat, 'tax': tax, 'rate': get_tax_rate(tax),
        'trans': d['transactions'], 'qty': d['qty'],
        'avg_price': avg_price, 'avg_cost': avg_cost,
        'revenue': d['revenue'], 'cogs': d['cogs'], 'tax_amt': d['tax'],
        'gp': gp, 'gp_pct': gp_pct, 'tax_pct': tax_pct
    })

# Sort by revenue
results.sort(key=lambda x: x['revenue'], reverse=True)

with open('september_2025_sales.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Category', 'TaxCode', 'TaxRate%', 'Transactions', 'Quantity',
                     'AvgPrice', 'AvgCost', 'Revenue', 'COGS', 'TaxAmount',
                     'GrossProfit', 'GP%', 'Tax%'])
    
    for r in results:
        writer.writerow([
            r['cat'], r['tax'], r['rate'], r['trans'], f"{r['qty']:.2f}",
            f"{r['avg_price']:.2f}", f"{r['avg_cost']:.2f}",
            f"{r['revenue']:.2f}", f"{r['cogs']:.2f}", f"{r['tax_amt']:.2f}",
            f"{r['gp']:.2f}", f"{r['gp_pct']:.2f}", f"{r['tax_pct']:.2f}"
        ])

print(f"\n✅ Saved {len(results)} rows to september_2025_sales.csv")

total_rev = sum(r['revenue'] for r in results)
total_gp = sum(r['gp'] for r in results)
total_tax = sum(r['tax_amt'] for r in results)

print(f"\nRevenue:      ${total_rev:,.2f}")
print(f"Gross Profit: ${total_gp:,.2f} ({total_gp/total_rev*100:.1f}%)")
print(f"Tax Collected: ${total_tax:,.2f}")

conn.close()
