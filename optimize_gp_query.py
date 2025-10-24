#!/usr/bin/env python3
"""
Test optimized GP category query that bypasses the slow view
Query the base tables directly with proper indexes
"""
import sys
import time
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

print("="*60)
print("Testing Optimized Direct Query (bypassing PUVIEW)")
print("="*60)

# Option 1: Query base tables directly with category join
query = """
SELECT
    cat.Name as CategoryName,
    COUNT(*) as item_count,
    SUM(te.Price * te.Quantity) as revenue,
    SUM(te.Cost * te.Quantity) as cogs,
    SUM(COALESCE(pe.PriceC, 0)) as excise_tax,
    SUM((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0)) as gross_profit
FROM [dbo].[Transaction] t WITH (NOLOCK)
INNER JOIN [dbo].[TransactionEntry] te WITH (NOLOCK) ON t.TransactionNumber = te.TransactionNumber
INNER JOIN [dbo].[Item] i WITH (NOLOCK) ON te.ItemID = i.ID
INNER JOIN [dbo].[Category] cat WITH (NOLOCK) ON i.CategoryID = cat.ID
LEFT JOIN [dbo].[PUExciseEntry] pe WITH (NOLOCK) ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-01-01'
    AND te.TransactionTime < '2025-10-16'
    AND te.Quantity != 0
GROUP BY cat.ID, cat.Name
ORDER BY gross_profit DESC
"""

print("\nRunning query with NOLOCK hints...")
print("This queries base tables directly instead of the PUVIEW view")
print()

start = time.time()
try:
    result = execute_query(query)
    elapsed = time.time() - start

    print(f"✅ Query completed in {elapsed:.2f} seconds")
    print(f"Categories returned: {len(result)}")
    print(f"\nTop 10 categories by GP:")
    print("-" * 80)
    for i, row in enumerate(result[:10], 1):
        gp_margin = (float(row['gross_profit']) / float(row['revenue']) * 100) if row['revenue'] and row['revenue'] > 0 else 0
        print(f"{i:2}. {row['CategoryName']:30} GP: ${row['gross_profit']:>12,.0f} ({gp_margin:5.1f}%)")

    print("\n" + "="*60)
    if elapsed < 5:
        print("✅ FAST! This approach works!")
        print("We can use this instead of pre-populating GP_Daily_Summary")
    elif elapsed < 15:
        print("⚠️  Acceptable speed. Might benefit from indexes.")
    else:
        print("❌ Still too slow. Pre-aggregation is better.")

except Exception as e:
    elapsed = time.time() - start
    print(f"❌ Query failed after {elapsed:.2f} seconds")
    print(f"Error: {e}")
