"""Check Item.SubDescription3 values to see if we can identify excise products."""
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

    print("=== ITEM.SUBDESCRIPTION3 VALUES ===\n")

    # Get unique SubDescription3 values
    query = """
    SELECT
        SubDescription3,
        COUNT(*) as ItemCount,
        SUM(CASE WHEN Quantity > 0 THEN 1 ELSE 0 END) as InStock
    FROM Item
    WHERE SubDescription3 IS NOT NULL AND SubDescription3 != ''
    GROUP BY SubDescription3
    ORDER BY ItemCount DESC
    """

    df = pd.read_sql(query, conn)
    print(df.to_string(index=False))

    print("\n\n=== SAMPLE ITEMS WITH SUBDESCRIPTION3 ===\n")

    # Get sample items for each SubDescription3 type
    query2 = """
    SELECT TOP 20
        ItemLookupCode,
        Description,
        SubDescription1,
        SubDescription2,
        SubDescription3,
        Price,
        Cost,
        CategoryID
    FROM Item
    WHERE SubDescription3 IS NOT NULL AND SubDescription3 != ''
    ORDER BY SubDescription3, ItemLookupCode
    """

    df2 = pd.read_sql(query2, conn)
    print(df2.to_string(index=False))

    print("\n\n=== TAX RATE MAPPING FROM SUBDESCRIPTION3 ===")
    print("If SubDescription3 contains tax codes, here's the pattern:")
    print("  LT10PAID/COLL = Loose Tobacco at 10%")
    print("  SL10PAID/COLL = Smokeless at 10%")
    print("  LC23PAID/COLL = Large Cigars at 23%")
    print("  LC25PAID/COLL = Little Cigars at 25%")
    print("  VO07PAID/COLL = Vapors Open at 7%")
    print("  VD07PAID/COLL = Vapors Device at 7%")
    print("  VC05PAID/COLL = Vapors Closed at 5%")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
