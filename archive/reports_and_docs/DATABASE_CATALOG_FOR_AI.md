# 🚨 COMPLETE DATABASE CATALOG FOR AI QUERY GENERATION 🚨
**CRITICAL: Read this entire document before generating ANY SQL queries**

## 🔥 MOST CRITICAL WARNINGS - READ FIRST 🔥
## Unless otherwise indicated, you should always use like, not exact, for customers names. 
### ⚠️ COLUMN NAME MISTAKES TO AVOID ⚠️
1. **Payment table uses `Time` NOT `Date`** - Always use `p.Time` never `p.Date`
2. **Transaction table uses `Time` NOT `Date`** - Always use `t.Time` never `t.Date`  
3. **TransactionEntry uses `TransactionTime` NOT `Time`** - Always use `te.TransactionTime`
4. **Customer primary key is `ID` NOT `CustomerID`** - Always use `c.ID`
5. **Item primary key is `ID` NOT `ItemID`** - Always use `i.ID`
6. **Category primary key is `ID` NOT `CategoryID`** - Always use `cat.ID`
7. **Payment table has NO CheckNumber column** - Check details are in `Comment` field
8. **Payment table has NO PaymentNumber, ReferenceNumber, or PaymentDate columns**

### 🛡️ REQUIRED SQL PRACTICES
- **ALWAYS** bracket table names: `[dbo].[Transaction]` not `dbo.Transaction`
- **ALWAYS** use UNIQUE table aliases - NEVER duplicate:
  - `c` = Customer (NOT Category!)
  - `cat` = Category 
  - `t` = Transaction
  - `te` = TransactionEntry
  - `i` = Item
  - `ar` = AccountReceivable
  - `arh` = AccountReceivableHistory
  - `p` = Payment
- **CRITICAL**: When referencing Category.Name for tobacco uplifts, use `cat.Name` NOT `c.Name`
- **NEVER** use `FORMAT()` function - use `CAST(field AS DATE)` instead
- **ALWAYS** parameterize with `%s` not `?`
- **ALWAYS** check if joins are on correct column names before executing
- **NEVER** use text/ntext columns in GROUP BY - use CAST(column AS NVARCHAR(MAX)) or exclude from GROUP BY
- **TEXT/NTEXT COLUMNS**: Customer.Notes, Transaction.Comment, TransactionEntry.Comment, Payment.Comment - these CANNOT be in GROUP BY

### ⛔ TEXT/NTEXT COLUMN HANDLING - CRITICAL FOR GROUP BY
**SQL Server 2008 R2 Error**: "The text, ntext, and image data types cannot be compared or sorted"

**Columns that are TEXT/NTEXT type (CANNOT be in GROUP BY)**:
- `Customer.Notes` - text type
- `Transaction.Comment` - nvarchar(255) 
- `TransactionEntry.Comment` - text type
- `Payment.Comment` - text type
- `Item.Notes` - text type

**SOLUTIONS**:
```sql
-- ❌ WRONG - Will cause error:
GROUP BY c.ID, c.Notes, t.Comment  

-- ✅ CORRECT Option 1 - Exclude text columns from GROUP BY:
GROUP BY c.ID  -- Only group by non-text columns

-- ✅ CORRECT Option 2 - Convert to NVARCHAR if needed:
GROUP BY c.ID, CAST(c.Notes AS NVARCHAR(MAX))

-- ✅ CORRECT Option 3 - Use aggregation for text columns:
SELECT c.ID, MAX(c.Notes) as Notes
GROUP BY c.ID
```

### 🚨 PAYMENT TABLE ERROR PREVENTION TEMPLATE
**Before using Payment table, copy this template:**
```sql
-- ✅ CORRECT Payment table columns (ONLY these exist):
SELECT 
    p.ID,           -- Primary key ✅
    p.CustomerID,   -- FK to Customer.ID ✅
    p.Time,         -- Payment datetime (NOT Date!) ✅
    p.Amount,       -- Payment amount ✅
    p.Comment,      -- Payment notes (includes check numbers) ✅
    p.BatchID,      -- Batch ID ✅
    p.CreatedBy,    -- Who entered payment ✅
    p.CreatedDate   -- When record was created ✅
    -- NO p.Type column exists!
FROM dbo.Payment p
WHERE p.Time >= DATEADD(month, -1, GETDATE())  -- Use Time not Date!

-- ❌ WRONG columns that DO NOT EXIST:
-- p.CheckNumber, p.PaymentNumber, p.ReferenceNumber, 
-- p.Date, p.PaymentDate, p.TransactionDate
```

## Database Overview
- **Database Name**: GAWDB
- **Server**: SQL Server 2008 R2
- **Total Records**: 4.6+ million transaction line items
- **Date Range**: 2012-12-07 to date (13+ years)
- **Business Type**: C-store distributor/wholesaler Point of Sale System

## Critical SQL Server 2008 R2 Compatibility Notes
- Use `CAST(date_field AS DATE)` instead of `FORMAT()` function
- Use `%s` parameterization, not `?`
- Always bracket reserved keywords: `[dbo].[Transaction]`
- Avoid complex CTEs and window functions
- Use `ISNULL()` instead of `COALESCE()` when possible
- **NO WINDOW FUNCTIONS WITH OVER(ORDER BY)** - Not supported in SQL Server 2008 R2
- **NO RUNNING TOTALS in SQL** - Calculate in application layer instead

## Core Tables and Relationships

## 🗂️ COMPLETE TABLE SCHEMAS - EVERY COLUMN DEFINED

### 1. [dbo].[Transaction] - Transaction Headers ⭐ MAIN SALES TABLE
**🔑 Primary Key**: `TransactionNumber` (int) - NEVER use any other field as PK
**📝 Description**: Main transaction records (sales, refunds, voids)
**📊 Record Count**: ~500,000+ transactions
**🏷️ Recommended Alias**: `t`

**🚨 CRITICAL COLUMNS - EXACT NAMES**:
```sql
-- EXACT COLUMN NAMES AND TYPES:
TransactionNumber    int           PRIMARY KEY ⭐
Time                datetime      🚨 NOT 'Date' - use 'Time'
CustomerID          int           🔗 FK to Customer.ID  
CashierID           int           Employee who processed
Total               money         Final transaction total
SalesTax            money         Tax amount
BatchNumber         int           Daily batch grouping
StoreID             int           Store identifier
Comment             nvarchar(255) Transaction notes (check numbers, NSF notices)
ReferenceNumber     nvarchar(50)  Order/reference/adjustment number  
Status              int           Transaction status code (0=normal)
CreatedDateTime     datetime      Record creation time
ModifiedDateTime    datetime      Last modification
```

**🔗 FOREIGN KEY RELATIONSHIPS**:
- `t.CustomerID` → `c.ID` (Customer table)
- `t.TransactionNumber` ← `te.TransactionNumber` (TransactionEntry table)
- `t.TransactionNumber` ← `ar.TransactionNumber` (AccountReceivable table)
- `t.TransactionNumber` ← `tender.TransactionNumber` (TenderEntry table)

**✅ TESTED QUERY PATTERNS**:
```sql
-- ✅ CORRECT: Daily sales with proper column names
SELECT 
    CAST(t.Time AS DATE) as sale_date,
    COUNT(t.TransactionNumber) as transaction_count,
    SUM(t.Total) as total_sales,
    AVG(t.Total) as avg_transaction_value,
    SUM(t.SalesTax) as total_tax_collected
FROM [dbo].[Transaction] t
WHERE t.Time >= DATEADD(day, -30, GETDATE())
    AND t.Status = 1  -- Active transactions only
GROUP BY CAST(t.Time AS DATE)
ORDER BY sale_date DESC;

-- ✅ CORRECT: Customer transaction analysis  
SELECT 
    c.Company,
    COUNT(t.TransactionNumber) as transaction_count,
    SUM(t.Total) as total_spent,
    MAX(t.Time) as last_purchase_date,
    MIN(t.Time) as first_purchase_date
FROM [dbo].[Transaction] t
INNER JOIN dbo.Customer c ON t.CustomerID = c.ID
WHERE t.Time >= DATEADD(year, -1, GETDATE())
GROUP BY c.ID, c.Company
HAVING COUNT(t.TransactionNumber) > 10
ORDER BY total_spent DESC;

-- ✅ CORRECT: Delivery vs Pickup analysis using Comment field
SELECT 
    CASE 
        WHEN t.Comment LIKE '%pick up%' OR t.Comment LIKE '%pickup%' THEN 'Pickup'
        WHEN t.Comment LIKE '%delivery%' OR t.Comment LIKE '%deliver%' THEN 'Delivery'
        WHEN t.Comment IS NULL OR t.Comment = '' THEN 'Unknown'
        ELSE 'Other'
    END as fulfillment_method,
    COUNT(t.TransactionNumber) as transaction_count,
    SUM(t.Total) as total_revenue,
    AVG(t.Total) as avg_order_value
FROM [dbo].[Transaction] t
WHERE t.Time >= DATEADD(month, -3, GETDATE())
    AND t.Total > 0  -- Exclude returns/voids
GROUP BY CASE 
    WHEN t.Comment LIKE '%pick up%' OR t.Comment LIKE '%pickup%' THEN 'Pickup'
    WHEN t.Comment LIKE '%delivery%' OR t.Comment LIKE '%deliver%' THEN 'Delivery'
    WHEN t.Comment IS NULL OR t.Comment = '' THEN 'Unknown'
    ELSE 'Other'
END
ORDER BY total_revenue DESC;
```

**❌ COMMON MISTAKES TO AVOID**:
```sql
-- ❌ WRONG: Using 'Date' instead of 'Time'
SELECT t.Date FROM [dbo].[Transaction] t  -- ERROR: No 'Date' column!

-- ❌ WRONG: Using wrong join columns
SELECT * FROM [dbo].[Transaction] t
JOIN dbo.Customer c ON t.CustomerID = c.CustomerID  -- ERROR: Use c.ID!

-- ✅ CORRECT: Proper column names and joins
SELECT * FROM [dbo].[Transaction] t  
JOIN dbo.Customer c ON t.CustomerID = c.ID  -- CORRECT!
```

**Query Examples**:
```sql
-- Daily sales
SELECT CAST(Time AS DATE) as date, SUM(Total) as sales 
FROM [dbo].[Transaction] 
WHERE Time >= DATEADD(day, -30, GETDATE())
GROUP BY CAST(Time AS DATE)

-- Customer transaction count
SELECT CustomerID, COUNT(*) as transactions
FROM [dbo].[Transaction] 
WHERE Time >= DATEADD(day, -90, GETDATE())
GROUP BY CustomerID

-- Delivery/Pickup analysis using Comment field
SELECT 
    CASE 
        WHEN t.Comment LIKE '%pick up%' OR t.Comment LIKE '%pick-up%' OR t.Comment LIKE '%pickup%' THEN 'Pickup'
        WHEN t.Comment LIKE '%delivery%' OR t.Comment LIKE '%deliver%' THEN 'Delivery' 
        ELSE 'Other'
    END as transaction_type,
    COUNT(*) as transaction_count,
    SUM(t.Total) as total_value
FROM [dbo].[Transaction] t
WHERE t.Time >= DATEADD(year, -1, GETDATE())
GROUP BY CASE 
    WHEN t.Comment LIKE '%pick up%' OR t.Comment LIKE '%pick-up%' OR t.Comment LIKE '%pickup%' THEN 'Pickup'
    WHEN t.Comment LIKE '%delivery%' OR t.Comment LIKE '%deliver%' THEN 'Delivery'
    ELSE 'Other'
END
```

### 2. dbo.TransactionEntry - Line Item Details ⭐ CORE SALES DATA
**🔑 Primary Key**: `ID` (int) - Unique line item identifier
**📝 Description**: Individual items/products sold in each transaction (4.6M+ records)
**📊 Record Count**: 4,600,000+ line items (main transaction detail table)
**🏷️ Recommended Alias**: `te`

**🚨 CRITICAL COLUMNS - EXACT NAMES**:
```sql
-- EXACT TRANSACTIONENTRY SCHEMA:
ID                  int           PRIMARY KEY ⭐
TransactionNumber   int           🔗 FK to Transaction.TransactionNumber
ItemID              int           🔗 FK to Item.ID
Price               money         Selling price per unit
Cost                money         Cost per unit (for GP calculations)
Quantity            float         Quantity sold (can be decimal)
SalesTax            money         Tax amount for this line
TransactionTime     datetime      🚨 NOT 'Time' - use 'TransactionTime'
DetailID            int           Line sequence number
DiscountAmount      money         Discount applied to line
TaxExempt           bit           Tax exemption flag
Comment             nvarchar(255) Line item notes
```

**🔗 FOREIGN KEY RELATIONSHIPS**:
- `te.TransactionNumber` → `t.TransactionNumber` (Transaction table)
- `te.ItemID` → `i.ID` (Item table)

**🚨 COLUMN NAME ERROR PREVENTION**:
```sql  
-- ❌ WRONG: Common timestamp mistakes
SELECT te.Time FROM dbo.TransactionEntry te         -- NO 'Time' COLUMN!
SELECT te.Date FROM dbo.TransactionEntry te         -- NO 'Date' COLUMN!

-- ✅ CORRECT: Use 'TransactionTime'
SELECT te.TransactionTime FROM dbo.TransactionEntry te  -- YES!

-- ❌ WRONG: Foreign key mistakes  
SELECT * FROM dbo.TransactionEntry te
JOIN dbo.Item i ON te.ItemID = i.ItemID             -- NO! Use i.ID

-- ✅ CORRECT: Proper joins
SELECT * FROM dbo.TransactionEntry te  
JOIN dbo.Item i ON te.ItemID = i.ID                 -- CORRECT!
```

**💰 CRITICAL TOBACCO COST ADJUSTMENT LOGIC**:
```sql
-- 🚬 TOBACCO EXCISE TAX UPLIFTS (ONLY for gross profit calculations)
-- MEMORIZE: These uplifts apply to COST when calculating GP, NOT to inventory valuation
-- ⚠️ CRITICAL: Use 'cat' alias for Category table, NOT 'c' (which is Customer)!
CASE 
    WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23      -- +23% excise tax
    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- +10% excise tax  
    ELSE te.Cost * te.Quantity                                    -- Standard cost
END as adjusted_cogs
```

**✅ TESTED QUERY PATTERNS**:
```sql
-- ✅ CORRECT: Product sales analysis with proper gross profit
SELECT 
    i.Description as product_name,
    c.Name as category,
    SUM(te.Quantity) as units_sold,
    SUM(te.Price * te.Quantity) as gross_revenue,
    SUM(te.SalesTax) as sales_tax_collected,
    SUM(CASE 
        WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23      
        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  
        ELSE te.Cost * te.Quantity
    END) as adjusted_cost_of_goods,
    SUM(te.Price * te.Quantity) - SUM(CASE 
        WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23      
        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  
        ELSE te.Cost * te.Quantity
    END) as gross_profit
FROM dbo.TransactionEntry te
INNER JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
INNER JOIN dbo.Item i ON te.ItemID = i.ID
LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
WHERE t.Time >= DATEADD(month, -1, GETDATE())
    AND te.Quantity > 0  -- Exclude returns
GROUP BY i.ID, i.Description, c.Name
ORDER BY gross_revenue DESC;

-- ✅ CORRECT: Daily line item trends
SELECT 
    CAST(t.Time AS DATE) as sale_date,
    COUNT(te.ID) as total_line_items,
    COUNT(DISTINCT te.TransactionNumber) as unique_transactions,
    SUM(te.Price * te.Quantity) as total_line_revenue,
    AVG(te.Price * te.Quantity) as avg_line_value
FROM dbo.TransactionEntry te
INNER JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
WHERE t.Time >= DATEADD(day, -30, GETDATE())
GROUP BY CAST(t.Time AS DATE)
ORDER BY sale_date DESC;

-- ✅ CORRECT: Category performance with margin analysis
SELECT 
    c.Name as category_name,
    COUNT(DISTINCT te.ItemID) as unique_products_sold,
    SUM(te.Quantity) as total_units,
    SUM(te.Price * te.Quantity) as category_revenue,
    AVG(te.Price) as avg_selling_price,
    SUM(te.Price * te.Quantity) / SUM(te.Quantity) as avg_revenue_per_unit,
    CASE 
        WHEN SUM(te.Price * te.Quantity) > 0 THEN
            (SUM(te.Price * te.Quantity) - SUM(CASE 
                WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23      
                WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  
                ELSE te.Cost * te.Quantity
            END)) / SUM(te.Price * te.Quantity) * 100.0
        ELSE 0
    END as gross_margin_percent
FROM dbo.TransactionEntry te
INNER JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
INNER JOIN dbo.Item i ON te.ItemID = i.ID
LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
WHERE t.Time >= DATEADD(month, -3, GETDATE())
    AND te.Quantity > 0
GROUP BY c.ID, c.Name
HAVING SUM(te.Price * te.Quantity) > 1000  -- Categories with $1K+ revenue
ORDER BY category_revenue DESC;
```

**Business Logic - CRITICAL TOBACCO COST UPLIFTS**:
```sql
-- Gross Profit with tobacco excise tax uplifts (ONLY for sold items)
SUM(te.Price * te.Quantity - 
    CASE 
        WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23      -- +23% excise tax
        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- +10% excise tax
        ELSE te.Cost * te.Quantity
    END
) as gross_profit
```

**Query Patterns**:
```sql
-- Revenue and profit analysis
SELECT 
    SUM(te.Price * te.Quantity) as revenue,
    SUM(CASE 
        WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
        ELSE te.Cost * te.Quantity
    END) as adjusted_cogs,
    COUNT(*) as line_items
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
JOIN dbo.Item i ON te.ItemID = i.ID
LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
WHERE t.Time >= DATEADD(day, -30, GETDATE())
```

### 3. dbo.Item - Product Master (12,332 products)
**Primary Key**: `ID` (int)
**Description**: Product/SKU master data with current inventory

**Key Columns**:
- `ID` (int) - Unique item ID ⭐ PRIMARY KEY
- `Description` (nvarchar) - Product name/description
- `Price` (money) - Current selling price
- `Cost` (money) - Current cost price (inventory valuation - NO uplifts)
- `Quantity` (float) - Current inventory quantity
- `CategoryID` (int) - Links to Category.ID ⭐ FOREIGN KEY
- `ItemLookupCode` (nvarchar) - Barcode/UPC
- `LastSold` (datetime) - Last sale date
- `Inactive` (bit) - Whether item is active (0=active, 1=inactive)

**Business Rules**:
- `Quantity > 0` = In stock
- `Quantity <= 0` = Out of stock
- `LastSold` > 30 days ago = Potential deadstock
- Inventory value uses `i.Cost` (no tobacco uplifts)

### 4. dbo.Category - Product Categories (83 categories)
**Primary Key**: `ID` (int)
**Description**: Product categorization with business rules

**Key Columns**:
- `ID` (int) - Category ID ⭐ PRIMARY KEY
- `Name` (nvarchar) - Category name
- `Code` (nvarchar) - Category code
- `DepartmentID` (int) - Links to Department

**🚬 Critical Tobacco Categories (for cost uplifts)**:
- **CIGARS** (ID: 23) → +23% cost uplift on SOLD items
- **LT-TAX-COLLECTED** (ID: 49) → +10% cost uplift on SOLD items
- CIGARETTE (ID: 48) → Standard cost
- CIGAR GA (ID: 56) → Standard cost

**Other Major Categories**:
- KRATOM, CBD/HEMP, ELECTRONIC CIG, DRINKS, AUTOMOTIVE, LOTTERY

### 5. dbo.Customer - Customer Master 👥 CUSTOMER DATA
**🔑 Primary Key**: `ID` (int) - NEVER use CustomerID as primary key
**📝 Description**: Customer master data with financial summaries and contact info
**📊 Record Count**: 2,824+ customers
**🏷️ Recommended Alias**: `c`

**🚨 CRITICAL COLUMNS - EXACT NAMES**:
```sql
-- EXACT CUSTOMER SCHEMA:
ID              int           PRIMARY KEY ⭐ (NOT CustomerID!)
FirstName       nvarchar(50)  Individual customer first name
LastName        nvarchar(50)  Individual customer last name  
Company         nvarchar(100) Business name (priority over names)
AccountNumber   nvarchar(50)  Customer account code
Address         nvarchar(255) Primary street address
City            nvarchar(50)  City name
State           nvarchar(10)  State abbreviation
Zip             nvarchar(15)  ZIP/postal code
PhoneNumber     nvarchar(25)  Primary phone number
EmailAddress    nvarchar(100) Email address
AccountBalance  money         Current AR balance (+ = owe us)
CreditLimit     money         Credit limit amount
TotalSales      money         Lifetime sales total
LastVisit       datetime      Last transaction date
TotalVisits     int           Total number of transactions
Notes           nvarchar(500) Customer notes and comments
TaxExempt       bit           Tax exemption status
```

**🔗 FOREIGN KEY RELATIONSHIPS**:
- `c.ID` ← `t.CustomerID` (Transaction table)  
- `c.ID` ← `p.CustomerID` (Payment table)
- `c.ID` ← `ar.CustomerID` (AccountReceivable table)

**🚨 COLUMN NAME ERROR PREVENTION**:
```sql
-- ❌ WRONG: Primary key mistakes
SELECT c.CustomerID FROM dbo.Customer c             -- NO 'CustomerID' COLUMN!
WHERE c.CustomerID = 123                           -- ERROR!

-- ✅ CORRECT: Use 'ID' as primary key
SELECT c.ID FROM dbo.Customer c                    -- YES! 'ID' is the PK
WHERE c.ID = 123                                   -- CORRECT!

-- ❌ WRONG: Join mistakes in other tables  
JOIN dbo.Customer c ON t.CustomerID = c.CustomerID  -- NO! Wrong PK
JOIN dbo.Customer c ON p.CustomerID = c.CustomerID  -- ERROR!

-- ✅ CORRECT: Proper joins
JOIN dbo.Customer c ON t.CustomerID = c.ID          -- YES!  
JOIN dbo.Customer c ON p.CustomerID = c.ID          -- CORRECT!
```

**📛 CUSTOMER DISPLAY NAME LOGIC**:
```sql
-- Standard customer display name (MEMORIZE THIS PATTERN)
CASE 
    WHEN c.Company IS NOT NULL AND c.Company <> '' THEN c.Company
    WHEN c.FirstName IS NOT NULL AND c.LastName IS NOT NULL 
         AND c.FirstName <> '' AND c.LastName <> '' 
         THEN c.FirstName + ' ' + c.LastName
    WHEN c.FirstName IS NOT NULL AND c.FirstName <> '' THEN c.FirstName
    WHEN c.LastName IS NOT NULL AND c.LastName <> '' THEN c.LastName
    ELSE 'Walk-in Customer'
END as customer_display_name
```

**✅ TESTED QUERY PATTERNS**:
```sql
-- ✅ CORRECT: Customer segmentation analysis
SELECT 
    CASE 
        WHEN c.TotalSales >= 50000 THEN 'VIP (50K+)'
        WHEN c.TotalSales >= 25000 THEN 'Premium (25K-50K)'
        WHEN c.TotalSales >= 10000 THEN 'High Value (10K-25K)'
        WHEN c.TotalSales >= 5000 THEN 'Regular (5K-10K)'
        WHEN c.TotalSales >= 1000 THEN 'Standard (1K-5K)'
        ELSE 'New/Low Volume (<1K)'
    END as customer_segment,
    COUNT(c.ID) as customer_count,
    SUM(c.TotalSales) as segment_total_sales,
    AVG(c.TotalSales) as avg_sales_per_customer,
    SUM(c.AccountBalance) as segment_ar_balance
FROM dbo.Customer c
WHERE c.AccountBalance > 0  -- Customers with AR balance
GROUP BY CASE 
    WHEN c.TotalSales >= 50000 THEN 'VIP (50K+)'
    WHEN c.TotalSales >= 25000 THEN 'Premium (25K-50K)'
    WHEN c.TotalSales >= 10000 THEN 'High Value (10K-25K)'
    WHEN c.TotalSales >= 5000 THEN 'Regular (5K-10K)'
    WHEN c.TotalSales >= 1000 THEN 'Standard (1K-5K)'
    ELSE 'New/Low Volume (<1K)'
END
ORDER BY segment_total_sales DESC;

-- ✅ CORRECT: AR aging with customer details
SELECT 
    CASE 
        WHEN c.Company IS NOT NULL AND c.Company <> '' THEN c.Company
        WHEN c.FirstName + ' ' + c.LastName <> ' ' THEN c.FirstName + ' ' + c.LastName
        ELSE 'Walk-in Customer'
    END as customer_name,
    c.AccountBalance,
    c.CreditLimit,
    c.LastVisit,
    DATEDIFF(day, c.LastVisit, GETDATE()) as days_since_last_visit,
    c.TotalVisits,
    c.TotalSales,
    CASE 
        WHEN c.AccountBalance > c.CreditLimit THEN 'Over Limit'
        WHEN c.AccountBalance > c.CreditLimit * 0.8 THEN 'Near Limit'
        WHEN c.AccountBalance > 0 THEN 'Has Balance'
        ELSE 'No Balance'
    END as credit_status
FROM dbo.Customer c  
WHERE c.AccountBalance > 0  -- Customers with outstanding balances
ORDER BY c.AccountBalance DESC;

-- ✅ CORRECT: Customer activity analysis
SELECT 
    c.ID as customer_id,
    COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in') as customer_name,
    c.TotalVisits as lifetime_transactions,
    c.TotalSales as lifetime_sales,
    c.LastVisit as last_purchase_date,
    CASE 
        WHEN c.LastVisit >= DATEADD(month, -1, GETDATE()) THEN 'Active (30 days)'
        WHEN c.LastVisit >= DATEADD(month, -3, GETDATE()) THEN 'Recent (90 days)'  
        WHEN c.LastVisit >= DATEADD(month, -6, GETDATE()) THEN 'Inactive (6 months)'
        WHEN c.LastVisit >= DATEADD(year, -1, GETDATE()) THEN 'Dormant (1 year)'
        ELSE 'Lost (1+ years)'
    END as activity_status,
    CASE 
        WHEN c.TotalVisits > 0 AND c.TotalSales > 0 
        THEN c.TotalSales / c.TotalVisits 
        ELSE 0 
    END as avg_transaction_value
FROM dbo.Customer c
WHERE c.TotalSales > 0  -- Customers with purchase history
ORDER BY c.LastVisit DESC;
```

**💡 CUSTOMER BUSINESS RULES**:
- **Display Priority**: Company name > FirstName + LastName > 'Walk-in Customer'  
- **AccountBalance > 0** = Customer owes money (Accounts Receivable)
- **AccountBalance < 0** = Customer has credit balance (rare)
- **TotalSales** = Lifetime revenue from this customer
- **TotalVisits** = Number of transactions (not number of days visited)

**Display Name Logic**:
```sql
COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in Customer') as customer_name
```


### 6. dbo.AccountReceivable - AR Records & ADJUSTMENTS (142,706 entries)
**Primary Key**: `ID` (int)
**Description**: Accounts receivable, aging data, and manual adjustments

**Key Columns**:
- `ID` (int) - AR record ID ⭐ PRIMARY KEY
- `CustomerID` (int) - Links to Customer.ID ⭐ FOREIGN KEY
- `Date` (datetime) - Transaction/invoice date
- `DueDate` (datetime) - Payment due date
- `Balance` (money) - Outstanding amount (0 = paid/adjusted)
- `OriginalAmount` (money) - Original invoice/adjustment amount
- `TransactionNumber` (int) - Links to Transaction (0 = manual adjustment)

**🔥 CRITICAL: ADJUSTMENT PATTERNS**:
- **TransactionNumber = 0** indicates MANUAL ADJUSTMENT (not a regular sale)
- **$65.00 entries** = NSF (Non-Sufficient Funds) return fees
- **Negative amounts** = Credits/refunds to customer account
- **Positive amounts with TransactionNumber = 0** = Manual debits/charges

**AR Aging Buckets**:
```sql
CASE 
    WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN '0-30 days'
    WHEN DATEDIFF(day, Date, GETDATE()) <= 60 THEN '31-60 days'
    WHEN DATEDIFF(day, Date, GETDATE()) <= 90 THEN '61-90 days'
    ELSE '90+ days'
END as aging_bucket
```

**Query Examples for Adjustments**:
```sql
-- Find all manual adjustments for a customer
SELECT 
    ar.ID,
    ar.Date,
    ar.OriginalAmount,
    ar.Balance,
    CASE 
        WHEN ar.OriginalAmount = 65.00 THEN 'NSF Return Fee'
        WHEN ar.OriginalAmount < 0 THEN 'Credit/Refund'
        WHEN ar.TransactionNumber = 0 THEN 'Manual Adjustment'
        ELSE 'Regular Invoice'
    END as adjustment_type
FROM dbo.AccountReceivable ar
INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
WHERE c.Company = 'NERR PETROLEUM INC'
    AND ar.TransactionNumber = 0  -- Manual adjustments only
ORDER BY ar.Date DESC;

-- Find NSF fees
SELECT 
    c.Company,
    ar.Date,
    ar.OriginalAmount,
    ar.Balance
FROM dbo.AccountReceivable ar
INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
WHERE ar.OriginalAmount = 65.00  -- NSF fee amount
    AND ar.TransactionNumber = 0
ORDER BY ar.Date DESC;

-- Reconcile adjustments with payments
SELECT 
    c.Company,
    ar.Date as adjustment_date,
    ar.OriginalAmount as adjustment_amount,
    ar.Balance as current_balance,
    p.Time as payment_date,
    p.Amount as payment_amount,
    p.Comment as payment_notes
FROM dbo.AccountReceivable ar
INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
LEFT JOIN dbo.Payment p ON c.ID = p.CustomerID 
    AND ABS(DATEDIFF(day, ar.Date, p.Time)) <= 30  -- Payments within 30 days
WHERE ar.TransactionNumber = 0  -- Adjustments only
ORDER BY ar.Date DESC, p.Time DESC;
```

### 7. dbo.AccountReceivableHistory - AR ADJUSTMENT NOTES & HISTORY
**🔑 Primary Key**: `ID` (int) - This ID is the REFERENCE NUMBER for adjustments!
**📝 Description**: Stores notes/comments for AR adjustments and history
**🏷️ Recommended Alias**: `arh`

**Key Columns**:
- `ID` (int) - Primary key AND reference number for adjustments ⭐
- `AccountReceivableID` (int) - Links to AccountReceivable.ID ⭐ FOREIGN KEY
- `Amount` (money) - Adjustment amount
- `Comment` (nvarchar) - **ADJUSTMENT NOTES/DESCRIPTION** ⭐
- `Date` (datetime) - When adjustment was made
- `HistoryType` (int) - Type of history record (5 = adjustment)
- `CashierID` (int) - User who created adjustment
- `BatchNumber` (int) - Batch reference

**🔥 CRITICAL: How to Find Adjustment Notes**:
```sql
-- Get full adjustment details with notes
SELECT 
    ar.ID as ar_id,
    ar.Date as adjustment_date,
    ar.OriginalAmount,
    ar.Balance,
    arh.ID as reference_number,  -- This is your adjustment reference!
    arh.Comment as adjustment_notes,  -- The actual notes/description
    c.Company as customer_name
FROM dbo.AccountReceivable ar
INNER JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
WHERE ar.TransactionNumber = 0  -- Manual adjustments
ORDER BY ar.Date DESC;

-- Find specific adjustment by reference number
SELECT 
    arh.ID as reference_number,
    arh.Comment as notes,
    arh.Amount,
    ar.OriginalAmount,
    c.Company
FROM dbo.AccountReceivableHistory arh
INNER JOIN dbo.AccountReceivable ar ON arh.AccountReceivableID = ar.ID
INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
WHERE arh.ID = 317912;  -- The reference number
```

### 8. dbo.TenderEntry - Payment Methods (358,194 entries)
**Key Columns**:
- `TransactionNumber` (int) - Links to Transaction ⭐ FOREIGN KEY
- `TenderID` (int) - Payment method type
- `Amount` (money) - Payment amount
- `Description` (nvarchar) - Payment description

### 9. dbo.Payment - Customer Payments
**🔑 Primary Key**: `ID` (int) - Auto-increment payment ID
**📝 Description**: Customer payment records - credits, checks, ACH, etc.
**📊 Record Count**: 63,021+ payments
**🏷️ Recommended Alias**: `p`

**🚨 CRITICAL COLUMNS - EXACT NAMES**:
```sql
-- 🔥 PAYMENT TABLE SCHEMA - MEMORIZE THIS 🔥
ID              int           PRIMARY KEY ⭐
CustomerID      int           🔗 FK to Customer.ID
Time            datetime      🚨 CRITICAL: Use 'Time' NOT 'Date'!!!  
Amount          money         Payment amount (positive for credits)
Comment         nvarchar(500) Payment notes/memo
BatchID         int           Payment batch identifier
CreatedBy       int           User who entered payment
CreatedDate     datetime      When payment record was created
-- ⚠️ NOTE: NO CheckNumber, NO PaymentNumber, NO ReferenceNumber, NO Type columns!
```

**🚨 PAYMENT COLUMN ERRORS TO AVOID**:
```sql
-- ❌ THESE COLUMNS DO NOT EXIST - WILL CAUSE ERRORS:
SELECT p.CheckNumber FROM dbo.Payment p         -- ❌ NO CheckNumber!
SELECT p.PaymentNumber FROM dbo.Payment p       -- ❌ NO PaymentNumber!
SELECT p.ReferenceNumber FROM dbo.Payment p     -- ❌ NO ReferenceNumber!
SELECT p.PaymentDate FROM dbo.Payment p         -- ❌ NO PaymentDate!
SELECT p.Date FROM dbo.Payment p                -- ❌ NO Date column!

-- ✅ ONLY THESE COLUMNS EXIST:
SELECT p.ID, p.CustomerID, p.Time, p.Amount, p.Comment, p.BatchID, 
       p.CreatedBy, p.CreatedDate FROM dbo.Payment p    -- ✅ CORRECT!
```

**🔗 FOREIGN KEY RELATIONSHIPS**:
- `p.CustomerID` → `c.ID` (Customer table)

**🚨 COLUMN NAME ERROR PREVENTION**:
```sql
-- ❌ ABSOLUTE WRONG - WILL CAUSE ERRORS:
SELECT p.Date FROM dbo.Payment p                    -- NO 'Date' COLUMN!
SELECT p.PaymentDate FROM dbo.Payment p             -- NO 'PaymentDate' COLUMN!  
SELECT p.DateTime FROM dbo.Payment p                -- NO 'DateTime' COLUMN!

-- ✅ ALWAYS CORRECT - MEMORIZE THIS:
SELECT p.Time FROM dbo.Payment p                    -- YES! 'Time' column exists
WHERE p.Time >= DATEADD(month, -1, GETDATE())      -- Correct date filtering
```

**✅ TESTED QUERY PATTERNS**:
```sql
-- ✅ CORRECT: Recent payments analysis
SELECT 
    COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in') as customer_name,
    p.Time as payment_date,  -- 🔥 ALWAYS 'Time' not 'Date'
    p.Amount as payment_amount,
    -- p.Type as payment_type,  -- NO Type column exists!
    p.Comment as payment_notes
FROM dbo.Payment p
INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
WHERE p.Time >= DATEADD(month, -3, GETDATE())  -- Last 3 months
    AND p.Amount > 0  -- Exclude negative adjustments
ORDER BY p.Time DESC;

-- ✅ CORRECT: Monthly payment totals by customer
SELECT 
    c.Company,
    YEAR(p.Time) as payment_year,
    MONTH(p.Time) as payment_month,
    COUNT(p.ID) as payment_count,
    SUM(p.Amount) as total_payments
FROM dbo.Payment p
INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
WHERE p.Time >= DATEADD(year, -1, GETDATE())
GROUP BY c.ID, c.Company, YEAR(p.Time), MONTH(p.Time)
ORDER BY c.Company, payment_year, payment_month;

-- ✅ CORRECT: NSF/Problem payment analysis
SELECT 
    c.Company,
    p.Time as payment_date,
    p.Amount,
    p.Comment
FROM dbo.Payment p
INNER JOIN dbo.Customer c ON p.CustomerID = c.ID  
WHERE p.Comment LIKE '%NSF%' 
    OR p.Comment LIKE '%returned%'
    OR p.Comment LIKE '%insufficient%'
    OR p.Comment LIKE '%post%dated%'
ORDER BY p.Time DESC;

-- ✅ CORRECT: Customer payment history with AR balance
SELECT 
    c.Company,
    c.AccountBalance as current_ar_balance,
    COUNT(p.ID) as payment_count,
    SUM(p.Amount) as total_payments_received,
    MAX(p.Time) as last_payment_date,
    AVG(p.Amount) as avg_payment_amount
FROM dbo.Customer c
LEFT JOIN dbo.Payment p ON c.ID = p.CustomerID 
    AND p.Time >= DATEADD(year, -1, GETDATE())
WHERE c.AccountBalance <> 0  -- Customers with AR balance
GROUP BY c.ID, c.Company, c.AccountBalance
ORDER BY c.AccountBalance DESC;
```

**💡 PAYMENT BUSINESS RULES**:
- Positive `Amount` = Customer payment received (credit to account)
- Negative `Amount` = Payment reversal or adjustment (debit to account)  
- `Comment` field contains critical info: NSF notices, post-dated check dates, check numbers
- Payment type details stored in `Comment` field, NOT a separate Type column
- Check numbers and reference details stored in `Comment` field, NOT separate columns

## Essential Query Patterns

### Sales Analysis Queries
```sql
-- Daily sales trend
SELECT 
    CAST(t.Time AS DATE) as date,
    SUM(t.Total) as total_sales,
    COUNT(DISTINCT t.TransactionNumber) as transactions,
    COUNT(DISTINCT t.CustomerID) as customers
FROM [dbo].[Transaction] t
WHERE t.Time BETWEEN @start_date AND @end_date
GROUP BY CAST(t.Time AS DATE)
ORDER BY date

-- Top products by revenue
SELECT TOP 10
    i.Description,
    SUM(te.Price * te.Quantity) as revenue,
    SUM(te.Quantity) as units_sold
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
JOIN dbo.Item i ON te.ItemID = i.ID
WHERE t.Time >= DATEADD(day, -30, GETDATE())
GROUP BY i.Description
ORDER BY revenue DESC
```

### Customer Analysis Queries
```sql
-- Customer segments
SELECT 
    segment,
    COUNT(*) as customer_count,
    AVG(total_revenue) as avg_revenue
FROM (
    SELECT 
        c.ID,
        CASE 
            WHEN c.TotalSales > 10000 THEN 'VIP'
            WHEN c.TotalSales > 5000 THEN 'High Value'
            WHEN c.TotalSales > 1000 THEN 'Regular'
            ELSE 'New'
        END as segment,
        c.TotalSales as total_revenue
    FROM dbo.Customer c
) segmented
GROUP BY segment

-- AR aging analysis
SELECT 
    CASE 
        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 days'
        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 days'
        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END as aging_bucket,
    COUNT(*) as invoice_count,
    SUM(ar.Balance) as total_balance
FROM dbo.AccountReceivable ar
WHERE ar.Balance > 0
GROUP BY CASE 
    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 days'
    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 days'
    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 days'
    ELSE '90+ days'
END
```

### Inventory Analysis Queries
```sql
-- Current inventory status
SELECT 
    c.Name as category,
    COUNT(i.ID) as sku_count,
    SUM(i.Quantity) as total_units,
    SUM(i.Quantity * i.Cost) as inventory_value
FROM dbo.Item i
LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
WHERE i.Quantity IS NOT NULL AND i.Quantity > 0
GROUP BY c.Name
ORDER BY inventory_value DESC

-- Deadstock analysis
SELECT 
    i.Description,
    i.Quantity,
    i.LastSold,
    DATEDIFF(day, i.LastSold, GETDATE()) as days_since_sold,
    (i.Quantity * i.Cost) as inventory_value
FROM dbo.Item i
WHERE i.Quantity > 0 
AND (i.LastSold IS NULL OR i.LastSold < DATEADD(day, -30, GETDATE()))
ORDER BY inventory_value DESC
```

## Date Handling Examples
```sql
-- Today's data
WHERE t.Time >= CAST(CAST(GETDATE() AS DATE) AS DATETIME)

-- Last 30 days
WHERE t.Time >= DATEADD(day, -30, GETDATE())

-- Month-to-date
WHERE t.Time >= DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)

-- Year-to-date
WHERE t.Time >= DATEADD(year, DATEDIFF(year, 0, GETDATE()), 0)

-- Custom date range
WHERE t.Time BETWEEN @start_date AND @end_date
```

## 🚀 ESSENTIAL QUERY PATTERNS & PERFORMANCE GUIDE

### 🔥 MOST COMMON QUERY PATTERNS (COPY-PASTE READY)

**1. Daily Sales Trend (30 days)**:
```sql
SELECT 
    CAST(t.Time AS DATE) as sale_date,
    COUNT(t.TransactionNumber) as transaction_count,
    SUM(t.Total) as daily_sales,
    AVG(t.Total) as avg_transaction_size,
    COUNT(DISTINCT t.CustomerID) as unique_customers
FROM [dbo].[Transaction] t
WHERE t.Time >= DATEADD(day, -30, GETDATE())
    AND t.Total > 0  -- Exclude voids/returns
GROUP BY CAST(t.Time AS DATE)
ORDER BY sale_date DESC;
```

**2. Top Products by Revenue (Current Month)**:
```sql
SELECT TOP 20
    i.Description as product_name,
    c.Name as category,
    SUM(te.Quantity) as units_sold,
    SUM(te.Price * te.Quantity) as gross_revenue,
    AVG(te.Price) as avg_selling_price,
    COUNT(DISTINCT te.TransactionNumber) as transactions_with_product
FROM dbo.TransactionEntry te
INNER JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
INNER JOIN dbo.Item i ON te.ItemID = i.ID
LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
WHERE t.Time >= DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)  -- Month-to-date
    AND te.Quantity > 0
GROUP BY i.ID, i.Description, c.Name
ORDER BY gross_revenue DESC;
```

**3. Customer Payment History with AR Balance**:
```sql
SELECT 
    COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in') as customer_name,
    c.AccountBalance as current_ar_balance,
    COUNT(p.ID) as payments_last_year,
    COALESCE(SUM(p.Amount), 0) as total_payments_received,
    MAX(p.Time) as last_payment_date,  -- 🔥 Use p.Time not p.Date
    COALESCE(SUM(CASE WHEN p.Time >= DATEADD(month, -3, GETDATE()) THEN p.Amount END), 0) as payments_last_90_days
FROM dbo.Customer c
LEFT JOIN dbo.Payment p ON c.ID = p.CustomerID 
    AND p.Time >= DATEADD(year, -1, GETDATE())
WHERE c.AccountBalance > 100  -- Customers with significant AR balance
GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountBalance
ORDER BY c.AccountBalance DESC;
```

**4. Inventory Status with Sales Velocity**:
```sql
SELECT 
    i.Description as product_name,
    c.Name as category,
    i.Quantity as current_inventory,
    i.Cost as unit_cost,
    (i.Quantity * i.Cost) as inventory_value,
    i.LastSold as last_sale_date,
    DATEDIFF(day, i.LastSold, GETDATE()) as days_since_last_sold,
    COALESCE(recent_sales.units_sold_30_days, 0) as units_sold_last_30_days,
    CASE 
        WHEN i.Quantity <= 0 THEN 'Out of Stock'
        WHEN recent_sales.units_sold_30_days IS NULL OR recent_sales.units_sold_30_days = 0 THEN 'No Recent Sales'
        WHEN i.Quantity / (recent_sales.units_sold_30_days / 30.0) < 30 THEN 'Low Stock (< 30 days)'
        WHEN i.Quantity / (recent_sales.units_sold_30_days / 30.0) > 180 THEN 'Overstock (> 6 months)'
        ELSE 'Normal'
    END as inventory_status
FROM dbo.Item i
LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
LEFT JOIN (
    SELECT 
        te.ItemID,
        SUM(te.Quantity) as units_sold_30_days
    FROM dbo.TransactionEntry te
    INNER JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE t.Time >= DATEADD(day, -30, GETDATE())
        AND te.Quantity > 0
    GROUP BY te.ItemID
) recent_sales ON i.ID = recent_sales.ItemID
WHERE i.Quantity IS NOT NULL
ORDER BY inventory_value DESC;
```

### ⚠️ CRITICAL ERROR PREVENTION CHECKLIST

**Before writing ANY query, verify:**
- [ ] Payment table: Using `p.Time` NOT `p.Date`
- [ ] Transaction table: Using `t.Time` NOT `t.Date`  
- [ ] TransactionEntry: Using `te.TransactionTime` NOT `te.Time`
- [ ] Customer joins: Using `c.ID` NOT `c.CustomerID`
- [ ] Item joins: Using `i.ID` NOT `i.ItemID`
- [ ] All table names bracketed: `[dbo].[Transaction]`
- [ ] Proper aliases used consistently
- [ ] Date ranges included for performance

### 🎯 PERFORMANCE OPTIMIZATION RULES

**1. ALWAYS Include Date Filters:**
```sql
-- ✅ GOOD: Includes date range
WHERE t.Time >= DATEADD(month, -3, GETDATE())

-- ❌ BAD: No date filter (scans entire table)
WHERE t.CustomerID = 123
```

**2. Use Proper Indexes (Primary Keys):**
```sql  
-- ✅ GOOD: Join on indexed primary keys
FROM [dbo].[Transaction] t
INNER JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
INNER JOIN dbo.Item i ON te.ItemID = i.ID

-- ❌ BAD: Join on non-indexed columns
INNER JOIN dbo.Item i ON te.ItemDescription = i.Description  -- SLOW!
```

**3. Limit Result Sets:**
```sql
-- ✅ GOOD: Use TOP to limit results
SELECT TOP 100 * FROM [dbo].[Transaction] t
ORDER BY t.Time DESC

-- ❌ BAD: No limit on large table
SELECT * FROM [dbo].[Transaction] t  -- Could return 500K+ rows!
```

**4. Aggregate Before Joining:**
```sql
-- ✅ GOOD: Aggregate first, then join
SELECT 
    c.Company,
    monthly_sales.total_sales
FROM dbo.Customer c
INNER JOIN (
    SELECT 
        t.CustomerID,
        SUM(t.Total) as total_sales
    FROM [dbo].[Transaction] t  
    WHERE t.Time >= DATEADD(month, -1, GETDATE())
    GROUP BY t.CustomerID
) monthly_sales ON c.ID = monthly_sales.CustomerID

-- ❌ SLOWER: Join first, then aggregate
SELECT 
    c.Company,
    SUM(t.Total) as total_sales  
FROM dbo.Customer c
INNER JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
WHERE t.Time >= DATEADD(month, -1, GETDATE())
GROUP BY c.ID, c.Company  -- Groups more rows
```

### 📋 SQL SERVER 2008 R2 COMPATIBILITY REMINDERS

- **NO** `FORMAT()` function - use `CAST(field AS DATE)`
- **NO** complex window functions - use subqueries  
- **NO** `STRING_AGG()` - use XML PATH for concatenation
- **YES** `ISNULL()` instead of `COALESCE()` for two values
- **YES** `%s` parameter markers, NOT `?`
- **ALWAYS** bracket reserved words: `[Transaction]`, `[Order]`, `[User]`

### 💡 BUSINESS INTELLIGENCE QUICK REFERENCE

**Key Metrics Formulas:**
```sql
-- Gross Profit (with tobacco uplifts)
SUM(te.Price * te.Quantity) - SUM(CASE 
    WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  
    ELSE te.Cost * te.Quantity
END) as gross_profit

-- Gross Margin %
CASE WHEN SUM(te.Price * te.Quantity) > 0 THEN
    (SUM(te.Price * te.Quantity) - SUM(adjusted_cost)) / SUM(te.Price * te.Quantity) * 100.0
    ELSE 0 
END as gross_margin_percent

-- Average Transaction Value  
SUM(t.Total) / COUNT(t.TransactionNumber) as avg_transaction_value

-- Customer Lifetime Value
c.TotalSales / c.TotalVisits as avg_order_value
```

**Date Range Quick Reference:**
```sql
-- Today only
WHERE t.Time >= CAST(CAST(GETDATE() AS DATE) AS DATETIME)

-- Yesterday  
WHERE t.Time >= CAST(CAST(DATEADD(day, -1, GETDATE()) AS DATE) AS DATETIME)
    AND t.Time < CAST(CAST(GETDATE() AS DATE) AS DATETIME)

-- Last 7 days
WHERE t.Time >= DATEADD(day, -7, GETDATE())

-- Last 30 days  
WHERE t.Time >= DATEADD(day, -30, GETDATE())

-- Month to date
WHERE t.Time >= DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)

-- Year to date
WHERE t.Time >= DATEADD(year, DATEDIFF(year, 0, GETDATE()), 0)

-- Last full month
WHERE t.Time >= DATEADD(month, DATEDIFF(month, 0, GETDATE()) - 1, 0)
    AND t.Time < DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)
```

## 🎯 BUSINESS RULES SUMMARY
- **Tobacco cost uplifts** apply ONLY to gross profit calculations (`te.Cost`), NOT inventory valuation (`i.Cost`)
- **Customer display priority**: Company > FirstName + LastName > 'Walk-in Customer'  
- **AR aging** based on invoice date (`ar.Date`), not due date
- **Inventory quantity** can be negative (indicates backorders)
- **Transaction totals** include sales tax
- **Primary key joins**: Always use `TransactionNumber` to join Transaction ↔ TransactionEntry
- **Date columns**: Payment uses `Time`, Transaction uses `Time`, TransactionEntry uses `TransactionTime`

## 📊 COMPLETE ACCOUNT HISTORY QUERIES - BEST PRACTICES

### For Complete Customer Account History (Sales + Payments + Adjustments):
```sql
-- RECOMMENDED: Use UNION ALL to combine different record types
WITH AccountHistory AS (
    -- Transactions/Sales
    SELECT 'Sale' as type, TransactionNumber as ref, Time as date, Total as debit, 0 as credit, Comment as notes
    FROM [dbo].[Transaction] WHERE CustomerID = [customer_id]
    
    UNION ALL
    
    -- Payments
    SELECT 'Payment', ID, Time, 0, Amount, Comment
    FROM dbo.Payment WHERE CustomerID = [customer_id]
    
    UNION ALL
    
    -- Adjustments with notes from AccountReceivableHistory
    SELECT 
        CASE WHEN ar.OriginalAmount = 65 THEN 'NSF Fee' 
             WHEN ar.OriginalAmount < 0 THEN 'Credit' 
             ELSE 'Adjustment' END,
        arh.ID,  -- This is the reference number!
        ar.Date,
        CASE WHEN ar.OriginalAmount > 0 THEN ar.OriginalAmount ELSE 0 END,
        CASE WHEN ar.OriginalAmount < 0 THEN ABS(ar.OriginalAmount) ELSE 0 END,
        arh.Comment  -- The adjustment notes!
    FROM dbo.AccountReceivable ar
    LEFT JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
    WHERE CustomerID = [customer_id] AND ar.TransactionNumber = 0
)
SELECT * FROM AccountHistory ORDER BY date DESC
```

### ⚠️ AVOID Complex Multi-Table JOINs for History:
- DON'T JOIN Transaction + TransactionEntry + Payment + AR all together (causes duplicates)
- DO use UNION ALL to combine different record types
- DO calculate running balances in application layer (SQL Server 2008 R2 has limited window functions)

## 💰 ADJUSTMENTS & CREDITS - CRITICAL BUSINESS LOGIC
**Adjustments are primarily stored in AccountReceivable table with TransactionNumber = 0**

### Types of Adjustments:
1. **NSF Return Fees**: $65.00 charges when customer check bounces
2. **Manual Credits**: Negative amounts in AccountReceivable 
3. **Manual Debits**: Positive amounts with TransactionNumber = 0
4. **Payment Adjustments**: Corrections to customer balances

### How to Identify Adjustments:
```sql
-- All adjustments have TransactionNumber = 0 in AccountReceivable
SELECT * FROM dbo.AccountReceivable 
WHERE TransactionNumber = 0

-- NSF fees are always $65.00
SELECT * FROM dbo.AccountReceivable 
WHERE OriginalAmount = 65.00 AND TransactionNumber = 0

-- Credits/refunds are negative amounts
SELECT * FROM dbo.AccountReceivable 
WHERE OriginalAmount < 0 AND TransactionNumber = 0
```

### Reference Numbers:
- Regular transactions: Store reference in Transaction.ReferenceNumber
- Adjustments: No direct reference field, but may appear in Transaction.Comment
- Check numbers: Usually in Transaction.Comment or Payment.Comment fields