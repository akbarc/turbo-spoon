#!/usr/bin/env python3
"""
Trace the balance calculation issue step by step
"""

from database_pymssql import SQLServerConnection
import pandas as pd

db = SQLServerConnection()

# First, get the correct customer ID
query = """
SELECT ID, AccountNumber, Company 
FROM Customer 
WHERE Company LIKE '%5 STAR%'
"""
customers = db.execute_query(query, "Find customer")
print("Customers found:")
for _, c in customers.iterrows():
    print(f"ID: {c['ID']}, Account: {c['AccountNumber']}, Name: {c['Company']}")

# Use the correct ID
customer_id = 4915  # Based on previous documentation

print(f"\nUsing Customer ID: {customer_id}")

# Now let's trace specific transactions
print("\n" + "="*80)
print("CHECKING FOR DUPLICATE NSF ENTRIES")
print("="*80)

# Look at a specific NSF amount: $11,667.85
query = """
-- Direct Charges
SELECT 
    'DC-AR' as Source,
    ar.Date,
    ar.ID,
    ar.OriginalAmount as Amount,
    ar.TransactionNumber,
    'Direct AR Entry' as Description
FROM AccountReceivable ar
WHERE ar.CustomerID = 4915
  AND ar.OriginalAmount = 11667.85

UNION ALL

-- AR History 
SELECT 
    'ARH' as Source,
    arh.Date,
    arh.ID,
    arh.Amount,
    arh.AccountReceivableID as TransactionNumber,
    arh.Comment as Description
FROM AccountReceivableHistory arh
INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID = 4915
  AND arh.Amount = 11667.85

UNION ALL

-- Payments
SELECT 
    'PMT' as Source,
    p.Time as Date,
    p.ID,
    p.Amount,
    0 as TransactionNumber,
    p.Comment as Description
FROM Payment p
WHERE p.CustomerID = 4915
  AND p.Amount = 11667.85

ORDER BY Date, Source
"""

df = db.execute_query(query, "Check $11,667.85 transactions")
print(f"\nAll instances of $11,667.85:")
print("-" * 80)
for _, row in df.iterrows():
    print(f"{row['Date'].strftime('%Y-%m-%d')} | {row['Source']:<7} | ID:{row['ID']:<8} | ${row['Amount']:>10,.2f} | {str(row['Description'])[:50]}")

# Now check the running total if we include everything
print("\n" + "="*80)
print("CALCULATING BALANCE WITH ALL SOURCES")
print("="*80)

query = """
WITH AllTransactions AS (
    -- Sales
    SELECT t.Time as Date, 'SALE' as Type, t.Total as Amount
    FROM [Transaction] t
    WHERE t.CustomerID = 4915
    
    UNION ALL
    
    -- ALL Payments (including NSF)
    SELECT p.Time, 'PMT', -p.Amount
    FROM Payment p
    WHERE p.CustomerID = 4915
    
    UNION ALL
    
    -- Direct AR Charges
    SELECT ar.Date, 'DC', ar.OriginalAmount
    FROM AccountReceivable ar
    WHERE ar.CustomerID = 4915 AND ar.TransactionNumber = 0
    
    UNION ALL
    
    -- AR History adjustments
    SELECT arh.Date, 'ARH', arh.Amount
    FROM AccountReceivableHistory arh
    INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = 4915
)
SELECT 
    COUNT(*) as TotalCount,
    SUM(Amount) as TotalSum,
    SUM(CASE WHEN Type = 'SALE' THEN Amount ELSE 0 END) as Sales,
    SUM(CASE WHEN Type = 'PMT' THEN Amount ELSE 0 END) as Payments,
    SUM(CASE WHEN Type = 'DC' THEN Amount ELSE 0 END) as DirectCharges,
    SUM(CASE WHEN Type = 'ARH' THEN Amount ELSE 0 END) as ARHistory
FROM AllTransactions
"""

totals = db.execute_query(query, "Calculate totals")
if not totals.empty:
    row = totals.iloc[0]
    print(f"Total transactions: {row['TotalCount']}")
    print(f"Sales total: ${row['Sales']:,.2f}")
    print(f"Payments total: ${row['Payments']:,.2f}")
    print(f"Direct Charges total: ${row['DirectCharges']:,.2f}")
    print(f"AR History total: ${row['ARHistory']:,.2f}")
    print(f"CALCULATED BALANCE: ${row['TotalSum']:,.2f}")

# Get actual AR balance
query = "SELECT AccountBalance FROM Customer WHERE ID = 4915"
actual = db.execute_query(query, "Get actual balance")
if not actual.empty:
    print(f"ACTUAL AR BALANCE: ${actual.iloc[0]['AccountBalance']:,.2f}")
    print(f"DIFFERENCE: ${row['TotalSum'] - actual.iloc[0]['AccountBalance']:,.2f}")

print("\n" + "="*80)
print("UNDERSTANDING THE DUPLICATION")
print("="*80)

# Check relationship between AR and ARH
query = """
SELECT TOP 5
    ar.ID as AR_ID,
    ar.Date as AR_Date,
    ar.OriginalAmount as AR_Amount,
    COUNT(arh.ID) as ARH_Count,
    SUM(arh.Amount) as ARH_Total
FROM AccountReceivable ar
LEFT JOIN AccountReceivableHistory arh ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID = 4915
  AND ar.TransactionNumber = 0
  AND ar.OriginalAmount > 1000
GROUP BY ar.ID, ar.Date, ar.OriginalAmount
ORDER BY ar.Date DESC
"""

relationships = db.execute_query(query, "Check AR to ARH relationship")
print("Direct Charges and their AR History entries:")
print("-" * 80)
for _, row in relationships.iterrows():
    print(f"AR #{row['AR_ID']} ({row['AR_Date'].strftime('%Y-%m-%d')}): ${row['AR_Amount']:,.2f}")
    print(f"  -> {row['ARH_Count']} ARH entries totaling ${row['ARH_Total']:,.2f}")
    if row['ARH_Total'] == row['AR_Amount']:
        print("  -> DUPLICATE! Same amount in both AR and ARH")