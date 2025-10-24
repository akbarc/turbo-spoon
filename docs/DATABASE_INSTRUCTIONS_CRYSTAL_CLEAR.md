# 🚨 Canonical Database Instructions (Authoritative) 🚨

These instructions are the single source of truth for generating SQL against the live SQL Server 2008 R2 POS database. Follow them exactly to avoid failures.

## 1) Aliases (mandatory)
- `c` = `dbo.Customer` (never use for Category)
- `cat` = `dbo.Category`
- `t` = `[dbo].[Transaction]` (must be bracketed)
- `te` = `dbo.TransactionEntry`
- `i` = `dbo.Item`
- `ar` = `dbo.AccountReceivable`
- `arh` = `dbo.AccountReceivableHistory`
- `p` = `dbo.Payment`

## 2) Primary keys (exact)
- `Customer.ID`
- `Item.ID`
- `Category.ID`
- `Transaction.TransactionNumber`
- `Payment.ID`
- `AccountReceivable.ID`
- `AccountReceivableHistory.ID` (also used as AR reference number)

## 3) Time columns (exact)
- `t.Time` (not `t.Date`)
- `p.Time` (not `p.Date`)
- `te.TransactionTime` (not `te.Time`)
- `ar.Date` (Date is correct here)

## 4) Safe join map (use these keys)
- `t.CustomerID = c.ID`
- `te.TransactionNumber = t.TransactionNumber`
- `te.ItemID = i.ID`
- `i.CategoryID = cat.ID`
- `ar.CustomerID = c.ID`
- `arh.AccountReceivableID = ar.ID`

## 5) Approved column reference map (only verified fields)
- `Customer (c)`: `ID`, `Name` or `Company` (use whichever exists for your query)
- `Transaction (t)`: `TransactionNumber`, `Time`, `CustomerID`, `Total`, `SalesTax`
- `TransactionEntry (te)`: `ID`, `TransactionNumber`, `ItemID`, `Price`, `Cost`, `Quantity`, `TransactionTime`
- `Item (i)`: `ID`, `Description`, `Price`, `Cost`, `CategoryID`, `ItemLookupCode`
- `Category (cat)`: `ID`, `Name`
- `Payment (p)`: `ID`, `CustomerID`, `Time`, `Amount`, `Comment`
- `AccountReceivable (ar)`: `ID`, `CustomerID`, `Date`, `OriginalAmount`, `TransactionNumber`
- `AccountReceivableHistory (arh)`: `ID`, `AccountReceivableID`, `Amount`, `Comment`, `Date`

If a column is not listed above, do not assume it exists. Query failures frequently come from using non-existent fields.

## 6) SQL Server 2008 R2 constraints
- No window functions (no `OVER(ORDER BY ...)`)
- No `FORMAT()`; use `CAST(... AS DATE)`
- Use `TOP N`, not `LIMIT`
- Prefer subqueries instead of analytic functions

## 7) Tobacco cost uplift rules (profit calculations)
- Use `cat.Name` to detect categories (never `c.Name`)
- Uplifts:
  - `CIGARS`: `Cost * 1.23`
  - `LT-TAX-COLLECTED`: `Cost * 1.10`
- Profit per line should be computed as: `te.Price * te.Quantity - (uplifted_unit_cost * te.Quantity)`

Example uplift expression:
```sql
CASE 
  WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
  WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
  ELSE te.Cost
END
```

## 8) Date filters (approved)
- Today: `CAST(t.Time AS DATE) = CAST(GETDATE() AS DATE)`
- Last 7 days: `t.Time >= DATEADD(DAY, -7, GETDATE())`
- Last 30 days: `t.Time >= DATEADD(DAY, -30, GETDATE())`
- MTD: `t.Time >= DATEADD(DAY, 1 - DAY(GETDATE()), CAST(GETDATE() AS DATE))`
- YTD: `t.Time >= CAST(CAST(YEAR(GETDATE()) AS VARCHAR(4)) + '-01-01' AS DATETIME)`

## 9) Approved query templates (copy these patterns)

Sales revenue by category (last 30 days):
```sql
SELECT cat.Name AS category,
       SUM(te.Price * te.Quantity) AS total_revenue
FROM [dbo].[Transaction] t
JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN Item i ON te.ItemID = i.ID
LEFT JOIN Category cat ON i.CategoryID = cat.ID
WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
GROUP BY cat.Name
ORDER BY total_revenue DESC
```

Gross profit by category (last 30 days) with tobacco uplifts:
```sql
SELECT cat.Name AS category,
       SUM(
         te.Price * te.Quantity - (
           CASE
             WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
             WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
             ELSE te.Cost
           END
         ) * te.Quantity
       ) AS total_profit
FROM [dbo].[Transaction] t
JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN Item i ON te.ItemID = i.ID
LEFT JOIN Category cat ON i.CategoryID = cat.ID
WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
GROUP BY cat.Name
ORDER BY total_profit DESC
```

AR adjustments with notes (manual adjustments only):
```sql
SELECT ar.ID,
       ar.Date,
       ar.OriginalAmount,
       arh.ID AS reference_number,
       arh.Comment AS adjustment_notes,
       c.Name AS customer_name
FROM AccountReceivable ar
LEFT JOIN AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
LEFT JOIN Customer c ON ar.CustomerID = c.ID
WHERE ar.TransactionNumber = 0
```

Payments by customer (last 30 days):
```sql
SELECT c.Name AS customer_name,
       COUNT(*) AS payments,
       SUM(p.Amount) AS total_paid
FROM Payment p
JOIN Customer c ON p.CustomerID = c.ID
WHERE p.Time >= DATEADD(DAY, -30, GETDATE())
GROUP BY c.Name
ORDER BY total_paid DESC
```

Low inventory (heuristic; column differs by deployment):
```sql
-- If Item.QuantityOnHand exists, use it; otherwise use the actual on-hand column available.
SELECT TOP 50 i.Description, i.QuantityOnHand AS on_hand
FROM Item i
WHERE i.QuantityOnHand <= 10
ORDER BY i.QuantityOnHand ASC
```

## 10) Validation checklist (run through every time)
- Aliases match the canonical list (no reusing `c` for Category)
- Primary keys and join keys are correct
- Time columns use `.Time` (except `ar.Date`)
- No window functions or unsupported syntax
- Category checks use `cat.Name`
- `[dbo].[Transaction]` is bracketed wherever referenced
- If querying adjustments, include `AccountReceivableHistory` for notes

## 11) Hard errors to avoid (these will fail)
- `Payment.Date`, `Payment.Type`
- `Customer.CustomerID`, `Item.ItemID`, `Category.CategoryID`
- `Transaction.Date`, `TransactionEntry.Time`
- Using `c.Name` for tobacco category checks
- Window functions on SQL Server 2008 R2

---

This document is intentionally strict and minimal. If a needed column is not listed, verify it directly in `INFORMATION_SCHEMA.COLUMNS` before using it in generated SQL.

---

## CRITICAL ADDENDUM – Field-accurate rules and templates (do not ignore)

### A) Canonical date fields (use these and only these)
- Payment: `p.Time`
- Transaction: `t.Time`
- TransactionEntry: `te.TransactionTime`
- AccountReceivable: `ar.Date`
- AccountReceivableHistory: `arh.Date`

Do NOT use: `arh.Time`, `arh.TransactionDate`, `p.Date`, `t.Date`, `te.Time`.

### B) Safe date ranges and monthly grouping (SQL Server 2008 R2)
- Inclusive start, inclusive end-day: use end < next day
```sql
WHERE t.Time >= '2012-01-01' AND t.Time < DATEADD(DAY, 1, '2025-08-01')
```
- Group by month (no FORMAT):
```sql
SELECT CONVERT(varchar(7), t.Time, 120) AS month -- YYYY-MM
```

### C) Payments vs. Collections (YTD) – correct pattern
- Do NOT try to join `Payment` to `AccountReceivableHistory` on imaginary keys (e.g., `CustomerRefID`).
- Compute separately; for collections, exclude NSF via `arh.Comment`.
```sql
SELECT
  (SELECT COALESCE(SUM(p.Amount), 0)
   FROM dbo.Payment p
   WHERE p.Time >= CAST(CAST(YEAR(GETDATE()) AS VARCHAR(4)) + '-01-01' AS DATETIME)
     AND p.Time <= GETDATE()) AS PaymentsYTD,
  (SELECT COALESCE(SUM(arh.Amount), 0)
   FROM dbo.AccountReceivableHistory arh
   WHERE arh.Date >= CAST(CAST(YEAR(GETDATE()) AS VARCHAR(4)) + '-01-01' AS DATETIME)
     AND arh.Date <= GETDATE()
     AND (arh.Comment IS NULL OR arh.Comment NOT LIKE '%NSF%')) AS CollectionsYTD;
```
- If you must link history to customers, the valid chain is: `AccountReceivableHistory.AccountReceivableID -> AccountReceivable.ID` then `AccountReceivable.CustomerID -> Customer.ID`.

### D) Total sales between two dates, monthly
```sql
SELECT
  CONVERT(varchar(7), t.Time, 120) AS month,  -- YYYY-MM
  SUM(te.Price * te.Quantity) AS total_revenue
FROM [dbo].[Transaction] t
JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
WHERE t.Time >= @start -- e.g., '2012-01-01'
  AND t.Time < DATEADD(DAY, 1, @end) -- e.g., '2025-08-01'
GROUP BY CONVERT(varchar(7), t.Time, 120)
ORDER BY month;
```

### E) Absolutely forbidden columns/joins (common failure sources)
- `AccountReceivableHistory.TransactionDate` – does not exist
- `AccountReceivableHistory.CustomerRefID` – does not exist
- `Payment.Date`, `Transaction.Date`, `TransactionEntry.Time` – wrong; use canonical set above
- Joining `Payment` directly to `AccountReceivableHistory` by customer without going through `AccountReceivable` – wrong

### F) Profit and tobacco uplift recap
- Use `cat.Name` for category checks; never `c.Name`.
- Profit line: `te.Price * te.Quantity - (uplifted te.Cost) * te.Quantity`.
- Uplifts: `CIGARS` = 1.23, `LT-TAX-COLLECTED` = 1.10.

### G) Validation checklist (additions)
- Date fields match canonical per-table list (A)
- Ranges honor inclusive-end via `< DATEADD(DAY, 1, @end)`
- Monthly grouping uses `CONVERT(varchar(7), <DateCol>, 120)`
- Payments vs collections computed separately; no invalid joins
- Only one SELECT statement; no DDL/DML/EXEC; `[dbo].[Transaction]` bracketed

---

These addendum rules are authoritative and must be applied to every query generation. If a required field is unknown, default to the canonical date fields in (A), and prefer separate subqueries over speculative joins.