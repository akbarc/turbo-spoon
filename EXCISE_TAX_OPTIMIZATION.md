# Excise Tax Query Optimization Notes

## Problem
The existing `VIEWEXCISETAXCOLLECT` view is slow because it stacks 3 views:
- `VIEWEXCISETAXCOLLECT` → `PUVIEWEXCISECOLLECT` → `PUVIEWEXCISETRANSACTION`
- Processing 4.7M rows from PUExciseEntry table
- Multiple MAX() and CASE statements on entire dataset

## How Excise Tax Works in GAWDB

### Key Tables
- **PUExciseEntry** (4.7M rows) - Contains excise tax data per transaction line
- **Transaction** - Transaction header with date/time
- **Customer** - Tax exempt status

### Key Fields in PUExciseEntry
- `TransactionEntryID` - Links to TransactionEntry
- `TransactionNumber` - Transaction identifier
- `TransactionTime` - Transaction timestamp (use this for date filtering!)
- `SubDescription3` - Excise tax category code (e.g., 'LT10COLL', 'SL10COLL')
- `PriceC` - **THE EXCISE TAX AMOUNT** (this is what you sum!)
- `Price` - Sale price
- `Cost` - Product cost
- `Quantity` - Quantity sold
- `Weight` - For weight-based taxes

### Excise Category Codes
**Collected from Customers (COLL suffix):**
- `LT10COLL` - Loose Tobacco (10% rate)
- `SL10COLL` - Smokeless Tobacco (10% rate)
- `LC23COLL` - Large Cigars (23% rate)
- `LC25COLL` - Little Cigars (25% rate)
- `VO07COLL` - Vapors Open (7% rate)
- `VD07COLL` - Vapors Device (7% rate)
- `VC05COLL` - Vapors Closed (5% rate)

**Paid to Suppliers/Government (PAID suffix):**
- Same codes but with `PAID` instead of `COLL`

## Optimized Query for Executive Dashboard

### Total Excise Tax by Period (Fast Query)
```sql
SELECT
    SUM(CASE WHEN SubDescription3 = 'LT10COLL' THEN PriceC * Quantity ELSE 0 END) as LooseTobacco,
    SUM(CASE WHEN SubDescription3 = 'SL10COLL' THEN PriceC * Quantity ELSE 0 END) as Smokeless,
    SUM(CASE WHEN SubDescription3 = 'LC23COLL' THEN PriceC * Quantity ELSE 0 END) as LargeCigars,
    SUM(CASE WHEN SubDescription3 = 'LC25COLL' THEN PriceC * Quantity ELSE 0 END) as LittleCigars,
    SUM(CASE WHEN SubDescription3 = 'VO07COLL' THEN PriceC * Quantity ELSE 0 END) as VaporsOpen,
    SUM(CASE WHEN SubDescription3 = 'VD07COLL' THEN PriceC * Quantity ELSE 0 END) as VaporsDevice,
    SUM(CASE WHEN SubDescription3 = 'VC05COLL' THEN PriceC * Quantity ELSE 0 END) as VaporsClosed,
    SUM(PriceC * Quantity) as TotalExciseTax
FROM PUExciseEntry
WHERE TransactionTime >= '2025-10-01'
  AND TransactionTime < '2025-11-01'
  AND SubDescription3 LIKE '%COLL'  -- Only collected (not paid)
```

### Excise Tax by Day (for trends)
```sql
SELECT
    CAST(TransactionTime as DATE) as SalesDate,
    SUM(PriceC * Quantity) as DailyExciseTax,
    COUNT(DISTINCT TransactionNumber) as TransactionCount
FROM PUExciseEntry
WHERE TransactionTime >= '2025-10-01'
  AND TransactionTime < '2025-11-01'
  AND SubDescription3 LIKE '%COLL'
GROUP BY CAST(TransactionTime as DATE)
ORDER BY SalesDate
```

### Excise Tax with Customer Info (slower but detailed)
```sql
SELECT
    CAST(pue.TransactionTime as DATE) as SalesDate,
    c.Company,
    c.TaxExempt,
    c.TaxNumber,
    SUM(CASE WHEN pue.SubDescription3 = 'LT10COLL' THEN pue.PriceC * pue.Quantity ELSE 0 END) as LooseTobacco,
    SUM(CASE WHEN pue.SubDescription3 = 'SL10COLL' THEN pue.PriceC * pue.Quantity ELSE 0 END) as Smokeless,
    SUM(pue.PriceC * pue.Quantity) as TotalExcise
FROM PUExciseEntry pue
JOIN [Transaction] t ON pue.TransactionNumber = t.TransactionNumber
LEFT JOIN Customer c ON t.CustomerID = c.ID
WHERE pue.TransactionTime >= '2025-10-01'
  AND pue.TransactionTime < '2025-11-01'
  AND pue.SubDescription3 LIKE '%COLL'
GROUP BY CAST(pue.TransactionTime as DATE), c.Company, c.TaxExempt, c.TaxNumber
ORDER BY SalesDate, TotalExcise DESC
```

## Why This is Faster

1. **Direct Table Access**: Query PUExciseEntry directly, skip nested views
2. **Date Filter First**: Use TransactionTime column (indexed) to filter before aggregation
3. **Single Pass**: One GROUP BY instead of multiple view aggregations
4. **Selective Categories**: Use `LIKE '%COLL'` to filter only collected taxes

## Performance Tips

1. **Always filter by date** - Don't scan all 4.7M rows
2. **Use TransactionTime** in PUExciseEntry (faster than joining to Transaction for date)
3. **Add index** if needed: `CREATE INDEX idx_transtime ON PUExciseEntry(TransactionTime, SubDescription3)`
4. **Limit date ranges** - Weekly/monthly queries are fast, yearly can be slow
5. **Use TOP** for samples: `SELECT TOP 1000 ...` when testing

## For Detailed Reports

The "PU Excise Detailed Sales Report" likely uses `PUVIEWEXCISETRANSACTION` which joins:
- Transaction (header info)
- TransactionEntry (line items)
- PUExciseEntry (excise details)
- Customer (tax exempt status)
- Item (product info)

This is slow but provides complete transaction detail. For dashboard summaries, use the optimized queries above.
