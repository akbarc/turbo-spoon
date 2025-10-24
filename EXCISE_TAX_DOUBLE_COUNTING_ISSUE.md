# CRITICAL FINDING: Excise Tax Double-Counting Issue

**Date**: October 15, 2025
**Discovered By**: User insight about CIGAR GA

---

## 🔴 The Problem

**We are DOUBLE-COUNTING pre-paid excise tax!**

### What We Found:

**1. Two Types of Excise Tax in System:**
- **`*PAID`** (LC23PAID, LC25PAID, LT10PAID, etc.) = Tax **PRE-PAID** by distributor, **ALREADY IN COGS**
- **`*COLL`** (LC23COLL, LC25COLL, LT10COLL, etc.) = Tax **COLLECTED** at POS, **NOT in COGS**

**2. Current (WRONG) GP Formula:**
```
GP = Revenue - COGS - ALL Excise Tax
```

This subtracts BOTH PAID and COLL excise tax!

**3. Example - CIGAR GA (GT WOODS):**
```
Price:  $16.49
COGS:   $15.43  (includes $2.89 pre-paid excise!)
Excise: $2.89   (LC23PAID - already in the $15.43 COGS!)

Current (wrong):
GP = $16.49 - $15.43 - $2.89 = -$1.83 ❌ NEGATIVE (double-counted!)

Correct:
GP = $16.49 - $15.43 = $1.06 ✅ POSITIVE (don't subtract pre-paid again!)
```

---

## 📊 Impact

### Categories Affected (showing false negative GP):

1. **CIGAR GA**: Showing -$39.08, should be **~$115 positive**
   - All cigars have LC23PAID excise ($154 double-counted)

2. **T7 SMOKELESS GA**: Showing -$4.11, should be **~$6 positive**
   - Has SL10PAID excise (~$10 double-counted)

3. **Other tobacco products** with PAID excise are also affected

### What's NOT Affected:

- **CIGARETTE**: Uses LC23**COLL** (collected at POS) - formula is correct ✅
- **Non-tobacco items**: No excise tax - formula is correct ✅

---

## ✅ The Correct Formula

```sql
GP = Revenue - COGS - (COLL excise only)

-- In SQL:
GrossProfit =
    (Price * Quantity) -
    (Cost * Quantity) -
    CASE
        WHEN SubDescription3 LIKE '%COLL' THEN ExciseTax
        ELSE 0  -- Don't subtract PAID excise (already in COGS)
    END
```

**Key Rule**: Only subtract excise if it's **COLLECTED** at POS

---

## 🔧 Why The Fix Is Slow

**Problem**: The query needs to check `SubDescription3 LIKE '%COLL'` for millions of records

**Current Performance**:
- Today's data only: **5+ minutes** (timing out)
- Full dataset: Would take hours

**Root Cause**:
- No index on `PUExciseEntry.SubDescription3`
- LIKE '%COLL' can't use indexes efficiently
- Millions of excise tax entries to check

---

## 💡 Solution Options

### Option 1: Document and Fix Manually (FASTEST)
**What**: Document which categories have PAID vs COLL excise
**How**:
- Know that CIGAR GA = LC23PAID (don't count excise)
- Know that CIGARETTE = LC23COLL (do count excise)
- Adjust reports manually or use lookup table

**Pros**: Immediate, no database changes
**Cons**: Manual tracking, not automatic

---

### Option 2: Add Computed Column (RECOMMENDED)
**What**: Add a `IsPaid` flag to PUExciseEntry

```sql
ALTER TABLE PUExciseEntry
ADD IsPaid AS (
    CASE
        WHEN SubDescription3 LIKE '%PAID' THEN 1
        ELSE 0
    END
) PERSISTED

CREATE INDEX IX_PUExciseEntry_IsPaid ON PUExciseEntry(IsPaid)
```

Then query becomes fast:
```sql
GP = Revenue - COGS - CASE WHEN IsPaid = 0 THEN ExciseTax ELSE 0 END
```

**Pros**: Fast queries, automatic
**Cons**: Requires DDL permissions (SA account)

---

### Option 3: Lookup Table
**What**: Create a reference table of tax types

```sql
CREATE TABLE ExciseTaxTypes (
    TaxType VARCHAR(50) PRIMARY KEY,
    IsPrePaid BIT NOT NULL
)

INSERT INTO ExciseTaxTypes VALUES
    ('LC23PAID', 1), ('LC23COLL', 0),
    ('LC25PAID', 1), ('LC25COLL', 0),
    ...
```

**Pros**: Clean, maintainable
**Cons**: Requires initial setup

---

## 📈 Real Impact on Today's Numbers

### Current (Wrong) Totals:
- Total GP: $5,395.90
- Total Excise: $876.88
- CIGAR GA: -$39.08 (wrong!)

### Estimated Correct Totals:
- Total GP: ~$5,549 (+$154 from CIGAR GA fix)
- Total COLL Excise: ~$722 (only collected excise)
- CIGAR GA: ~$115 (positive!)

**We're understating GP by ~$150-200 due to double-counting!**

---

## 🎯 Immediate Action Items

### For Now (Workaround):
1. ✅ **Documented the issue** in this file
2. 📝 **Know that CIGAR GA GP is understated** by $154
3. 📝 **Manual adjustment**: Add $154 to today's GP = **$5,550 actual GP**

### To Fix Permanently:
1. **Option A**: Add IsPaid computed column (requires SA permissions)
2. **Option B**: Create ExciseTaxTypes lookup table
3. **Option C**: Pre-process data nightly into summary table with correct formula

---

## 📋 Excise Tax Type Reference

**PRE-PAID (Already in COGS - Don't Subtract)**:
- LC23PAID - Little Cigars 23% (Georgia)
- LC25PAID - Little Cigars 25%
- LT10PAID - Large Tobacco 10%
- SL10PAID - Smokeless 10%
- VC05PAID - Vapor/Cigarettes 5%
- VD07PAID - Vapor/Devices 7%

**COLLECTED (At POS - Do Subtract)**:
- LC23COLL - Little Cigars 23% (collected)
- LC25COLL - Little Cigars 25% (collected)
- LT10COLL - Large Tobacco 10% (collected)
- SL10COLL - Smokeless 10% (collected)
- VC05COLL - Vapor/Cigarettes 5% (collected)
- VD07COLL - Vapor/Devices 7% (collected)

---

## 🎓 Business Insight

**Why This Matters**:

1. **Pricing Decisions**: CIGAR GA looks unprofitable but it's actually profitable!
2. **Product Mix**: We might be avoiding profitable pre-paid categories
3. **Accurate Reporting**: True GP is ~3% higher than reported
4. **Tax Compliance**: Need to track PAID vs COLL for tax reporting

**Your instinct was spot-on** - CIGAR GA category does have pre-paid excise, and we were indeed double-counting it!

---

## ✅ Verified Examples

### CIGAR GA - GT WOODS 2/1.39 BANANA:
- **Price**: $16.49
- **COGS**: $15.43 (includes $2.89 excise)
- **Excise Entry**: $2.89 (LC23**PAID**)
- **Wrong GP**: -$1.83 (subtracted excise twice!)
- **Right GP**: $1.06 (don't subtract pre-paid excise)

### CIGARETTE - Works Correctly:
- **Price**: $9.50
- **COGS**: $8.00 (does NOT include excise)
- **Excise Entry**: $0.37 (LC23**COLL**)
- **GP**: $1.13 (correctly subtracts collected excise) ✅

---

## 📝 Summary

**Problem**: Pre-paid excise tax (PAID) is in COGS and also subtracted separately = double-counting

**Solution**: Only subtract COLLECTED excise tax, ignore PAID excise tax

**Impact**: ~$150-200 GP understated today, affects all cigar and some tobacco products

**Status**: Issue documented, workaround in place, permanent fix needs database schema change

---

**Recommendation**: Add computed `IsPaid` column to PUExciseEntry for fast queries, then update populate script to use it.

**Your dashboard insight just saved us from systematically understating profit on tobacco products!** 🎉
