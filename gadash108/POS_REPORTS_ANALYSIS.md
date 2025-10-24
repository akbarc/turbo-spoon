# POS System Reports Analysis
**Analysis Date:** January 2025
**Endpoint:** `/api/pos/run-report` in `app/main.py`

## Executive Summary

The POS system has **23 report types** implemented in the `/api/pos/run-report` endpoint. Analysis shows:
- **15 Working Reports** (65%) - Using standard Transaction/TransactionEntry tables
- **5 Potentially Broken Reports** (22%) - Using excise tables that may not exist
- **3 AR Reports** (13%) - Working but separate from POS

---

## Working Reports (15 Total)

### 1. **daily_sales** ✅
- **Tables:** `Transaction`
- **Logic:** Groups sales by date, calculates totals, avg transaction, unique customers
- **Status:** WORKING
- **Location:** app/main.py:4144-4157

### 2. **category_sales** ✅
- **Tables:** `Transaction`, `TransactionEntry`, `Item`, `Category`
- **Logic:** Aggregates sales by category with quantity, revenue, avg price
- **Status:** WORKING
- **Location:** app/main.py:4159-4175

### 3. **customer_sales** ✅
- **Tables:** `Transaction`, `Customer`
- **Logic:** Per-customer sales summary with lifetime totals
- **Status:** WORKING
- **Location:** app/main.py:4177-4192

### 4. **item_sales** ✅
- **Tables:** `Transaction`, `TransactionEntry`, `Item`, `Category`
- **Logic:** TOP 100 items by revenue with detailed metrics
- **Status:** WORKING
- **Location:** app/main.py:4194-4212

### 5. **cashier_performance** ✅
- **Tables:** `Transaction`, `Cashier`
- **Logic:** Performance metrics per cashier
- **Status:** WORKING
- **Location:** app/main.py:4214-4228

### 6. **payment_methods** ✅
- **Tables:** `Transaction`, `TenderEntry`
- **Logic:** Payment type breakdown from TenderEntry table
- **Status:** WORKING
- **Location:** app/main.py:4230-4242

### 7. **daily_sales_pos** ✅
- **Tables:** `DailySales` (pre-calculated POS table)
- **Logic:** Uses DailySales table with Type codes (1=Sales, 2=Returns, 3=Voids, 4=Payments)
- **Status:** WORKING (if DailySales table exists)
- **Location:** app/main.py:4327-4343

### 8. **register_analysis** ✅
- **Tables:** `Transaction`
- **Logic:** Mimics RegAnaly.def Crystal Report - daily register summary
- **Status:** WORKING
- **Location:** app/main.py:4346-4362

### 9. **customer_labels** ✅
- **Tables:** `Customer`
- **Logic:** Mimics Labels.def Crystal Report - customer contact info
- **Status:** WORKING
- **Location:** app/main.py:4364-4382

### 10. **daily_sales_table** ✅
- **Tables:** `DailySales`
- **Logic:** Direct query to DailySales table with type mapping
- **Status:** WORKING (if DailySales exists)
- **Location:** app/main.py:4405-4419

### 11. **audit_log** ✅
- **Tables:** `AuditLog`
- **Logic:** Last 100 audit entries
- **Status:** WORKING
- **Location:** app/main.py:4421-4426

### 12. **inventory_valuation** ✅
- **Tables:** `Item`, `Category`
- **Logic:** Cost vs retail valuation by category
- **Status:** WORKING
- **Location:** app/main.py:4440-4455

### 13. **sales_by_category** ✅
- **Tables:** `Transaction`, `TransactionEntry`, `Item`, `Category`
- **Logic:** Enhanced category sales with cost/profit analysis
- **Status:** WORKING
- **Location:** app/main.py:4457-4475

### 14. **sales_by_item** ✅
- **Tables:** `Transaction`, `TransactionEntry`, `Item`, `Category`
- **Logic:** TOP 100 items with profit metrics
- **Status:** WORKING
- **Location:** app/main.py:4477-4498

### 15. **profit_analysis** ✅
- **Tables:** `Transaction`, `TransactionEntry`, `Item`, `Category`
- **Logic:** Category profit with tax adjustments (CIGARS +23%, LT-TAX-COLLECTED +10%)
- **Status:** WORKING
- **Location:** app/main.py:4500-4533

---

## Potentially Broken Reports (5 Total)

### 16. **pu_excise_summary** ⚠️
- **Tables:** `PUExciseEntry`
- **Logic:** Daily excise tax summary
- **Issue:** PUExciseEntry table may not exist in all POS databases
- **Location:** app/main.py:4244-4256

### 17. **excise_by_category** ⚠️
- **Tables:** `PUExciseEntry`, `Item`, `Category`
- **Logic:** Excise tax by category
- **Issue:** PUExciseEntry table may not exist
- **Location:** app/main.py:4258-4273

### 18. **excise_transactions** ⚠️
- **Tables:** `PUExciseEntry`, `Item`, `Category`
- **Logic:** TOP 100 excise transactions with item details
- **Issue:** PUExciseEntry table may not exist
- **Location:** app/main.py:4275-4292

### 19. **daily_excise** ⚠️
- **Tables:** `PUExciseEntry`
- **Logic:** Daily excise tax totals
- **Issue:** PUExciseEntry table may not exist
- **Location:** app/main.py:4294-4306

### 20. **excise_simple** ⚠️
- **Tables:** `PUExciseEntry`, `Item`, `Category`
- **Logic:** Simple excise transaction list with LEFT JOINs for safety
- **Issue:** PUExciseEntry table may not exist
- **Location:** app/main.py:4385-4403

---

## AR Reports (3 Total)

### 21. **ar_aging** ✅
- **Tables:** `AccountReceivable`, `Customer`
- **Logic:** Aging buckets (0-30, 31-60, 61-90, 90+ days)
- **Status:** WORKING (AR system, not POS)
- **Location:** app/main.py:4308-4324

### 22. **ar_history** ✅
- **Tables:** `AccountReceivableHistory`, `AccountReceivable`, `Customer`
- **Logic:** TOP 100 AR history records
- **Status:** WORKING (AR system)
- **Location:** app/main.py:4428-4438

---

## Database Structure Verification

### Core POS Tables (Confirmed Working):
```sql
[dbo].[Transaction]       -- Main transaction header
dbo.TransactionEntry      -- Line items
dbo.TenderEntry          -- Payment methods
dbo.Customer             -- Customer master
dbo.Item                 -- Product master
dbo.Category             -- Product categories
dbo.Cashier              -- Cashier master
```

### Specialized Tables (May Not Exist):
```sql
dbo.PUExciseEntry        -- Pennsylvania excise tax (state-specific)
dbo.DailySales           -- Pre-calculated daily summary
dbo.AuditLog             -- Audit trail
```

### AR Tables (Separate System):
```sql
dbo.AccountReceivable
dbo.AccountReceivableHistory
```

---

## Key Findings

### 1. Filter Logic Issues
**Problem:** All excise reports use this pattern:
```python
date_filter.replace('t.Time', 'pue.TransactionTime')
```
**Issue:** If excise reports don't have category_id filter, they still pass it through and may cause errors

### 2. Category Filter Not Used in Excise Reports
The `category_id` parameter is collected but never applied to excise reports:
```python
category_id = request.args.get('category_id')  # Line 4120
# But excise queries don't use additional_filters that includes category_id
```

### 3. Missing Export Format Validation
`/api/pos/export-report` doesn't validate if pandas or xlsxwriter are installed before attempting Excel export

### 4. Profit Analysis Has Hardcoded Tax Rates
```python
WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23  # 23% markup
WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  # 10%
```
These should be configurable, not hardcoded

---

## Recommendations

### Immediate Fixes:
1. **Add table existence checks** before running excise reports
2. **Fix category_id filter** in excise reports (currently ignored)
3. **Add try-catch** around DailySales queries with fallback
4. **Validate export dependencies** (pandas, xlsxwriter)

### Enhancement Opportunities:
1. Move tax rates to configuration table
2. Create view for excise data if PUExciseEntry doesn't exist
3. Add caching for frequently-run reports
4. Implement pagination for large result sets (currently TOP 100)

### Testing Required:
- [ ] Test all excise reports on production DB
- [ ] Verify DailySales table exists
- [ ] Test category_id filter on all report types
- [ ] Test export functionality with missing dependencies
- [ ] Validate date range filters with edge cases

---

## Report Type Quick Reference

| Report Type | Tables | Working | Location |
|-------------|--------|---------|----------|
| daily_sales | Transaction | ✅ | 4144 |
| category_sales | Transaction, TransactionEntry, Item, Category | ✅ | 4159 |
| customer_sales | Transaction, Customer | ✅ | 4177 |
| item_sales | Transaction, TransactionEntry, Item, Category | ✅ | 4194 |
| cashier_performance | Transaction, Cashier | ✅ | 4214 |
| payment_methods | Transaction, TenderEntry | ✅ | 4230 |
| pu_excise_summary | PUExciseEntry | ⚠️ | 4244 |
| excise_by_category | PUExciseEntry, Item, Category | ⚠️ | 4258 |
| excise_transactions | PUExciseEntry, Item, Category | ⚠️ | 4275 |
| daily_excise | PUExciseEntry | ⚠️ | 4294 |
| ar_aging | AccountReceivable, Customer | ✅ | 4308 |
| daily_sales_pos | DailySales | ✅ | 4327 |
| register_analysis | Transaction | ✅ | 4346 |
| customer_labels | Customer | ✅ | 4364 |
| excise_simple | PUExciseEntry, Item, Category | ⚠️ | 4385 |
| daily_sales_table | DailySales | ✅ | 4405 |
| audit_log | AuditLog | ✅ | 4421 |
| ar_history | AccountReceivableHistory, AccountReceivable, Customer | ✅ | 4428 |
| inventory_valuation | Item, Category | ✅ | 4440 |
| sales_by_category | Transaction, TransactionEntry, Item, Category | ✅ | 4457 |
| sales_by_item | Transaction, TransactionEntry, Item, Category | ✅ | 4477 |
| profit_analysis | Transaction, TransactionEntry, Item, Category | ✅ | 4500 |

---

## Related Endpoints

- `/api/pos/search-transactions` (Line 4559) - Transaction search with filters
- `/api/pos/export-report` (Line 4640) - CSV/Excel export
- `/api/pos/daily-summary` (Line 4693) - Daily metrics dashboard
- `/api/pos/reports` (Line 3980) - List all available reports

