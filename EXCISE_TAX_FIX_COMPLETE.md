# Excise Tax Fix - COMPLETE ✅

**Date**: October 15, 2025

---

## Problem Summary

We were **double-counting pre-paid excise tax**, causing categories like CIGAR GA to show negative GP when they were actually profitable.

**Two Types of Excise Tax**:
- **PAID** (LC23PAID, LC25PAID, etc.) = Pre-paid by distributor, **ALREADY IN COGS**
- **COLL** (LC23COLL, LC25COLL, etc.) = Collected at POS, **NOT in COGS**

**Wrong Formula**: `GP = Revenue - COGS - ALL Excise`
**Correct Formula**: `GP = Revenue - COGS - (COLL Excise only)`

---

## Solution Implemented

### 1. Created ExciseTaxTypes Lookup Table
```sql
CREATE TABLE ExciseTaxTypes (
    TaxType VARCHAR(50) PRIMARY KEY,
    IsPrePaid BIT NOT NULL,
    Description VARCHAR(255) NULL
)
```

**Contains 14 tax types**:
- 6 PRE-PAID types (LC23PAID, LC25PAID, LT10PAID, SL10PAID, VC05PAID, VD07PAID)
- 7 COLLECTED types (LC23COLL, LC25COLL, LT10COLL, SL10COLL, VC05COLL, VD07COLL)
- 1 unknown (048155905153)

### 2. Updated GP Calculation Query

**Old (slow) approach**:
```sql
WHEN pe.SubDescription3 LIKE '%COLL' THEN COALESCE(pe.PriceC, 0)
```
⚠️ Pattern matching on millions of records = 5+ minute timeout

**New (fast) approach**:
```sql
LEFT JOIN [dbo].[ExciseTaxTypes] ett ON pe.SubDescription3 = ett.TaxType
...
WHEN ett.IsPrePaid = 0 THEN COALESCE(pe.PriceC, 0)
```
✅ Simple JOIN = completes in seconds

---

## Results

### Before Fix (Double-Counting):
```
CIGAR GA:          -$39.08  ❌ NEGATIVE
T7 SMOKELESS GA:   -$4.11   ❌ NEGATIVE
Total GP:          $5,395   ⚠️  Understated
```

### After Fix (Correct):
```
CIGAR GA:          $120.38 (11.4%)  ✅ POSITIVE
T7 SMOKELESS GA:   $5.88 (3.5%)     ✅ POSITIVE
Total GP:          $6,744 (3.2%)    ✅ Accurate
```

**GP increased by ~$1,350** (we were understating profit by 20%!)

---

## Files Created

1. **create_excise_tax_lookup.py** - Creates ExciseTaxTypes lookup table
2. **populate_gp_summary.py** - Populates GP_Daily_Summary with correct formula
3. **verify_corrected_gp.py** - Verifies the fix worked

---

## Performance

**Old query** (LIKE pattern): Timeout after 5+ minutes ❌
**New query** (JOIN lookup): Completes in ~10 seconds ✅

**Performance improvement: 30x faster**

---

## Key Insights

1. **CIGAR GA is actually profitable** at 11.4% margin (not losing money)
2. **Pre-paid excise** (PAID) should never be subtracted from GP
3. **Collected excise** (COLL) should be subtracted from GP
4. **Lookup tables** are much faster than LIKE pattern matching

---

## Remaining Issues

**NICOTINE POUCHES**: Still showing negative GP (-$328.84)
**Cause**: FRE products priced below cost ($9.99 price vs $18.50 cost)
**Solution**: Needs pricing update in POS (not an excise tax issue)

---

## Dashboard Status

✅ Dashboard running at http://100.126.106.37:8081
✅ Category breakdown displaying correctly
✅ Excise tax calculated accurately
✅ GP_Daily_Summary table populated with correct data

---

## Maintenance

To update daily data:
```bash
python3 populate_gp_summary.py
```

To add new excise tax types (if created in POS):
```bash
python3 create_excise_tax_lookup.py
```

---

## Technical Notes

- Uses SA account for table creation (Tech7World)
- All operations are READ-ONLY on POS tables
- GP_Daily_Summary is our calculation table
- ExciseTaxTypes is our lookup table
- Both tables safe to modify/rebuild

---

**Your insight about CIGAR GA having pre-paid excise was 100% correct and saved us from systematically understating profit!** 🎉
