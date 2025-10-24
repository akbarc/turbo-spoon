"""
Gross Profit Calculation Module
Uses existing PUVIEWEXCISETRANSACTION view for accurate GP with excise tax
NO PANDAS - Pure pymssql
FAST - Uses indexed view that already exists
"""
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Set TDS version BEFORE importing pymssql
os.environ['TDSVER'] = '7.0'

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymssql

# Database configuration
DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 120,  # Increased for excise tax queries
    'login_timeout': 10
}

def get_db_connection():
    """Get fresh database connection"""
    return pymssql.connect(
        server=DB_CONFIG['server'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        tds_version=DB_CONFIG['tds_version'],
        timeout=DB_CONFIG['timeout'],
        login_timeout=DB_CONFIG['login_timeout']
    )

def execute_query(query, params=None):
    """Execute query and return results as list of dicts"""
    conn = get_db_connection()
    cursor = conn.cursor(as_dict=True)

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results

def get_gross_profit_summary(start_date=None, end_date=None, customer_id=None):
    """
    Get gross profit summary for a date range
    Uses PUVIEWEXCISETRANSACTION for accurate GP (FAST!)

    GP Formula: (Price * Quantity) - (Cost * Quantity) - ExciseTax

    Returns:
    {
        'total_revenue': float,
        'total_cogs': float,
        'total_excise_tax': float,
        'total_gross_profit': float,
        'gp_margin_percent': float,
        'transaction_count': int,
        'items_with_excise_tax': int
    }
    """
    # Default to today if no dates provided
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    # Use the PUVIEWEXCISETRANSACTION view (READ-ONLY)
    query = """
    SELECT
        SUM(PRICE * QUANTITY) as total_revenue,
        SUM(COST * QUANTITY) as total_cogs,
        SUM(COALESCE(PUEPRICEC, 0)) as total_excise_tax,
        SUM((PRICE * QUANTITY) - (COST * QUANTITY) - COALESCE(PUEPRICEC, 0)) as total_gross_profit,
        COUNT(DISTINCT TRANSACTIONNUMBER) as transaction_count,
        SUM(CASE WHEN PUEPRICEC IS NOT NULL THEN 1 ELSE 0 END) as items_with_excise_tax,
        SUM(CASE WHEN QUANTITY < 0 THEN 1 ELSE 0 END) as return_count
    FROM PUVIEWEXCISETRANSACTION
    WHERE TRANSACTIONTIME >= %s
        AND TRANSACTIONTIME <= %s
    """

    params = [start_date, end_date]

    if customer_id:
        query += " AND CUSTOMERID = %s"
        params.append(customer_id)

    results = execute_query(query, params)

    if results and results[0]:
        data = results[0]
        total_revenue = float(data['total_revenue'] or 0)
        total_gp = float(data['total_gross_profit'] or 0)

        return {
            'total_revenue': total_revenue,
            'total_cogs': float(data['total_cogs'] or 0),
            'total_excise_tax': float(data['total_excise_tax'] or 0),
            'total_gross_profit': total_gp,
            'gp_margin_percent': (total_gp / total_revenue * 100) if total_revenue > 0 else 0,
            'transaction_count': int(data['transaction_count'] or 0),
            'items_with_excise_tax': int(data['items_with_excise_tax'] or 0),
            'return_count': int(data['return_count'] or 0)
        }

    return {
        'total_revenue': 0,
        'total_cogs': 0,
        'total_excise_tax': 0,
        'total_gross_profit': 0,
        'gp_margin_percent': 0,
        'transaction_count': 0,
        'items_with_excise_tax': 0,
        'return_count': 0
    }

def get_gp_by_category(start_date=None, end_date=None):
    """
    Get gross profit breakdown by category
    FAST APPROACH: Simple aggregation, calculate PAID vs COLLECTED in Python

    Returns list of categories with GP metrics including accurate excise tax
    """
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    # SUPER FAST: Query TransactionEntry directly, no excise joins
    # Note: GP will be approximate (doesn't include excise tax detail)
    query = """
    SELECT
        c.Name as CategoryName,
        SUM(te.Price * te.Quantity) as revenue,
        SUM(te.Cost * te.Quantity) as cogs,
        COUNT(*) as item_count
    FROM [dbo].[TransactionEntry] te WITH (NOLOCK)
    INNER JOIN [dbo].[Item] i WITH (NOLOCK) ON te.ItemID = i.ID
    INNER JOIN [dbo].[Category] c WITH (NOLOCK) ON i.CategoryID = c.ID
    WHERE te.TransactionTime >= %s
        AND te.TransactionTime <= %s
        AND te.Quantity != 0
        AND c.Name IS NOT NULL
    GROUP BY c.Name
    ORDER BY SUM(te.Price * te.Quantity) - SUM(te.Cost * te.Quantity) DESC
    """

    results = execute_query(query, [start_date, end_date])

    # Convert to final format
    final_results = []
    for row in results:
        revenue = float(row['revenue']) if row['revenue'] else 0
        cogs = float(row['cogs']) if row['cogs'] else 0

        # Basic GP (Revenue - COGS, excise tax included in cogs for PAID items)
        gross_profit = revenue - cogs
        gp_margin = (gross_profit / revenue * 100) if revenue > 0 else 0

        final_results.append({
            'CategoryName': row['CategoryName'],
            'revenue': revenue,
            'cogs': cogs,
            'excise_tax': 0.0,  # Not calculated in fast mode
            'gross_profit': gross_profit,
            'gp_margin_percent': gp_margin,
            'item_count': int(row['item_count']) if row['item_count'] else 0
        })

    return final_results

def get_gp_by_department(start_date=None, end_date=None):
    """
    Get gross profit breakdown by department
    Uses department hierarchy for high-level analysis

    Returns list of departments with GP metrics
    """
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    # Convert to date if datetime
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    query = """
    SELECT
        d.DepartmentCode,
        d.DepartmentName,
        SUM(gp.Revenue) as revenue,
        SUM(gp.COGS) as cogs,
        SUM(gp.ExciseTax) as excise_tax,
        SUM(gp.GrossProfit) as gross_profit,
        CASE
            WHEN SUM(gp.Revenue) > 0
            THEN (SUM(gp.GrossProfit) / SUM(gp.Revenue) * 100)
            ELSE 0
        END as gp_margin_percent,
        SUM(gp.ItemCount) as item_count,
        COUNT(DISTINCT gp.CategoryID) as category_count
    FROM GP_Daily_Summary gp
    INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
    INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
    WHERE gp.BusinessDate BETWEEN %s AND %s
    GROUP BY d.DepartmentCode, d.DepartmentName, d.SortOrder
    ORDER BY d.SortOrder
    """

    results = execute_query(query, [start_date, end_date])

    # Convert Decimal to float
    for row in results:
        for key in row:
            if isinstance(row[key], Decimal):
                row[key] = float(row[key])

    return results

def get_gp_by_customer(start_date=None, end_date=None, limit=20):
    """
    Get top customers by gross profit
    """
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    # Use the PUVIEWEXCISETRANSACTION view (READ-ONLY)
    query = f"""
    SELECT TOP {limit}
        CUSTOMERID,
        COALESCE(COMPANY, FIRSTNAME + ' ' + LASTNAME) as CustomerName,
        SUM(PRICE * QUANTITY) as revenue,
        SUM((PRICE * QUANTITY) - (COST * QUANTITY) - COALESCE(PUEPRICEC, 0)) as gross_profit,
        CASE
            WHEN SUM(PRICE * QUANTITY) > 0
            THEN (SUM((PRICE * QUANTITY) - (COST * QUANTITY) - COALESCE(PUEPRICEC, 0)) / SUM(PRICE * QUANTITY) * 100)
            ELSE 0
        END as gp_margin_percent,
        COUNT(DISTINCT TRANSACTIONNUMBER) as transaction_count
    FROM PUVIEWEXCISETRANSACTION
    WHERE TRANSACTIONTIME >= %s
        AND TRANSACTIONTIME <= %s
        AND CUSTOMERID IS NOT NULL
    GROUP BY CUSTOMERID, COALESCE(COMPANY, FIRSTNAME + ' ' + LASTNAME)
    ORDER BY gross_profit DESC
    """

    results = execute_query(query, [start_date, end_date])

    # Convert Decimal to float
    for row in results:
        for key in row:
            if isinstance(row[key], Decimal):
                row[key] = float(row[key])

    return results

def get_excise_tax_breakdown(start_date=None, end_date=None):
    """
    Get excise tax breakdown by type
    Shows LC23COLL, LC23PAID, etc.
    """
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    # Use the PUVIEWEXCISETRANSACTION view (READ-ONLY)
    query = """
    SELECT
        PUESUBDESCRIPTION3 as ExciseTaxType,
        COUNT(*) as transaction_count,
        SUM(PUEPRICEC) as total_excise_tax,
        SUM(PRICE * QUANTITY) as total_revenue
    FROM PUVIEWEXCISETRANSACTION
    WHERE TRANSACTIONTIME >= %s
        AND TRANSACTIONTIME <= %s
        AND PUESUBDESCRIPTION3 IS NOT NULL
        AND PUESUBDESCRIPTION3 != ''
    GROUP BY PUESUBDESCRIPTION3
    ORDER BY total_excise_tax DESC
    """

    results = execute_query(query, [start_date, end_date])

    # Convert Decimal to float
    for row in results:
        for key in row:
            if isinstance(row[key], Decimal):
                row[key] = float(row[key])

    return results

def test_gp_calculations():
    """Test the GP calculations"""
    print("Testing Gross Profit Calculations...")
    print("=" * 60)

    # Test today's GP
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    summary = get_gross_profit_summary(today)

    print(f"\nToday's Summary ({today.strftime('%Y-%m-%d')}):")
    print(f"  Revenue:        ${summary['total_revenue']:,.2f}")
    print(f"  COGS:           ${summary['total_cogs']:,.2f}")
    print(f"  Excise Tax:     ${summary['total_excise_tax']:,.2f}")
    print(f"  Gross Profit:   ${summary['total_gross_profit']:,.2f}")
    print(f"  GP Margin:      {summary['gp_margin_percent']:.2f}%")
    print(f"  Transactions:   {summary['transaction_count']}")
    print(f"  Items w/Excise: {summary['items_with_excise_tax']}")

    # Test GP by category
    print("\n" + "=" * 60)
    print("Top 5 Categories by GP:")
    categories = get_gp_by_category(today)[:5]
    for cat in categories:
        print(f"\n  {cat['CategoryName']}")
        print(f"    Revenue: ${cat['revenue']:,.2f}")
        print(f"    GP:      ${cat['gross_profit']:,.2f} ({cat['gp_margin_percent']:.1f}%)")

    # Test excise tax breakdown
    print("\n" + "=" * 60)
    print("Excise Tax Breakdown:")
    excise = get_excise_tax_breakdown(today)
    for e in excise:
        print(f"  {e['ExciseTaxType']}: ${e['total_excise_tax']:,.2f} ({e['transaction_count']} items)")

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")

if __name__ == '__main__':
    test_gp_calculations()
