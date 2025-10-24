#!/usr/bin/env python3
"""
Fast bulk populate GP_Daily_Summary - processes ALL days in ONE query
Much faster than day-by-day approach (1-2 minutes vs 4-5 hours)
"""
import os
import sys
from datetime import datetime, timedelta
os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'sa',
    'password': 'Tech7World',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 600,  # 10 minutes for bulk operation
    'login_timeout': 10
}

# Parse command line arguments
if len(sys.argv) >= 3:
    start_date = sys.argv[1]
    end_date = sys.argv[2]
else:
    # Default: Year to Date (Jan 1 to yesterday)
    today = datetime.now().date()
    start_date = f"{today.year}-01-01"
    end_date = str(today - timedelta(days=1))

print("="*60)
print("FAST Bulk Populate GP_Daily_Summary")
print("="*60)
print(f"\nDate Range: {start_date} to {end_date}")
print("\nUsing SINGLE bulk INSERT query (FAST approach)")
print("Estimated time: 1-2 minutes")
print()

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

try:
    # Step 1: Delete existing data in date range
    print("Step 1: Clearing existing data in date range...")
    cursor.execute("""
        DELETE FROM GP_Daily_Summary
        WHERE BusinessDate >= %s AND BusinessDate <= %s
    """, (start_date, end_date))
    deleted_count = cursor.rowcount
    conn.commit()
    print(f"  Deleted {deleted_count} existing records")

    # Step 2: Bulk INSERT all days at once
    print("\nStep 2: Bulk inserting all days (this will take 1-2 minutes)...")
    start_time = datetime.now()

    cursor.execute("""
        INSERT INTO GP_Daily_Summary (
            BusinessDate,
            CategoryID,
            CategoryName,
            Revenue,
            COGS,
            ExciseTax,
            GrossProfit,
            TransactionCount,
            ItemCount
        )
        SELECT
            CAST(te.TransactionTime AS DATE) as BusinessDate,
            cat.ID as CategoryID,
            cat.Name as CategoryName,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as COGS,

            -- Only count COLLECTED excise tax (not PAID)
            SUM(CASE
                WHEN ett.IsPrePaid = 0 THEN COALESCE(pe.PriceC, 0)
                ELSE 0
            END) as ExciseTax,

            -- CORRECT GP: Only subtract COLLECTED excise (PAID is already in COGS)
            SUM(
                (te.Price * te.Quantity) -
                (te.Cost * te.Quantity) -
                CASE
                    WHEN ett.IsPrePaid = 0 THEN COALESCE(pe.PriceC, 0)
                    ELSE 0
                END
            ) as GrossProfit,

            COUNT(DISTINCT te.TransactionNumber) as TransactionCount,
            COUNT(*) as ItemCount
        FROM [dbo].[TransactionEntry] te
        INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
        INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
        LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
        LEFT JOIN [dbo].[ExciseTaxTypes] ett ON pe.SubDescription3 = ett.TaxType
        WHERE CAST(te.TransactionTime AS DATE) >= %s
          AND CAST(te.TransactionTime AS DATE) <= %s
          AND te.Quantity != 0
        GROUP BY CAST(te.TransactionTime AS DATE), cat.ID, cat.Name
    """, (start_date, end_date))

    inserted_count = cursor.rowcount
    conn.commit()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"  Inserted {inserted_count} records")
    print(f"  Time taken: {duration:.1f} seconds ({duration/60:.1f} minutes)")

    # Step 3: Verify results
    print("\nStep 3: Verifying results...")
    cursor.execute("""
        SELECT
            MIN(BusinessDate) as earliest,
            MAX(BusinessDate) as latest,
            COUNT(DISTINCT BusinessDate) as days,
            COUNT(*) as total_records,
            SUM(Revenue) as total_revenue,
            SUM(GrossProfit) as total_gp
        FROM GP_Daily_Summary
        WHERE BusinessDate >= %s AND BusinessDate <= %s
    """, (start_date, end_date))

    result = cursor.fetchone()

    print("\n" + "="*60)
    print("SUCCESS! Data populated")
    print("="*60)
    print(f"  Date Range: {result['earliest']} to {result['latest']}")
    print(f"  Days: {result['days']}")
    print(f"  Total Records: {result['total_records']}")
    print(f"  Total Revenue: ${result['total_revenue']:,.2f}")
    print(f"  Total GP: ${result['total_gp']:,.2f}")
    print(f"\n  Average categories per day: {result['total_records'] / result['days']:.1f}")

    print("\n🎉 Historical data populated! Date filtering now works.")
    print("\nTest it at: http://localhost:8081")
    print("Try selecting different date ranges (MTD, QTD, YTD, custom)")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    cursor.close()
    conn.close()

print("\n" + "="*60)
