"""Quick check of vape excise tax - simplified query."""
import os
os.environ['TDSVER'] = '7.0'
import pymssql
import pandas as pd

SERVER = '10.1.10.105'
USER = 'amchranya'
PASSWORD = '2000Akbar!'
DATABASE = 'GAWDB'

try:
    conn = pymssql.connect(
        server=SERVER,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        tds_version='7.0',
        timeout=30
    )

    print("=== RECENT VAPE TRANSACTIONS (SAMPLE) ===\n")

    # Get just a few recent vape transactions
    query = """
    SELECT TOP 10
        pue.SubDescription3,
        pue.Price as SalePrice,
        pue.Cost as ProductCost,
        pue.PriceC as ExciseTax,
        pue.Quantity,
        pue.Weight,
        -- Is it percentage of cost?
        CAST((pue.PriceC / NULLIF(pue.Cost, 0)) * 100 as DECIMAL(10,2)) as Tax_Pct_Of_Cost,
        -- Is it per ML/weight?
        CAST(pue.PriceC / NULLIF(pue.Weight, 0) as DECIMAL(10,4)) as Tax_Per_Weight
    FROM PUExciseEntry pue
    WHERE pue.SubDescription3 LIKE 'V%PAID'
    ORDER BY pue.ID DESC
    """

    df = pd.read_sql(query, conn)

    if df.empty:
        print("No vape excise entries found. Let's check if they exist at all...")

        count_query = "SELECT COUNT(*) as Total FROM PUExciseEntry WHERE SubDescription3 LIKE 'V%'"
        count_df = pd.read_sql(count_query, conn)
        print(f"\nTotal vape excise entries: {count_df['Total'].iloc[0]}")

    else:
        print(df.to_string(index=False))
        print("\n\n=== ANALYSIS ===")

        # Check if it's consistent
        for code in df['SubDescription3'].unique():
            code_data = df[df['SubDescription3'] == code]
            avg_pct = code_data['Tax_Pct_Of_Cost'].mean()
            avg_weight = code_data['Tax_Per_Weight'].mean()

            print(f"\n{code}:")
            print(f"  Avg % of Cost: {avg_pct:.2f}%")
            print(f"  Avg per Weight: ${avg_weight:.4f} per unit")

            # Determine which is more consistent
            pct_std = code_data['Tax_Pct_Of_Cost'].std()
            weight_std = code_data['Tax_Per_Weight'].std()

            print(f"  Variation in % method: {pct_std:.4f}")
            print(f"  Variation in weight method: {weight_std:.4f}")

            if pct_std < weight_std:
                print(f"  ✓ Likely PERCENTAGE-based: {avg_pct:.1f}% of cost")
            else:
                print(f"  ✓ Likely WEIGHT-based: ${avg_weight:.4f} per unit")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
