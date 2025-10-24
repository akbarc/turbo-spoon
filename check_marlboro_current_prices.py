"""
Check current POS prices and costs for specific Marlboro items
Gets the most recent price from the Item table
"""

from database_pymssql import SQLServerConnection
import pandas as pd

def check_marlboro_prices():
    """Get current prices and costs for specific Marlboro items"""

    db = SQLServerConnection()

    # List of specific items to check
    items_to_check = [
        'MARL BLACK GOLD 100 BOX',
        'MARL BLACK GOLD BOX 10CT',
        'MARL MENTHL SLATE 100 BOX 10CT',
        'MARL MENTHOL BLACK 100 BX 10CT',
        'MARL MENTHOL BLACK BOX 10CT',
        'MARL MIDNIGHT BOX',
        'MARL NXT BOX 10CT',
        'MARL SB BLACK 100 BOX 10CT',
        'MARL SB BLACK BOX 10CT',
        'MARL 83 BOX 10CT',
        'MARL 72 GOLD BOX 10CT',
        'MARL 72 RED BOX 10CT',
        'MARL 72 SILVER BOX 10CT',
        'MARL BLEND #27 BOX 10CT'
    ]

    # Build query to get current POS data
    query = """
    SELECT
        i.Description as ProductName,
        i.ItemLookupCode as SKU,
        i.Cost as CurrentCost,
        i.LastCost as LastCost,
        i.Price as CurrentPrice,
        i.PriceA,
        i.PriceB,
        i.PriceC,
        i.SalePrice,
        i.LastUpdated,
        i.LastSold,
        -- Get the most recent selling price from transactions
        (SELECT TOP 1 te.Price
         FROM dbo.TransactionEntry te
         JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
         WHERE te.ItemID = i.ID
         ORDER BY t.Time DESC) as MostRecentSellingPrice,
        -- Get the date of most recent sale
        (SELECT TOP 1 t.Time
         FROM dbo.TransactionEntry te
         JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
         WHERE te.ItemID = i.ID
         ORDER BY t.Time DESC) as MostRecentSaleDate
    FROM dbo.Item i
    WHERE i.Description IN ({})
    ORDER BY i.Description
    """.format(','.join([f"'{item}'" for item in items_to_check]))

    print("Checking current POS prices for Marlboro items...\n")
    result = db.execute_query(query)

    if result is not None and not result.empty:
        # Convert decimal to float for display
        numeric_columns = ['CurrentCost', 'LastCost', 'CurrentPrice', 'PriceA', 'PriceB', 'PriceC', 'SalePrice', 'MostRecentSellingPrice']
        for col in numeric_columns:
            if col in result.columns:
                result[col] = result[col].astype(float)

        print("="*100)
        print("CURRENT POS PRICES FOR MARLBORO ITEMS")
        print("="*100)

        for _, row in result.iterrows():
            print(f"\n{row['ProductName']}")
            print("-" * 50)
            print(f"  SKU:                {row['SKU']}")
            print(f"  Current Cost:       ${row['CurrentCost']:.2f}")
            if row['LastCost'] and row['LastCost'] > 0:
                print(f"  Last Cost:          ${row['LastCost']:.2f}")
            print(f"  Current Price:      ${row['CurrentPrice']:.2f}")

            if row['SalePrice'] and row['SalePrice'] > 0:
                print(f"  Sale Price:         ${row['SalePrice']:.2f}")

            if row['PriceA'] and row['PriceA'] > 0:
                print(f"  Price A:            ${row['PriceA']:.2f}")
            if row['PriceB'] and row['PriceB'] > 0:
                print(f"  Price B:            ${row['PriceB']:.2f}")
            if row['PriceC'] and row['PriceC'] > 0:
                print(f"  Price C:            ${row['PriceC']:.2f}")

            if row['MostRecentSellingPrice']:
                print(f"  Last Sold At:       ${row['MostRecentSellingPrice']:.2f}")
                if row['MostRecentSaleDate']:
                    print(f"  Last Sale Date:     {row['MostRecentSaleDate']}")

            # Calculate margin
            if row['CurrentPrice'] > 0 and row['CurrentCost'] > 0:
                margin = ((row['CurrentPrice'] - row['CurrentCost']) / row['CurrentPrice']) * 100
                print(f"  Margin:             {margin:.1f}%")

        # Create summary table
        summary = pd.DataFrame({
            'Product': result['ProductName'],
            'Current Cost': result['CurrentCost'].round(2),
            'Current Price': result['CurrentPrice'].round(2),
            'Sale Price': result['SalePrice'].round(2),
            'Last Sold At': result['MostRecentSellingPrice'].round(2),
            'Margin %': ((result['CurrentPrice'] - result['CurrentCost']) / result['CurrentPrice'] * 100).round(1)
        })

        # Save to CSV
        filename = 'marlboro_current_prices.csv'
        summary.to_csv(filename, index=False)
        print(f"\n✅ Summary saved to {filename}")

        # Print summary statistics
        print("\n" + "="*100)
        print("SUMMARY STATISTICS")
        print("="*100)
        print(f"Average Cost:        ${summary['Current Cost'].mean():.2f}")
        print(f"Average Price:       ${summary['Current Price'].mean():.2f}")
        print(f"Average Margin:      {summary['Margin %'].mean():.1f}%")

        # Group by cost tier
        print("\n" + "="*100)
        print("ITEMS BY COST TIER")
        print("="*100)

        cost_tiers = summary.groupby('Current Cost').agg({
            'Product': 'count',
            'Current Price': 'mean',
            'Margin %': 'mean'
        }).round(2)

        for cost, row in cost_tiers.iterrows():
            print(f"Cost ${cost:.2f}: {int(row['Product'])} items | Avg Price: ${row['Current Price']:.2f} | Avg Margin: {row['Margin %']:.1f}%")

    else:
        print("No items found in the database matching those descriptions")

    return result

if __name__ == "__main__":
    check_marlboro_prices()