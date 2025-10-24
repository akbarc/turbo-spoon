#!/usr/bin/env python3
"""
Example: Using Department Hierarchy Across the System
Shows how the department structure is accessible everywhere
"""
import os
from datetime import datetime
os.environ['TDSVER'] = '7.0'
import pymssql

# Import the module
from data_foundation.gross_profit import get_gp_by_department, get_gp_by_category

print("="*60)
print("Department Hierarchy - Practical Usage Examples")
print("="*60)

# ============================================================
# Example 1: Python API - Get Department GP
# ============================================================
print("\n1. Using Python API (get_gp_by_department):\n")

today = datetime.now()
departments = get_gp_by_department(today)

print(f"   Today's GP by Department ({today.date()}):\n")
for dept in departments:
    print(f"   {dept['DepartmentName']:<35} ${dept['gross_profit']:>10,.2f} ({dept['gp_margin_percent']:>5.1f}%)")

# ============================================================
# Example 2: Direct SQL - Category to Department Mapping
# ============================================================
print("\n2. Using Direct SQL (category to department mapping):\n")

conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=10
)
cursor = conn.cursor(as_dict=True)

cursor.execute("""
    SELECT
        cat.Name as CategoryName,
        d.DepartmentName,
        cm.SubCategoryName
    FROM Category cat
    INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
    INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
    WHERE cat.Name IN ('CIGARETTE', 'CANDYS', 'VITAMINS', 'NOVELTY ITEMS')
    ORDER BY d.DepartmentName
""")

print("   Category to Department Mapping:\n")
for row in cursor.fetchall():
    print(f"   {row['CategoryName']:<20} → {row['DepartmentName']:<35} ({row['SubCategoryName']})")

# ============================================================
# Example 3: Combining Category and Department Data
# ============================================================
print("\n3. Combining Category + Department Data:\n")

categories = get_gp_by_category(today)

cursor.execute("""
    SELECT
        cat.ID as CategoryID,
        d.DepartmentCode
    FROM Category cat
    INNER JOIN CategoryMapping cm ON cat.ID = cm.CategoryID
    INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
""")

# Build category to department lookup
cat_to_dept = {row['CategoryID']: row['DepartmentCode'] for row in cursor.fetchall()}

# Group categories by department
dept_categories = {}
for cat in categories:
    # Get department code for this category
    cursor.execute("SELECT ID FROM Category WHERE Name = %s", (cat['CategoryName'],))
    result = cursor.fetchone()
    if result:
        cat_id = result['ID']
        dept_code = cat_to_dept.get(cat_id, 'UNKNOWN')

        if dept_code not in dept_categories:
            dept_categories[dept_code] = []
        dept_categories[dept_code].append(cat)

print("   Top Category in Each Department:\n")
for dept_code in ['TOBACCO', 'VAPING', 'FOOD_BEV', 'HEALTH', 'HOUSEHOLD']:
    if dept_code in dept_categories and dept_categories[dept_code]:
        top_cat = max(dept_categories[dept_code], key=lambda x: x['gross_profit'])
        cursor.execute("SELECT DepartmentName FROM Departments WHERE DepartmentCode = %s", (dept_code,))
        dept_name = cursor.fetchone()['DepartmentName']

        print(f"   {dept_name:<35}")
        print(f"      Best: {top_cat['CategoryName']:<20} GP: ${top_cat['gross_profit']:>8,.2f}")

# ============================================================
# Example 4: REST API Example
# ============================================================
print("\n4. Using REST API:\n")
print("   curl http://100.126.106.37:8081/api/gp/departments")
print("\n   Returns JSON with all department GP data")

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ Department hierarchy is accessible from:")
print("   • Python API (get_gp_by_department)")
print("   • Direct SQL (JOIN with CategoryMapping + Departments)")
print("   • REST API (/api/gp/departments)")
print("   • Any custom query or dashboard")
print("="*60)
