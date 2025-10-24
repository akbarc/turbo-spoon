"""
Find all cigarette sales to Murad Ali and related customers in 2025
Uses fuzzy matching to identify all customer variations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('.')))
from database_pymssql import SQLServerConnection
from difflib import SequenceMatcher
import re
import pandas as pd
from datetime import datetime

def normalize_text(text):
    if not text:
        return ''
    text = str(text).upper().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def calculate_similarity(str1, str2):
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()

def find_murad_ali_customers():
    """Find all customer records that could be Murad Ali"""
    target_first = 'MURAD'
    target_last = 'ALI'

    with SQLServerConnection() as db:
        # Find all customers with similar names to Murad Ali
        query = """
        SELECT
            ID,
            Company,
            FirstName,
            LastName,
            PhoneNumber,
            Address,
            AccountBalance
        FROM dbo.Customer
        WHERE
            (FirstName LIKE '%MURAD%' OR FirstName LIKE '%MURAT%' OR FirstName LIKE '%MOURAD%')
            OR (LastName LIKE '%ALI%' OR LastName LIKE '%ALLY%')
            OR (Company LIKE '%MURAD%' AND Company LIKE '%ALI%')
            OR (FirstName = 'ALI' AND LastName LIKE '%MURAD%')  -- Check for swapped names
        ORDER BY FirstName, LastName
        """

        customers = db.execute_query(query)

        matched_ids = []

        if not customers.empty:
            print("Found potential Murad Ali customer records:")
            print("=" * 100)

            for idx, row in customers.iterrows():
                # Calculate match score
                first_norm = normalize_text(row['FirstName'] or '')
                last_norm = normalize_text(row['LastName'] or '')
                company_norm = normalize_text(row['Company'] or '')

                # Check various matching patterns
                first_match = calculate_similarity(first_norm, target_first)
                last_match = calculate_similarity(last_norm, target_last)

                # Check for swapped names
                swap_first = calculate_similarity(first_norm, target_last)
                swap_last = calculate_similarity(last_norm, target_first)

                # Check company field
                company_has_murad = 'MURAD' in company_norm
                company_has_ali = 'ALI' in company_norm

                # Determine if this is a match
                is_match = False
                match_reason = ''

                if first_match >= 0.8 and last_match >= 0.8:
                    is_match = True
                    match_reason = f'Name match (First:{first_match:.0%}, Last:{last_match:.0%})'
                elif swap_first >= 0.8 and swap_last >= 0.8:
                    is_match = True
                    match_reason = f'Swapped name match'
                elif company_has_murad and company_has_ali:
                    is_match = True
                    match_reason = 'Company name match'
                elif (first_norm == 'MURAD' or last_norm == 'ALI') and (first_norm or last_norm):
                    is_match = True
                    match_reason = 'Partial name match'

                if is_match:
                    matched_ids.append(row['ID'])
                    balance = float(row['AccountBalance']) if row['AccountBalance'] else 0
                    print(f"ID: {row['ID']:6} | {(row['FirstName'] or ''):15} {(row['LastName'] or ''):15} | "
                          f"Company: {(row['Company'] or 'N/A'):30} | AR: ${balance:,.2f}")
                    print(f"           Match reason: {match_reason}")
                    print("-" * 100)

        return matched_ids

def get_cigarette_sales_2025(customer_ids):
    """Get cigarette sales for given customer IDs in 2025"""

    if not customer_ids:
        print("No customer IDs provided")
        return None

    with SQLServerConnection() as db:
        # Build customer ID list for SQL
        id_list = ','.join(str(id) for id in customer_ids)

        # Query for cigarette sales in 2025
        query = f"""
        WITH CigaretteSales AS (
            SELECT
                t.CustomerID,
                c.FirstName,
                c.LastName,
                c.Company,
                YEAR(t.Time) as SaleYear,
                MONTH(t.Time) as SaleMonth,
                DATENAME(MONTH, t.Time) as MonthName,
                td.ItemName,
                td.SellQty as Quantity,
                td.SellPrice as UnitPrice,
                (td.SellQty * td.SellPrice) as TotalAmount,
                t.Time as SaleDate
            FROM [Transaction] t
            INNER JOIN TransactionDetail td ON t.ID = td.TransactionID
            INNER JOIN Customer c ON t.CustomerID = c.ID
            INNER JOIN Items i ON td.ItemID = i.ID
            WHERE t.CustomerID IN ({id_list})
                AND YEAR(t.Time) = 2025
                AND (i.SubDepartmentID = 25 OR i.CategoryID = 5)  -- Cigarettes
                AND td.TransactionType = 0  -- Sales only
        )
        SELECT
            SaleMonth,
            MonthName,
            COUNT(DISTINCT ItemName) as UniqueProducts,
            SUM(Quantity) as TotalUnits,
            SUM(TotalAmount) as TotalDollars,
            COUNT(*) as TransactionCount
        FROM CigaretteSales
        GROUP BY SaleMonth, MonthName
        ORDER BY SaleMonth
        """

        monthly_summary = db.execute_query(query)

        # Get detailed product breakdown
        detail_query = f"""
        SELECT
            MONTH(t.Time) as SaleMonth,
            DATENAME(MONTH, t.Time) as MonthName,
            td.ItemName,
            SUM(td.SellQty) as TotalQuantity,
            AVG(td.SellPrice) as AvgPrice,
            SUM(td.SellQty * td.SellPrice) as TotalSales
        FROM [Transaction] t
        INNER JOIN TransactionDetail td ON t.ID = td.TransactionID
        INNER JOIN Items i ON td.ItemID = i.ID
        WHERE t.CustomerID IN ({id_list})
            AND YEAR(t.Time) = 2025
            AND (i.SubDepartmentID = 25 OR i.CategoryID = 5)  -- Cigarettes
            AND td.TransactionType = 0  -- Sales only
        GROUP BY MONTH(t.Time), DATENAME(MONTH, t.Time), td.ItemName
        ORDER BY SaleMonth, TotalSales DESC
        """

        product_details = db.execute_query(detail_query)

        return monthly_summary, product_details

def main():
    print("="*100)
    print("CIGARETTE SALES ANALYSIS - MURAD ALI - 2025")
    print("="*100)
    print()

    # Step 1: Find all Murad Ali customer IDs
    print("Step 1: Finding all Murad Ali customer records using fuzzy matching...")
    print("-"*100)
    customer_ids = find_murad_ali_customers()

    if not customer_ids:
        print("No Murad Ali customers found in the database")
        return

    print(f"\nFound {len(customer_ids)} related customer ID(s): {customer_ids}")
    print()

    # Step 2: Get cigarette sales for 2025
    print("Step 2: Retrieving cigarette sales for 2025...")
    print("-"*100)

    monthly_summary, product_details = get_cigarette_sales_2025(customer_ids)

    if monthly_summary is None or monthly_summary.empty:
        print("No cigarette sales found for Murad Ali in 2025")
        return

    # Display monthly summary
    print("\nMONTHLY CIGARETTE SALES SUMMARY - 2025")
    print("="*100)
    print(f"{'Month':<15} {'Units Sold':>12} {'Total Sales $':>15} {'Unique Products':>15} {'Transactions':>12}")
    print("-"*100)

    total_units = 0
    total_dollars = 0

    for _, row in monthly_summary.iterrows():
        units = int(row['TotalUnits'])
        dollars = float(row['TotalDollars'])
        total_units += units
        total_dollars += dollars

        print(f"{row['MonthName']:<15} {units:>12,} ${dollars:>14,.2f} {int(row['UniqueProducts']):>15} {int(row['TransactionCount']):>12}")

    print("-"*100)
    print(f"{'TOTAL':<15} {total_units:>12,} ${total_dollars:>14,.2f}")
    print()

    # Display top products by month
    if not product_details.empty:
        print("\nTOP CIGARETTE PRODUCTS BY MONTH")
        print("="*100)

        for month in product_details['SaleMonth'].unique():
            month_data = product_details[product_details['SaleMonth'] == month]
            month_name = month_data.iloc[0]['MonthName']

            print(f"\n{month_name} 2025:")
            print("-"*80)
            print(f"{'Product':<40} {'Quantity':>10} {'Avg Price':>12} {'Total Sales':>15}")
            print("-"*80)

            # Show top 5 products for the month
            for _, product in month_data.head(5).iterrows():
                qty = int(product['TotalQuantity'])
                avg_price = float(product['AvgPrice'])
                total = float(product['TotalSales'])
                print(f"{product['ItemName'][:40]:<40} {qty:>10,} ${avg_price:>11,.2f} ${total:>14,.2f}")

    print("\n" + "="*100)
    print("Analysis complete")

if __name__ == "__main__":
    main()