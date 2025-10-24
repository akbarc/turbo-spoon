# GP Category Summary - Performance Fix

## Problem
Category queries with accurate excise tax timeout for periods > 1 day:
- PUVIEWEXCISETRANSACTION with GROUP BY: 120+ seconds (times out)
- Need: Fast queries (<5 sec) for all date ranges

## Solution: Pre-Calculated Overlay Table

### Option 1: Use Existing GP_Daily_Summary (FAST - Recommended)
**Pros:**
- Table already exists
- Just needs proper population
- Queries are instant (<1 second)

**Current Issue:**
- Only has 2 dates populated (Jan 1, Oct 15)
- Population script times out

**Fix:**
Populate incrementally (1 day at a time) using the accurate formula:
```sql
-- Only subtract COLLECTED excise (IsPrePaid = 0)
GP = Revenue - COGS - CASE WHEN IsPrePaid = 0 THEN ExciseTax ELSE 0 END
```

### Option 2: Create Category Reference Table
Store excise tax rules per category:
```sql
CREATE TABLE CategoryExciseRules (
    CategoryName VARCHAR(100),
    TaxType VARCHAR(20),
    IsPercentOfCost BIT,
    TaxRate DECIMAL(5,2),  -- For percentage-based
    TaxPerUnit DECIMAL(5,2),  -- For per-ml/per-unit
    UnitType VARCHAR(20)  -- 'ml', 'oz', etc.
)
```

Then calculate on-the-fly using these rules (faster than joining PUExciseEntry).

## Current Excise Tax Rates (ACCURATE)

### Cigars & Tobacco
- **LC23COLL** (Cigars, collected): 23% of wholesale cost
- **LC23PAID** (Cigar GA, pre-paid): 18.69% of wholesale cost
- **LT10COLL** (Little tobacco, collected): 10% of wholesale cost
- **LT10PAID** (Little tobacco, pre-paid): 9.08% of wholesale cost
- **SL10PAID** (Smokeless GA, pre-paid): 9.09% of wholesale cost

### Vapor Products
- **VD07COLL** (Vapor open, collected): 7% of wholesale cost
- **VD07PAID** (Vapor open, pre-paid): 7% of wholesale cost
- **VC05COLL** (Vapor closed, collected): $0.05 per ml
- **VC05PAID** (Vapor closed, pre-paid): $0.05 per ml

### GP Calculation Rule
```
IF IsPrePaid = True (PAID):
    GP = Revenue - COGS
    (excise already in COGS, don't subtract)

IF IsPrePaid = False (COLLECTED):
    GP = Revenue - COGS - ExciseTax
    (you collect from customer and remit to state)
```

## Recommended Next Steps

1. **Populate GP_Daily_Summary incrementally**
   - Start from most recent date backwards
   - Do 1 day at a time to avoid timeouts
   - Schedule nightly population for new day

2. **Add indexes** for speed:
   ```sql
   CREATE INDEX IX_GPDailySummary_Date ON GP_Daily_Summary(BusinessDate)
   CREATE INDEX IX_GPDailySummary_Category ON GP_Daily_Summary(CategoryName)
   ```

3. **Update dashboard** to query GP_Daily_Summary instead of live view

## Files Modified
- `data_foundation/gross_profit.py` - Updated `get_gp_by_category()` with accurate excise logic
- Timeout increased to 120 seconds
- Added NOLOCK hints for speed
- Uses PUVIEWEXCISETRANSACTION + ExciseTaxTypes join

## Current Status
✅ **Today (1 day)**: Works perfectly, accurate excise (5 seconds)
❌ **Multi-day ranges**: Times out (120+ seconds)
🔧 **Solution**: Need pre-calculated summary table
