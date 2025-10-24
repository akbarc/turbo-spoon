# GA Database Directory

**Database:** GAWDB  
**Server:** SQL Server 2008 R2  
**Total Transactions:** 233,211  
**Date Range:** 2012-12-07 to 2025-07-15 (13+ years of data)  
**Discovery Date:** 2025-07-15

---

## 📊 Database Overview

This is a comprehensive Point of Sale (POS) retail database for a tobacco/convenience store operation with over **4.6 million transaction line items** spanning 13+ years of business data.

### Key Statistics
- **Transaction Entries:** 4,670,963 rows
- **Daily Sales Records:** 563,775 rows  
- **Items (SKUs):** 12,332 products
- **Customers:** 2,824 customers
- **Categories:** 83 product categories
- **Account Receivables:** 142,706 entries

---

## 🏗️ Core Business Tables

### 1. Transaction (dbo.Transaction)
**Primary transaction header table**

**Key Columns:**
- `TransactionNumber` (int) - Unique transaction ID ⭐ **PRIMARY KEY**
- `Time` (datetime) - Transaction timestamp
- `CustomerID` (int) - Links to Customer table
- `CashierID` (int) - Employee who processed sale
- `Total` (money) - Total transaction amount
- `SalesTax` (money) - Tax amount
- `BatchNumber` (int) - Daily batch grouping
- `StoreID` (int) - Store identifier

**Issue:** Row count query fails, likely due to "Transaction" being a reserved SQL keyword
**Solution:** Always use `[dbo].[Transaction]` in queries

---

### 2. TransactionEntry (dbo.TransactionEntry) 
**Line item details for each transaction**
**📊 4,670,963 rows** - The largest table

**Key Columns:**
- `ID` (int) - Unique line item ID
- `TransactionNumber` (int) - Links to Transaction table ⭐ **FOREIGN KEY**
- `ItemID` (int) - Links to Item table ⭐ **FOREIGN KEY**  
- `Price` (money) - Selling price per unit
- `Cost` (money) - Cost price per unit ⭐ **Used for GP calculations**
- `Quantity` (float) - Quantity sold
- `SalesTax` (money) - Tax for this line item
- `TransactionTime` (datetime) - Line item timestamp

**Business Rules:**
- Revenue = `Price × Quantity`
- Cost needs uplift adjustments for tobacco categories
- Gross Profit = Revenue - (Adjusted Cost)

---

### 3. Item (dbo.Item)
**Product/SKU master table**
**📊 12,332 rows**

**Key Columns:**
- `ID` (int) - Unique item ID ⭐ **PRIMARY KEY**
- `Description` (nvarchar) - Product name/description
- `Price` (money) - Current selling price
- `Cost` (money) - Current cost price
- `Quantity` (float) - Current inventory quantity
- `CategoryID` (int) - Links to Category table ⭐ **FOREIGN KEY**
- `ItemLookupCode` (nvarchar) - Barcode/UPC
- `LastSold` (datetime) - Last sale date (for deadstock analysis)
- `Inactive` (bit) - Whether item is active

**Business Logic:**
- `Quantity > 0` = Items in stock
- `LastSold` NULL or > 30 days = Deadstock candidates

---

### 4. Category (dbo.Category)
**Product categories with business-critical tax classifications**
**📊 83 categories**

**Key Columns:**
- `ID` (int) - Category ID ⭐ **PRIMARY KEY**
- `Name` (nvarchar) - Category name
- `Code` (nvarchar) - Category code
- `DepartmentID` (int) - Links to Department

**🚬 Tobacco Categories (Require Cost Uplifts):**
- **CIGARS** (ID: 23) → **+23% cost uplift** for excise tax
- **LT-TAX-COLLECTED** (ID: 49) → **+10% cost uplift** for excise tax
- **CIGARETTE** (ID: 48) → Standard cost
- **CIGAR GA** (ID: 56) → Standard cost  
- **LIT CIGARS 003251** (ID: 51) → Standard cost
- **T7 SMOKELESS GA** (ID: 45) → Standard cost

**📦 Other Key Categories:**
- KRATOM, CBD/HEMP, ELECTRONIC CIG, DRINKS, AUTOMOTIVE, etc.

---

### 5. Customer (dbo.Customer)
**Customer master data**
**📊 2,824 customers**

**Key Columns:**
- `ID` (int) - Customer ID ⭐ **PRIMARY KEY**
- `FirstName` (nvarchar) - Customer first name
- `LastName` (nvarchar) - Customer last name  
- `Company` (nvarchar) - Business name
- `AccountBalance` (money) - Current AR balance
- `TotalSales` (money) - Lifetime sales total
- `LastVisit` (datetime) - Last transaction date
- `TotalVisits` (int) - Number of transactions

**Business Logic:**
- Use `COALESCE(Company, FirstName + ' ' + LastName)` for display name
- `LastVisit` for customer activity analysis

---

### 6. AccountReceivable (dbo.AccountReceivable)
**Account receivables and aging**
**📊 142,706 entries**

**Key Columns:**
- `ID` (int) - AR record ID
- `CustomerID` (int) - Links to Customer ⭐ **FOREIGN KEY**
- `Date` (datetime) - Transaction/invoice date
- `DueDate` (datetime) - Payment due date
- `Balance` (money) - Outstanding amount
- `OriginalAmount` (money) - Original invoice amount
- `TransactionNumber` (int) - Links to Transaction

**Aging Buckets:**
- 0-30 days: `DATEDIFF(day, Date, GETDATE()) <= 30`
- 31-60 days: `DATEDIFF(day, Date, GETDATE()) <= 60`
- 61-90 days: `DATEDIFF(day, Date, GETDATE()) <= 90`
- 90+ days: `DATEDIFF(day, Date, GETDATE()) > 90`

---

## 💰 Financial Tables

### 7. TenderEntry (dbo.TenderEntry)
**Payment method details**
**📊 358,194 entries**

**Key Columns:**
- `TransactionNumber` (int) - Links to Transaction ⭐ **FOREIGN KEY**
- `TenderID` (int) - Payment method type
- `Amount` (money) - Payment amount
- `Description` (nvarchar) - Payment description

### 8. Payment (dbo.Payment)  
**Customer payments on account**
**📊 63,021 payments**

### 9. DailySales (dbo.DailySales)
**Daily sales summary data**
**📊 563,775 records**

---

## 🔗 Critical Database Relationships

```sql
-- Core Transaction Flow
Transaction (TransactionNumber) 
    → TransactionEntry (TransactionNumber)
    → Item (ID = ItemID)
    → Category (ID = CategoryID)

-- Customer Flow  
Transaction (CustomerID) → Customer (ID)
AccountReceivable (CustomerID) → Customer (ID)

-- Payment Flow
TenderEntry (TransactionNumber) → Transaction (TransactionNumber)
```

---

## 📅 Data Patterns & Business Hours

### Recent Activity (Last 7 Days):
- **2025-07-15:** 30 transactions, $66,823.27
- **2025-07-14:** 53 transactions, $104,660.73  
- **2025-07-13:** 27 transactions, $100,632.32
- **2025-07-11:** 61 transactions, $149,039.94 (busiest day)

### Data Completeness:
✅ **TransactionEntry:** 4.6M records (complete)  
✅ **Item:** 12.3K products (complete)  
✅ **Customer:** 2.8K customers (complete)  
✅ **Category:** 83 categories (complete)  
❌ **Transaction:** Row count issues (reserved keyword)

---

## 🛠️ Technical Implementation Notes

### SQL Query Best Practices:

1. **Transaction Table:** Always use brackets
   ```sql
   SELECT * FROM [dbo].[Transaction] t
   ```

2. **Joins:** Use TransactionNumber (not ID) to join Transaction ↔ TransactionEntry
   ```sql
   FROM [dbo].[Transaction] t
   JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
   ```

3. **Item Lookups:** Use ItemID to join TransactionEntry ↔ Item
   ```sql
   FROM dbo.TransactionEntry te  
   JOIN dbo.Item i ON te.ItemID = i.ID
   ```

4. **Category Joins:** Use CategoryID
   ```sql
   FROM dbo.Item i
   LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
   ```

### Cost Uplift Business Logic:
```sql
CASE 
    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23     -- +23%
    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- +10%
    ELSE te.Cost * te.Quantity  -- Standard cost
END as AdjustedCost
```

---

## 🎯 Dashboard Query Templates

### Sales Summary:
```sql
SELECT 
    SUM(te.Price * te.Quantity) as NetSales,
    SUM(te.Quantity) as Units,
    COUNT(DISTINCT t.TransactionNumber) as Invoices
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
WHERE CAST(t.Time as DATE) BETWEEN @StartDate AND @EndDate
```

### Top Movers:
```sql
SELECT TOP 5
    i.Description,
    SUM(te.Price * te.Quantity) as Revenue,
    SUM(te.Quantity) as Units
FROM [dbo].[Transaction] t
JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
JOIN dbo.Item i ON te.ItemID = i.ID
WHERE t.Time >= DATEADD(day, -7, GETDATE())
GROUP BY i.Description
ORDER BY Revenue DESC
```

### Inventory Value:
```sql
SELECT 
    COUNT(DISTINCT i.ID) as SKUCount,
    SUM(i.Quantity * i.Cost) as TotalValue
FROM dbo.Item i
WHERE i.Quantity > 0
```

---

## ✅ Verified Working Joins

All critical joins have been tested and confirmed working:

1. ✅ **Transaction ↔ TransactionEntry** - Core sales data
2. ✅ **Item ↔ Category** - Product categorization  
3. ✅ **Full Sales Join** - Transaction → TransactionEntry → Item → Category

---

This database contains a complete 13-year history of retail operations with proper relationships and business logic for building comprehensive dashboards and analytics. 