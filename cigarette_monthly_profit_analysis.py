#!/usr/bin/env python3
"""
Cigarette Sales by Month with Gross Profit
Including Petrey Purchase Analysis with $0.25 discount
2024-2025 Period
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime
import calendar

def get_monthly_cigarette_sales_with_profit():
    """Get cigarette sales by month with gross profit calculations"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Query for monthly cigarette sales with cost data
        query = """
        SELECT
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            DATENAME(MONTH, t.Time) as MonthName,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            COUNT(DISTINCT te.ItemID) as UniqueProducts,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            AVG(te.Price) as AvgSellingPrice,
            AVG(i.Cost) as AvgCost,
            SUM((te.Price - i.Cost) * te.Quantity) as GrossProfit
        FROM TransactionEntry te
        INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.Time >= '2024-01-01'
            AND t.Time < '2026-01-01'
            AND c.Name LIKE '%CIGARETTE%'
            AND i.Description NOT LIKE '%LIGHTER%'
            AND i.Description NOT LIKE '%TORCH%'
            AND i.Description NOT LIKE '%PAPER%'
            AND i.Description NOT LIKE '%TUBE%'
            AND i.Description NOT LIKE '%MACHINE%'
            AND i.Description NOT LIKE '%CASE%'
        GROUP BY
            YEAR(t.Time),
            MONTH(t.Time),
            DATENAME(MONTH, t.Time)
        ORDER BY
            YEAR(t.Time),
            MONTH(t.Time)
        """

        sales_df = conn.execute_query(query, description="Get monthly cigarette sales with profit")

        # Query for Petrey purchases by month
        petrey_query = """
        SELECT
            YEAR(po.DateCreated) as Year,
            MONTH(po.DateCreated) as Month,
            DATENAME(MONTH, po.DateCreated) as MonthName,
            COUNT(DISTINCT po.ID) as PurchaseOrders,
            SUM(poe.QuantityOrdered) as UnitsOrdered,
            SUM(poe.Price * poe.QuantityOrdered) as TotalCost,
            AVG(poe.Price) as AvgUnitCost
        FROM PurchaseOrderEntry poe
        INNER JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
        INNER JOIN Item i ON poe.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE po.SupplierID = 1330  -- Petrey
            AND po.DateCreated >= '2024-01-01'
            AND po.DateCreated < '2026-01-01'
            AND c.Name LIKE '%CIGARETTE%'
        GROUP BY
            YEAR(po.DateCreated),
            MONTH(po.DateCreated),
            DATENAME(MONTH, po.DateCreated)
        ORDER BY
            YEAR(po.DateCreated),
            MONTH(po.DateCreated)
        """

        petrey_df = conn.execute_query(petrey_query, description="Get Petrey purchases by month")

        return sales_df, petrey_df

    finally:
        conn.close()

def main():
    print("="*120)
    print("CIGARETTE SALES BY MONTH WITH GROSS PROFIT & PETREY PURCHASES")
    print("2024-2025 PERIOD")
    print("="*120)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get data
    sales_df, petrey_df = get_monthly_cigarette_sales_with_profit()

    if sales_df is None or len(sales_df) == 0:
        print("No sales data found for 2024-2025")
        return

    # Convert numeric columns
    numeric_cols_sales = ['UnitsSold', 'TotalRevenue', 'AvgSellingPrice', 'AvgCost', 'GrossProfit', 'Transactions']
    for col in numeric_cols_sales:
        if col in sales_df.columns:
            sales_df[col] = pd.to_numeric(sales_df[col], errors='coerce')

    if petrey_df is not None:
        numeric_cols_petrey = ['UnitsOrdered', 'TotalCost', 'AvgUnitCost']
        for col in numeric_cols_petrey:
            if col in petrey_df.columns:
                petrey_df[col] = pd.to_numeric(petrey_df[col], errors='coerce')

        # Apply $0.25 discount per unit to Petrey purchases
        petrey_df['Discount_Amount'] = petrey_df['UnitsOrdered'] * 0.25
        petrey_df['Adjusted_TotalCost'] = petrey_df['TotalCost'] - petrey_df['Discount_Amount']
        petrey_df['Adjusted_AvgCost'] = petrey_df['Adjusted_TotalCost'] / petrey_df['UnitsOrdered']

    # Calculate profit margins
    sales_df['ProfitMargin%'] = (sales_df['GrossProfit'] / sales_df['TotalRevenue'] * 100).round(2)

    # Separate 2024 and 2025 data
    df_2024 = sales_df[sales_df['Year'] == 2024].copy()
    df_2025 = sales_df[sales_df['Year'] == 2025].copy()

    if petrey_df is not None:
        petrey_2024 = petrey_df[petrey_df['Year'] == 2024].copy()
        petrey_2025 = petrey_df[petrey_df['Year'] == 2025].copy()

    # Print 2024 Summary with Profit
    print("2024 MONTHLY SALES & PROFIT")
    print("-"*120)

    if len(df_2024) > 0:
        print(f"{'Month':<12} {'Units Sold':>11} {'Revenue':>13} {'Gross Profit':>13} {'Margin%':>8} {'Avg Cost':>9} {'Avg Price':>10}")
        print("-"*120)

        total_2024_units = 0
        total_2024_revenue = 0
        total_2024_profit = 0

        for _, row in df_2024.iterrows():
            print(f"{row['MonthName']:<12} {row['UnitsSold']:11,.0f} ${row['TotalRevenue']:12,.2f} ${row['GrossProfit']:12,.2f} {row['ProfitMargin%']:7.1f}% ${row['AvgCost']:8.2f} ${row['AvgSellingPrice']:9.2f}")
            total_2024_units += row['UnitsSold']
            total_2024_revenue += row['TotalRevenue']
            total_2024_profit += row['GrossProfit']

        print("-"*120)
        overall_margin_2024 = (total_2024_profit / total_2024_revenue * 100) if total_2024_revenue > 0 else 0
        print(f"{'2024 TOTAL':<12} {total_2024_units:11,.0f} ${total_2024_revenue:12,.2f} ${total_2024_profit:12,.2f} {overall_margin_2024:7.1f}%")

    # Print 2025 Summary with Profit
    print("\n" + "="*120)
    print("2025 MONTHLY SALES & PROFIT (Year to Date)")
    print("-"*120)

    if len(df_2025) > 0:
        print(f"{'Month':<12} {'Units Sold':>11} {'Revenue':>13} {'Gross Profit':>13} {'Margin%':>8} {'Avg Cost':>9} {'Avg Price':>10}")
        print("-"*120)

        total_2025_units = 0
        total_2025_revenue = 0
        total_2025_profit = 0

        for _, row in df_2025.iterrows():
            print(f"{row['MonthName']:<12} {row['UnitsSold']:11,.0f} ${row['TotalRevenue']:12,.2f} ${row['GrossProfit']:12,.2f} {row['ProfitMargin%']:7.1f}% ${row['AvgCost']:8.2f} ${row['AvgSellingPrice']:9.2f}")
            total_2025_units += row['UnitsSold']
            total_2025_revenue += row['TotalRevenue']
            total_2025_profit += row['GrossProfit']

        print("-"*120)
        overall_margin_2025 = (total_2025_profit / total_2025_revenue * 100) if total_2025_revenue > 0 else 0
        print(f"{'2025 YTD':<12} {total_2025_units:11,.0f} ${total_2025_revenue:12,.2f} ${total_2025_profit:12,.2f} {overall_margin_2025:7.1f}%")

    # Print Petrey Purchase Summary
    if petrey_df is not None and len(petrey_df) > 0:
        print("\n" + "="*120)
        print("PETREY WHOLESALE PURCHASES BY MONTH (with $0.25/unit discount)")
        print("-"*120)

        # 2024 Petrey Purchases
        if len(petrey_2024) > 0:
            print("\n2024 PETREY PURCHASES")
            print(f"{'Month':<12} {'Units Bought':>12} {'Invoice Cost':>13} {'Discount':>10} {'Net Cost':>13} {'Avg/Unit':>9}")
            print("-"*110)

            total_petrey_2024_units = 0
            total_petrey_2024_cost = 0
            total_petrey_2024_discount = 0

            for _, row in petrey_2024.iterrows():
                print(f"{row['MonthName']:<12} {row['UnitsOrdered']:12,.0f} ${row['TotalCost']:12,.2f} ${row['Discount_Amount']:9,.2f} ${row['Adjusted_TotalCost']:12,.2f} ${row['Adjusted_AvgCost']:8.2f}")
                total_petrey_2024_units += row['UnitsOrdered']
                total_petrey_2024_cost += row['TotalCost']
                total_petrey_2024_discount += row['Discount_Amount']

            print("-"*110)
            net_total_2024 = total_petrey_2024_cost - total_petrey_2024_discount
            print(f"{'2024 TOTAL':<12} {total_petrey_2024_units:12,.0f} ${total_petrey_2024_cost:12,.2f} ${total_petrey_2024_discount:9,.2f} ${net_total_2024:12,.2f}")

        # 2025 Petrey Purchases
        if len(petrey_2025) > 0:
            print("\n2025 PETREY PURCHASES (YTD)")
            print(f"{'Month':<12} {'Units Bought':>12} {'Invoice Cost':>13} {'Discount':>10} {'Net Cost':>13} {'Avg/Unit':>9}")
            print("-"*110)

            total_petrey_2025_units = 0
            total_petrey_2025_cost = 0
            total_petrey_2025_discount = 0

            for _, row in petrey_2025.iterrows():
                print(f"{row['MonthName']:<12} {row['UnitsOrdered']:12,.0f} ${row['TotalCost']:12,.2f} ${row['Discount_Amount']:9,.2f} ${row['Adjusted_TotalCost']:12,.2f} ${row['Adjusted_AvgCost']:8.2f}")
                total_petrey_2025_units += row['UnitsOrdered']
                total_petrey_2025_cost += row['TotalCost']
                total_petrey_2025_discount += row['Discount_Amount']

            print("-"*110)
            net_total_2025 = total_petrey_2025_cost - total_petrey_2025_discount
            print(f"{'2025 YTD':<12} {total_petrey_2025_units:12,.0f} ${total_petrey_2025_cost:12,.2f} ${total_petrey_2025_discount:9,.2f} ${net_total_2025:12,.2f}")

    # Year-over-Year Comparison with Profit
    if len(df_2024) > 0 and len(df_2025) > 0:
        print("\n" + "="*120)
        print("YEAR-OVER-YEAR PROFIT COMPARISON")
        print("-"*120)

        months_2024_set = set(df_2024['Month'].values)
        months_2025_set = set(df_2025['Month'].values)
        common_months = months_2024_set.intersection(months_2025_set)

        if common_months:
            print(f"{'Month':<12} {'2024 Profit':>13} {'2025 Profit':>13} {'Change':>13} {'% Change':>10}")
            print("-"*120)

            for month in sorted(common_months):
                profit_2024 = df_2024[df_2024['Month'] == month]['GrossProfit'].values[0]
                profit_2025 = df_2025[df_2025['Month'] == month]['GrossProfit'].values[0]
                change = profit_2025 - profit_2024
                pct_change = (change / profit_2024 * 100) if profit_2024 > 0 else 0

                month_name = calendar.month_name[int(month)]
                print(f"{month_name:<12} ${profit_2024:12,.2f} ${profit_2025:12,.2f} ${change:+12,.2f} {pct_change:+9.1f}%")

    # Save to Excel
    with pd.ExcelWriter('cigarette_monthly_profit_analysis.xlsx', engine='openpyxl') as writer:
        # Sales data with profit
        sales_df.to_excel(writer, sheet_name='Monthly_Sales_Profit', index=False)

        # Petrey purchases
        if petrey_df is not None and len(petrey_df) > 0:
            petrey_df.to_excel(writer, sheet_name='Petrey_Purchases', index=False)

        # Combined summary
        summary_data = []

        for year in [2024, 2025]:
            year_sales = sales_df[sales_df['Year'] == year]
            if len(year_sales) > 0:
                row_data = {
                    'Year': year,
                    'Total_Units_Sold': year_sales['UnitsSold'].sum(),
                    'Total_Revenue': year_sales['TotalRevenue'].sum(),
                    'Total_Gross_Profit': year_sales['GrossProfit'].sum(),
                    'Avg_Profit_Margin%': (year_sales['GrossProfit'].sum() / year_sales['TotalRevenue'].sum() * 100) if year_sales['TotalRevenue'].sum() > 0 else 0
                }

                if petrey_df is not None:
                    year_petrey = petrey_df[petrey_df['Year'] == year]
                    if len(year_petrey) > 0:
                        row_data['Petrey_Units_Bought'] = year_petrey['UnitsOrdered'].sum()
                        row_data['Petrey_Invoice_Cost'] = year_petrey['TotalCost'].sum()
                        row_data['Petrey_Discount'] = year_petrey['Discount_Amount'].sum()
                        row_data['Petrey_Net_Cost'] = year_petrey['Adjusted_TotalCost'].sum()

                summary_data.append(row_data)

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Annual_Summary', index=False)

    print(f"\n✅ Detailed report saved to: cigarette_monthly_profit_analysis.xlsx")

    # Print grand totals
    print("\n" + "="*120)
    print("GRAND TOTALS (2024-2025)")
    print("="*120)

    total_units_all = sales_df['UnitsSold'].sum()
    total_revenue_all = sales_df['TotalRevenue'].sum()
    total_profit_all = sales_df['GrossProfit'].sum()
    overall_margin = (total_profit_all / total_revenue_all * 100) if total_revenue_all > 0 else 0

    print(f"Total Units Sold: {total_units_all:,.0f}")
    print(f"Total Revenue: ${total_revenue_all:,.2f}")
    print(f"Total Gross Profit: ${total_profit_all:,.2f}")
    print(f"Overall Profit Margin: {overall_margin:.1f}%")

    if petrey_df is not None and len(petrey_df) > 0:
        total_petrey_units = petrey_df['UnitsOrdered'].sum()
        total_petrey_invoice = petrey_df['TotalCost'].sum()
        total_petrey_discount = petrey_df['Discount_Amount'].sum()
        total_petrey_net = petrey_df['Adjusted_TotalCost'].sum()

        print(f"\nTotal Petrey Units Bought: {total_petrey_units:,.0f}")
        print(f"Total Petrey Invoice Cost: ${total_petrey_invoice:,.2f}")
        print(f"Total Petrey Discount ($0.25/unit): ${total_petrey_discount:,.2f}")
        print(f"Total Petrey Net Cost: ${total_petrey_net:,.2f}")

if __name__ == "__main__":
    main()