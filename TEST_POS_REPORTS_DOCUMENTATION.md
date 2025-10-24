# POS Reports Test Script Documentation

**Created:** January 2025
**Script:** `test_pos_reports.py`
**Purpose:** Comprehensive validation of all 23 POS system report types

---

## Overview

This test script validates all POS system reports implemented in `/api/pos/run-report` endpoint. It checks:
- ✅ Database table existence
- ✅ Query execution without errors
- ✅ Expected column presence
- ✅ Data retrieval success
- ✅ Performance metrics (execution time)
- ✅ Sample data validation

---

## Quick Start

```bash
# Run all tests with full validation
python test_pos_reports.py

# Quick validation only (no date filters)
python test_pos_reports.py --quick

# Test specific report
python test_pos_reports.py --report daily_sales

# Get help
python test_pos_reports.py --help
```

---

## Test Coverage

### Reports Tested: 23 Total

| Category | Count | Reports |
|----------|-------|---------|
| ✅ Working Reports | 15 | daily_sales, category_sales, customer_sales, item_sales, cashier_performance, payment_methods, daily_sales_pos, register_analysis, customer_labels, daily_sales_table, audit_log, inventory_valuation, sales_by_category, sales_by_item, profit_analysis |
| ⚠️ Warning Reports | 5 | pu_excise_summary, excise_by_category, excise_transactions, daily_excise, excise_simple |
| 📊 AR Reports | 3 | ar_aging, ar_history |

---

## Report Definitions

### 1. Working Reports (15)

#### **daily_sales**
- **Tables:** Transaction
- **Filters:** date, customer, cashier
- **Columns:** SaleDate, TransactionCount, TotalSales, TotalTax, AvgTransaction, UniqueCustomers
- **Description:** Daily sales summary with transaction counts

#### **category_sales**
- **Tables:** Transaction, TransactionEntry, Item, Category
- **Filters:** date, customer, cashier
- **Columns:** Category, TransactionCount, TotalQuantity, TotalRevenue, AvgPrice, UniqueItems
- **Description:** Sales aggregated by product category

#### **customer_sales**
- **Tables:** Transaction, Customer
- **Filters:** date, customer, cashier
- **Columns:** CustomerName, AccountNumber, TransactionCount, TotalSales, AvgTransaction, LastPurchase, LifetimeSales
- **Description:** Per-customer sales summary

#### **item_sales**
- **Tables:** Transaction, TransactionEntry, Item, Category
- **Filters:** date, customer, cashier
- **Columns:** ItemName, ItemLookupCode, Category, TotalQuantity, TotalRevenue, AvgPrice, TransactionCount, UniqueCustomers
- **Description:** Top 100 items by revenue

#### **cashier_performance**
- **Tables:** Transaction, Cashier
- **Filters:** date, customer, cashier
- **Columns:** CashierName, TransactionCount, TotalSales, AvgTransaction, FirstTransaction, LastTransaction
- **Description:** Performance metrics per cashier

#### **payment_methods**
- **Tables:** Transaction, TenderEntry
- **Filters:** date, customer, cashier
- **Columns:** PaymentMethod, TransactionCount, TotalAmount, AvgAmount
- **Description:** Payment type breakdown

#### **daily_sales_pos**
- **Tables:** DailySales
- **Filters:** date
- **Columns:** BusinessDate, TotalSales, TotalReturns
- **Description:** Daily sales from DailySales table
- **Note:** Requires DailySales table

#### **register_analysis**
- **Tables:** Transaction
- **Filters:** date
- **Columns:** SaleDate, TransactionCount, TotalSales, TotalReturns
- **Description:** Daily register summary (Crystal Report: RegAnaly.def)

#### **customer_labels**
- **Tables:** Customer
- **Filters:** none
- **Columns:** CustomerName, Address, City, Phone
- **Description:** Customer contact info (Crystal Report: Labels.def)

#### **daily_sales_table**
- **Tables:** DailySales
- **Filters:** date
- **Columns:** BusinessDate, Type, Amount
- **Description:** Direct query to DailySales table
- **Note:** Requires DailySales table

#### **audit_log**
- **Tables:** AuditLog
- **Filters:** none
- **Columns:** Timestamp, Action, User, Details
- **Description:** Last 100 audit entries
- **Note:** Requires AuditLog table

#### **inventory_valuation**
- **Tables:** Item, Category
- **Filters:** none
- **Columns:** Category, ItemCount, TotalCost, TotalRetail, PotentialProfit
- **Description:** Cost vs retail valuation by category

#### **sales_by_category**
- **Tables:** Transaction, TransactionEntry, Item, Category
- **Filters:** date, customer, cashier
- **Columns:** Category, TotalRevenue, TotalCost, GrossProfit, ProfitMargin
- **Description:** Enhanced category sales with profit analysis

#### **sales_by_item**
- **Tables:** Transaction, TransactionEntry, Item, Category
- **Filters:** date, customer, cashier
- **Columns:** ItemName, TotalRevenue, TotalCost, GrossProfit, ProfitMargin
- **Description:** Top 100 items with profit metrics

#### **profit_analysis**
- **Tables:** Transaction, TransactionEntry, Item, Category
- **Filters:** date, customer, cashier
- **Columns:** Category, Revenue, AdjustedCost, GrossProfit, ProfitMargin
- **Description:** Category profit with tax adjustments
- **Note:** Includes hardcoded tax rates for CIGARS (+23%) and LT-TAX-COLLECTED (+10%)

---

### 2. Warning Reports (5) - May Not Work

All excise reports require the **PUExciseEntry** table which is Pennsylvania-specific and may not exist in all databases.

#### **pu_excise_summary**
- **Tables:** PUExciseEntry
- **Filters:** date
- **Columns:** ExciseDate, TransactionCount, TotalExciseTax
- **Description:** Daily excise tax summary

#### **excise_by_category**
- **Tables:** PUExciseEntry, Item, Category
- **Filters:** date
- **Columns:** Category, TotalExciseTax, TransactionCount
- **Description:** Excise tax by category

#### **excise_transactions**
- **Tables:** PUExciseEntry, Item, Category
- **Filters:** date
- **Columns:** TransactionTime, ItemName, Category, ExciseTax
- **Description:** Top 100 excise transactions with item details

#### **daily_excise**
- **Tables:** PUExciseEntry
- **Filters:** date
- **Columns:** ExciseDate, TotalExciseTax, TransactionCount
- **Description:** Daily excise tax totals

#### **excise_simple**
- **Tables:** PUExciseEntry, Item, Category
- **Filters:** date
- **Columns:** TransactionTime, ItemDescription, ExciseTax
- **Description:** Simple excise transaction list

---

### 3. AR Reports (3)

#### **ar_aging**
- **Tables:** AccountReceivable, Customer
- **Filters:** none
- **Columns:** CustomerName, Current, Days30, Days60, Days90, TotalDue
- **Description:** Aging buckets (0-30, 31-60, 61-90, 90+ days)
- **Note:** AR system, not POS

#### **ar_history**
- **Tables:** AccountReceivableHistory, AccountReceivable, Customer
- **Filters:** none
- **Columns:** CustomerName, TransactionDate, Amount, Balance
- **Description:** Top 100 AR history records
- **Note:** AR system

---

## Test Date Ranges

The script automatically tests with multiple date ranges:

| Range | Description |
|-------|-------------|
| `today` | Current date |
| `yesterday` | Previous day |
| `last_7_days` | Last week |
| `last_30_days` | Last month (default for full tests) |
| `last_90_days` | Last quarter |
| `current_month` | Month to date |

---

## Output Format

### Console Output

```
============================================================
Testing: daily_sales
Description: Daily sales summary with transaction counts
Expected Status: working
Tables: Transaction
  ✅ Table 'Transaction' exists
✅ PASSED: 150 rows in 0.234s

============================================================
TEST SUMMARY
============================================================
Total Tests:  23
✅ Passed:    18
❌ Failed:    0
⚠️  Warnings:  3
⏭️  Skipped:   2

Success Rate: 78.3%
```

### JSON Output File

Results are saved to `test_pos_reports_results_YYYYMMDD_HHMMSS.json`:

```json
{
  "test_run": {
    "timestamp": "2025-01-15T10:30:00",
    "total_tests": 23,
    "passed": 18,
    "failed": 0,
    "warnings": 3,
    "skipped": 2
  },
  "test_dates": { ... },
  "results": [
    {
      "report_type": "daily_sales",
      "status": "passed",
      "message": "Query executed successfully",
      "row_count": 150,
      "execution_time": 0.234,
      "columns": ["SaleDate", "TransactionCount", "TotalSales", ...],
      "sample_data": [ ... ],
      "errors": [],
      "warnings": []
    }
  ]
}
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Tests passed but warnings present |

---

## Implementation Details

### Test Flow

1. **Connect to Database** - Establishes connection using `database_pymssql.py`
2. **Check Tables** - Verifies all required tables exist
3. **Build Query** - Constructs SQL with appropriate filters
4. **Execute Query** - Runs query and measures performance
5. **Validate Results** - Checks columns and data structure
6. **Record Results** - Saves detailed metrics
7. **Generate Report** - Creates summary and JSON output

### Query Building

The script mimics the exact logic from `app/main.py:4111-4533`:

```python
# Date filter
if start_date and end_date:
    date_filter = "AND t.Time >= %s AND t.Time < DATEADD(day, 1, %s)"
elif start_date:
    date_filter = "AND CAST(t.Time AS DATE) = %s"

# Additional filters
if customer_id:
    additional_filters += " AND t.CustomerID = %s"
if cashier_id:
    additional_filters += " AND t.CashierID = %s"
```

### Table Existence Check

```python
SELECT COUNT(*)
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME = %s
```

---

## Known Issues & Limitations

### 1. Excise Reports May Fail
**Problem:** PUExciseEntry table is Pennsylvania-specific
**Impact:** 5 reports will be skipped if table doesn't exist
**Solution:** Expected behavior - these are marked as "warning" status

### 2. Category Filter Not Tested
**Problem:** category_id filter is accepted but not applied to excise reports
**Impact:** Excise reports ignore category filter
**Solution:** This is a known issue in the main application (see POS_REPORTS_ANALYSIS.md)

### 3. Limited Query Templates
**Problem:** Not all 23 reports have full query templates in test script
**Impact:** Some reports tested with placeholder logic
**Solution:** Core reports (daily_sales, category_sales, customer_sales, inventory_valuation) fully implemented

### 4. No Mock Data
**Problem:** Tests require live database with real data
**Impact:** Cannot run in CI/CD without database access
**Solution:** Future enhancement - add mock data mode

---

## Future Enhancements

### Planned Features:
- [ ] Add all 23 complete query templates
- [ ] Test export functionality (CSV/Excel)
- [ ] Test pagination for large result sets
- [ ] Add performance benchmarks
- [ ] Test concurrent report execution
- [ ] Add mock data mode for offline testing
- [ ] Test category_id filter on all reports
- [ ] Validate hardcoded tax rates in profit_analysis
- [ ] Test edge cases (empty dates, invalid IDs)
- [ ] Add visual diff for result changes over time

### Integration Tests:
- [ ] Test `/api/pos/export-report` endpoint
- [ ] Test `/api/pos/daily-summary` endpoint
- [ ] Test `/api/pos/search-transactions` endpoint
- [ ] Test `/api/pos/reports` endpoint (list all reports)

---

## Troubleshooting

### Connection Errors
```bash
# Check database connectivity
python -c "from database_pymssql import get_db_connection; conn = get_db_connection(); print('✅ Connected')"
```

### Missing Tables
```bash
# List all tables in database
python -c "from database_pymssql import get_db_connection; conn = get_db_connection(); cur = conn.cursor(); cur.execute('SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES'); print([row[0] for row in cur.fetchall()])"
```

### Slow Queries
- Check database indexes on Transaction.Time, TransactionEntry.TransactionNumber
- Consider adding WHERE clause to limit date range
- Use `--quick` mode for faster validation

---

## Related Files

- **Main App:** `app/main.py:4111-4533` - Report endpoint implementation
- **Analysis:** `POS_REPORTS_ANALYSIS.md` - Detailed report breakdown
- **Database:** `database_pymssql.py` - Database connection module
- **Templates:** `templates/pos_system_dashboard.html` - POS UI

---

## Sample Commands

```bash
# Test all reports with full date filters
python test_pos_reports.py

# Quick smoke test (no filters)
python test_pos_reports.py --quick

# Test individual reports
python test_pos_reports.py --report daily_sales
python test_pos_reports.py --report category_sales
python test_pos_reports.py --report profit_analysis

# Run and save output to file
python test_pos_reports.py > test_output.log 2>&1

# Check exit code
python test_pos_reports.py
echo $?  # 0=success, 1=failed, 2=warnings
```

---

## Success Criteria

A report is considered **PASSED** if:
- ✅ All required tables exist
- ✅ Query executes without errors
- ✅ Expected columns are present (or warnings noted)
- ✅ Execution time < 30 seconds
- ✅ Data structure is valid (can be serialized to JSON)

A report is **SKIPPED** if:
- ⏭️ Required tables don't exist
- ⏭️ Report is optional (like audit_log, DailySales)

A report has **WARNINGS** if:
- ⚠️ Returns zero rows (may be expected)
- ⚠️ Missing expected columns
- ⚠️ Expected to be broken but actually works

A report **FAILED** if:
- ❌ SQL syntax error
- ❌ Database connection error
- ❌ Python exception during execution
- ❌ Invalid data structure

---

## Maintenance

**Update Frequency:** As needed when reports are added/modified
**Owner:** Development Team
**Last Updated:** January 2025

When adding new reports to `app/main.py`:
1. Add report definition to `REPORT_DEFINITIONS` in test script
2. Add query template to `build_query()` method
3. Run full test suite to validate
4. Update this documentation
