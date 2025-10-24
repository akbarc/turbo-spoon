"""
Test script to debug PD checks and verify Payment table structure.
"""

import sys
import os
from datetime import datetime, timedelta

print("=" * 70)
print("PD CHECKS DEBUG SCRIPT")
print("=" * 70)
print()

# Test imports
print("Step 1: Testing database connection...")
try:
    from src.database.sql_server import execute_query, test_connection

    if not test_connection():
        print("❌ Cannot connect to database")
        sys.exit(1)

    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)

print()

# Check if Payment table exists
print("Step 2: Checking Payment table...")
try:
    table_check = execute_query("""
        SELECT COUNT(*) as table_exists
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = 'Payment'
    """)

    if table_check.iloc[0]['table_exists'] > 0:
        print("✅ Payment table exists")
    else:
        print("❌ Payment table NOT found")
        print()
        print("Checking alternative tables...")
        tables = execute_query("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME LIKE '%Payment%'
               OR TABLE_NAME LIKE '%Tender%'
               OR TABLE_NAME LIKE '%Check%'
            ORDER BY TABLE_NAME
        """)
        print("Found these payment-related tables:")
        for _, row in tables.iterrows():
            print(f"  - {row['TABLE_NAME']}")
except Exception as e:
    print(f"❌ Error checking tables: {str(e)}")

print()

# Get Payment table structure
print("Step 3: Getting Payment table structure...")
try:
    columns = execute_query("""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Payment'
        ORDER BY ORDINAL_POSITION
    """)

    if not columns.empty:
        print("Payment table columns:")
        for _, col in columns.iterrows():
            max_len = f"({col['CHARACTER_MAXIMUM_LENGTH']})" if col['CHARACTER_MAXIMUM_LENGTH'] else ""
            print(f"  - {col['COLUMN_NAME']:<30} {col['DATA_TYPE']}{max_len}")
    else:
        print("❌ No columns found (table might not exist)")
except Exception as e:
    print(f"❌ Error: {str(e)}")

print()

# Sample PD check records
print("Step 4: Searching for PD checks in Payment table...")
try:
    pd_samples = execute_query("""
        SELECT TOP 10
            ID,
            Time,
            Amount,
            Comment,
            CustomerID
        FROM dbo.Payment
        WHERE (
            UPPER(Comment) LIKE '%PD%'
            OR UPPER(Comment) LIKE '%POST DATE%'
            OR UPPER(Comment) LIKE '%P D%'
            OR Comment LIKE '%/%/%'
        )
        AND Amount > 0
        ORDER BY Time DESC
    """)

    if not pd_samples.empty:
        print(f"✅ Found {len(pd_samples)} sample PD checks:")
        print()
        for _, row in pd_samples.iterrows():
            print(f"  ID: {row['ID']}")
            print(f"  Date: {row['Time']}")
            print(f"  Amount: ${row['Amount']:.2f}")
            print(f"  Comment: {row['Comment']}")
            print(f"  CustomerID: {row['CustomerID']}")
            print("-" * 50)
    else:
        print("❌ No PD checks found with current patterns")
        print()
        print("Let's check what comments actually look like...")

        # Sample any comments
        sample_comments = execute_query("""
            SELECT TOP 20
                Comment
            FROM dbo.Payment
            WHERE Comment IS NOT NULL
                AND Comment != ''
                AND Amount > 0
            ORDER BY Time DESC
        """)

        if not sample_comments.empty:
            print("Sample payment comments:")
            for _, row in sample_comments.iterrows():
                print(f"  - {row['Comment']}")
        else:
            print("❌ No comments found at all")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print()

# Test query for a specific customer
print("Step 5: Testing PD check query for first customer in CSV...")
try:
    import csv
    if os.path.exists('customer_groups.csv'):
        with open('customer_groups.csv', 'r') as f:
            reader = csv.DictReader(f)
            # Skip header comments
            for line in f:
                if not line.startswith('#'):
                    break

            first_row = next(reader, None)
            if first_row:
                test_customer_id = first_row['CustomerID']
                print(f"Testing with CustomerID: {test_customer_id}")

                test_query = f"""
                    SELECT
                        COUNT(*) as pd_count,
                        ISNULL(SUM(Amount), 0) as pd_total,
                        MAX(Comment) as sample_comment
                    FROM dbo.Payment
                    WHERE CustomerID = {test_customer_id}
                        AND (
                            UPPER(Comment) LIKE '%PD%'
                            OR UPPER(Comment) LIKE '%POST DATE%'
                            OR UPPER(Comment) LIKE '%P D%'
                            OR UPPER(Comment) LIKE '%POSTDATE%'
                            OR Comment LIKE '%/%/%'
                        )
                        AND Amount > 0
                """

                result = execute_query(test_query)
                print(f"PD Checks found: {result.iloc[0]['pd_count']}")
                print(f"Total amount: ${result.iloc[0]['pd_total']:.2f}")
                if result.iloc[0]['sample_comment']:
                    print(f"Sample comment: {result.iloc[0]['sample_comment']}")

except Exception as e:
    print(f"❌ Error: {str(e)}")

print()
print("=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)
