# Task 12: Database Investigation - Excise Tables

**Date**: October 6, 2025
**Objective**: Connect to actual POS database and discover the EXACT excise logic used by the system

## Key Discoveries

### 1. Excise Tables Found

The POS system has **8 excise-related tables/views**:

| Table/View Name | Type | Purpose |
|----------------|------|---------|
| `PUExciseEntry` | BASE TABLE | Core excise transaction data |
| `PUVIEWEXCISECOLLECT` | VIEW | Aggregated excise collections |
| `PUVIEWEXCISEPAID` | VIEW | Excise paid tracking |
| `PUVIEWEXCISETRANSACTION` | VIEW | Base view joining all excise data |
| `VIEWEXCISETAXCOLLECT` | VIEW | Tax collection view |
| `VIEWEXCISETAXPAID` | VIEW | Tax paid view |
| `VIEWHOLDEXCISETAX` | VIEW | Held excise tax |
| `VIEWPOEXCISETAX` | VIEW | Purchase order excise tax |

### 2. Core Table: PUExciseEntry

**Structure** (18 columns):
```
ID                  int       NOT NULL
TransactionNumber   nvarchar(30) NOT NULL
TransactionEntryID  int       NOT NULL
FullPrice           money     NOT NULL
Price               money     NOT NULL
Cost                money     NOT NULL
PriceA              money     NOT NULL
PriceB              money     NOT NULL (can be NULL)
PriceC              money     NOT NULL  ← **EXCISE TAX AMOUNT**
Quantity            float     NOT NULL
SalesTax            money     NOT NULL
ItemID              int       NOT NULL
Weight              float     NOT NULL
TareWeight          float     NOT NULL
SubDescription1     nvarchar(30) NOT NULL
SubDescription2     nvarchar(30) NOT NULL
SubDescription3     nvarchar(30) NOT NULL  ← **EXCISE CATEGORY CODE**
TransactionTime     datetime  NULL
```

**Critical Finding**: `PriceC` stores the **per-unit excise tax amount**

### 3. Excise Calculation Logic (from PUVIEWEXCISECOLLECT)

```sql
-- TOTAL EXCISE COLLECTED PER TRANSACTION:
SUM(PUEPRICEC * PUEQUANTITY) AS TOTALEXCISECOLLECT

-- This is equivalent to:
SUM(PriceC * Quantity) AS TOTALEXCISECOLLECT
```

**Where**:
- `PUEPRICEC` = PriceC from PUExciseEntry = excise tax per unit
- `PUEQUANTITY` = Quantity from PUExciseEntry = number of units sold

### 4. Excise Category Codes (SubDescription3)

The POS system uses these category codes in `SubDescription3`:

| Code | Category | Calculation |
|------|----------|-------------|
| `LT10COLL` | Loose Tobacco | `SUM(Cost * Quantity)` |
| `SL10COLL` | Smokeless | `SUM(Cost * Quantity)` |
| `LC23COLL` | Large Cigars | `SUM(Cost * Quantity)` |
| `LC25COLL` | Little Cigars | `SUM(Cost * Quantity)` + Weight tracking |
| `VO07COLL` | Vapors Open | `SUM(Cost * Quantity)` |
| `VD07COLL` | Vapors Device | `SUM(Cost * Quantity)` |
| `VC05COLL` | Vapors Closed | `SUM(Cost * Quantity)` + Weight tracking |

### 5. Complete Data Flow

```
TRANSACTION (main sales table)
    ↓
TRANSACTIONENTRY (line items)
    ↓
PUExciseEntry (excise data for specific items)
    ↓ (joined with)
ITEM (product details, including SubDescription3 category code)
    ↓
PUVIEWEXCISETRANSACTION (combines all data)
    ↓
PUVIEWEXCISECOLLECT (aggregates by transaction and category)
```

### 6. Exact Excise Query Logic

From `PUVIEWEXCISECOLLECT` view:

```sql
SELECT
    MAX(TIME) AS DATE,
    MAX(TRANSACTIONNUMBER) AS TRANSACTIONNUMBER,
    MAX(ACCOUNTNUMBER) AS ACCOUNTNUMBER,
    MAX(COMPANY) AS COMPANY,

    -- Category breakdowns (by SubDescription3 code):
    CASE WHEN PUESUBDESCRIPTION3 = 'LT10COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS LOOSETOBACCO,
    CASE WHEN PUESUBDESCRIPTION3 = 'SL10COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS SMOKELESS,
    CASE WHEN PUESUBDESCRIPTION3 = 'LC23COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS LARGECIGARS,
    CASE WHEN PUESUBDESCRIPTION3 = 'LC25COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS LITTLECIGARS,
    CASE WHEN PUESUBDESCRIPTION3 = 'VO07COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS VAPORSOPEN,
    CASE WHEN PUESUBDESCRIPTION3 = 'VD07COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS VAPORSDEVICE,
    CASE WHEN PUESUBDESCRIPTION3 = 'VC05COLL'
         THEN SUM(PUECOST * PUEQUANTITY) ELSE 0 END AS VAPORSCLOSED,

    -- TOTAL EXCISE TAX COLLECTED:
    SUM(PUEPRICEC * PUEQUANTITY) AS TOTALEXCISECOLLECT,

    -- TOTAL SALES:
    SUM(PUEPRICE * PUEQUANTITY) AS TOTALSALES

FROM DBO.PUVIEWEXCISETRANSACTION
GROUP BY TRANSACTIONNUMBER, PUESUBDESCRIPTION3
```

## Critical Implementation Requirements

### For Dashboard Queries

To match the POS system exactly, we must:

1. **Join to PUExciseEntry table**:
   ```sql
   LEFT JOIN PUExciseEntry pue ON te.ID = pue.TransactionEntryID
   ```

2. **Calculate excise using PriceC**:
   ```sql
   SUM(pue.PriceC * pue.Quantity) AS excise_tax
   ```

3. **Filter by SubDescription3 categories** if needed:
   ```sql
   WHERE i.SubDescription3 IN ('LT10COLL', 'SL10COLL', 'LC23COLL', 'LC25COLL',
                                'VO07COLL', 'VD07COLL', 'VC05COLL')
   ```

### Why Our Current Approach is Wrong

**Current (incorrect)**:
```sql
-- Using Item.PriceC - this is the ITEM MASTER price, not the transaction price
SUM(i.PriceC * te.Quantity) AS excise_tax
```

**Correct**:
```sql
-- Using PUExciseEntry.PriceC - this is the ACTUAL excise charged on the transaction
SUM(pue.PriceC * pue.Quantity) AS excise_tax
```

**The difference**:
- `Item.PriceC` = current/default excise tax in the item master (static)
- `PUExciseEntry.PriceC` = actual excise tax charged on that specific transaction (dynamic, historical)

## Files Created

1. `investigate_excise_tables.py` - Initial discovery script
2. `investigate_excise_simple.py` - Simplified investigation
3. `examine_excise_view.py` - View definition extraction
4. `examine_base_excise_view.py` - Base view analysis
5. `PUVIEWEXCISECOLLECT_definition.sql` - Saved view definition
6. `PUVIEWEXCISETRANSACTION_definition.sql` - Saved base view definition

## Next Steps

1. Update all dashboard queries to use `PUExciseEntry.PriceC` instead of `Item.PriceC`
2. Add proper joins to `PUExciseEntry` table
3. Test queries against known good data from the POS system
4. Verify totals match between dashboard and PUVIEWEXCISECOLLECT
