# Fix Broken Reports - Column Name Corrections

## Summary of Issues
Several reports in `app/main.py` use incorrect column names that don't exist in the actual database tables.

## Database Column Analysis

### Batch Table
**Incorrect columns used:**
- `OpenDate` → **CORRECT:** `OpeningTime`
- `CloseDate` → **CORRECT:** `ClosingTime`
- `ExpectedAmount` → **CORRECT:** `OpeningTotal`
- `CountedAmount` → **CORRECT:** `ClosingTotal`
- `DepositTotal` → **CORRECT:** `Dropped`
- `PayoutTotal` → **CORRECT:** `PaidOut`
- `CashierID` → **DOES NOT EXIST** (Remove)

### TaxEntry Table
**Incorrect columns used:**
- `TaxAmount` → **CORRECT:** `Tax`
- `Price * Quantity` → **NOT IN TAXENTRY** (must join to TransactionEntry)

### Transaction Table
**Incorrect columns used:**
- `VoidTransaction` → **DOES NOT EXIST** (use `Status` field instead)

### TenderEntry Table
**Incorrect columns used:**
- `ChangedAmount` → **DOES NOT EXIST** (possibly use `Amount` or remove)

### TransactionEntry Table
**Incorrect columns used:**
- `OriginalPrice` → **DOES NOT EXIST** (use `FullPrice`)

## Reports to Fix

### 1. cash_drawer_report (line 4741)
**Changes:**
- `b.OpenDate` → `b.OpeningTime`
- `b.CloseDate` → `b.ClosingTime`
- `b.ExpectedAmount` → `b.OpeningTotal`
- `b.CountedAmount` → `b.ClosingTotal`
- `b.DepositTotal` → `b.Dropped`
- `b.PayoutTotal` → `b.PaidOut`
- Remove `cash.Name as CashierName` (no CashierID in Batch)

### 2. tax_summary (line 4766)
**Changes:**
- `te.TaxAmount` → `te.Tax`
- `te.Price * te.Quantity` → Must join with TransactionEntry to get taxable amount

### 3. void_report (line 4782)
**Changes:**
- `t.VoidTransaction = 1` → `t.Status` (need to determine correct status value)

### 4. tender_types_detail (line 4802)
**Changes:**
- `te.ChangedAmount` → Remove or use alternative field

### 5. discount_report (line 4820)
**Changes:**
- `te.OriginalPrice` → `te.FullPrice`
- Update calculations to use `FullPrice`

## Status Values
Need to check what Status value indicates void (likely negative Total or specific Status code)
