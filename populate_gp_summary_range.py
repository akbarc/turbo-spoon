#!/usr/bin/env python3
"""
Populate GP_Daily_Summary table with historical data
Populates from start_date to end_date (defaults to YTD)
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
    'timeout': 300,  # 5 minutes per day
    'login_timeout': 10
}

def populate_day(date):
    """Populate summary data for one day - creates its own connection"""
    # Create fresh connection for this day to avoid timeouts
    conn = pymssql.connect(**DB_CONFIG)
    cursor = conn.cursor(as_dict=True)

    # Delete existing data for this date
    cursor.execute("DELETE FROM GP_Daily_Summary WHERE BusinessDate = %s", (date,))

    # Insert new data with CORRECT excise tax handling
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
    cursor.close()
    conn.close()  # Close connection for this day

    return row_count

# Parse command line arguments
if len(sys.argv) >= 3:
    start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    end_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
else:
    # Default: Year to Date (Jan 1 to yesterday)
    today = datetime.now().date()
    start_date = datetime(today.year, 1, 1).date()
    end_date = today - timedelta(days=1)  # Don't include today (already populated)

print("="*60)
print("Populating GP_Daily_Summary - Historical Data")
print("="*60)
print(f"\nDate Range: {start_date} to {end_date}")

# Calculate number of days
delta = end_date - start_date
num_days = delta.days + 1

print(f"Total Days: {num_days}")
print("\nThis will take several minutes...")
print(f"Estimated time: {num_days * 2} seconds (~{num_days * 2 / 60:.1f} minutes)")
print()

total_categories = 0
days_processed = 0
days_with_data = 0

try:
    current_date = start_date

    while current_date <= end_date:
        print(f"[{days_processed + 1}/{num_days}] {current_date}...", end=" ", flush=True)

        count = populate_day(current_date)  # Each day creates its own connection

        if count > 0:
            print(f"✅ {count} categories")
            total_categories += count
            days_with_data += 1
        else:
            print("⚠️  No data")

        days_processed += 1
        current_date += timedelta(days=1)

    print("\n" + "="*60)
    print("✅ COMPLETE!")
    print("="*60)
    print(f"Days Processed: {days_processed}")
    print(f"Days with Data: {days_with_data}")
    print(f"Total Categories Inserted: {total_categories}")
    print(f"\nAverage categories per day: {total_categories / days_with_data if days_with_data > 0 else 0:.1f}")
    print("\n🎉 Historical data populated! Date filtering now works.")
    print("\nTest it at: http://localhost:8081")
    print("Try selecting different date ranges (MTD, QTD, YTD, custom)")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
