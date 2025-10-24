"""
Extract cigarette sales data for the last 30 days
Outputs: Product name, cost, units sold, selling price, total revenue
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta

def get_cigarette_sales():
    """Get cigarette sales data for last 30 days"""

    db = SQLServerConnection()

    query = """
    WITH CigaretteSales AS (
        SELECT
            i.Description as ProductName,
            i.ItemLookupCode as SKU,
            i.Cost as UnitCost,
            i.SalePrice as ListPrice,
            COUNT(DISTINCT te.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            AVG(te.Price) as AvgSellingPrice,
            MIN(te.Price) as MinSellingPrice,
            MAX(te.Price) as MaxSellingPrice,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM dbo.Item i
        JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
            AND (
                UPPER(i.Description) LIKE '%CIGARETTE%'
                OR UPPER(i.Description) LIKE '%MARLBORO%'
                OR UPPER(i.Description) LIKE '%NEWPORT%'
                OR UPPER(i.Description) LIKE '%CAMEL%'
                OR UPPER(i.Description) LIKE '%AMERICAN SPIRIT%'
                OR UPPER(i.Description) LIKE '%WINSTON%'
                OR UPPER(i.Description) LIKE '%PALL MALL%'
                OR UPPER(i.Description) LIKE '%VIRGINIA SLIM%'
                OR UPPER(i.Description) LIKE '%KOOL%'
                OR UPPER(i.Description) LIKE '%SALEM%'
                OR UPPER(i.Description) LIKE '%PARLIAMENT%'
                OR UPPER(i.Description) LIKE '%LUCKY STRIKE%'
                OR UPPER(i.Description) LIKE '%MAVERICK%'
                OR UPPER(i.Description) LIKE '%EAGLE%'
                OR UPPER(i.Description) LIKE '%PYRAMID%'
                OR UPPER(i.Description) LIKE '%SENECA%'
                OR UPPER(i.Description) LIKE '%DORAL%'
                OR UPPER(i.Description) LIKE '%MISTY%'
                OR UPPER(i.Description) LIKE '%MONTEGO%'
                OR UPPER(i.Description) LIKE '%305%'
                OR UPPER(i.Description) LIKE '%LIGGETT%'
                OR UPPER(c.Name) LIKE '%CIGARETTE%'
                OR UPPER(c.Name) LIKE '%TOBACCO%'
            )
        GROUP BY i.Description, i.ItemLookupCode, i.Cost, i.SalePrice
    )
    SELECT
        ProductName,
        SKU,
        UnitCost,
        ListPrice,
        UnitsSold,
        AvgSellingPrice,
        MinSellingPrice,
        MaxSellingPrice,
        Transactions,
        TotalRevenue,
        GrossProfit,
        CASE
            WHEN UnitsSold > 0 AND TotalRevenue > 0 THEN
                (GrossProfit / TotalRevenue) * 100
            ELSE 0
        END as GrossMarginPercent
    FROM CigaretteSales
    WHERE UnitsSold > 0
    ORDER BY UnitsSold DESC
    """

    print("Executing query for cigarette sales data...")
    result = db.execute_query(query)

    if result is not None and not result.empty:
        # Format the data for CSV - convert Decimal to float first
        output_df = pd.DataFrame({
            'Product Name': result['ProductName'],
            'SKU': result['SKU'],
            'Unit Cost': result['UnitCost'].astype(float).round(2),
            'List Price': result['ListPrice'].astype(float).round(2),
            'Units Sold (30 days)': result['UnitsSold'].astype(int),
            'Avg Selling Price': result['AvgSellingPrice'].astype(float).round(2),
            'Min Selling Price': result['MinSellingPrice'].astype(float).round(2),
            'Max Selling Price': result['MaxSellingPrice'].astype(float).round(2),
            'Total Transactions': result['Transactions'].astype(int),
            'Total Revenue': result['TotalRevenue'].astype(float).round(2),
            'Gross Profit': result['GrossProfit'].astype(float).round(2),
            'Gross Margin %': result['GrossMarginPercent'].astype(float).round(1)
        })

        # Save to CSV
        filename = f'cigarette_sales_30days_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        output_df.to_csv(filename, index=False)

        print(f"\n✅ Data exported to {filename}")
        print(f"Total products: {len(output_df)}")
        print(f"Total units sold: {output_df['Units Sold (30 days)'].sum():,}")
        print(f"Total revenue: ${output_df['Total Revenue'].sum():,.2f}")
        print(f"Total gross profit: ${output_df['Gross Profit'].sum():,.2f}")
        print(f"Average margin: {output_df['Gross Margin %'].mean():.1f}%")

        # Show top 10 products
        print("\nTop 10 Products by Units Sold:")
        print("="*80)
        for idx, row in output_df.head(10).iterrows():
            print(f"{row['Product Name'][:40]:40} | Units: {row['Units Sold (30 days)']:6,} | Revenue: ${row['Total Revenue']:10,.2f}")

        return filename
    else:
        print("No cigarette sales data found for the last 30 days")
        return None

if __name__ == "__main__":
    get_cigarette_sales()