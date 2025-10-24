#!/usr/bin/env python3
"""
Analyze returns and adjustments for 5 Star Food Mart
"""

from database_pymssql import SQLServerConnection
import pandas as pd

db = SQLServerConnection()

# Check for returns in Transaction table (negative amounts)
print('=== ANALYZING RETURNS FOR 5 STAR FOOD MART ===')
query = '''
SELECT TOP 20
    t.TransactionNumber,
    t.Time,
    t.Total,
    t.Comment,
    t.SalesRepID,
    CASE 
        WHEN t.Total < 0 THEN 'RETURN'
        ELSE 'SALE'
    END as TransactionType
FROM [Transaction] t
WHERE t.CustomerID IN (4915, 5334)
AND t.Total < 0
ORDER BY t.Time DESC
'''
returns = db.execute_query(query, 'Find return transactions')
print(f'Found {len(returns)} return transactions (negative totals)')

if not returns.empty:
    print('\n=== SAMPLE RETURNS ===')
    for _, r in returns.head(5).iterrows():
        print(f"Trans #{r['TransactionNumber']}, Date: {r['Time']}, Amount: ${r['Total']:.2f}, Comment: {r['Comment'] or '[none]'}")

# Check AccountReceivableHistory for return-related adjustments
print('\n=== RETURN-RELATED ADJUSTMENTS IN AR HISTORY ===')
query = '''
SELECT TOP 30
    arh.Date,
    arh.Amount,
    arh.Comment,
    ar.TransactionNumber,
    CASE 
        WHEN arh.Comment LIKE '%RETURN%' OR arh.Comment LIKE '%RTN%' OR arh.Comment LIKE '%RET%' THEN 'RETURN'
        WHEN arh.Comment LIKE '%CREDIT%' AND arh.Amount < 0 THEN 'CREDIT/RETURN'
        WHEN arh.Amount < 0 AND ar.TransactionNumber IN (
            SELECT TransactionNumber FROM [Transaction] WHERE Total < 0
        ) THEN 'RETURN_TRANSACTION'
        ELSE 'OTHER'
    END as AdjustmentType
FROM AccountReceivableHistory arh
JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID IN (4915, 5334)
AND (
    arh.Comment LIKE '%RETURN%' 
    OR arh.Comment LIKE '%RTN%'
    OR arh.Comment LIKE '%RET%'
    OR arh.Comment LIKE '%CREDIT%'
    OR arh.Amount < 0
)
ORDER BY arh.Date DESC
'''
ar_returns = db.execute_query(query, 'Find return adjustments')
print(f'Found {len(ar_returns)} potential return-related adjustments')

if not ar_returns.empty:
    # Group by type
    type_counts = ar_returns['AdjustmentType'].value_counts()
    print('\n=== RETURN ADJUSTMENT TYPES ===')
    for adj_type, count in type_counts.items():
        print(f'{adj_type}: {count}')
    
    print('\n=== SAMPLE RETURN ADJUSTMENTS ===')
    for _, adj in ar_returns.head(10).iterrows():
        print(f"Date: {adj['Date']}, Amount: ${adj['Amount']:.2f}, Type: {adj['AdjustmentType']}, Comment: {adj['Comment'] or '[none]'}")

# Check for NSF returns specifically
print('\n=== NSF AND RETURNED CHECK ANALYSIS ===')
query = '''
SELECT 
    COUNT(CASE WHEN Comment LIKE '%NSF%' THEN 1 END) as NSF_Count,
    SUM(CASE WHEN Comment LIKE '%NSF%' THEN Amount ELSE 0 END) as NSF_Total,
    COUNT(CASE WHEN Comment LIKE '%RETURN%' THEN 1 END) as Return_Count,
    SUM(CASE WHEN Comment LIKE '%RETURN%' THEN Amount ELSE 0 END) as Return_Total
FROM Payment
WHERE CustomerID IN (4915, 5334)
'''
nsf_summary = db.execute_query(query, 'NSF and return summary')
if not nsf_summary.empty:
    row = nsf_summary.iloc[0]
    print(f"NSF Payments: {int(row['NSF_Count'])}, Total: ${row['NSF_Total']:.2f}")
    print(f"Returned Payments: {int(row['Return_Count'])}, Total: ${row['Return_Total']:.2f}")

# Check all negative transactions to understand credits/returns
print('\n=== ALL NEGATIVE TRANSACTIONS (CREDITS/RETURNS) ===')
query = '''
SELECT 
    COUNT(*) as Count,
    SUM(Total) as TotalAmount,
    MIN(Total) as LargestReturn,
    MAX(Time) as MostRecentDate
FROM [Transaction]
WHERE CustomerID IN (4915, 5334)
AND Total < 0
'''
neg_trans = db.execute_query(query, 'Negative transaction summary')
if not neg_trans.empty:
    row = neg_trans.iloc[0]
    print(f"Total Returns/Credits: {int(row['Count'])}")
    print(f"Total Return Amount: ${row['TotalAmount']:.2f}")
    print(f"Largest Return: ${row['LargestReturn']:.2f}")
    print(f"Most Recent: {row['MostRecentDate']}")

# Look for all types of adjustments in AR History
print('\n=== ALL AR HISTORY PATTERNS FOR 5 STAR ===')
query = '''
SELECT 
    CASE 
        WHEN arh.Comment LIKE '%NSF%' THEN 'NSF Related'
        WHEN arh.Comment LIKE '%RETURN%' OR arh.Comment LIKE '%RTN%' THEN 'Return'
        WHEN arh.Comment LIKE '%FEE%' THEN 'Fee'
        WHEN arh.Comment LIKE '%CREDIT%' THEN 'Credit'
        WHEN arh.Comment LIKE '%DEBIT%' THEN 'Debit'
        WHEN arh.Comment LIKE '%Payment%' THEN 'Payment Application'
        WHEN arh.Amount < 0 THEN 'Credit/Reduction'
        WHEN arh.Amount > 0 THEN 'Charge/Addition'
        ELSE 'Other'
    END as Category,
    COUNT(*) as Count,
    SUM(arh.Amount) as TotalAmount
FROM AccountReceivableHistory arh
JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID IN (4915, 5334)
GROUP BY 
    CASE 
        WHEN arh.Comment LIKE '%NSF%' THEN 'NSF Related'
        WHEN arh.Comment LIKE '%RETURN%' OR arh.Comment LIKE '%RTN%' THEN 'Return'
        WHEN arh.Comment LIKE '%FEE%' THEN 'Fee'
        WHEN arh.Comment LIKE '%CREDIT%' THEN 'Credit'
        WHEN arh.Comment LIKE '%DEBIT%' THEN 'Debit'
        WHEN arh.Comment LIKE '%Payment%' THEN 'Payment Application'
        WHEN arh.Amount < 0 THEN 'Credit/Reduction'
        WHEN arh.Amount > 0 THEN 'Charge/Addition'
        ELSE 'Other'
    END
ORDER BY Count DESC
'''
ar_patterns = db.execute_query(query, 'AR History patterns')
if not ar_patterns.empty:
    print('\n=== AR ADJUSTMENT CATEGORY SUMMARY ===')
    for _, row in ar_patterns.iterrows():
        print(f"{row['Category']:20s}: {int(row['Count']):4d} items, Total: ${row['TotalAmount']:,.2f}")

db.close()