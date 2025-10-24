# PUVIEWEXCISETRANSACTION View - Complete Technical Breakdown

## Overview

`PUVIEWEXCISETRANSACTION` is a SQL Server VIEW that combines transaction data with excise tax information. It's the primary data source for gross profit calculations in the Georgia Dashboard.

**Key Insight**: This is NOT a table - it's a virtual view that joins 10+ tables on every query, which is why it's slow for large date ranges.

## View Purpose

Combines regular transaction data with excise tax entries to provide a complete picture of:
- What was sold (item, price, quantity)
- Who bought it (customer info)
- How much excise tax was collected (PUEPRICEC)
- Category/department classification
- Full transaction context

## Tables Involved (10 tables)

### Core Tables
1. **Transaction** - Main transaction header (TransactionNumber, Time, CustomerID, Total)
2. **TransactionEntry** - Line items (ItemID, Price, Cost, Quantity)
3. **PUExciseEntry** - Excise tax data (PriceC = tax amount, SubDescription3 = tax type)

### Reference Tables
4. **Customer** - Customer details (FirstName, LastName, Company, AccountBalance)
5. **Item** - Product master (ItemLookupCode, Description, Price, Cost)
6. **Category** - Product categories (Name, Code)
7. **Department** - Product departments (Name, Code)
8. **Supplier** - Supplier information
9. **Cashier** - Cashier who processed sale
10. **Register** - POS register used
11. **Batch** - Batch number linking register to transaction

## Join Structure (How It Works)

### The Join Chain

```
PUEXCISEENTRY (excise tax data)
    INNER JOIN TransactionEntry (te.ID = pe.TransactionEntryID)
        ↓
    ON TransactionEntry (line items)
        LEFT JOIN Item (te.ItemID = i.ID)
            LEFT JOIN Category (i.CategoryID = cat.ID)
            LEFT JOIN Department (i.DepartmentID = dept.ID)
            LEFT JOIN Supplier (i.SupplierID = s.ID)
        ↓
    ON Transaction (te.TransactionNumber = t.TransactionNumber)
        LEFT JOIN Customer (t.CustomerID = c.ID)
        LEFT JOIN Cashier (t.CashierID = cashier.ID)
        LEFT JOIN Batch (t.BatchNumber = batch.BatchNumber)
            LEFT JOIN Register (batch.RegisterID = reg.ID)
```

### Key Join Details

**INNER JOIN on PUExciseEntry**:
```sql
DBO.PUEXCISEENTRY INNER JOIN
DBO.TRANSACTIONENTRY ON DBO.PUEXCISEENTRY.TRANSACTIONENTRYID = DBO.TRANSACTIONENTRY.ID
```
- This means **only transaction entries with excise tax** are included
- Non-excise items (grocery, general merchandise) are excluded
- This is why the view is called "ExciseTransaction"

**LEFT OUTER JOINs on Reference Tables**:
- Category, Department, Supplier, Customer, Cashier, Register all use LEFT OUTER JOIN
- Means transactions can exist even if reference data is missing
- Result: CNAME (CategoryName) can be NULL

## Important Columns

### Transaction Data
- **TRANSACTIONNUMBER**: Unique transaction ID
- **TIME**: Transaction timestamp (from Transaction table)
- **TRANSACTIONTIME**: Item-level timestamp (from TransactionEntry)
- **CUSTOMERID**: Customer ID reference

### Line Item Data
- **ITEMID**: Product ID
- **PRICE**: Actual selling price per unit
- **COST**: Cost per unit
- **QUANTITY**: Units sold (can be negative for returns)
- **FULLPRICE**: Original/full price

### Excise Tax Data (PUE prefix)
- **PUEPRICEC**: The excise tax amount (this is what gets subtracted from GP)
- **PUESUBDESCRIPTION3**: Tax type (LC23COLL, LC23PAID, LT10COLL, etc.)
- **PUEQUANTITY**: Quantity for excise calculation
- **PUETRANSACTIONENTRYID**: Links to TransactionEntry.ID

### Reference Data
- **CNAME**: Category name (from Category table)
- **CCODE**: Category code
- **DNAME**: Department name
- **DESCRIPTION**: Item description
- **ITEMLOOKUPCODE**: Item SKU/barcode
- **COMPANY**: Customer company name
- **FIRSTNAME**, **LASTNAME**: Customer name

## Gross Profit Calculation

### The Formula Used
```sql
Gross Profit = (PRICE * QUANTITY) - (COST * QUANTITY) - COALESCE(PUEPRICEC, 0)

Revenue = PRICE * QUANTITY
COGS = COST * QUANTITY
Excise Tax = PUEPRICEC
```

### Example Calculation
```
Sale: 1 pack of cigarettes
PRICE: $8.50
COST: $7.20
QUANTITY: 1
PUEPRICEC: $1.01 (excise tax collected)

Revenue = $8.50 × 1 = $8.50
COGS = $7.20 × 1 = $7.20
Excise Tax = $1.01
Gross Profit = $8.50 - $7.20 - $1.01 = $0.29
GP Margin = $0.29 / $8.50 = 3.4%
```

## Why It's Slow

### Performance Issues

1. **Complex Join Chain**: 10+ table joins on every query

2. **No Materialization**: View is recalculated every time
   - Not an indexed view
   - Not a materialized view
   - Pure virtual view

3. **Large Dataset**: 293K+ rows for YTD 2025

4. **Multiple Aggregations**: When grouping by category:
   ```sql
   GROUP BY CNAME  -- Requires joining all 10 tables first, then grouping
   ```

5. **No Covering Indexes**: Joins require table scans

### Query Execution Order
```
1. SQL Server joins all 10 tables → Creates virtual 293K row result set
2. Applies WHERE clause (date filter)
3. Groups by CNAME (Category)
4. Calculates aggregations (SUM, COUNT)
5. Sorts by result
```

**For YTD category query**: Process 293K rows through 10 joins before grouping = 30+ seconds

## Why GP_Daily_Summary is Faster

Pre-aggregated table:
```sql
CREATE TABLE GP_Daily_Summary (
    BusinessDate DATE,
    CategoryID INT,
    CategoryName VARCHAR(100),
    Revenue DECIMAL(18,2),
    COGS DECIMAL(18,2),
    ExciseTax DECIMAL(18,2),
    GrossProfit DECIMAL(18,2),
    ...
)
```

**Benefits**:
- Only 37 rows per day (one per category)
- No joins needed (already denormalized)
- Indexed on BusinessDate
- Simple SUM query: `SELECT SUM(GrossProfit) WHERE BusinessDate BETWEEN ... GROUP BY CategoryName`
- Returns in < 1 second vs 30+ seconds

## Excise Tax Types (PUESUBDESCRIPTION3)

Common values found:
- **LC23COLL** - Large Cigar 23% Collected (most common)
- **LC23PAID** - Large Cigar 23% Pre-paid
- **LT10COLL** - Little Tobacco 10% Collected
- **LT10PAID** - Little Tobacco 10% Pre-paid
- **SL10PAID** - Smokeless 10% Pre-paid
- **ECIG** - E-cigarette tax

**COLL vs PAID**:
- **COLL** (Collected): Tax collected at point of sale → Subtract from GP
- **PAID** (Pre-paid): Tax already paid in COGS → Don't subtract again

## Missing Category Names

Why `CNAME` can be NULL:
```sql
LEFT OUTER JOIN DBO.CATEGORY ON DBO.ITEM.CATEGORYID = DBO.CATEGORY.ID
```

If an item has no CategoryID or CategoryID doesn't exist in Category table:
- CNAME = NULL
- Shows as "Uncategorized" in reports

## Data Quality Notes

### Returns (Negative Quantities)
```sql
WHERE QUANTITY != 0  -- Include both positive and negative
```
- Returns have QUANTITY < 0
- GP calculation handles correctly: negative revenue, negative COGS

### Zero Price Items
```sql
WHERE PRICE > 0  -- Filter out zero-price items when needed
```
- Some promotional items have PRICE = 0
- Can skew margin calculations

### Excise Tax on Returns
- Returns have negative PUEPRICEC (tax refunded)
- GP calculation correctly adds back tax on returns

## Alternative Approaches Tested

### 1. Direct Base Table Query (Failed)
```sql
-- Bypass view, query tables directly
SELECT ... FROM Transaction t
INNER JOIN TransactionEntry te ...
LEFT JOIN PUExciseEntry pe ...
...
```
**Result**: Still times out after 30 seconds (same joins as view)

### 2. NOLOCK Hints (Failed)
```sql
FROM Transaction WITH (NOLOCK)
INNER JOIN TransactionEntry WITH (NOLOCK) ...
```
**Result**: Slightly faster but still times out

### 3. Indexed View (Not Possible)
- Can't create indexed view with complex OUTER JOINs
- SQL Server limitation

### 4. Filtered Index (Minimal Help)
```sql
CREATE INDEX IX_TransactionEntry_Time ON TransactionEntry(TransactionTime)
WHERE TransactionTime >= '2025-01-01'
```
**Result**: Helps with date filter but doesn't solve join problem

## The Only Fast Solution

**Pre-aggregate data into GP_Daily_Summary table**:

### Population Query (used by populate script)
```sql
INSERT INTO GP_Daily_Summary
SELECT
    CAST(te.TransactionTime AS DATE) as BusinessDate,
    cat.ID as CategoryID,
    cat.Name as CategoryName,
    SUM(te.Price * te.Quantity) as Revenue,
    SUM(te.Cost * te.Quantity) as COGS,
    SUM(CASE
        WHEN ett.IsPrePaid = 0 THEN COALESCE(pe.PriceC, 0)
        ELSE 0
    END) as ExciseTax,
    SUM((te.Price * te.Quantity) - (te.Cost * te.Quantity) -
        CASE WHEN ett.IsPrePaid = 0 THEN COALESCE(pe.PriceC, 0) ELSE 0 END
    ) as GrossProfit,
    COUNT(DISTINCT te.TransactionNumber) as TransactionCount,
    COUNT(*) as ItemCount
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
INNER JOIN Category cat ON i.CategoryID = cat.ID
LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
LEFT JOIN ExciseTaxTypes ett ON pe.SubDescription3 = ett.TaxType
WHERE CAST(te.TransactionTime AS DATE) = @date
GROUP BY cat.ID, cat.Name
```

**Why This Works**:
- Runs ONCE per day (or on-demand)
- Stores results permanently
- Future queries are instant (no joins, just SUM on pre-aggregated data)
- Trade-off: Requires maintenance (daily population)

## Summary

### What PUVIEWEXCISETRANSACTION Is
- A VIEW joining 10+ tables
- Combines transaction data with excise tax
- Only includes items with excise tax (INNER JOIN on PUExciseEntry)
- Recalculated on every query

### Why It's Slow
- 293K+ rows for YTD
- Complex multi-table joins
- Not materialized or indexed
- No way to make it fast for aggregate queries

### The Solution
- Pre-aggregate into GP_Daily_Summary table
- Populate once, query many times
- Instant results vs 30+ second timeouts

### Files
- View definition saved to: `/Users/akbarchranya/georgiadashboard/PUVIEWEXCISETRANSACTION_definition.sql`
- Population script: `/Users/akbarchranya/georgiadashboard/populate_gp_summary_range.py`
