# Product Categorization Overlay - Design Plan

**Date**: October 15, 2025

---

## Current State

**83 total categories** with inconsistent naming:
- Many duplicate/overlapping categories (MISC appears twice, multiple tobacco categories)
- No department-level grouping
- Hard to analyze high-level trends
- Categories not aligned with business logic

---

## Proposed Department Hierarchy

### Department 1: TOBACCO & SMOKING
**Revenue Driver - Regulated Products**

**Sub-Categories**:
- Cigarettes (CIGARETTE)
- Cigars (CIGARS, CIGAR GA, LITTLE CIGAR-GA, LIT CIGARS 003251)
- Smokeless Tobacco (T7 SMOKELESS GA, LT-TAX-COLLECTED, LT-TAX PAID, LT-NON-GA/ROL UR OWN)
- Rolling Papers & Wraps (CIG ROLLING PAPER, BLUNT WRAP)

**Key Attributes**:
- High volume, low margin
- Excise tax implications (PAID vs COLL)
- Age-restricted

---

### Department 2: VAPING & ALTERNATIVES
**Growing Category - Modern Nicotine**

**Sub-Categories**:
- E-Cigarettes & Devices (ELECTRONIC CIG, ECIG - PODS, ECIG - DISP D8, ECIG - PODS D8)
- Nicotine Pouches (NICOTINE POUCHES)
- CBD & Hemp Products (CBD/HEMP, KRATOM)

**Key Attributes**:
- Higher margin than traditional tobacco
- Age-restricted
- Rapidly evolving products

---

### Department 3: FOOD & BEVERAGE
**Convenience Store Core**

**Sub-Categories**:
- Candy & Sweets (CANDYS, GUMS/CHICLETS, COOKIES)
- Packaged Food (FOOD, FROZEN)
- Beverages (DRINKS, WATER)

**Key Attributes**:
- Impulse purchases
- Medium margin
- High turnover

---

### Department 4: HEALTH & WELLNESS
**Growing Category**

**Sub-Categories**:
- Medicine & OTC (MEDICINE)
- Vitamins & Supplements (VITAMINS)
- Personal Care (COSMETICS & BEAUTY, PERFUMES, TOOTH, CONDOMS)

**Key Attributes**:
- Higher margin
- Repeat customers
- Health-conscious buyers

---

### Department 5: HOUSEHOLD & GENERAL MERCHANDISE
**High SKU Count**

**Sub-Categories**:
- Cleaning Supplies (CLEANING PRODUCTS, KITCHEN & TOILET, CLEKIT, CLEAM)
- Household Essentials (HOUSEHOLD GOODS, HARDWARE, AUTOMOTIVE)
- Home Fragrance (AIR FRESHENER, AIR SCENTS, CANDLES, INCENSE)
- Accessories & Novelty (NOVELTY ITEMS, LIGHTERS, SHOPPING BAGS, GLOVES & T SHIRTS, APPAREL & CLOTHING)
- Electronics & Tech (CELLUAR ACCESSORIES, PHONE CARDS, BATTERY)
- Stationery & Entertainment (STATIONARY, PLAYING CARDS, TOYS, KIDS STUFF, ENTERTAINMENT)

**Key Attributes**:
- Diverse product mix
- Variable margins
- 1,361 items in NOVELTY ITEMS alone

---

### Department 6: OTHER / UNCATEGORIZED
**Cleanup Category**

**Sub-Categories**:
- Miscellaneous (MISC x2, JBR)
- Temporary/System (TMP, TMP2, TMPSE, DELETE, NoCat, SUPPLIER, QUOTATION)
- Legacy/Inactive (TOB 003211-003215, LIST-1, LIST-2, KC, MAPS, JUICES, FILMS, CAMERA, KITS, ZIPPO, FLOWERS, STAINLESS STEEL, LIL DRUG, LT-RYO-TAX COLLECTED)

**Action**: Clean up and consolidate

---

## Database Schema Design

### Table: Departments
```sql
CREATE TABLE Departments (
    DepartmentID INT IDENTITY(1,1) PRIMARY KEY,
    DepartmentCode VARCHAR(20) NOT NULL UNIQUE,
    DepartmentName VARCHAR(100) NOT NULL,
    Description VARCHAR(500),
    SortOrder INT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedDate DATETIME DEFAULT GETDATE(),
    ModifiedDate DATETIME DEFAULT GETDATE()
)
```

### Table: CategoryMapping
```sql
CREATE TABLE CategoryMapping (
    MappingID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryID INT NOT NULL,  -- Links to existing Category.ID
    DepartmentID INT NOT NULL,  -- Links to Departments
    SubCategoryName VARCHAR(100),  -- Optional sub-category grouping
    SortOrder INT DEFAULT 0,
    IsActive BIT DEFAULT 1,
    CreatedDate DATETIME DEFAULT GETDATE(),
    ModifiedDate DATETIME DEFAULT GETDATE(),

    CONSTRAINT FK_CategoryMapping_Category FOREIGN KEY (CategoryID) REFERENCES Category(ID),
    CONSTRAINT FK_CategoryMapping_Department FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID),
    CONSTRAINT UQ_CategoryMapping UNIQUE (CategoryID)  -- Each category mapped once
)
```

### View: vw_ProductHierarchy
```sql
CREATE VIEW vw_ProductHierarchy AS
SELECT
    i.ID as ItemID,
    i.ItemLookupCode,
    i.Description,
    i.Price,
    i.Cost,
    cat.ID as CategoryID,
    cat.Name as CategoryName,
    d.DepartmentID,
    d.DepartmentCode,
    d.DepartmentName,
    cm.SubCategoryName,
    d.SortOrder as DeptSortOrder,
    cm.SortOrder as CategorySortOrder
FROM Item i
INNER JOIN Category cat ON i.CategoryID = cat.ID
LEFT JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
LEFT JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE i.Inactive = 0
```

---

## Implementation Steps

1. **Create Department table** with 6 main departments
2. **Create CategoryMapping table** to link categories to departments
3. **Populate mappings** for all 83 categories
4. **Create view** for easy hierarchical queries
5. **Update GP_Daily_Summary** to include department rollups
6. **Update dashboard** to show department-level breakdowns

---

## Benefits

1. **Cleaner Reporting**: Department-level GP analysis
2. **Better Insights**: See which product areas drive profit
3. **Flexible**: Can re-map categories without changing POS
4. **Fast**: Pre-calculated department summaries
5. **Scalable**: Easy to add sub-departments or product lines

---

## Example Queries

### Department GP Summary:
```sql
SELECT
    d.DepartmentName,
    SUM(gp.Revenue) as Revenue,
    SUM(gp.GrossProfit) as GP,
    SUM(gp.GrossProfit) / SUM(gp.Revenue) * 100 as GPMargin
FROM GP_Daily_Summary gp
INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE gp.BusinessDate = '2025-10-15'
GROUP BY d.DepartmentName
ORDER BY GP DESC
```

### Top Products by Department:
```sql
SELECT TOP 10
    d.DepartmentName,
    i.Description,
    SUM(te.Quantity) as Units,
    SUM(te.Price * te.Quantity) as Revenue
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
INNER JOIN Category cat ON i.CategoryID = cat.ID
INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE CAST(te.TransactionTime AS DATE) = '2025-10-15'
GROUP BY d.DepartmentName, i.Description
ORDER BY Revenue DESC
```

---

## Next Steps

Ready to implement? This will create:
- 6 departments
- Map all 83 categories
- Update GP summaries with department rollups
- Enhanced dashboard with department view

**Estimated time**: 20-30 minutes
**Risk**: LOW (read-only on POS tables, new overlay tables only)
