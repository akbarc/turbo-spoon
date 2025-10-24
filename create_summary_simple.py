#!/usr/bin/env python3
"""
Create GP_Daily_Summary table - simplified approach
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
    'timeout': 600,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor()

print("="*60)
print("Creating GP_Daily_Summary Table")
print("="*60)

# Step 1: Drop existing table if exists
print("\n1. Dropping existing table if it exists...")
try:
    cursor.execute("DROP TABLE GP_Daily_Summary")
    conn.commit()
    print("   ✅ Dropped existing table")
except:
    print("   ℹ️  No existing table to drop")

# Step 2: Create table
print("\n2. Creating GP_Daily_Summary table...")
cursor.execute("""
    CREATE TABLE GP_Daily_Summary (
        ID INT IDENTITY(1,1) PRIMARY KEY,
        BusinessDate DATE NOT NULL,
        CategoryID INT NULL,
        CategoryName NVARCHAR(255) NULL,
        Revenue DECIMAL(18,2) NOT NULL DEFAULT 0,
        COGS DECIMAL(18,2) NOT NULL DEFAULT 0,
        ExciseTax DECIMAL(18,2) NOT NULL DEFAULT 0,
        GrossProfit DECIMAL(18,2) NOT NULL DEFAULT 0,
        TransactionCount INT NOT NULL DEFAULT 0,
        ItemCount INT NOT NULL DEFAULT 0,
        LastUpdated DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_GP_Daily_Summary UNIQUE (BusinessDate, CategoryID)
    )
""")
conn.commit()
print("   ✅ Table created")

# Step 3: Create indexes
print("\n3. Creating indexes...")
try:
    cursor.execute("CREATE INDEX IX_GP_Daily_Summary_Date ON GP_Daily_Summary(BusinessDate)")
    conn.commit()
    print("   ✅ Date index created")
except Exception as e:
    print(f"   ⚠️  Date index: {e}")

try:
    cursor.execute("CREATE INDEX IX_GP_Daily_Summary_Category ON GP_Daily_Summary(CategoryID)")
    conn.commit()
    print("   ✅ Category index created")
except Exception as e:
    print(f"   ⚠️  Category index: {e}")

# Step 4: Grant permissions
print("\n4. Granting permissions...")
try:
    cursor.execute("GRANT SELECT ON GP_Daily_Summary TO PUBLIC")
    conn.commit()
    print("   ✅ SELECT permissions granted")
except Exception as e:
    print(f"   ⚠️  Permissions: {e}")

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ Table created successfully!")
print("\nNext: Populate with data using:")
print("  python3 populate_gp_summary.py")
