# Sales Investigation Report: Root Cause Analysis

## Executive Summary

**PROBLEM IDENTIFIED**: The AI SQL query assistant is generating unrealistic sales figures ($15M+ per week) due to a fundamental SQL query construction error.

**ROOT CAUSE**: The AI is incorrectly using `SUM(t.Total)` while joining the Transaction table to TransactionEntry table, causing transaction totals to be multiplied by the number of line items in each transaction.

**IMPACT**: Sales figures are inflated by approximately **27x** the actual amounts.

---

## Investigation Results

### Actual vs Reported Sales Figures

| Metric | AI Generated (Incorrect) | Actual (Correct) | Inflation Factor |
|--------|-------------------------|------------------|------------------|
| Weekly Sales | $27,033,444.46 | $987,032.50 | 27.39x |
| Transaction Count | 343 | 343 | Correct |
| Customer Count | 211 | 211 | Correct |

### Database Structure Confirmed

- **Database**: GAWDB (SQL Server 2008 R2)
- **Server**: SOSERVER (10.1.10.105)
- **Data Range**: 2012-12-07 to 2025-08-07 (234,312 total transactions)
- **Tables Involved**:
  - `[dbo].[Transaction]` - Master transaction records with totals
  - `dbo.TransactionEntry` - Line item details for each transaction

### Technical Root Cause Analysis

#### The Problem Query Pattern
```sql
-- PROBLEMATIC - This inflates totals
SELECT SUM(t.Total) as total_sales
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
WHERE t.Time >= DATEADD(day, -7, GETDATE())
```

#### Why This Happens
1. Each transaction can have multiple line items (TransactionEntry records)
2. When joining Transaction to TransactionEntry, the `t.Total` value gets repeated for each line item
3. `SUM(t.Total)` then adds up the transaction total multiple times
4. Example: A $100 transaction with 5 line items becomes $500 in the sum

#### Proof of Inflation
Sample transaction analysis shows:
- Transaction #234305: $9,491.32 actual → $1,053,536.52 inflated (111 line items)
- Overall inflation factor: **19.92x** for multi-line transactions

### Correct Query Patterns

#### For Transaction-Level Totals (Use This)
```sql
-- CORRECT - No unnecessary JOIN
SELECT SUM(t.Total) as total_sales
FROM [dbo].[Transaction] t
WHERE t.Time >= DATEADD(day, -7, GETDATE())
```

#### For Line-Item Analysis (When JOIN is Needed)
```sql
-- VALID - When calculating line item metrics
SELECT SUM(te.Price * te.Quantity) as line_item_sales
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
WHERE t.Time >= DATEADD(day, -7, GETDATE())
```

---

## Data Quality Assessment

### No Major Data Issues Found
- ✅ Date ranges are calculated correctly with DATEADD functions
- ✅ No significant duplicate transactions detected
- ✅ High-value transactions (>$10K) are legitimate wholesale purchases
- ✅ Daily sales patterns are consistent and realistic
- ✅ Transaction counts match expected convenience store volumes

### Realistic Sales Figures
- **Current week**: $987,032.50 (7,250 transactions)
- **Previous week**: $659,603.73 (7,017 transactions) 
- **Average daily sales**: $109,775.75
- **Weekly projection**: $768,430.24

These figures are reasonable for a convenience store operation.

---

## AI Query Validation Issues

The AI assistant's validation system detected the problem but couldn't consistently fix it:

1. **Question 1**: Detected inflated totals, attempted correction, still produced $15M+ figures
2. **Question 2**: Multiple correction attempts, continued inflation issues
3. **Question 3**: Reported $24M+ weekly sales 
4. **Question 4**: Finally produced correct figures ($550K-$798K range)
5. **Question 5**: Produced correct figure ($550K)

**Pattern**: The AI validation works but the query correction logic is inconsistent.

---

## Recommendations

### Immediate Actions

1. **Update AI Schema Documentation**
   - Emphasize when JOINs to TransactionEntry are appropriate
   - Provide clear examples of correct vs incorrect patterns
   - Add warnings about SUM(t.Total) with TransactionEntry JOINs

2. **Strengthen Validation Rules**
   - Flag any query using `SUM(t.Total)` with TransactionEntry JOIN
   - Add business logic validation (weekly sales >$5M = suspicious)
   - Implement automatic query pattern detection

3. **Query Template Fixes**
   - Transaction-level summaries: Use Transaction table only
   - Line-item analysis: Use TransactionEntry with appropriate metrics
   - Gross profit calculations: JOIN required with proper cost uplifts

### Technical Implementation

```sql
-- TEMPLATE: Transaction Level Summary
SELECT 
    SUM(t.Total) as total_sales,
    COUNT(DISTINCT t.TransactionNumber) as transactions
FROM [dbo].[Transaction] t
WHERE [date_filter]

-- TEMPLATE: Line Item Analysis  
SELECT 
    SUM(te.Price * te.Quantity) as line_item_sales,
    COUNT(DISTINCT t.TransactionNumber) as transactions
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
WHERE [date_filter]
```

### Long-term Monitoring

- Track AI query validation success rates
- Monitor for inflation patterns in generated queries
- Regular spot-checks of AI-generated financial reports
- User feedback loop for detecting unrealistic figures

---

## Conclusion

The investigation successfully identified the root cause of unrealistic sales figures in the AI SQL assistant. The problem is technical rather than data-related:

- **Data Quality**: ✅ Good - No corruption or duplicates
- **Query Logic**: ❌ Flawed - Unnecessary JOINs causing inflation
- **Validation**: ⚠️ Partial - Detects issues but inconsistent fixes

**Impact**: By fixing the query generation logic, sales figures will drop from unrealistic $15M+ weekly to realistic ~$750K-$1M weekly figures, providing accurate business intelligence for decision-making.

---

*Investigation completed on 2025-08-07*  
*Database: GAWDB on SOSERVER*  
*Investigation scripts: investigate_sales.py, test_ai_weekly_sales.py, sales_problem_analysis.py*