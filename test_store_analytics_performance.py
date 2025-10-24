"""
Test different approaches for loading all store analytics data.

Goal: Find the fastest way to get analytics for ALL stores at once,
      so customer groups page can just filter which stores to display.
"""

import sys
import time
from datetime import datetime, timedelta

print("=" * 70)
print("STORE ANALYTICS PERFORMANCE TEST")
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
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Define test parameters
DAYS = 30
LIMIT_STORES = 20  # Test with subset first

print(f"Test parameters: Last {DAYS} days, Top {LIMIT_STORES} stores by sales")
print()

# ===== APPROACH 1: Individual queries per store =====
print("=" * 70)
print("APPROACH 1: Individual Queries Per Store")
print("=" * 70)
print()

start_time = time.time()

try:
    # Get top stores
    stores_query = f"""
        SELECT TOP {LIMIT_STORES}
            c.ID as CustomerID,
            c.Company + ' - ' + c.FirstName + ' ' + c.LastName as CustomerName,
            c.Company
        FROM dbo.Customer c
        WHERE c.TotalSales > 0
        ORDER BY c.TotalSales DESC
    """

    stores_df = execute_query(stores_query)
    print(f"✅ Found {len(stores_df)} stores")

    # Query each store individually
    store_analytics = []
    for idx, store in stores_df.iterrows():
        customer_id = store['CustomerID']

        # Sales and GP
        sales_query = f"""
            SELECT
                ISNULL(SUM(te.Price * te.Quantity), 0) as total_sales,
                ISNULL(SUM((te.Price - te.Cost) * te.Quantity), 0) as gross_profit
            FROM dbo.[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.CustomerID = {customer_id}
                AND t.Time >= DATEADD(day, -{DAYS}, GETDATE())
        """
        sales_result = execute_query(sales_query)

        # AR Balance
        ar_query = f"""
            SELECT ISNULL(AccountBalance, 0) as ar_balance
            FROM dbo.Customer
            WHERE ID = {customer_id}
        """
        ar_result = execute_query(ar_query)

        store_analytics.append({
            'customer_id': customer_id,
            'customer_name': store['CustomerName'],
            'total_sales': sales_result.iloc[0]['total_sales'],
            'gross_profit': sales_result.iloc[0]['gross_profit'],
            'ar_balance': ar_result.iloc[0]['ar_balance']
        })

    approach1_time = time.time() - start_time
    print(f"✅ Completed in {approach1_time:.2f} seconds")
    print(f"   Average per store: {approach1_time / len(stores_df):.3f} seconds")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    approach1_time = None

print()

# ===== APPROACH 2: Single aggregated query =====
print("=" * 70)
print("APPROACH 2: Single Aggregated Query")
print("=" * 70)
print()

start_time = time.time()

try:
    # Get all store analytics in one query
    bulk_query = f"""
        WITH StoreSales AS (
            SELECT
                t.CustomerID,
                SUM(te.Price * te.Quantity) as total_sales,
                SUM((te.Price - te.Cost) * te.Quantity) as gross_profit
            FROM dbo.[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -{DAYS}, GETDATE())
            GROUP BY t.CustomerID
        )
        SELECT TOP {LIMIT_STORES}
            c.ID as CustomerID,
            c.Company + ' - ' + c.FirstName + ' ' + c.LastName as CustomerName,
            c.Company,
            c.AccountBalance as ar_balance,
            ISNULL(ss.total_sales, 0) as total_sales,
            ISNULL(ss.gross_profit, 0) as gross_profit
        FROM dbo.Customer c
        LEFT JOIN StoreSales ss ON c.ID = ss.CustomerID
        WHERE c.TotalSales > 0
        ORDER BY c.TotalSales DESC
    """

    result_df = execute_query(bulk_query)
    print(f"✅ Found {len(result_df)} stores")

    approach2_time = time.time() - start_time
    print(f"✅ Completed in {approach2_time:.2f} seconds")

    if approach1_time:
        speedup = approach1_time / approach2_time
        print(f"   🚀 {speedup:.1f}x faster than Approach 1!")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    approach2_time = None

print()

# ===== APPROACH 3: Bulk with categories =====
print("=" * 70)
print("APPROACH 3: Single Query with Category Breakdown")
print("=" * 70)
print()

start_time = time.time()

try:
    # Get all store analytics + category data in one query
    bulk_with_categories_query = f"""
        WITH StoreSales AS (
            SELECT
                t.CustomerID,
                SUM(te.Price * te.Quantity) as total_sales,
                SUM((te.Price - te.Cost) * te.Quantity) as gross_profit
            FROM dbo.[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -{DAYS}, GETDATE())
            GROUP BY t.CustomerID
        ),
        CategorySales AS (
            SELECT
                t.CustomerID,
                cat.Name as CategoryName,
                SUM(te.Price * te.Quantity) as category_sales,
                SUM((te.Price - te.Cost) * te.Quantity) as category_gp,
                ROW_NUMBER() OVER (PARTITION BY t.CustomerID ORDER BY SUM(te.Price * te.Quantity) DESC) as rn
            FROM dbo.[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            JOIN dbo.Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= DATEADD(day, -{DAYS}, GETDATE())
            GROUP BY t.CustomerID, cat.Name
        )
        SELECT TOP {LIMIT_STORES}
            c.ID as CustomerID,
            c.Company + ' - ' + c.FirstName + ' ' + c.LastName as CustomerName,
            c.Company,
            c.AccountBalance as ar_balance,
            ISNULL(ss.total_sales, 0) as total_sales,
            ISNULL(ss.gross_profit, 0) as gross_profit,
            cs.CategoryName as top_category,
            ISNULL(cs.category_sales, 0) as top_category_sales
        FROM dbo.Customer c
        LEFT JOIN StoreSales ss ON c.ID = ss.CustomerID
        LEFT JOIN CategorySales cs ON c.ID = cs.CustomerID AND cs.rn = 1
        WHERE c.TotalSales > 0
        ORDER BY c.TotalSales DESC
    """

    result_df = execute_query(bulk_with_categories_query)
    print(f"✅ Found {len(result_df)} stores")
    print(f"   Sample top category: {result_df.iloc[0]['top_category']} (${result_df.iloc[0]['top_category_sales']:.2f})")

    approach3_time = time.time() - start_time
    print(f"✅ Completed in {approach3_time:.2f} seconds")

    if approach1_time:
        speedup = approach1_time / approach3_time
        print(f"   🚀 {speedup:.1f}x faster than Approach 1!")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    approach3_time = None

print()

# ===== SUMMARY =====
print("=" * 70)
print("PERFORMANCE SUMMARY")
print("=" * 70)
print()

if approach1_time:
    print(f"Approach 1 (Individual queries): {approach1_time:.2f}s")
if approach2_time:
    print(f"Approach 2 (Single bulk query):  {approach2_time:.2f}s")
if approach3_time:
    print(f"Approach 3 (Bulk + categories):  {approach3_time:.2f}s")

print()

if approach2_time and approach3_time:
    if approach2_time < approach3_time:
        print("✅ RECOMMENDATION: Use Approach 2 for basic analytics")
        print("   Then load category data separately when viewing group details")
    else:
        print("✅ RECOMMENDATION: Use Approach 3 to get everything at once")
        print("   Categories included with minimal overhead")

print()
print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print()
print("1. Use the fastest approach to load ALL store analytics on page load")
print("2. Store results in st.session_state for instant filtering")
print("3. Customer groups page filters this cached data by CustomerID")
print("4. No per-group calculations needed!")
print()
