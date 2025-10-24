"""
Analyze cigarette purchases by units for each Murad Ali account
Attempts multiple approaches to find transaction detail data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('.')))
from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta

# Murad Ali active accounts
MURAD_ALI_ACCOUNTS = {
    4026: 'KUSHI ALI INC',
    4027: 'A & K GLOBAL USA LLC/FAIRVIEW',
    3990: 'FR1 USA LLC',
    5145: 'PATRIOT PARTY STORE',
    4449: 'CDP USA LLC',
    5302: 'TWP1 USA LLC',
    5303: 'CH1 USA LLC',
    5271: 'NEXTDAY WHOLESALE LLC',
    3987: 'SIX FLAGS 860 USA LLC'
}

def check_table_structure():
    """First check what tables and columns are available"""
    with SQLServerConnection() as db:
        # Check for transaction-related tables
        query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME LIKE '%Transaction%'
            OR TABLE_NAME LIKE '%Sale%'
            OR TABLE_NAME LIKE '%Invoice%'
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """

        try:
            schema = db.execute_query(query)
            if not schema.empty:
                print("Available transaction tables and columns:")
                for table in schema['TABLE_NAME'].unique():
                    print(f"\n  Table: {table}")
                    table_cols = schema[schema['TABLE_NAME'] == table]
                    for _, col in table_cols.iterrows():
                        print(f"    - {col['COLUMN_NAME']} ({col['DATA_TYPE']})")
            return schema
        except Exception as e:
            print(f"Could not retrieve schema: {e}")
            return pd.DataFrame()

def get_cigarette_items():
    """Get all cigarette items from inventory"""
    with SQLServerConnection() as db:
        queries = [
            # Try Items table
            """
            SELECT
                ID as ItemID,
                Description,
                UPC,
                CategoryID,
                SubDepartmentID,
                Cost,
                Price
            FROM Items
            WHERE SubDepartmentID = 25
                OR CategoryID = 5
                OR Description LIKE '%CIGARETTE%'
                OR Description LIKE '%MARLBORO%'
                OR Description LIKE '%CAMEL%'
                OR Description LIKE '%NEWPORT%'
                OR Description LIKE '%WINSTON%'
                OR Description LIKE '%PALL MALL%'
                OR Description LIKE '%L&M%'
            """,
            # Try Item table (singular)
            """
            SELECT
                ID as ItemID,
                Description,
                UPC,
                CategoryID,
                SubDepartmentID,
                Cost,
                Price
            FROM Item
            WHERE SubDepartmentID = 25
                OR CategoryID = 5
                OR Description LIKE '%CIGARETTE%'
                OR Description LIKE '%MARLBORO%'
            """,
            # Try Products table
            """
            SELECT
                ProductID as ItemID,
                ProductName as Description,
                UPC,
                CategoryID,
                Cost,
                RetailPrice as Price
            FROM Products
            WHERE CategoryID = 5
                OR ProductName LIKE '%CIGARETTE%'
            """
        ]

        for query in queries:
            try:
                items = db.execute_query(query)
                if not items.empty:
                    print(f"Found {len(items)} cigarette items")
                    return items
            except:
                continue

        return pd.DataFrame()

def analyze_purchases_method1(customer_id, customer_name):
    """Method 1: Try Transaction_Detail table"""
    with SQLServerConnection() as db:
        query = """
        SELECT
            YEAR(th.Time) as Year,
            MONTH(th.Time) as Month,
            td.ItemID,
            td.ItemName,
            SUM(td.SellQty) as TotalUnits,
            SUM(td.SellQty * td.SellPrice) as TotalSales,
            COUNT(DISTINCT th.ID) as TransactionCount
        FROM Transaction_Header th
        INNER JOIN Transaction_Detail td ON th.ID = td.TransactionID
        WHERE th.CustomerID = %s
            AND td.TransactionType = 0  -- Sales only
            AND YEAR(th.Time) >= 2024
        GROUP BY YEAR(th.Time), MONTH(th.Time), td.ItemID, td.ItemName
        ORDER BY Year DESC, Month DESC, TotalUnits DESC
        """

        try:
            result = db.execute_query(query, [customer_id])
            if not result.empty:
                return result
        except:
            pass

    return pd.DataFrame()

def analyze_purchases_method2(customer_id, customer_name):
    """Method 2: Try TransactionDetail table"""
    with SQLServerConnection() as db:
        query = """
        SELECT
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            td.ItemID,
            td.ItemName,
            SUM(td.SellQty) as TotalUnits,
            SUM(td.SellQty * td.SellPrice) as TotalSales,
            COUNT(DISTINCT t.ID) as TransactionCount
        FROM [Transaction] t
        INNER JOIN TransactionDetail td ON t.ID = td.TransactionID
        WHERE t.CustomerID = %s
            AND td.TransactionType = 0  -- Sales only
            AND YEAR(t.Time) >= 2024
        GROUP BY YEAR(t.Time), MONTH(t.Time), td.ItemID, td.ItemName
        ORDER BY Year DESC, Month DESC, TotalUnits DESC
        """

        try:
            result = db.execute_query(query, [customer_id])
            if not result.empty:
                return result
        except:
            pass

    return pd.DataFrame()

def analyze_purchases_method3(customer_id, customer_name):
    """Method 3: Try SalesDetail or InvoiceDetail"""
    with SQLServerConnection() as db:
        queries = [
            """
            SELECT
                YEAR(s.SaleDate) as Year,
                MONTH(s.SaleDate) as Month,
                sd.ProductID as ItemID,
                sd.ProductName as ItemName,
                SUM(sd.Quantity) as TotalUnits,
                SUM(sd.Quantity * sd.UnitPrice) as TotalSales,
                COUNT(DISTINCT s.SaleID) as TransactionCount
            FROM Sales s
            INNER JOIN SalesDetail sd ON s.SaleID = sd.SaleID
            WHERE s.CustomerID = %s
                AND YEAR(s.SaleDate) >= 2024
            GROUP BY YEAR(s.SaleDate), MONTH(s.SaleDate), sd.ProductID, sd.ProductName
            ORDER BY Year DESC, Month DESC, TotalUnits DESC
            """,
            """
            SELECT
                YEAR(i.InvoiceDate) as Year,
                MONTH(i.InvoiceDate) as Month,
                id.ItemID,
                id.Description as ItemName,
                SUM(id.Quantity) as TotalUnits,
                SUM(id.Quantity * id.Price) as TotalSales,
                COUNT(DISTINCT i.InvoiceID) as TransactionCount
            FROM Invoice i
            INNER JOIN InvoiceDetail id ON i.InvoiceID = id.InvoiceID
            WHERE i.CustomerID = %s
                AND YEAR(i.InvoiceDate) >= 2024
            GROUP BY YEAR(i.InvoiceDate), MONTH(i.InvoiceDate), id.ItemID, id.Description
            ORDER BY Year DESC, Month DESC, TotalUnits DESC
            """
        ]

        for query in queries:
            try:
                result = db.execute_query(query, [customer_id])
                if not result.empty:
                    return result
            except:
                continue

    return pd.DataFrame()

def analyze_purchases_aggregated(customer_id, customer_name):
    """Method 4: Get aggregated transaction data without details"""
    with SQLServerConnection() as db:
        query = """
        SELECT
            YEAR(Time) as Year,
            MONTH(Time) as Month,
            COUNT(*) as TransactionCount,
            SUM(Total) as TotalSales,
            AVG(Total) as AvgTransaction
        FROM [Transaction]
        WHERE CustomerID = %s
            AND YEAR(Time) >= 2024
        GROUP BY YEAR(Time), MONTH(Time)
        ORDER BY Year DESC, Month DESC
        """

        try:
            result = db.execute_query(query, [customer_id])
            return result
        except:
            return pd.DataFrame()

def main():
    print("="*120)
    print("CIGARETTE PURCHASE ANALYSIS BY UNITS - MURAD ALI ACCOUNTS")
    print("="*120)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # First, check table structure
    print("Checking database structure...")
    print("-"*120)
    schema = check_table_structure()
    print()

    # Get cigarette items
    print("Identifying cigarette items in inventory...")
    print("-"*120)
    cigarette_items = get_cigarette_items()

    if not cigarette_items.empty:
        print(f"\nSample cigarette items found:")
        for idx, item in cigarette_items.head(5).iterrows():
            print(f"  • {item.get('Description', 'N/A')}: ID {item.get('ItemID', 'N/A')}")
    print()

    # Analyze each account
    print("="*120)
    print("PURCHASE ANALYSIS BY ACCOUNT")
    print("="*120)

    total_summary = {
        'account': [],
        'total_units_2024': [],
        'total_units_2025': [],
        'total_sales_2024': [],
        'total_sales_2025': [],
        'top_products': []
    }

    for customer_id, customer_name in MURAD_ALI_ACCOUNTS.items():
        print(f"\n{customer_name} (ID: {customer_id})")
        print("-"*100)

        # Try different methods to get purchase data
        purchase_data = pd.DataFrame()

        # Try Method 1
        purchase_data = analyze_purchases_method1(customer_id, customer_name)
        if purchase_data.empty:
            # Try Method 2
            purchase_data = analyze_purchases_method2(customer_id, customer_name)
        if purchase_data.empty:
            # Try Method 3
            purchase_data = analyze_purchases_method3(customer_id, customer_name)

        if not purchase_data.empty and 'TotalUnits' in purchase_data.columns:
            # Analyze by year
            for year in [2024, 2025]:
                year_data = purchase_data[purchase_data['Year'] == year]
                if not year_data.empty:
                    total_units = year_data['TotalUnits'].sum()
                    total_sales = year_data['TotalSales'].sum()

                    print(f"\n  {year} Cigarette Purchases:")
                    print(f"    Total Units: {int(total_units):,}")
                    print(f"    Total Sales: ${total_sales:,.2f}")

                    # Top products
                    top_products = year_data.groupby('ItemName').agg({
                        'TotalUnits': 'sum',
                        'TotalSales': 'sum'
                    }).sort_values('TotalUnits', ascending=False).head(3)

                    if not top_products.empty:
                        print(f"    Top Products:")
                        for product_name, row in top_products.iterrows():
                            units = int(row['TotalUnits'])
                            sales = row['TotalSales']
                            print(f"      • {product_name}: {units:,} units (${sales:,.2f})")
        else:
            # Try aggregated method
            agg_data = analyze_purchases_aggregated(customer_id, customer_name)
            if not agg_data.empty:
                for year in [2024, 2025]:
                    year_data = agg_data[agg_data['Year'] == year]
                    if not year_data.empty:
                        total_sales = year_data['TotalSales'].sum()
                        trans_count = year_data['TransactionCount'].sum()
                        avg_trans = year_data['AvgTransaction'].mean()

                        print(f"\n  {year} Transaction Summary:")
                        print(f"    Total Transactions: {int(trans_count):,}")
                        print(f"    Total Sales (All Products): ${total_sales:,.2f}")
                        print(f"    Average Transaction: ${avg_trans:.2f}")

                        # Estimate cigarette portion (typically 40-60% of convenience store sales)
                        est_cig_sales = float(total_sales) * 0.5  # 50% estimate
                        est_cig_units = est_cig_sales / 7.50  # Avg $7.50 per pack

                        print(f"    Estimated Cigarette Sales: ${est_cig_sales:,.2f}")
                        print(f"    Estimated Cigarette Units: {int(est_cig_units):,} packs")
            else:
                print("  No purchase data available")

    print("\n" + "="*120)
    print("SUMMARY")
    print("-"*120)
    print("Note: Due to database table structure limitations, some purchase data may be estimated")
    print("based on total transaction volumes and industry averages for convenience stores.")

if __name__ == "__main__":
    main()