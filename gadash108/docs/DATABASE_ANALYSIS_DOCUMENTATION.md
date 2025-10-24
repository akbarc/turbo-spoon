# Georgia Dashboard Database Analysis & Documentation

## Database Connection Configuration

**Server**: SQL Server 2008 R2 at 10.1.10.105
**Database**: GAWDB (Georgia Warehouse Database)
**Connection Method**: pymssql with TDS 7.0 protocol
**Connection Pool**: 3 max connections with automatic cleanup

## Core Database Tables

1. **Customer** - Customer master data
2. **Transaction** - Sales transaction headers
3. **TransactionEntry** - Sales line items
4. **Item** - Product/item master
5. **Category** - Product categories
6. **Payment** - Payment records
7. **AccountReceivable** - AR balances
8. **AccountReceivableHistory** - AR transaction history

## Table Relationships & Keys

- Transaction → Customer: `t.CustomerID = c.ID`
- TransactionEntry → Transaction: `te.TransactionNumber = t.TransactionNumber`
- TransactionEntry → Item: `te.ItemID = i.ID`
- Item → Category: `i.CategoryID = cat.ID`
- Payment → Customer: `p.CustomerID = c.ID`
- AccountReceivable → Customer: `ar.CustomerID = c.ID`
- AccountReceivableHistory → AccountReceivable: `arh.AccountReceivableID = ar.ID`

## Critical Date Fields (SQL Server 2008 R2)

- **Transaction**: `t.Time` (NOT t.Date)
- **TransactionEntry**: `te.TransactionTime` (NOT te.Time)
- **Payment**: `p.Time` (NOT p.Date)
- **AccountReceivable**: `ar.Date`
- **AccountReceivableHistory**: `arh.Date`

## SQL Patterns & Best Practices

### Standard Table Aliases
```sql
c = Customer
cat = Category
t = [dbo].[Transaction]  -- Must be bracketed
te = TransactionEntry
i = Item
ar = AccountReceivable
arh = AccountReceivableHistory
p = Payment
```

### Tobacco Cost Uplift Rules
- CIGARS: Cost * 1.23
- LT-TAX-COLLECTED: Cost * 1.10

### Date Range Filters
```sql
-- Today
CAST(t.Time AS DATE) = CAST(GETDATE() AS DATE)

-- Last 30 days
t.Time >= DATEADD(DAY, -30, GETDATE())

-- YTD
t.Time >= CAST(CAST(YEAR(GETDATE()) AS VARCHAR(4)) + '-01-01' AS DATETIME)
```

## Database Query Patterns

### Sales Analysis Pattern
```sql
SELECT cat.Name AS category,
       SUM(te.Price * te.Quantity) AS total_revenue
FROM [dbo].[Transaction] t
JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN Item i ON te.ItemID = i.ID
LEFT JOIN Category cat ON i.CategoryID = cat.ID
WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
GROUP BY cat.Name
```

### Customer Balance Calculation
```sql
SELECT ar.CustomerID,
       SUM(arh.Amount) as Balance
FROM AccountReceivableHistory arh
JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
GROUP BY ar.CustomerID
```

## Key Discoveries

1. **Connection Management**: Fresh connections prevent TDS assertion errors
2. **Date Column Naming**: Inconsistent between tables (Time vs Date)
3. **Transaction Table**: Must always be bracketed as [dbo].[Transaction]
4. **Customer Names**: Use COALESCE(Company, FirstName + ' ' + LastName)
5. **AR Structure**: History table contains all balance changes
6. **Payment vs Collections**: Separate tracking through Payment and ARHistory tables