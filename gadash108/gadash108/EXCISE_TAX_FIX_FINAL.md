# EXCISE TAX FIX - FINAL CORRECTION
## Date: October 6, 2025

## The Problem
Previous "fixes" were calculating excise tax incorrectly by trying to derive it from Item table fields or custom calculations. This was completely wrong.

## The Solution
The POS system **already stores** excise tax in the `PUExciseEntry` table. We just needed to use it.

## What Was Changed

### File: /Users/akbarchranya/georgiadashboard/app/main.py

#### 1. Receipt Query (Lines 3849-3871)
**Before**: Getting `i.PriceC` from Item table
**After**: Getting `pe.PriceC` from PUExciseEntry table

```sql
-- WRONG (old code)
SELECT i.PriceC
FROM TransactionEntry te
JOIN Item i ON te.ItemID = i.ID

-- CORRECT (new code)
SELECT pe.PriceC as ExciseTaxAmount, pe.SubDescription3 as ExciseType
FROM TransactionEntry te
LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
```

#### 2. Excise Tax Calculation (Lines 3922-3930)
**Before**: Multiplying Quantity × Item.PriceC (wrong source)
**After**: Using PUExciseEntry.PriceC directly (already the total)

```python
# WRONG (old code)
item_excise = float(item['Quantity']) * float(item.get('PriceC', 0) or 0)

# CORRECT (new code)
item_excise = float(item.get('ExciseTaxAmount', 0) or 0)
```

## Key Insights

1. **PUExciseEntry.PriceC** stores the TOTAL excise tax for the transaction line item
2. **PUExciseEntry.SubDescription3** indicates the tax type (LC23COLL, LC23PAID, etc.)
3. Not all items have excise tax - must use LEFT JOIN
4. The POS system has been recording this correctly since 2013

## Database Structure

```
TransactionEntry (main sales records)
    ↓ (te.ID = pe.TransactionEntryID)
PUExciseEntry (excise tax records)
    - PriceC: Excise tax amount for this line item
    - SubDescription3: Tax type (LC23COLL, LC23PAID, LT10PAID, etc.)
    - Quantity: Quantity sold
    - TransactionTime: When sold
```

## Testing

To verify the fix works:
1. Query any recent transaction with tobacco/vaping products
2. Check that excise tax appears on the receipt
3. Verify the amount matches PUExciseEntry.PriceC

```sql
-- Test query
SELECT
    te.TransactionNumber,
    i.Description,
    te.Quantity,
    te.Price,
    pe.PriceC as ExciseTax,
    pe.SubDescription3 as ExciseType
FROM TransactionEntry te
JOIN Item i ON te.ItemID = i.ID
LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
WHERE te.TransactionTime >= '2025-10-01'
    AND pe.PriceC IS NOT NULL
ORDER BY te.TransactionTime DESC
```

## Files Modified
- `/Users/akbarchranya/georgiadashboard/app/main.py` (Receipt endpoint)

## Files Created
- `/Users/akbarchranya/georgiadashboard/CORRECT_EXCISE_TAX_STRUCTURE.md` (Full documentation)
- `/Users/akbarchranya/georgiadashboard/EXCISE_TAX_FIX_FINAL.md` (This file)

## Status
✅ COMPLETE - Excise tax now uses POS system source of truth
