# Department Hierarchy - Complete Access Guide

**Date**: October 15, 2025

---

## ✅ YES - It's a Persistent, Reusable Data Structure

The department hierarchy is **permanently stored in the database** and accessible from:
- ✅ SQL queries (any tool)
- ✅ Python API (data_foundation module)
- ✅ REST API (dashboard endpoints)
- ✅ Dashboard UI (web interface)

---

## Database Tables (Permanent Storage)

### 1. Departments Table
```sql
SELECT * FROM Departments ORDER BY SortOrder

-- Returns:
TOBACCO     | Tobacco & Smoking
VAPING      | Vaping & Alternatives
FOOD_BEV    | Food & Beverage
HEALTH      | Health & Wellness
HOUSEHOLD   | Household & General Merchandise
OTHER       | Other / Uncategorized
```

### 2. CategoryMapping Table
```sql
SELECT * FROM CategoryMapping ORDER BY DepartmentID

-- Links every category to a department:
CategoryID → DepartmentID → SubCategoryName
```

---

## Access Methods

### 1. Direct SQL (Anywhere)

**Get Department GP**:
```sql
SELECT
    d.DepartmentName,
    SUM(gp.Revenue) as Revenue,
    SUM(gp.GrossProfit) as GP,
    (SUM(gp.GrossProfit) / SUM(gp.Revenue) * 100) as Margin
FROM GP_Daily_Summary gp
INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE gp.BusinessDate = CAST(GETDATE() AS DATE)
GROUP BY d.DepartmentName
ORDER BY GP DESC
```

**Get Products by Department**:
```sql
SELECT
    d.DepartmentName,
    cat.Name as CategoryName,
    i.Description as ProductName,
    i.Price,
    i.Cost
FROM Item i
INNER JOIN Category cat ON i.CategoryID = cat.ID
INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE i.Inactive = 0
ORDER BY d.DepartmentName, cat.Name
```

**Get Category to Department Mapping**:
```sql
SELECT
    cat.Name as CategoryName,
    d.DepartmentName,
    cm.SubCategoryName
FROM Category cat
INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
ORDER BY d.DepartmentName, cat.Name
```

---

### 2. Python API (data_foundation module)

```python
from data_foundation.gross_profit import get_gp_by_department
from datetime import datetime

# Get today's department GP
today = datetime.now()
departments = get_gp_by_department(today)

for dept in departments:
    print(f"{dept['DepartmentName']}: ${dept['gross_profit']:,.2f}")
```

**Returns**:
```json
[
    {
        "DepartmentCode": "TOBACCO",
        "DepartmentName": "Tobacco & Smoking",
        "revenue": 199449.89,
        "gross_profit": 5683.98,
        "gp_margin_percent": 2.85,
        "category_count": 9,
        "item_count": 408
    },
    ...
]
```

---

### 3. REST API (HTTP Endpoints)

**Base URL**: http://100.126.106.37:8081

**Endpoints**:
- `GET /api/gp/departments` - Today's department GP
- `GET /api/gp/categories` - Today's category GP (includes department info)
- `GET /api/gp/today` - Overall GP summary

**Example**:
```bash
curl http://100.126.106.37:8081/api/gp/departments
```

**Response**:
```json
[
    {
        "DepartmentCode": "TOBACCO",
        "DepartmentName": "Tobacco & Smoking",
        "category_count": 9,
        "revenue": 199449.89,
        "gross_profit": 5683.98,
        "gp_margin_percent": 2.8498
    },
    {
        "DepartmentCode": "FOOD_BEV",
        "DepartmentName": "Food & Beverage",
        "category_count": 6,
        "revenue": 1879.16,
        "gross_profit": 364.08,
        "gp_margin_percent": 19.3746
    }
]
```

---

### 4. Dashboard UI

**URL**: http://100.126.106.37:8081

**Available Data**:
- Today's GP summary
- Category breakdown (37 categories)
- Department breakdown (6 departments) - **NEW**
- Excise tax details

---

## Department Structure (Reference)

### Department Codes:
| Code | Name | Categories | Use Case |
|------|------|------------|----------|
| `TOBACCO` | Tobacco & Smoking | 16 | Cigarettes, cigars, smokeless |
| `VAPING` | Vaping & Alternatives | 7 | E-cigs, nicotine pouches, CBD |
| `FOOD_BEV` | Food & Beverage | 8 | Candy, snacks, drinks |
| `HEALTH` | Health & Wellness | 6 | Medicine, vitamins, beauty |
| `HOUSEHOLD` | Household & General | 24 | Cleaning, electronics, novelty |
| `OTHER` | Other / Uncategorized | 21 | Misc, temp, inactive |

---

## Use Cases

### 1. Executive Dashboard
**Show high-level department performance**:
```python
departments = get_gp_by_department(today)
# Display 6 department cards with GP, margin, trend
```

### 2. Category Analysis
**Drill down from department to categories**:
```sql
-- Click on "Tobacco & Smoking" department
SELECT
    cat.Name,
    gp.Revenue,
    gp.GrossProfit
FROM GP_Daily_Summary gp
INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
WHERE cm.DepartmentID = (SELECT DepartmentID FROM Departments WHERE DepartmentCode = 'TOBACCO')
```

### 3. Product Search
**Find products by department**:
```sql
SELECT i.Description
FROM Item i
INNER JOIN Category cat ON i.CategoryID = cat.ID
INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
WHERE cm.DepartmentID = (SELECT DepartmentID FROM Departments WHERE DepartmentCode = 'FOOD_BEV')
```

### 4. Reporting
**Generate department-level sales reports**:
```sql
SELECT
    d.DepartmentName,
    CAST(te.TransactionTime AS DATE) as Date,
    SUM(te.Price * te.Quantity) as DailyRevenue
FROM TransactionEntry te
INNER JOIN Item i ON te.ItemID = i.ID
INNER JOIN Category cat ON i.CategoryID = cat.ID
INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE te.TransactionTime >= DATEADD(day, -30, GETDATE())
GROUP BY d.DepartmentName, CAST(te.TransactionTime AS DATE)
ORDER BY Date DESC
```

---

## Modifying the Structure

### Add New Department:
```sql
INSERT INTO Departments (DepartmentCode, DepartmentName, Description, SortOrder)
VALUES ('NEW_DEPT', 'New Department', 'Description', 7)
```

### Remap a Category:
```sql
UPDATE CategoryMapping
SET DepartmentID = (SELECT DepartmentID FROM Departments WHERE DepartmentCode = 'FOOD_BEV')
WHERE CategoryID = (SELECT ID FROM Category WHERE Name = 'COOKIES')
```

### Add New Category Mapping:
```sql
INSERT INTO CategoryMapping (CategoryID, DepartmentID, SubCategoryName, SortOrder)
VALUES (
    (SELECT ID FROM Category WHERE Name = 'NEW CATEGORY'),
    (SELECT DepartmentID FROM Departments WHERE DepartmentCode = 'HOUSEHOLD'),
    'Miscellaneous',
    100
)
```

---

## Integration Examples

### Add Department to Existing Queries:

**Before** (flat categories):
```sql
SELECT CategoryName, SUM(GrossProfit) as GP
FROM GP_Daily_Summary
WHERE BusinessDate = CAST(GETDATE() AS DATE)
GROUP BY CategoryName
```

**After** (with departments):
```sql
SELECT
    d.DepartmentName,
    cat.Name as CategoryName,
    SUM(gp.GrossProfit) as GP
FROM GP_Daily_Summary gp
INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
INNER JOIN Category cat ON gp.CategoryID = cat.ID
WHERE gp.BusinessDate = CAST(GETDATE() AS DATE)
GROUP BY d.DepartmentName, cat.Name
ORDER BY d.DepartmentName, GP DESC
```

---

## Python Helper Functions

```python
# Get all departments
def get_departments():
    cursor.execute("SELECT * FROM Departments ORDER BY SortOrder")
    return cursor.fetchall()

# Get categories in a department
def get_categories_by_department(dept_code):
    cursor.execute("""
        SELECT cat.ID, cat.Name
        FROM Category cat
        INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
        INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
        WHERE d.DepartmentCode = %s
        ORDER BY cm.SortOrder
    """, (dept_code,))
    return cursor.fetchall()

# Get department for a category
def get_department_for_category(category_id):
    cursor.execute("""
        SELECT d.DepartmentCode, d.DepartmentName
        FROM Departments d
        INNER JOIN CategoryMapping cm ON d.DepartmentID = cm.DepartmentID
        WHERE cm.CategoryID = %s
    """, (category_id,))
    return cursor.fetchone()
```

---

## Performance

- **Department queries**: < 1 second
- **Category to department JOINs**: < 1 second
- **Product to department JOINs**: < 2 seconds
- **Indexed on**: CategoryID, DepartmentID

---

## Summary

✅ **Persistent**: Stored in SQL Server database
✅ **Accessible**: SQL, Python API, REST API, Dashboard
✅ **Fast**: Indexed, pre-calculated summaries
✅ **Flexible**: Easy to modify, remap, extend
✅ **Reusable**: Available to all dashboards, reports, queries

**The department hierarchy is now a core data structure in your system that can be used everywhere!**
