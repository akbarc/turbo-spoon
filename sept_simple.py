import pymssql
import csv

conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=600
)

print("Step 1: Getting category sales (no tax data)...")

# First, get sales by category WITHOUT joining to excise table
q1 = """
SELECT TOP 50000
    te.ID as TransEntryID,
    COALESCE(cat.Name, 'Uncategorized') as Category,
    te.Quantity,
    te.Price,
    te.Cost
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
LEFT JOIN Category cat ON i.CategoryID = cat.ID
WHERE te.TransactionTime >= '2025-09-01'
  AND te.TransactionTime < '2025-10-01'
ORDER BY te.TransactionTime DESC
"""

c = conn.cursor(as_dict=True)
c.execute(q1)
trans = c.fetchall()
print(f"Got {len(trans):,} transactions")

print("Step 2: Getting excise tax data...")

# Get ALL excise entries for September
q2 = """
SELECT
    TransactionEntryID,
    SubDescription3 as TaxCode,
    PriceC as TaxAmount
FROM PUExciseEntry
WHERE TransactionEntryID IN (
    SELECT ID FROM TransactionEntry
    WHERE TransactionTime >= '2025-09-01'
      AND TransactionTime < '2025-10-01'
)
"""

c2 = conn.cursor(as_dict=True)
c2.execute(q2)
taxes = c2.fetchall()
print(f"Got {len(taxes):,} tax entries")

# Create tax lookup
tax_lookup = {}
for t in taxes:
    tax_lookup[t['TransactionEntryID']] = {
        'code': t['TaxCode'],
        'amount': t['TaxAmount'] or 0
    }

print("Step 3: Aggregating by category and tax type...")

# Aggregate
from collections import defaultdict
data = defaultdict(lambda: {
    'trans': 0, 'qty': 0, 'revenue': 0, 'cogs': 0, 'tax': 0
})

for tr in trans:
    tid = tr['TransEntryID']
    cat = tr['Category']
    tax_info = tax_lookup.get(tid, {'code': 'NO_TAX', 'amount': 0})
    key = (cat, tax_info['code'])
    
    d = data[key]
    d['trans'] += 1
    d['qty'] += tr['Quantity']
    d['revenue'] += tr['Price'] * tr['Quantity']
    d['cogs'] += tr['Cost'] * tr['Quantity']
    d['tax'] += tax_info['amount']

print(f"Step 4: Writing CSV ({len(data)} category/tax combinations)...")

results = []
for (cat, tax), d in data.items():
    gp = d['revenue'] - d['cogs'] - d['tax']
    results.append({
        'cat': cat, 'tax': tax or 'NO_TAX',
        'trans': d['trans'], 'qty': d['qty'],
        'revenue': d['revenue'], 'cogs': d['cogs'], 'tax_amt': d['tax'],
        'gp': gp, 'gp_pct': (gp / d['revenue'] * 100) if d['revenue'] > 0 else 0
    })

results.sort(key=lambda x: x['revenue'], reverse=True)

with open('september_2025_sales.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Category', 'TaxCode', 'Transactions', 'Quantity', 
                'Revenue', 'COGS', 'TaxAmount', 'GrossProfit', 'GP%'])
    
    for r in results:
        w.writerow([
            r['cat'], r['tax'], r['trans'], f"{r['qty']:.2f}",
            f"{r['revenue']:.2f}", f"{r['cogs']:.2f}", f"{r['tax_amt']:.2f}",
            f"{r['gp']:.2f}", f"{r['gp_pct']:.2f}"
        ])

print(f"\n✅ DONE! Saved to september_2025_sales.csv")

tot_rev = sum(r['revenue'] for r in results)
tot_gp = sum(r['gp'] for r in results)
tot_tax = sum(r['tax_amt'] for r in results)

print(f"\nRevenue: ${tot_rev:,.2f}")
print(f"GP:      ${tot_gp:,.2f} ({tot_gp/tot_rev*100:.1f}%)")
print(f"Tax:     ${tot_tax:,.2f}")

conn.close()
