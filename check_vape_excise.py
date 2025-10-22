"""Check vape products and their excise tax calculation method."""
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

    print("=== ALL VAPE-RELATED SUBDESCRIPTION3 CODES ===\n")

    # Get all vape tax codes
    query = """
    SELECT
        SubDescription3,
        COUNT(*) as ItemCount
    FROM Item
    WHERE SubDescription3 LIKE 'V%'
    GROUP BY SubDescription3
    ORDER BY SubDescription3
    """
    df = pd.read_sql(query, conn)
    print(df.to_string(index=False))

    print("\n\n=== SAMPLE VAPE ITEMS WITH DETAILS ===\n")

    # Get sample vape items with all relevant fields
    query2 = """
    SELECT TOP 30
        ItemLookupCode,
        Description,
        SubDescription1,
        SubDescription2,
        SubDescription3,
        Price,
        Cost,
        Weight,
        UnitOfMeasure
    FROM Item
    WHERE SubDescription3 LIKE 'V%'
    ORDER BY SubDescription3, Description
    """
    df2 = pd.read_sql(query2, conn)
    print(df2.to_string(index=False))

    print("\n\n=== CHECK ACTUAL EXCISE CALCULATIONS FROM PUEXCISEENTRY ===\n")

    # Get actual excise tax data for vape products
    query3 = """
    SELECT TOP 20
        pue.SubDescription3,
        pue.Price as SalePrice,
        pue.Cost as ProductCost,
        pue.PriceC as ExciseTaxAmount,
        pue.Quantity,
        pue.Weight,
        i.Description,
        i.UnitOfMeasure,
        -- Calculate what the rate appears to be
        CASE
            WHEN pue.Cost > 0 THEN CAST((pue.PriceC / pue.Cost) * 100 as DECIMAL(10,2))
            ELSE 0
        END as ApparentTaxRate_Pct,
        CASE
            WHEN pue.Weight > 0 THEN CAST(pue.PriceC / pue.Weight as DECIMAL(10,4))
            ELSE 0
        END as ApparentTaxPer_Weight
    FROM PUExciseEntry pue
    JOIN Item i ON pue.ItemID = i.ID
    WHERE pue.SubDescription3 LIKE 'V%'
      AND pue.TransactionTime >= DATEADD(day, -30, GETDATE())
    ORDER BY pue.SubDescription3, pue.TransactionTime DESC
    """
    df3 = pd.read_sql(query3, conn)
    print(df3.to_string(index=False))

    print("\n\n=== EXCISE TAX PATTERN ANALYSIS ===")
    print("Checking if tax is percentage-based or volume-based...\n")

    # Analyze patterns
    query4 = """
    SELECT
        pue.SubDescription3,
        COUNT(*) as SampleSize,
        AVG(CASE WHEN pue.Cost > 0 THEN (pue.PriceC / pue.Cost) * 100 ELSE 0 END) as AvgTaxRate_Pct,
        MIN(CASE WHEN pue.Cost > 0 THEN (pue.PriceC / pue.Cost) * 100 ELSE 0 END) as MinTaxRate_Pct,
        MAX(CASE WHEN pue.Cost > 0 THEN (pue.PriceC / pue.Cost) * 100 ELSE 0 END) as MaxTaxRate_Pct,
        AVG(CASE WHEN pue.Weight > 0 THEN pue.PriceC / pue.Weight ELSE 0 END) as AvgTaxPer_Weight,
        AVG(pue.PriceC) as AvgExciseTax
    FROM PUExciseEntry pue
    WHERE pue.SubDescription3 LIKE 'V%'
      AND pue.TransactionTime >= DATEADD(day, -30, GETDATE())
    GROUP BY pue.SubDescription3
    ORDER BY pue.SubDescription3
    """
    df4 = pd.read_sql(query4, conn)
    print(df4.to_string(index=False))

    print("\n\n=== INTERPRETATION ===")
    print("If AvgTaxRate_Pct is consistent (e.g., always 7.0), it's percentage-based")
    print("If AvgTaxPer_Weight is consistent (e.g., always 0.05), it's cents-per-ml/weight")
    print("Check the Min/Max range - consistent = that's the calculation method")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
