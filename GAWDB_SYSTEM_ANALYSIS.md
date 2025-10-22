# GAWDB System Analysis

## Overview
**System**: Microsoft Retail Management System (RMS) with SQL Server 2008 R2
**Database**: GAWDB (General Alcohol & Wholesale Database)
**Reports**: Crystal Reports (.def files)
**Generated**: 2025-10-22

## Database Size
- **114 tables** total
- **4.7M+ transaction records**
- **12,741 products**
- **2,856 customers**

## Key Excise Tax Tracking

### Excise Tax Categories
Your system tracks excise taxes using `PUExciseEntry.SubDescription3` field with these codes:

**Collected from Customers (COLL suffix):**
- `LT10COLL` - Loose Tobacco
- `SL10COLL` - Smokeless Tobacco
- `LC23COLL` - Large Cigars
- `LC25COLL` - Little Cigars
- Vapors Open, Device, Closed

**Paid to Government/Suppliers (PAID suffix):**
- `LT10PAID` - Loose Tobacco
- `SL10PAID` - Smokeless Tobacco
- `LC23PAID` - Large Cigars
- `LC25PAID` - Little Cigars
- Vapors Open, Device, Closed

### Excise Tax Views (Already Built into Your System)
1. **PUVIEWEXCISECOLLECT** - Raw excise tax collected data
2. **PUVIEWEXCISEPAID** - Raw excise tax paid data
3. **VIEWEXCISETAXCOLLECT** - Aggregated excise collected by transaction
4. **VIEWEXCISETAXPAID** - Aggregated excise paid by transaction
5. **PUVIEWEXCISETRANSACTION** - Complete transaction with excise details
6. **VIEWPOEXCISETAX** - Purchase orders with excise tax
7. **VIEWHOLDEXCISETAX** - Held transactions with excise

## Key Business Views

### Transaction & Sales
- **PUBLIC_Transaction** - Clean view of all transactions
- **PUBLIC_TransactionEntry** - Transaction line items
- **vw_TransactionGrossProfit** - Complete profit analysis per transaction
  - Includes: Revenue, COGS, Excise Tax, Gross Profit
  - Joins: Transaction, Customer, Item, Category, Department, PUExciseEntry

### Products & Inventory
- **PUBLIC_Item** - Product catalog
- **PUBLIC_Category** - Product categories (83 total)
- **PUBLIC_Department** - Departments
- **VIEWITEMMOVEMENT** - Item sales and inventory movements
- **VIEWITEMMOVEMENTHISTORY** - Historical inventory changes

### Customers & Payments
- **PUBLIC_Customer** - Customer master
- **PUBLIC_TenderEntry** - Payment methods per transaction
- **VIEWTENDERS** - Tender/payment analysis

## Table Relationships

```
Transaction (238K)
├── TransactionEntry (4.7M) - Line items
│   ├── PUExciseEntry (4.7M) - Excise tax details
│   └── TaxEntry (4.7M) - Sales tax details
├── Customer (2.8K)
├── TenderEntry (366K) - Payments
└── DailySales (576K) - Daily aggregates

Item (12.7K)
├── Category (83)
├── Department
└── Supplier (754)
```

## Data Points Available

### Sales Analysis
- Transaction date/time
- Customer purchase history
- Product sales by category/department
- Gross profit per transaction
- Price levels (A, B, C, Sale)
- Discounts and promotions
- Returns and exchanges

### Excise Tax Analysis (Your Key Use Case!)
- Excise collected vs paid (COLL vs PAID)
- Breakdown by tobacco/cigar/vapor type
- Customer tax exempt status (TaxExempt, TaxNumber, TLIC)
- Weight-based calculations for certain products
- Purchase order excise tracking

### Customer Analysis
- Account balances & credit limits
- Total sales per customer
- Visit frequency
- Total savings (discounts received)
- Price level assignments
- Tax exempt customers

### Inventory Analysis
- Current quantities
- Last sold / last received dates
- Reorder points & restock levels
- Item movement history
- Physical inventory counts
- Supplier performance

## Product Classification

### Item Fields for Categorization
- `CategoryID` - Category (1 of 83)
- `DepartmentID` - Department
- `SubDescription1`, `SubDescription2`, `SubDescription3` - Additional classifiers
- `ItemType` - Item type code
- `Taxable` - Tax status
- `FoodStampable` - EBT eligible
- `Consignment` - Consignment item

## Sample Queries from Views

### Total Sales by Category
```sql
SELECT
    cat.Name as CategoryName,
    SUM(te.Price * te.Quantity) as TotalSales,
    SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
    COUNT(DISTINCT t.CustomerID) as UniqueCustomers
FROM [Transaction] t
JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
JOIN Item i ON te.ItemID = i.ID
JOIN Category cat ON i.CategoryID = cat.ID
WHERE t.Time >= '2024-01-01'
GROUP BY cat.Name
ORDER BY TotalSales DESC
```

### Excise Tax Collected vs Paid
```sql
SELECT
    CAST(Date as DATE) as SalesDate,
    SUM(LOOSETOBACCO) as LooseTobacco,
    SUM(SMOKELESS) as Smokeless,
    SUM(LARGECIGARS) as LargeCigars,
    SUM(LITTLECIGARS) as LittleCigars,
    SUM(TOTALEXCISECOLLECT) as TotalExciseCollected
FROM VIEWEXCISETAXCOLLECT
WHERE Date >= '2024-01-01'
GROUP BY CAST(Date as DATE)
ORDER BY SalesDate DESC
```

### Top Customers by Sales
```sql
SELECT TOP 20
    c.Company,
    c.FirstName + ' ' + c.LastName as CustomerName,
    c.TotalSales,
    c.TotalVisits,
    c.LastVisit,
    c.AccountBalance
FROM Customer c
ORDER BY c.TotalSales DESC
```

## Dashboard Opportunities

### 1. Excise Tax Dashboard ✅ HIGH PRIORITY
- Collected vs Paid comparison
- Breakdown by product type (tobacco, cigars, vapors)
- Tax exempt customer transactions
- Monthly/quarterly tax reports
- Purchase order excise tracking

### 2. Sales Performance Dashboard
- Daily/weekly/monthly sales trends
- Category performance
- Gross profit analysis
- Top selling items
- Discount impact analysis

### 3. Customer Intelligence Dashboard
- RFM analysis (Recency, Frequency, Monetary)
- Customer lifetime value
- Tax exempt customers
- Account receivables aging
- Customer purchase patterns

### 4. Inventory Management Dashboard
- Stock levels vs reorder points
- Slow-moving items
- Item movement history
- Supplier performance
- Physical inventory variance

### 5. Cashier & Register Analysis
- Sales by cashier
- Tender type analysis
- Void/return patterns
- Hourly sales patterns

## Next Steps

1. **Build Excise Tax Analytics** - Use VIEWEXCISETAXCOLLECT and VIEWEXCISETAXPAID
2. **Leverage vw_TransactionGrossProfit** - Already has profit calculations
3. **Use PUBLIC_ views** - They're optimized for reporting
4. **Integrate with Dashboard** - Replace generic queries with system-specific ones

## Notes
- System uses tax exempt tracking (Customer.TaxExempt, Customer.TaxNumber, Customer.CustomText2 as TLIC)
- Multiple price levels supported (Price, PriceA, PriceB, PriceC, SalePrice)
- Extensive audit trail (AuditLog, RecordDeletedLog)
- Supports holds, layaways, exchanges
- Multi-store capable (StoreID in most tables)
