# Date Filter Fix Analysis - Oct 6, 2025

## Problem
The date_filter logic in app/main.py line 4126 assumes all reports use 't.Time' but many reports use different date columns or don't have 't' alias. This causes 'invalid date' errors across multiple reports.

## Current Broken Implementation (Line 4126-4130)
```python
if start_date and end_date:
    date_filter = "AND t.Time >= %s AND t.Time < DATEADD(day, 1, %s)"
    params.extend([start_date, end_date])
elif start_date:
    date_filter = "AND CAST(t.Time AS DATE) = %s"
    params.append(start_date)
```

## Report Types and Their Date Column Requirements

### Group 1: Standard Transaction Reports (use `t.Time`)
- daily_sales
- category_sales
- customer_sales
- item_sales
- cashier_performance
- payment_methods
- hourly_sales
- register_analysis
- sales_by_category
- sales_by_item
- profit_analysis
- sales_by_department
- top_items
- top_customers
- transaction_detail
- return_report
- tax_summary
- void_report
- tender_types_detail
- discount_report

### Group 2: PUExciseEntry Reports (use `pue.TransactionTime`)
- pu_excise_summary
- excise_by_category
- excise_transactions
- daily_excise
- excise_simple

### Group 3: DailySales Reports (use `Date`)
- daily_sales_pos
- daily_sales_table

### Group 4: AR History Reports (use `arh.Date`)
- ar_history

### Group 5: Cash Drawer Reports (use `b.OpenDate`)
- cash_drawer_report

### Group 6: No Date Filter Needed
- ar_aging (uses current balance, no date filter)
- inventory_valuation (snapshot report, no date filter)
- inventory_list (current inventory, no date filter)
- reorder_report (current stock levels, no date filter)
- physical_count_worksheet (current inventory, no date filter)
- audit_log (if exists - check implementation)
- customer_labels (customer data, no date filter)

## Solution Strategy
Create a mapping of report types to their date column, then build date_filter dynamically based on report_type.

## Implementation - COMPLETED ✓

### Changes Made

1. **Replaced hardcoded date filter (lines 4121-4130)** with dynamic date column mapping
   - Added `date_column_map` dictionary mapping each report_type to its correct date column
   - Modified date filter building logic to use the mapped column name
   - Added support for reports that don't use date filters (mapped to None)

2. **Removed all .replace() workarounds** throughout report queries
   - Previously: `WHERE 1=1 {date_filter.replace('t.Time', 'pue.TransactionTime')}`
   - Now: `WHERE 1=1 {date_filter}` (date filter already has correct column)

### New Code Structure (app/main.py:4121-4180)

```python
# Build date filter - Map report types to their date columns
date_column_map = {
    # Standard Transaction reports (use t.Time)
    'daily_sales': 't.Time',
    'category_sales': 't.Time',
    # ... 18 more Transaction reports

    # PUExciseEntry reports (use pue.TransactionTime)
    'pu_excise_summary': 'pue.TransactionTime',
    # ... 4 more Excise reports

    # DailySales reports (use Date)
    'daily_sales_pos': 'Date',
    'daily_sales_table': 'Date',

    # AR History reports (use arh.Date)
    'ar_history': 'arh.Date',

    # Cash Drawer reports (use b.OpenDate)
    'cash_drawer_report': 'b.OpenDate',

    # Reports that don't use date filters
    'ar_aging': None,
    'inventory_valuation': None,
    # ... 5 more non-date reports
}

date_filter = ""
params = []

# Get the appropriate date column for this report type
date_column = date_column_map.get(report_type, 't.Time')  # Default to t.Time

# Only build date filter if this report type uses dates
if date_column is not None:
    if start_date and end_date:
        date_filter = f"AND {date_column} >= %s AND {date_column} < DATEADD(day, 1, %s)"
        params.extend([start_date, end_date])
    elif start_date:
        date_filter = f"AND CAST({date_column} AS DATE) = %s"
        params.append(start_date)
```

### Files Modified
- `app/main.py` - Lines 4121-4180 (date filter builder) and removed .replace() calls throughout

### Files Created
- `DATE_FILTER_FIX_ANALYSIS.md` - This documentation
- `test_date_filter_fix.py` - Verification test script for all report types

### Testing
Run `python3 test_date_filter_fix.py` to verify all report types work correctly with date filters.

### Benefits
1. ✓ Fixes 'invalid date' errors across all report types
2. ✓ Cleaner code - no more .replace() workarounds
3. ✓ Easier to maintain - centralized date column mapping
4. ✓ Self-documenting - map clearly shows which reports use which date columns
5. ✓ Backwards compatible - defaults to 't.Time' for unknown report types
6. ✓ Handles reports without date filters correctly (None value)
