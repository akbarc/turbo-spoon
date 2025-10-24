# Customer Balance Calculation Methodology
**Based on Analysis of 5 Star Food Mart Somani (Customer ID 4915)**

## Executive Summary
This document explains how to properly calculate a customer's current balance by analyzing all transaction types throughout the account's lifetime. The methodology was validated using 5 Star Food Mart Somani's complete transaction history spanning from 2022 to 2025.

## Key Findings

### Customer Overview
- **Customer**: 5 Star Food Mart LLC - Sameer Somani
- **Customer ID**: 4915  
- **Account Number**: 2058737683
- **Current AR Balance**: $43,424.87

### Transaction Summary
- **Total Invoiced Amount**: $221,633.95 (from Transaction table)
- **Total Payments Received**: $392,819.31 (from Payment table)  
- **Total AR Records**: 150 (spanning 3+ years)
- **Active AR Records**: 15 outstanding invoices
- **Paid AR Records**: 135 fully paid invoices

## Balance Calculation Methods

### Method 1: Simple Calculation (❌ INCORRECT)
```
Simple Balance = Total Invoiced - Total Payments
Simple Balance = $221,633.95 - $392,819.31 = -$171,185.36
```
**Why this is wrong**: This doesn't account for adjustments, NSFs, PDs, and other AR movements.

### Method 2: AR History Calculation (✅ CORRECT)
```
Current AR Balance = Sum of all AR History entries
Current AR Balance = $43,424.87
```
**Why this is correct**: AR History tracks ALL movements including invoices, payments, adjustments, NSFs, transfers, etc.

## Detailed Analysis of AR History

### Transaction Types Found:
1. **Invoice Created (Type 0)**: Regular sales transactions
2. **Adjustments (Type 1)**: Balance corrections
3. **Payment Applied (Type 2)**: Customer payments applied to specific invoices
4. **Transfer/NSF (Type 3)**: Non-sufficient funds, returned checks
5. **Other (Type 5)**: NSF fees, collection fees, returned check fees

### Key Insights from 5 Star Food Mart Somani:

#### NSF (Non-Sufficient Funds) Pattern:
- Multiple returned checks with $65 NSF fees
- Pattern: Check returned → NSF fee added → Customer pays back both amounts
- Example: Check #22166 for $2,500 returned + $65 NSF fee = $2,565 added to AR

#### Partial Payments:
- Invoice #228377: Original $5,601.72, Paid $249.37, Balance $5,352.35
- Demonstrates how payments can be partially applied to specific invoices

#### Collection Activities:
- $5,664.11 in collection fees added on 2025-07-21
- $1,842.17 "190 FUEL BALANCE" adjustment

## Current Outstanding Balance Breakdown

### Active AR Records (15 total):
1. **Real Invoices** (2 records):
   - Invoice #228377: $5,352.35 (partially paid)
   - Invoice #230079: $3,556.57 (unpaid)
   - Invoice #230792: -$1,157.55 (credit/adjustment)

2. **NSF-Related** (12 records):
   - Various returned checks and NSF fees
   - Range from $45.00 to $11,667.85

3. **Collection Fees** (2 records):
   - $1,842.17 fuel balance
   - $5,664.11 collection fees

## How to Properly Calculate Customer Balance

### Step-by-Step Process:

1. **Start with $0.00 balance**

2. **Process each AR History entry chronologically**:
   ```sql
   SELECT arh.*, ar.TransactionNumber
   FROM AccountReceivableHistory arh
   LEFT JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID  
   WHERE ar.CustomerID = [CUSTOMER_ID]
   ORDER BY arh.Date ASC
   ```

3. **Apply each entry to running balance**:
   - **Type 0 (Invoice Created)**: Add amount (increases balance)
   - **Type 1 (Adjustment)**: Add/subtract amount as specified
   - **Type 2 (Payment Applied)**: Subtract amount (decreases balance)
   - **Type 3 (Transfer/NSF)**: Add amount (increases balance)
   - **Type 5 (Other)**: Add amount (usually fees, increases balance)

4. **Final result should match current AR balance**

### Validation Query:
```sql
-- This should equal the sum of all current AR.Balance records
SELECT SUM(arh.Amount) as CalculatedBalance
FROM AccountReceivableHistory arh
LEFT JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
WHERE ar.CustomerID = [CUSTOMER_ID]

-- Compare with:
SELECT SUM(Balance) as CurrentARBalance  
FROM AccountReceivable
WHERE CustomerID = [CUSTOMER_ID]
```

## Understanding Different Transaction Types

### 1. Regular Sales Transactions
- Appear in `Transaction` table with transaction numbers
- Create corresponding `AccountReceivable` records
- Generate `AccountReceivableHistory` Type 0 entries

### 2. Payments  
- Recorded in `Payment` table
- Applied to specific AR records via `AccountReceivableHistory` Type 2
- Can be partial payments (reducing but not eliminating AR balance)

### 3. NSF (Non-Sufficient Funds)
- Customer's check bounces
- Original payment is reversed (increases AR balance)
- NSF fee added (usually $65, increases AR balance further)
- Creates `AccountReceivableHistory` Type 5 entries

### 4. Adjustments
- Manual corrections to customer balance
- Can be positive (increase balance) or negative (decrease balance)
- Creates `AccountReceivableHistory` Type 1 entries

### 5. Collection Activities
- Additional fees for collection efforts
- Creates `AccountReceivableHistory` Type 5 entries
- Increases customer balance

## Key Reconciliation Rules

### ✅ What Should Match:
- **AR History Sum** = **Current AR Balance Sum**
- Individual AR record movements should trace through AR History

### ❌ What Won't Match:
- **Simple (Invoices - Payments)** ≠ **Current AR Balance**
- This difference represents adjustments, NSFs, fees, and other movements

### 🔍 Red Flags to Investigate:
- AR History sum ≠ Current AR balance sum
- Payments in Payment table with no corresponding AR History entries
- AR records with no AR History entries
- Large unexplained balance differences

## Practical Implementation

### For Customer Service:
1. Always use AR History to explain balance to customers
2. Show specific invoices, payments, and adjustments
3. Explain NSF fees and collection charges separately
4. Provide chronological history of account activity

### For Financial Reporting:
1. Use Current AR Balance for official reporting
2. Reconcile against AR History monthly
3. Investigate any discrepancies immediately
4. Track aging of outstanding invoices vs. fees/adjustments

### For System Development:
1. Always update AR History when touching AR records
2. Ensure all payment applications create proper AR History entries
3. Implement validation checks: AR History sum = AR Balance sum
4. Create audit trails for all AR adjustments

## Conclusion

The proper way to calculate a customer's current balance is through the **AccountReceivableHistory** table, which provides a complete audit trail of all account movements. Simple invoice-minus-payment calculations will be incorrect due to adjustments, NSFs, fees, and other account activities.

**The AR History method is the only reliable way to understand and validate customer balances.** 