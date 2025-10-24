#!/usr/bin/env python3
"""Check September 2025 excise tax breakdown"""
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

# Simple query - just get the actual excise tax by category
query = """
SELECT
    cat.Name as CategoryName,
    pe.SubDescription3 as TaxType,
    COUNT(*) as item_count,
    SUM(te.Price * te.Quantity) as total_revenue,
    SUM(te.Cost * te.Quantity) as total_cogs,
    SUM(pe.PriceC) as actual_excise_tax
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
INNER JOIN Category cat ON i.CategoryID = cat.ID
INNER JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-09-01'
    AND te.TransactionTime < '2025-10-01'
    AND pe.PriceC IS NOT NULL
    AND pe.PriceC > 0
GROUP BY cat.Name, pe.SubDescription3
ORDER BY actual_excise_tax DESC
"""

print('='*110)
print('September 2025 Excise Tax Breakdown by Category & Tax Type')
print('='*110)
print(f'{"Category":<30} {"Tax Type":<15} {"Items":<8} {"Revenue":<12} {"COGS":<12} {"Excise Tax":<12} {"Tax %":<8}')
print('='*110)

result = execute_query(query)
total_revenue = 0
total_cogs = 0
total_tax = 0

for row in result:
    cat = row['CategoryName'][:29] if row['CategoryName'] else 'Unknown'
    tax_type = row['TaxType'][:14] if row['TaxType'] else 'N/A'
    items = row['item_count']
    revenue = float(row['total_revenue'] or 0)
    cogs = float(row['total_cogs'] or 0)
    tax = float(row['actual_excise_tax'] or 0)

    # Calculate effective tax rate
    if cogs > 0:
        tax_pct = (tax / cogs) * 100
    else:
        tax_pct = 0

    total_revenue += revenue
    total_cogs += cogs
    total_tax += tax

    print(f'{cat:<30} {tax_type:<15} {items:<8} ${revenue:>10,.0f} ${cogs:>10,.0f} ${tax:>10,.2f} {tax_pct:>6.1f}%')

print('='*110)
print(f'{"TOTALS":<30} {"":15} {"":8} ${total_revenue:>10,.0f} ${total_cogs:>10,.0f} ${total_tax:>10,.2f}')
print('='*110)

print(f'\nOverall effective tax rate: {(total_tax / total_cogs * 100) if total_cogs > 0 else 0:.2f}%')
print(f'Tax as % of revenue: {(total_tax / total_revenue * 100) if total_revenue > 0 else 0:.2f}%')
