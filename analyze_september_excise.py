"""
Analyze September excise tax to understand the correct calculation.

This script will:
1. Query PUExciseEntry for September data
2. Query Item-based calculation for September
3. Compare the two approaches
4. Show sample data to understand the relationship
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from database.sql_server import db

# Load environment variables
load_dotenv()

def analyze_september():
    """Analyze September excise tax data."""

    print("\n" + "="*80)
    print("SEPTEMBER EXCISE TAX ANALYSIS")
    print("="*80)

    # September 2024 date range
    start_date = "2024-09-01 00:00:00"
    end_date = "2024-09-30 23:59:59"

    print(f"\nDate Range: September 2024")
    print("-" * 80)

    # METHOD 1: Query PUExciseEntry directly (using PriceC field)
    print("\n1. PUEXCISEENTRY TABLE (PriceC field - actual tax amount):")
    print("-" * 80)

    puexcise_paid_query = f"""
    SELECT
        SubDescription3,
        COUNT(*) as EntryCount,
        SUM(Quantity) as TotalQuantity,
        SUM(PriceC * Quantity) as TotalExciseTax,
        AVG(PriceC) as AvgPriceC,
        AVG(Cost) as AvgCost,
        AVG(Price) as AvgPrice
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_date}'
      AND TransactionTime <= '{end_date}'
      AND SubDescription3 LIKE '%PAID'
    GROUP BY SubDescription3
    ORDER BY SubDescription3
    """

    puexcise_coll_query = f"""
    SELECT
        SubDescription3,
        COUNT(*) as EntryCount,
        SUM(Quantity) as TotalQuantity,
        SUM(PriceC * Quantity) as TotalExciseTax,
        AVG(PriceC) as AvgPriceC,
        AVG(Cost) as AvgCost,
        AVG(Price) as AvgPrice
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_date}'
      AND TransactionTime <= '{end_date}'
      AND SubDescription3 LIKE '%COLL'
    GROUP BY SubDescription3
    ORDER BY SubDescription3
    """

    try:
        print("\nPAID (to state):")
        paid_result = db.execute_query(puexcise_paid_query)
        if not paid_result.empty:
            print(paid_result.to_string(index=False))
            total_paid = paid_result['TotalExciseTax'].sum()
            print(f"\n** TOTAL PAID TO STATE: ${total_paid:,.2f} **\n")
        else:
            print("No PAID data found")

        print("\nCOLLECTED (from customers):")
        coll_result = db.execute_query(puexcise_coll_query)
        if not coll_result.empty:
            print(coll_result.to_string(index=False))
            total_coll = coll_result['TotalExciseTax'].sum()
            print(f"\n** TOTAL COLLECTED FROM CUSTOMERS: ${total_coll:,.2f} **\n")
        else:
            print("No COLL data found")

    except Exception as e:
        print(f"Error querying PUExciseEntry: {e}")

    # METHOD 2: Query Item table approach (calculating from Cost)
    print("\n2. ITEM TABLE APPROACH (calculating Cost * Quantity * Rate):")
    print("-" * 80)

    item_paid_query = f"""
    SELECT TOP 10
        i.SubDescription3,
        i.Description,
        te.Cost,
        te.Price,
        te.Quantity,
        (te.Cost * te.Quantity) as TotalCost,
        (te.Price * te.Quantity) as TotalPrice
    FROM [Transaction] t WITH (NOLOCK)
    INNER JOIN TransactionEntry te WITH (NOLOCK)
        ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i WITH (NOLOCK)
        ON te.ItemID = i.ID
    WHERE t.Time >= '{start_date}'
      AND t.Time <= '{end_date}'
      AND i.SubDescription3 LIKE '%PAID'
    ORDER BY t.Time DESC
    """

    try:
        print("\nSample PAID transactions (Item table approach):")
        item_paid = db.execute_query(item_paid_query)
        if not item_paid.empty:
            print(item_paid.to_string(index=False))
        else:
            print("No data found")
    except Exception as e:
        print(f"Error: {e}")

    # METHOD 3: Compare PUExciseEntry fields to understand PriceC
    print("\n3. SAMPLE PUEXCISEENTRY RECORDS (to understand PriceC):")
    print("-" * 80)

    sample_query = f"""
    SELECT TOP 20
        SubDescription3,
        Price as SalePrice,
        Cost as ProductCost,
        PriceC as ExciseTaxAmount,
        Quantity,
        (Price * Quantity) as TotalSalePrice,
        (Cost * Quantity) as TotalCost,
        (PriceC * Quantity) as TotalExcise,
        CAST((PriceC / NULLIF(Cost, 0)) * 100 as DECIMAL(10,2)) as Excise_Pct_Of_Cost,
        CAST((PriceC / NULLIF(Price, 0)) * 100 as DECIMAL(10,2)) as Excise_Pct_Of_Price
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_date}'
      AND TransactionTime <= '{end_date}'
      AND SubDescription3 LIKE '%PAID'
    ORDER BY ID DESC
    """

    try:
        sample = db.execute_query(sample_query)
        if not sample.empty:
            print(sample.to_string(index=False))
            print("\nAnalyzing PriceC relationship:")
            print(f"  Avg Excise as % of Cost: {sample['Excise_Pct_Of_Cost'].mean():.2f}%")
            print(f"  Avg Excise as % of Price: {sample['Excise_Pct_Of_Price'].mean():.2f}%")
        else:
            print("No sample data found")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nPlease check the September excise report in your Downloads folder and compare")
    print("the numbers above. Which method matches the report?")
    print("\n1. If PUExciseEntry totals match, we should use PriceC directly (not calculate)")
    print("2. If neither matches, please share the exact numbers from the report")
    print("="*80 + "\n")


if __name__ == "__main__":
    analyze_september()
