#!/usr/bin/env python3
"""
Analyze current category structure to design department hierarchy
"""
import os
os.environ['TDSVER'] = '7.0'
import pymssql

conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=30
)
cursor = conn.cursor(as_dict=True)

print("="*60)
print("Current Category Analysis")
print("="*60)

# Get all categories with item counts
print("\n1. All Categories with Item Counts:\n")
cursor.execute("""
    SELECT
        cat.ID,
        cat.Name as CategoryName,
        COUNT(i.ID) as ItemCount,
        SUM(CASE WHEN i.Inactive = 0 THEN 1 ELSE 0 END) as ActiveItems
    FROM Category cat
    LEFT JOIN Item i ON cat.ID = i.CategoryID
    GROUP BY cat.ID, cat.Name
    ORDER BY COUNT(i.ID) DESC
""")

categories = cursor.fetchall()
print(f"   Total categories: {len(categories)}\n")

for cat in categories:
    print(f"   {cat['CategoryName']}: {cat['ItemCount']} items ({cat['ActiveItems']} active)")

# Sample items from each major category
print("\n2. Sample Items from Top Categories:\n")
cursor.execute("""
    SELECT TOP 100
        cat.Name as CategoryName,
        i.Description,
        i.Price
    FROM Item i
    INNER JOIN Category cat ON i.CategoryID = cat.ID
    WHERE i.Inactive = 0
    ORDER BY cat.Name, i.Description
""")

current_cat = None
count = 0
for item in cursor.fetchall():
    if item['CategoryName'] != current_cat:
        if count > 0:
            print()
        current_cat = item['CategoryName']
        count = 0
        print(f"   {current_cat}:")

    count += 1
    if count <= 3:  # Show first 3 items per category
        print(f"      - {item['Description']}")

cursor.close()
conn.close()

print("\n" + "="*60)
