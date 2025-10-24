#!/usr/bin/env python3
"""Analyze PUExciseEntry table structure and relationship to items"""
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

print("="*80)
print("PUExciseEntry Table Analysis")
print("="*80)

# 1. Check table structure
print("\n1. Table Columns:")
print("-"*80)
query1 = """
SELECT TOP 1 * FROM PUExciseEntry
"""
result = execute_query(query1)
if result:
    print("Columns:", sorted(result[0].keys()))

# 2. Check if excise tax is consistent per item
print("\n2. Excise Tax Consistency per Item (checking variance):")
print("-"*80)
query2 = """
SELECT TOP 20
    pe.ItemID,
    i.ItemLookupCode,
    i.Description,
    COUNT(DISTINCT pe.PriceC) as unique_tax_amounts,
    MIN(pe.PriceC) as min_tax,
    MAX(pe.PriceC) as max_tax,
    AVG(pe.PriceC) as avg_tax,
    COUNT(*) as transaction_count,
    pe.SubDescription3 as tax_type
FROM PUExciseEntry pe
LEFT JOIN Item i ON pe.ItemID = i.ID
WHERE pe.PriceC > 0
GROUP BY pe.ItemID, i.ItemLookupCode, i.Description, pe.SubDescription3
ORDER BY transaction_count DESC
"""
result = execute_query(query2)
print(f"{'ItemID':<10} {'SKU':<15} {'Description':<30} {'TaxType':<12} {'Unique$':<8} {'Avg Tax':<10} {'Count':<8}")
print("-"*80)
for row in result[:20]:
    unique = row['unique_tax_amounts']
    avg_tax = float(row['avg_tax']) if row['avg_tax'] else 0
    print(f"{str(row['ItemID']):<10} {str(row['ItemLookupCode'] or '')[:14]:<15} {str(row['Description'] or '')[:29]:<30} {str(row['tax_type'] or '')[:11]:<12} {str(unique):<8} ${avg_tax:<9.2f} {row['transaction_count']:<8}")

# 3. Check if we can create a simple lookup
print("\n3. Can we create ItemID → ExciseTax lookup?")
print("-"*80)
query3 = """
SELECT
    COUNT(DISTINCT ItemID) as unique_items,
    COUNT(DISTINCT CONCAT(ItemID, '|', CAST(PriceC AS VARCHAR))) as unique_item_tax_combos,
    CASE
        WHEN COUNT(DISTINCT ItemID) = COUNT(DISTINCT CONCAT(ItemID, '|', CAST(PriceC AS VARCHAR)))
        THEN 'YES - One tax amount per item'
        ELSE 'NO - Tax varies per item'
    END as can_use_simple_lookup
FROM PUExciseEntry
WHERE PriceC > 0
"""
result = execute_query(query3)
if result:
    for k, v in result[0].items():
        print(f"{k}: {v}")

# 4. Check if tax type varies per item
print("\n4. Do items have multiple tax types?")
print("-"*80)
query4 = """
SELECT TOP 10
    ItemID,
    COUNT(DISTINCT SubDescription3) as tax_type_count,
    STRING_AGG(DISTINCT SubDescription3, ', ') as tax_types
FROM PUExciseEntry
WHERE SubDescription3 IS NOT NULL
GROUP BY ItemID
HAVING COUNT(DISTINCT SubDescription3) > 1
ORDER BY tax_type_count DESC
"""
result = execute_query(query4)
if result:
    print(f"Items with multiple tax types: {len(result)}")
    for row in result[:5]:
        print(f"  ItemID {row['ItemID']}: {row['tax_type_count']} types - {row['tax_types']}")
else:
    print("No items found with multiple tax types")

# 5. Sample of actual excise entries
print("\n5. Sample Excise Entries (showing variation):")
print("-"*80)
query5 = """
SELECT TOP 10
    pe.ItemID,
    i.ItemLookupCode,
    i.Description,
    pe.PriceC as excise_tax,
    pe.SubDescription3 as tax_type,
    pe.Quantity,
    te.Price as sale_price,
    te.TransactionTime
FROM PUExciseEntry pe
LEFT JOIN Item i ON pe.ItemID = i.ID
LEFT JOIN TransactionEntry te ON pe.TransactionEntryID = te.ID
WHERE pe.PriceC > 0
ORDER BY pe.TransactionTime DESC
"""
result = execute_query(query5)
for row in result:
    print(f"Item {row['ItemID']}: ${row['excise_tax']:.2f} tax on ${row['sale_price']:.2f} sale ({row['tax_type']})")

print("\n" + "="*80)
print("Analysis Complete")
print("="*80)
