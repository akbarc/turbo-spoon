# Excise Tax Reports Revert Summary

**Date:** 2025-10-06
**Action:** REVERTED all custom Georgia tax rate calculations

## What Was Reverted

All fake Georgia excise tax calculations using hardcoded rates (0.37 for cigarettes, 0.23 for cigars, etc.) have been **REMOVED** from `app/main.py`.

### Reports Affected

The following report queries were reverted to use the original `PUExciseEntry` table:

1. **`pu_excise_summary`** (Line ~4219)
   - ❌ REMOVED: Custom Georgia tax rate calculation (0.37 * Quantity)
   - ✅ RESTORED: `SELECT FROM dbo.PUExciseEntry` using `PriceC` field

2. **`excise_by_category`** (Line ~4233)
   - ❌ REMOVED: Custom Georgia tax rate calculation by category
   - ✅ RESTORED: `SELECT FROM dbo.PUExciseEntry` using `PriceC` field

3. **`excise_transactions`** (Line ~4251)
   - ❌ REMOVED: Custom Georgia tax rate calculation in CASE statements
   - ✅ RESTORED: `SELECT FROM dbo.PUExciseEntry` using `PriceC` field

4. **`daily_excise`** (Line ~4271)
   - ❌ REMOVED: Custom Georgia tax rate calculation
   - ✅ RESTORED: `SELECT FROM dbo.PUExciseEntry` using `PriceC` field

5. **`excise_simple`** (Line ~4361)
   - ❌ REMOVED: Custom Georgia tax rate calculation
   - ✅ RESTORED: `SELECT FROM dbo.PUExciseEntry` using `PriceC` field

### Excise Reports List

The excise reports have been **REMOVED** from the `/api/pos-reports` endpoint (Line ~4063):

```python
# BEFORE (WRONG):
excise_reports = [
    {'id': 'excise_simple', 'name': 'Excise Tax Transactions', ...},
    {'id': 'pu_excise_summary', 'name': 'Daily Excise Tax Summary', ...},
    {'id': 'excise_by_category', 'name': 'Excise Tax by Category', ...},
]

# AFTER (CORRECT):
# Excise Tax Reports REMOVED - PUExciseEntry table does not exist in this database
# If excise tax reporting is needed, the POS system must be configured to populate PUExciseEntry table
```

## Why This Was Wrong

1. **Custom tax calculations are NOT the source of truth** - The POS system is the ONLY source of truth for all financial data
2. **PUExciseEntry table doesn't exist** - The Pennsylvania-specific table is not present in this database
3. **Hardcoded rates are unreliable** - Tax rates change, product categories vary, and calculations must come from the POS
4. **Creates fake data** - Custom calculations don't match actual excise tax paid/collected

## What Happens Now

### If PUExciseEntry Table Exists
- All 5 excise reports will work correctly using actual POS data
- Reports will show real excise tax from `PriceC` field

### If PUExciseEntry Table Does NOT Exist
- All 5 excise reports will **fail with SQL error** (table not found)
- This is **CORRECT BEHAVIOR** - better to fail than show fake data
- Reports should be removed from the UI or disabled

## Receipt Endpoint (NOT Changed)

The `/api/pos/receipt/<transaction_number>` endpoint was **NOT changed** because it correctly uses:
```python
excise_tax = item['Quantity'] * item.get('PriceC', 0)
```

This is correct because:
- ✅ It reads `PriceC` from actual transaction data (stored by POS)
- ✅ It doesn't calculate custom rates
- ✅ It's the source of truth from the POS system

## Files Modified

- `app/main.py`:
  - Line ~4063: Removed excise reports from reports list
  - Line ~4219: Reverted `pu_excise_summary` query
  - Line ~4233: Reverted `excise_by_category` query
  - Line ~4251: Reverted `excise_transactions` query
  - Line ~4271: Reverted `daily_excise` query
  - Line ~4361: Reverted `excise_simple` query (was already correct)

## Next Steps

1. **Test if PUExciseEntry exists:**
   ```sql
   SELECT TOP 1 * FROM dbo.PUExciseEntry
   ```

2. **If table exists:** Reports will work correctly

3. **If table doesn't exist:** Remove these reports from the UI entirely:
   - excise_simple
   - pu_excise_summary
   - excise_by_category
   - excise_transactions
   - daily_excise

## Key Principle

**THE POS SYSTEM IS THE ONLY SOURCE OF TRUTH.**

Never create custom calculations for:
- Excise tax
- Sales tax
- Discounts
- Totals
- Prices
- Costs

Always use the data **exactly as stored** by the POS system.
