#!/usr/bin/env python3
"""
Analyze duplicate NSF entries
"""

from database_pymssql import SQLServerConnection
db = SQLServerConnection()

# Check for duplicate NSF entries on a specific date
query = """
SELECT 
    'DC' as Source,
    ar.Date,
    ar.ID as RefNum,
    ar.OriginalAmount as Amount,
    'Direct Charge' as Type
FROM AccountReceivable ar
WHERE ar.CustomerID = 2058737683
  AND ar.Date = '2025-04-30'
  AND ar.TransactionNumber = 0

UNION ALL

SELECT 
    'ARH' as Source,
    arh.Date,
    arh.ID as RefNum,
    arh.Amount,
    arh.Comment as Type
FROM AccountReceivableHistory arh
INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID = 2058737683
  AND arh.Date = '2025-04-30'

UNION ALL

SELECT 
    'PMT' as Source,
    p.Time as Date,
    p.ID as RefNum,
    p.Amount,
    p.Comment as Type
FROM Payment p
WHERE p.CustomerID = 2058737683
  AND CAST(p.Time as DATE) = '2025-04-30'

ORDER BY Date, Amount
"""

df = db.execute_query(query, 'Check duplicates')
print('Transactions on 2025-04-30:')
print('-' * 80)
for _, row in df.iterrows():
    print(f'{row["Source"]:<5} Ref:{row["RefNum"]:<10} Amount: ${float(row["Amount"]):>10,.2f}  Type: {str(row["Type"])[:50]}')

print('\n\nNow checking April 24, 2025:')
print('-' * 80)

query2 = """
SELECT 
    'DC' as Source,
    ar.Date,
    ar.ID as RefNum,
    ar.OriginalAmount as Amount
FROM AccountReceivable ar
WHERE ar.CustomerID = 2058737683
  AND ar.Date = '2025-04-24'
  AND ar.TransactionNumber = 0

UNION ALL

SELECT 
    'ARH' as Source,
    arh.Date,
    arh.ID as RefNum,
    arh.Amount
FROM AccountReceivableHistory arh
INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID = 2058737683
  AND arh.Date = '2025-04-24'

ORDER BY Amount DESC
"""

df2 = db.execute_query(query2, 'Check April 24')
for _, row in df2.iterrows():
    print(f'{row["Source"]:<5} Ref:{row["RefNum"]:<10} Amount: ${float(row["Amount"]):>10,.2f}')

# Now let's understand the relationship
print('\n\nChecking AccountReceivable to ARHistory relationship:')
print('-' * 80)

query3 = """
SELECT TOP 10
    ar.ID as AR_ID,
    ar.OriginalAmount as AR_Amount,
    ar.Date as AR_Date,
    arh.ID as ARH_ID,
    arh.Amount as ARH_Amount,
    arh.Date as ARH_Date,
    arh.Type as ARH_Type,
    arh.Comment as ARH_Comment
FROM AccountReceivable ar
LEFT JOIN AccountReceivableHistory arh ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID = 2058737683
  AND ar.TransactionNumber = 0  -- Direct charges only
  AND ar.OriginalAmount = 11667.85  -- Specific NSF amount
ORDER BY ar.Date DESC
"""

df3 = db.execute_query(query3, 'Check AR to ARH relationship')
for _, row in df3.iterrows():
    print(f'AR #{row["AR_ID"]}: ${row["AR_Amount"]:,.2f} on {row["AR_Date"]}')
    print(f'  -> ARH #{row["ARH_ID"]}: ${row["ARH_Amount"]:,.2f} Type:{row["ARH_Type"]} Comment: {row["ARH_Comment"]}')