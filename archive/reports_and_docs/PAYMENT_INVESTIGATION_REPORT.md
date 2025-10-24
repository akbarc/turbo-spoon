# Georgia Dashboard Payment Processing Investigation Report

**Date:** August 7, 2025  
**Author:** Claude Code Analysis  
**Database:** GAWDB (SQL Server 2008 R2)

## Executive Summary

This investigation analyzed the Georgia Dashboard database structure to understand payment processing, NSF handling, and AR (Accounts Receivable) creation. The analysis revealed clear business logic patterns and provided recommendations for proper collections tracking.

## Key Findings

### 1. Payment Method Analysis (TenderEntry.TenderID)

| TenderID | Description | Frequency | Total Amount | AR Creation Rate | Business Logic |
|----------|-------------|-----------|--------------|------------------|----------------|
| 5 | STORE CREDIT | 137,366 | $202.7M | 100% | Credit sales - always creates AR |
| 1 | CASH | 128,803 | $29.6M | 6.4% | Immediate payment - rare AR creation |
| 2 | CHECK | 58,614 | $191.8M | 1.0% | Immediate payment - minimal AR |
| 4 | DEBIT CARD | 21,498 | $19.1M | 2.4% | Immediate payment |
| 3 | CREDIT CARD | 8,624 | $8.2M | 4.1% | Immediate payment |
| 6 | MONEY ORDER | 3,916 | $5.0M | 32.7% | Some credit terms |
| 9 | DIRECT BANK DEPOSIT | 847 | $11.1M | 16.7% | Mixed payment terms |

### 2. NSF Check Investigation

**Finding:** Minimal NSF activity in recent data. Only 1 NSF-related transaction found in recent history:
- Transaction 181370: $319.98 return with comment "CUSTOMER RETURNED THE PRODUCT"
- 15 negative check transactions found (2022-2025), indicating returned checks
- Most negative amounts are refunds/returns, not NSF-specific

### 3. Store Credit and AR Relationship

**Critical Discovery:** Store credit transactions (TenderID 5) have a **100% AR creation rate**
- Store Credit Usage: 11,780 transactions, $25.3M
- Store Credit Refunds: 692 transactions, -$553K
- All store credit transactions automatically create AR entries
- Largest outstanding AR: $298,873.87 (N ALI ENTERPRISES INC, 587 days outstanding)

### 4. Payment vs TenderEntry Comparison (Last Year)

| Source | Record Count | Total Amount | Unique Customers |
|--------|--------------|--------------|------------------|
| Payment Table | 6,909 | $26.3M | 479 |
| TenderEntry (excl Store Credit) | 4,853 | $4.9M | 454 |
| All TenderEntry Payments | 18,518 | $29.5M | 680 |

**Key Insight:** Payment table represents customer payments against existing AR, while TenderEntry represents point-of-sale transactions.

## Business Logic Recommendations

### AR Creation Logic

```sql
-- Recommended AR Creation Logic
CASE 
    WHEN te.TenderID = 5 THEN 'CREATE_AR'  -- Store Credit always creates AR
    WHEN te.TenderID = 2 AND t.Comment LIKE '%terms%' THEN 'CREATE_AR'  -- Check with terms
    WHEN te.TenderID = 1 AND t.Comment LIKE '%layaway%' THEN 'CREATE_AR'  -- Cash layaway
    ELSE 'IMMEDIATE_PAYMENT'  -- All other payments are immediate
END as ar_logic
```

### Collections Calculation

```sql
-- Total Collections Query
SELECT 
    'Customer Payments Against AR' as collection_type,
    SUM(p.Amount) as total_amount
FROM dbo.Payment p
WHERE p.Time >= @start_date AND p.Time <= @end_date

UNION ALL

SELECT 
    'Immediate Cash Collections' as collection_type,
    SUM(te.Amount) as total_amount
FROM dbo.TenderEntry te
JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
WHERE t.Time >= @start_date AND t.Time <= @end_date
AND te.TenderID != 5  -- Exclude store credit
AND te.Amount > 0     -- Only positive payments
```

### NSF Monitoring Query

```sql
-- NSF Check Monitoring
SELECT 
    te.TransactionNumber,
    te.Amount,
    t.Time,
    t.Comment,
    c.Company,
    c.FirstName,
    c.LastName
FROM dbo.TenderEntry te
JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
WHERE te.TenderID = 2  -- CHECK payments
AND (
    t.Comment LIKE '%NSF%'
    OR t.Comment LIKE '%returned%'
    OR t.Comment LIKE '%bounced%'
    OR t.Comment LIKE '%insufficient%'
    OR te.Amount < 0  -- Negative check amounts
)
ORDER BY t.Time DESC
```

### Store Credit AR Aging

```sql
-- Store Credit AR Aging Analysis
SELECT 
    c.Company,
    c.FirstName,
    c.LastName,
    ar.TransactionNumber,
    ar.Date,
    ar.OriginalAmount,
    ar.Balance,
    DATEDIFF(day, ar.Date, GETDATE()) as days_outstanding,
    CASE 
        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 days'
        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 days'
        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END as aging_bucket
FROM dbo.AccountReceivable ar
JOIN dbo.Customer c ON ar.CustomerID = c.ID
JOIN dbo.TenderEntry te ON ar.TransactionNumber = te.TransactionNumber
WHERE te.TenderID = 5  -- Store Credit
AND ar.Balance > 0
ORDER BY ar.Balance DESC
```

## Implementation Recommendations

### 1. Collections Dashboard

- **Customer Payments:** Use `dbo.Payment` table for payments against existing AR
- **Immediate Collections:** Use `dbo.TenderEntry` (excluding TenderID 5) for cash transactions
- **Total Collections:** Sum of both Payment and immediate TenderEntry amounts

### 2. AR Management

- **Store Credit:** Monitor aging closely as 100% creates AR
- **High-Risk Customers:** Track customers with large outstanding store credit AR
- **Credit Limits:** Implement controls on store credit transactions

### 3. Payment Method Analysis

```sql
-- Payment Method Performance Dashboard
SELECT 
    te.TenderID,
    te.Description as payment_method,
    COUNT(*) as transaction_count,
    SUM(te.Amount) as total_amount,
    AVG(te.Amount) as avg_amount,
    COUNT(CASE WHEN ar.TransactionNumber IS NOT NULL THEN 1 END) as ar_transactions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (COUNT(CASE WHEN ar.TransactionNumber IS NOT NULL THEN 1 END) * 100.0 / COUNT(*))
        ELSE 0 
    END as ar_percentage
FROM dbo.TenderEntry te
JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN dbo.AccountReceivable ar ON t.TransactionNumber = ar.TransactionNumber
WHERE t.Time >= DATEADD(month, -12, GETDATE())
GROUP BY te.TenderID, te.Description
ORDER BY total_amount DESC
```

## Table Structure Summary

### dbo.Payment
- **Primary Purpose:** Customer payments against existing AR
- **Key Columns:** CustomerID, Time, Amount, Comment
- **Note:** Uses 'Time' column, not 'Date'

### dbo.TenderEntry
- **Primary Purpose:** Point-of-sale payment methods
- **Key Columns:** TransactionNumber, TenderID, Amount, Description
- **Critical:** TenderID 5 (Store Credit) creates AR 100% of the time

### dbo.AccountReceivable
- **Primary Purpose:** Outstanding customer balances
- **Key Columns:** CustomerID, TransactionNumber, Balance, Date, DueDate
- **Business Rule:** Automatically created for store credit transactions

## Risk Areas Identified

1. **Large Outstanding Store Credit AR:** $298K+ balances with 500+ days outstanding
2. **Minimal NSF Monitoring:** Current NSF detection may be insufficient
3. **Credit Risk:** Store credit customers with large outstanding balances need monitoring

## Conclusion

The Georgia Dashboard database has clear business logic for payment processing:
- Store credit transactions always create AR (credit sales)
- Most other payment methods are immediate (cash transactions)
- Payment table tracks customer payments against existing AR
- TenderEntry tracks point-of-sale payment methods

The recommended implementation separates immediate collections from credit sales tracking, providing accurate financial reporting and AR management.