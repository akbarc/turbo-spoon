#!/usr/bin/env python3
"""
Populate GP_Daily_Summary table with data
Start with just TODAY to test, then can expand
"""
import os
from datetime import datetime, timedelta
os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'sa',
    'password': 'Tech7World',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 300,  # 5 minutes per day
    'login_timeout': 10
}

def populate_day(date, conn):
    """Populate summary data for one day"""
    cursor = conn.cursor(as_dict=True)

    print(f"\n  Processing {date}...")

    # Delete existing data for this date
    cursor.execute("DELETE FROM GP_Daily_Summary WHERE BusinessDate = %s", (date,))

    # Insert new data with CORRECT excise tax handling
    # PAID excise = already in COGS, don't subtract
    # COLL excise = collected at POS, subtract from GP
    # Uses ExciseTaxTypes lookup table for FAST performance (no LIKE pattern matching!)
    query = """
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
            CAST(%s AS DATE) as BusinessDate,
            cat.ID as CategoryID,
            cat.Name as CategoryName,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as COGS,

            -- Only count COLLECTED excise tax (not PAID)
            -- Uses lookup table for FAST performance
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
        WHERE CAST(te.TransactionTime AS DATE) = %s
        AND te.Quantity != 0
        GROUP BY cat.ID, cat.Name
    """

    cursor.execute(query, (date, date))
    row_count = cursor.rowcount
    conn.commit()

    print(f"    ✅ Inserted {row_count} category records")

    cursor.close()
    return row_count

print("="*60)
print("Populating GP_Daily_Summary")
print("="*60)

conn = pymssql.connect(**DB_CONFIG)

# Start with just today
today = datetime.now().date()

print(f"\nPopulating TODAY ({today})...")
print("This will take a few minutes as it processes all transactions...")

try:
    count = populate_day(today, conn)

    if count > 0:
        print(f"\n✅ SUCCESS! {count} categories populated for {today}")
        print("\nNext steps:")
        print("  1. Test it: python3 test_category_summary.py")
        print("  2. To populate more days:")
        print("     python3 populate_gp_summary_range.py --days 7")
    else:
        print(f"\n⚠️  No data found for {today}")
        print("Try yesterday instead:")
        yesterday = today - timedelta(days=1)
        count = populate_day(yesterday, conn)
        print(f"\n✅ Populated {count} categories for {yesterday}")

except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    conn.close()

print("\n" + "="*60)
