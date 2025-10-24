"""
SQL Server 2008 R2 Compatibility Fixes
This script will fix all SQL compatibility issues in the dashboard APIs
"""

import os

def fix_string_agg():
    """Replace STRING_AGG with compatible alternative for SQL Server 2008 R2"""

    # Fix in sales_api.py
    sales_api_path = '/Users/akbarchranya/georgiadashboard/sales_dashboard_v2/backend/sales_api.py'

    with open(sales_api_path, 'r') as f:
        content = f.read()

    # Replace STRING_AGG with XML PATH method for SQL Server 2008 R2
    old_string_agg = "STRING_AGG(i.Description, ', ') as Items"
    new_xml_method = """STUFF((
                SELECT ', ' + i2.Description
                FROM dbo.TransactionEntry te2
                JOIN dbo.Item i2 ON te2.ItemID = i2.ID
                WHERE te2.TransactionNumber = t.TransactionNumber
                FOR XML PATH('')
            ), 1, 2, '') as Items"""

    content = content.replace(old_string_agg, new_xml_method)

    with open(sales_api_path, 'w') as f:
        f.write(content)

    print("✅ Fixed STRING_AGG in sales_api.py")

def fix_window_functions():
    """Fix ROWS BETWEEN syntax for SQL Server 2008 R2"""

    analytics_path = '/Users/akbarchranya/georgiadashboard/sales_dashboard_v2/backend/advanced_analytics.py'

    with open(analytics_path, 'r') as f:
        content = f.read()

    # SQL Server 2008 R2 doesn't support ROWS BETWEEN in window functions
    # Use a subquery approach instead
    old_window = "AVG(DailySales) OVER (ORDER BY Date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) as AvgPrevWeek"
    new_subquery = """(SELECT AVG(d2.DailySales)
            FROM DailyDemand d2
            WHERE d2.Date BETWEEN DATEADD(DAY, -7, d.Date) AND DATEADD(DAY, -1, d.Date)) as AvgPrevWeek"""

    content = content.replace(old_window, new_subquery)

    # Also need to add alias to the main query
    content = content.replace("FROM DailyDemand", "FROM DailyDemand d")

    with open(analytics_path, 'w') as f:
        f.write(content)

    print("✅ Fixed window functions in advanced_analytics.py")

def fix_decimal_multiplication():
    """Fix Decimal multiplication with float"""

    analytics_path = '/Users/akbarchranya/georgiadashboard/sales_dashboard_v2/backend/advanced_analytics.py'

    with open(analytics_path, 'r') as f:
        content = f.read()

    # Fix line 284: item['SalePrice'] * 1.1
    content = content.replace(
        "recommendation['suggested_price'] = float(item['SalePrice'] * 1.1)",
        "recommendation['suggested_price'] = float(item['SalePrice']) * 1.1"
    )

    # Fix line 287: item['SalePrice'] * 0.95
    content = content.replace(
        "recommendation['suggested_price'] = float(item['SalePrice'] * 0.95)",
        "recommendation['suggested_price'] = float(item['SalePrice']) * 0.95"
    )

    with open(analytics_path, 'w') as f:
        f.write(content)

    print("✅ Fixed Decimal multiplication in advanced_analytics.py")

def fix_cashier_references():
    """Fix Cashier table column references"""

    analytics_path = '/Users/akbarchranya/georgiadashboard/sales_dashboard_v2/backend/advanced_analytics.py'

    with open(analytics_path, 'r') as f:
        content = f.read()

    # The FirstName and LastName columns are in Customer table, not Cashier
    # For Cashier, we should use c.Name
    content = content.replace(
        "COALESCE(c.FirstName + ' ' + c.LastName, 'Cashier ' + CAST(t.CashierID as VARCHAR)) as CashierName,",
        "COALESCE(c.Name, 'Cashier ' + CAST(t.CashierID as VARCHAR)) as CashierName,"
    )

    content = content.replace(
        "GROUP BY t.CashierID, c.FirstName, c.LastName",
        "GROUP BY t.CashierID, c.Name"
    )

    with open(analytics_path, 'w') as f:
        f.write(content)

    print("✅ Fixed Cashier table references in advanced_analytics.py")

def fix_date_formatting():
    """Fix date formatting issues"""

    sales_api_path = '/Users/akbarchranya/georgiadashboard/sales_dashboard_v2/backend/sales_api.py'

    with open(sales_api_path, 'r') as f:
        content = f.read()

    # Add import for datetime handling
    if "from datetime import datetime, timedelta" not in content:
        content = content.replace(
            "from flask import Blueprint, jsonify, request",
            "from flask import Blueprint, jsonify, request\nfrom datetime import datetime, timedelta"
        )

    with open(sales_api_path, 'w') as f:
        f.write(content)

    print("✅ Added datetime imports to sales_api.py")

if __name__ == "__main__":
    print("Starting SQL Server 2008 R2 compatibility fixes...")

    fix_string_agg()
    fix_window_functions()
    fix_decimal_multiplication()
    fix_cashier_references()
    fix_date_formatting()

    print("\n✅ All SQL compatibility fixes applied!")
    print("Please restart the Flask application to see the changes.")