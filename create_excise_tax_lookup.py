#!/usr/bin/env python3
"""
Create ExciseTaxTypes lookup table for fast PAID vs COLL checking
This makes the correct GP calculation FAST
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
print("Creating ExciseTaxTypes Lookup Table")
print("="*60)

# Step 1: Create lookup table
print("\n1. Creating ExciseTaxTypes table...")
cursor.execute("""
    IF OBJECT_ID('dbo.ExciseTaxTypes', 'U') IS NOT NULL
        DROP TABLE dbo.ExciseTaxTypes
""")

cursor.execute("""
    CREATE TABLE ExciseTaxTypes (
        TaxType VARCHAR(50) PRIMARY KEY,
        IsPrePaid BIT NOT NULL,
        Description VARCHAR(255) NULL
    )
""")
print("   ✅ Table created")

# Step 2: Get all actual tax types from database
print("\n2. Finding all excise tax types in database...")
cursor.execute("""
    SELECT DISTINCT SubDescription3
    FROM PUExciseEntry
    WHERE SubDescription3 IS NOT NULL
    ORDER BY SubDescription3
""")

tax_types = [row[0] for row in cursor.fetchall()]
print(f"   Found {len(tax_types)} tax types:")
for tt in tax_types:
    print(f"      {tt}")

# Step 3: Insert tax types with PAID/COLL classification
print("\n3. Populating lookup table...")
for tax_type in tax_types:
    is_prepaid = 1 if 'PAID' in tax_type.upper() else 0
    description = "Pre-paid (already in COGS)" if is_prepaid else "Collected at POS"

    cursor.execute("""
        INSERT INTO ExciseTaxTypes (TaxType, IsPrePaid, Description)
        VALUES (%s, %s, %s)
    """, (tax_type, is_prepaid, description))

conn.commit()
print(f"   ✅ Inserted {len(tax_types)} tax types")

# Step 4: Show the results
print("\n4. Lookup Table Contents:")
cursor.execute("SELECT * FROM ExciseTaxTypes ORDER BY TaxType")
for row in cursor.fetchall():
    tax_type, is_prepaid, desc = row
    status = "🔴 PRE-PAID" if is_prepaid else "✅ COLLECTED"
    print(f"   {status} {tax_type}: {desc}")

# Step 5: Create index for fast lookups
print("\n5. Creating index...")
cursor.execute("""
    CREATE INDEX IX_ExciseTaxTypes_IsPrePaid
    ON ExciseTaxTypes(IsPrePaid)
""")
conn.commit()
print("   ✅ Index created")

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ ExciseTaxTypes lookup table ready!")
print("\nNow the populate script can use fast JOINs instead of LIKE!")
print("="*60)
