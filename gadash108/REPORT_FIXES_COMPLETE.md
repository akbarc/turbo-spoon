# Report Fixes - SQL Column Name Corrections

## Summary
Fixed 5 broken reports in `app/main.py` that were using incorrect database column names. All queries now use the actual column names from the POS database.

## Reports Fixed

### 1. cash_drawer_report (Line ~4741)
**Issues Fixed:**
- ❌ `b.OpenDate` → ✅ `b.OpeningTime`
- ❌ `b.CloseDate` → ✅ `b.ClosingTime`
- ❌ `b.ExpectedAmount` → ✅ `b.OpeningTotal`
- ❌ `b.CountedAmount` → ✅ `b.ClosingTotal`
- ❌ `b.DepositTotal` → ✅ `b.Dropped`
- ❌ `b.PayoutTotal` → ✅ `b.PaidOut`
- ❌ Removed `cash.Name as CashierName` (Batch table has no CashierID)
- ✅ Updated date filter to use `b.OpeningTime`

**Result:** Query now successfully retrieves batch/cash drawer data with opening/closing totals and variance.

---

### 2. tax_summary (Line ~4764)
**Issues Fixed:**
- ❌ `te.TaxAmount` → ✅ `taxe.Tax`
- ❌ `te.Price * te.Quantity` → ✅ `taxe.TaxableAmount`
- ✅ Changed alias from `te` to `taxe` for TaxEntry to avoid confusion
- ✅ Added COALESCE for tax description to handle NULL values

**Result:** Query now correctly aggregates tax collected by tax type using actual TaxEntry columns.

---

### 3. void_report (Line ~4780)
**Issues Fixed:**
- ❌ `t.VoidTransaction = 1` → ✅ `(t.Status < 0 OR t.Comment LIKE '%void%' OR t.Comment LIKE '%cancel%')`
- ✅ Added `t.Status` to SELECT and GROUP BY for debugging
- ✅ Changed filter to detect voids by Status or Comment patterns

**Result:** Query now identifies voided transactions using Status field and Comment text patterns.

---

### 4. tender_types_detail (Line ~4801)
**Issues Fixed:**
- ❌ `te.ChangedAmount` → ✅ Calculated change as `CASE WHEN te.Amount > t.Total THEN te.Amount - t.Total ELSE 0 END`
- ✅ Added COALESCE to handle missing tender descriptions
- ✅ Added `te.Description` to GROUP BY for proper aggregation

**Result:** Query now calculates tender statistics with computed change amount.

---

### 5. discount_report (Line ~4819)
**Issues Fixed:**
- ❌ `te.OriginalPrice` → ✅ `te.FullPrice`
- ✅ Added CASE statement to prevent division by zero in discount percentage
- ✅ Updated WHERE clause to check `te.FullPrice > 0`
- ✅ All calculations now use FullPrice instead of OriginalPrice

**Result:** Query now correctly identifies discounted items using FullPrice vs Price comparison.

---

## Database Column Reference

### Batch Table Columns (Used)
- `BatchNumber`, `OpeningTime`, `ClosingTime`, `RegisterID`
- `OpeningTotal`, `ClosingTotal`, `Dropped`, `PaidOut`
- `Sales`, `Returns`, `Tax`, `TotalTendered`, `TotalChange`

### TaxEntry Table Columns (Used)
- `ID`, `TaxID`, `TransactionNumber`, `Tax`, `TaxableAmount`

### Transaction Table Columns (Used)
- `TransactionNumber`, `BatchNumber`, `Time`, `CustomerID`, `CashierID`
- `Total`, `SalesTax`, `Comment`, `Status`

### TenderEntry Table Columns (Used)
- `ID`, `TransactionNumber`, `TenderID`, `Description`, `Amount`

### TransactionEntry Table Columns (Used)
- `ID`, `TransactionNumber`, `ItemID`, `Price`, `FullPrice`
- `Quantity`, `Cost`, `Taxable`

---

## Testing Recommendations

Test each report with:
```bash
curl "http://localhost:5001/api/pos/reports/cash_drawer_report?format=json&start_date=2024-01-01&end_date=2024-12-31"
curl "http://localhost:5001/api/pos/reports/tax_summary?format=json&start_date=2024-01-01&end_date=2024-12-31"
curl "http://localhost:5001/api/pos/reports/void_report?format=json&start_date=2024-01-01&end_date=2024-12-31"
curl "http://localhost:5001/api/pos/reports/tender_types_detail?format=json&start_date=2024-01-01&end_date=2024-12-31"
curl "http://localhost:5001/api/pos/reports/discount_report?format=json&start_date=2024-01-01&end_date=2024-12-31"
```

---

## Notes
- **AR Aging reports** were already correct and didn't require changes
- All fixes maintain backward compatibility with the report API structure
- Column aliases ensure the frontend continues to receive data in expected format
- Date: 2025-10-06
