# GP Dashboard Issue & Fix

## Problem Identified

The GP Dashboard on port 8081 is **not working properly** because:

### Root Cause
The `GP_Daily_Summary` table only has **1 day of data** (October 15, 2025):

```
GP_Daily_Summary Coverage:
  first_date: 2025-10-15
  last_date: 2025-10-15
  days_covered: 1
  total_rows: 37
  unique_categories: 37
```

### Impact
1. **Category breakdown** - Only shows Oct 15th data, not the full date range
2. **Department breakdown** - Same problem
3. **Trending** - Can't show trends with only 1 day
4. **Date range queries** - Return incomplete data

### Why This Happens
The GP dashboard uses two data sources:

1. **PUVIEWEXCISETRANSACTION** (real-time view)
   - Used for: Overall summary, excise tax breakdown
   - ✅ Works for all dates
   - ❌ TOO SLOW for category grouping (query times out after 30 seconds)

2. **GP_Daily_Summary** (pre-aggregated table)
   - Used for: Category breakdown, department breakdown
   - ✅ INSTANT queries (no timeouts)
   - ❌ Requires manual population

**The table is missing historical data**, so category/department endpoints return incomplete results.

## Solution: Populate Historical Data

### Quick Fix (Run This Now)

```bash
cd /Users/akbarchranya/georgiadashboard

# Populate YTD (Jan 1 to yesterday)
python3 populate_gp_summary_range.py

# Or specify custom date range
python3 populate_gp_summary_range.py 2025-01-01 2025-10-15
```

### Expected Output
```
============================================================
Populating GP_Daily_Summary - Historical Data
============================================================

Date Range: 2025-01-01 to 2025-10-15
Total Days: 288

This will take several minutes...
Estimated time: 576 seconds (~9.6 minutes)

[1/288] 2025-01-01... ✅ 37 categories
[2/288] 2025-01-02... ✅ 38 categories
[3/288] 2025-01-03... ✅ 36 categories
...
[288/288] 2025-10-15... ✅ 37 categories

============================================================
✅ COMPLETE!
============================================================
Days Processed: 288
Days with Data: 288
Total Categories Inserted: 10,656
```

### Time Estimate
- **~2 seconds per day**
- **YTD (288 days)**: ~10 minutes
- **Full year (365 days)**: ~12 minutes

## How Populate Works

The script queries `PUVIEWEXCISETRANSACTION` **one day at a time** to avoid timeouts:

```python
def populate_day(date):
    # Delete existing data for this date
    DELETE FROM GP_Daily_Summary WHERE BusinessDate = date

    # Insert aggregated data for this date
    INSERT INTO GP_Daily_Summary
    SELECT
        date as BusinessDate,
        CategoryID,
        CategoryName,
        SUM(Revenue) as Revenue,
        SUM(COGS) as COGS,
        SUM(ExciseTax) as ExciseTax,
        SUM(GrossProfit) as GrossProfit,
        COUNT(Transactions) as TransactionCount,
        COUNT(Items) as ItemCount
    FROM TransactionEntry
    WHERE TransactionTime = date
    GROUP BY CategoryID, CategoryName
```

**Key Features**:
- Fresh connection per day (avoids timeout accumulation)
- Deletes old data before inserting (safe to re-run)
- Shows progress bar
- Can be interrupted and resumed

## After Populate: What Works

Once populated, the GP Dashboard will:

### ✅ Fast Category Analysis
```bash
curl "http://localhost:8081/api/gp/categories?start_date=2025-01-01&end_date=2025-10-15"
# Returns in < 1 second
```

### ✅ Department Breakdown
```bash
curl "http://localhost:8081/api/gp/departments?start_date=2025-01-01&end_date=2025-10-15"
# Returns in < 1 second
```

### ✅ Trending Over Time
The trending chart will show monthly/daily trends across the full date range

### ✅ All Timeframe Buttons Work
- MTD (Month to Date)
- QTD (Quarter to Date)
- YTD (Year to Date)
- 12M (Last 12 months)

## Alternative: Direct Query Solution (Not Recommended)

I also created a version that queries PUVIEWEXCISETRANSACTION directly for categories, but:

❌ **SLOW**: Takes 30+ seconds and often times out
❌ **Unreliable**: Database connection times out
❌ **Resource Intensive**: Puts load on SQL Server

**This is why GP_Daily_Summary exists** - to pre-aggregate data for instant queries.

## Maintenance: Keep Data Updated

### Option 1: Daily Cron Job (Recommended)
```bash
# Add to crontab (run at 1 AM daily)
0 1 * * * cd /Users/akbarchranya/georgiadashboard && python3 populate_gp_summary.py
```

This will populate yesterday's data each morning.

### Option 2: Manual Update
Run the populate script whenever you need updated data:
```bash
python3 populate_gp_summary.py  # Populates yesterday
```

### Option 3: Populate on Dashboard Startup
Modify `gp_dashboard.py` to auto-populate recent days on startup:
```python
# In gp_dashboard.py, before app.run():
from populate_gp_summary import populate_day
from datetime import datetime, timedelta

# Auto-populate last 7 days on startup
for i in range(7):
    date = (datetime.now() - timedelta(days=i)).date()
    populate_day(date)
```

## Testing After Fix

### 1. Check Data Coverage
```bash
python3 -c "
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

query = 'SELECT MIN(BusinessDate) as first, MAX(BusinessDate) as last, COUNT(DISTINCT BusinessDate) as days FROM GP_Daily_Summary'
result = execute_query(query)
print(result[0])
"
```

Expected:
```
{'first': datetime.date(2025, 1, 1), 'last': datetime.date(2025, 10, 15), 'days': 288}
```

### 2. Test Category API
```bash
curl "http://localhost:8081/api/gp/categories?start_date=2025-01-01&end_date=2025-10-15" | python3 -m json.tool | head -30
```

Should show full YTD category data.

### 3. Test Dashboard UI
1. Go to http://localhost:8081
2. Click "Categories" tab
3. Try different timeframes (MTD, QTD, YTD)
4. Verify charts and tables populate

## Summary

### What Was Wrong
- GP_Daily_Summary table only had 1 day of data
- Category/department queries returned incomplete results
- Direct queries on PUVIEWEXCISETRANSACTION timed out

### The Fix
```bash
python3 populate_gp_summary_range.py 2025-01-01 2025-10-15
```
Takes ~10 minutes for YTD.

### Result
- ✅ Instant category/department queries (< 1 second)
- ✅ Full date range coverage
- ✅ All timeframe buttons work
- ✅ Trending charts show proper data
- ✅ No timeouts

### Ongoing Maintenance
Set up a daily cron job to keep data updated automatically.

## Files Reference

- `/Users/akbarchranya/georgiadashboard/populate_gp_summary_range.py` - Historical data population
- `/Users/akbarchranya/georgiadashboard/populate_gp_summary.py` - Daily update (yesterday)
- `/Users/akbarchranya/georgiadashboard/gp_dashboard.py` - Dashboard application
- `/Users/akbarchranya/georgiadashboard/data_foundation/gross_profit.py` - GP calculation logic
