#!/usr/bin/env python3
"""
Create Department hierarchy structure
Maps existing 83 categories to 6 logical departments
"""
import os
os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'sa',
    'password': 'Tech7World',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 30,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor()

print("="*60)
print("Creating Department Structure")
print("="*60)

# Step 1: Create Departments table
print("\n1. Creating Departments table...")
cursor.execute("""
    IF OBJECT_ID('dbo.Departments', 'U') IS NOT NULL
        DROP TABLE dbo.CategoryMapping
""")
cursor.execute("""
    IF OBJECT_ID('dbo.Departments', 'U') IS NOT NULL
        DROP TABLE dbo.Departments
""")

cursor.execute("""
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
""")
conn.commit()
print("   ✅ Departments table created")

# Step 2: Insert departments
print("\n2. Creating 6 main departments...")
departments = [
    ('TOBACCO', 'Tobacco & Smoking', 'Cigarettes, cigars, smokeless tobacco, rolling papers', 1),
    ('VAPING', 'Vaping & Alternatives', 'E-cigarettes, nicotine pouches, CBD/hemp products', 2),
    ('FOOD_BEV', 'Food & Beverage', 'Candy, snacks, drinks, packaged food', 3),
    ('HEALTH', 'Health & Wellness', 'Medicine, vitamins, beauty, personal care', 4),
    ('HOUSEHOLD', 'Household & General Merchandise', 'Cleaning, household goods, electronics, novelty items', 5),
    ('OTHER', 'Other / Uncategorized', 'Miscellaneous, temporary, inactive categories', 6)
]

for code, name, desc, sort in departments:
    cursor.execute("""
        INSERT INTO Departments (DepartmentCode, DepartmentName, Description, SortOrder)
        VALUES (%s, %s, %s, %s)
    """, (code, name, desc, sort))

conn.commit()
print(f"   ✅ {len(departments)} departments created")

# Step 3: Show departments
cursor.execute("SELECT * FROM Departments ORDER BY SortOrder")
print("\n   Departments:")
for row in cursor.fetchall():
    print(f"      {row[1]}: {row[2]}")

# Step 4: Create CategoryMapping table
print("\n3. Creating CategoryMapping table...")
cursor.execute("""
    CREATE TABLE CategoryMapping (
        MappingID INT IDENTITY(1,1) PRIMARY KEY,
        CategoryID INT NOT NULL,
        DepartmentID INT NOT NULL,
        SubCategoryName VARCHAR(100),
        SortOrder INT DEFAULT 0,
        IsActive BIT DEFAULT 1,
        CreatedDate DATETIME DEFAULT GETDATE(),
        ModifiedDate DATETIME DEFAULT GETDATE(),

        CONSTRAINT FK_CategoryMapping_Category FOREIGN KEY (CategoryID) REFERENCES Category(ID),
        CONSTRAINT FK_CategoryMapping_Department FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID),
        CONSTRAINT UQ_CategoryMapping UNIQUE (CategoryID)
    )
""")
conn.commit()
print("   ✅ CategoryMapping table created")

# Step 5: Get category IDs for mapping
print("\n4. Fetching category IDs for mapping...")
cursor.execute("SELECT ID, Name FROM Category ORDER BY Name")
categories = {row[1]: row[0] for row in cursor.fetchall()}
print(f"   Found {len(categories)} categories")

# Step 6: Map categories to departments
print("\n5. Mapping categories to departments...")

# Get department IDs
cursor.execute("SELECT DepartmentID, DepartmentCode FROM Departments")
dept_ids = {row[1]: row[0] for row in cursor.fetchall()}

# Category mappings
mappings = []

# TOBACCO department
tobacco_cats = [
    ('CIGARETTE', 'Cigarettes', 1),
    ('CIGARS', 'Cigars', 2),
    ('CIGAR GA', 'Cigars', 3),
    ('LITTLE CIGAR-GA', 'Cigars', 4),
    ('LIT CIGARS 003251', 'Cigars', 5),
    ('T7 SMOKELESS GA', 'Smokeless Tobacco', 6),
    ('LT-TAX-COLLECTED', 'Smokeless Tobacco', 7),
    ('LT-TAX PAID', 'Smokeless Tobacco', 8),
    ('LT-NON-GA/ROL UR OWN', 'Smokeless Tobacco', 9),
    ('TOB 003211', 'Smokeless Tobacco', 10),
    ('TOB 003212', 'Smokeless Tobacco', 11),
    ('TOB 003213', 'Smokeless Tobacco', 12),
    ('TOB 003214', 'Smokeless Tobacco', 13),
    ('TOB 003215', 'Smokeless Tobacco', 14),
    ('CIG ROLLING PAPER', 'Rolling Papers & Wraps', 15),
    ('BLUNT WRAP', 'Rolling Papers & Wraps', 16),
]

for cat_name, subcat, sort in tobacco_cats:
    if cat_name in categories:
        mappings.append((categories[cat_name], dept_ids['TOBACCO'], subcat, sort))

# VAPING department
vaping_cats = [
    ('ELECTRONIC CIG', 'E-Cigarettes', 1),
    ('ECIG - PODS', 'E-Cigarettes', 2),
    ('ECIG - DISP D8', 'E-Cigarettes', 3),
    ('ECIG - PODS D8', 'E-Cigarettes', 4),
    ('NICOTINE POUCHES', 'Nicotine Alternatives', 5),
    ('CBD/HEMP', 'CBD & Hemp', 6),
    ('KRATOM', 'CBD & Hemp', 7),
]

for cat_name, subcat, sort in vaping_cats:
    if cat_name in categories:
        mappings.append((categories[cat_name], dept_ids['VAPING'], subcat, sort))

# FOOD_BEV department
food_cats = [
    ('CANDYS', 'Candy & Sweets', 1),
    ('GUMS/CHICLETS', 'Candy & Sweets', 2),
    ('COOKIES', 'Candy & Sweets', 3),
    ('FOOD', 'Packaged Food', 4),
    ('FROZEN', 'Packaged Food', 5),
    ('DRINKS', 'Beverages', 6),
    ('WATER', 'Beverages', 7),
    ('JUICES', 'Beverages', 8),
]

for cat_name, subcat, sort in food_cats:
    if cat_name in categories:
        mappings.append((categories[cat_name], dept_ids['FOOD_BEV'], subcat, sort))

# HEALTH department
health_cats = [
    ('MEDICINE', 'Medicine & OTC', 1),
    ('VITAMINS', 'Vitamins & Supplements', 2),
    ('COSMETICS & BEAUTY', 'Beauty & Personal Care', 3),
    ('PERFUMES', 'Beauty & Personal Care', 4),
    ('TOOTH', 'Personal Care', 5),
    ('CONDOMS', 'Personal Care', 6),
]

for cat_name, subcat, sort in health_cats:
    if cat_name in categories:
        mappings.append((categories[cat_name], dept_ids['HEALTH'], subcat, sort))

# HOUSEHOLD department
household_cats = [
    ('CLEANING PRODUCTS', 'Cleaning Supplies', 1),
    ('KITCHEN & TOILET', 'Cleaning Supplies', 2),
    ('CLEKIT', 'Cleaning Supplies', 3),
    ('CLEAM', 'Cleaning Supplies', 4),
    ('HOUSEHOLD GOODS', 'Household Essentials', 5),
    ('HARDWARE', 'Household Essentials', 6),
    ('AUTOMOTIVE', 'Automotive', 7),
    ('AIR FRESHENER', 'Home Fragrance', 8),
    ('AIR SCENTS', 'Home Fragrance', 9),
    ('CANDLES', 'Home Fragrance', 10),
    ('INCENSE', 'Home Fragrance', 11),
    ('NOVELTY ITEMS', 'Accessories & Novelty', 12),
    ('LIGHTERS', 'Accessories & Novelty', 13),
    ('SHOPPING BAGS', 'Accessories & Novelty', 14),
    ('GLOVES & T SHIRTS', 'Apparel', 15),
    ('APPAREL & CLOTHING', 'Apparel', 16),
    ('CELLUAR ACCESSORIES', 'Electronics & Tech', 17),
    ('PHONE CARDS', 'Electronics & Tech', 18),
    ('BATTERY', 'Electronics & Tech', 19),
    ('STATIONARY', 'Stationery & Entertainment', 20),
    ('PLAYING CARDS', 'Stationery & Entertainment', 21),
    ('TOYS', 'Stationery & Entertainment', 22),
    ('KIDS STUFF', 'Stationery & Entertainment', 23),
    ('ENTERTAINMENT', 'Stationery & Entertainment', 24),
]

for cat_name, subcat, sort in household_cats:
    if cat_name in categories:
        mappings.append((categories[cat_name], dept_ids['HOUSEHOLD'], subcat, sort))

# OTHER department (catch-all for miscellaneous/temp categories)
mapped_cats = set([m[0] for m in tobacco_cats + vaping_cats + food_cats + health_cats + household_cats])
other_cats = [cat for cat in categories.keys() if cat not in mapped_cats]

for i, cat_name in enumerate(sorted(other_cats)):
    mappings.append((categories[cat_name], dept_ids['OTHER'], 'Miscellaneous', i + 1))

# Insert mappings
for cat_id, dept_id, subcat, sort in mappings:
    cursor.execute("""
        INSERT INTO CategoryMapping (CategoryID, DepartmentID, SubCategoryName, SortOrder)
        VALUES (%s, %s, %s, %s)
    """, (cat_id, dept_id, subcat, sort))

conn.commit()
print(f"   ✅ Mapped {len(mappings)} categories to departments")

# Step 7: Show mapping summary
print("\n6. Mapping Summary:")
cursor.execute("""
    SELECT
        d.DepartmentName,
        d.SortOrder,
        COUNT(*) as CategoryCount
    FROM CategoryMapping cm
    INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
    GROUP BY d.DepartmentName, d.SortOrder
    ORDER BY d.SortOrder
""")

for row in cursor.fetchall():
    print(f"   {row[0]}: {row[2]} categories")

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ Department structure created!")
print("\nNext: Create department-level GP summaries")
print("="*60)
