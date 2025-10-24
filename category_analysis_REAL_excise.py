#!/usr/bin/env python3
"""
Category Analysis with REAL Excise Tax Data from PUExciseEntry
Uses actual PriceC (excise tax) from your POS system
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_with_real_excise():
    """Run category analysis with REAL excise tax from PUExciseEntry"""

    end_date = datetime.now()
    start_12mo = end_date - timedelta(days=365)

    # Query joining TransactionEntry with PUExciseEntry to get real excise costs
    query = f"""
    WITH ExciseSales AS (
        SELECT
            ISNULL(c.Name, 'Uncategorized') as Category,
            c.ID as CategoryID,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as Units,
            SUM(te.Price * te.Quantity) as Revenue,
            -- Base cost without excise
            SUM(te.Cost * te.Quantity) as BaseCost,
            -- Excise tax from PUExciseEntry (stored in PriceC)
            SUM(ISNULL(pue.PriceC, 0) * te.Quantity) as TotalExciseTax,
            -- Total actual cost including excise
            SUM((te.Cost + ISNULL(pue.PriceC, 0)) * te.Quantity) as TotalCostWithExcise,
            -- Gross profit reported (without excise)
            SUM((te.Price - te.Cost) * te.Quantity) as ReportedGrossProfit,
            -- REAL gross profit (with excise)
            SUM((te.Price - te.Cost - ISNULL(pue.PriceC, 0)) * te.Quantity) as ActualGrossProfit
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        -- Join to get excise tax data
        LEFT JOIN PUExciseEntry pue ON te.ID = pue.TransactionEntryID
        WHERE t.[Time] >= '{start_12mo.strftime('%Y-%m-%d')}'
            AND t.[Time] <= '{end_date.strftime('%Y-%m-%d')}'
            AND te.Price > 0
        GROUP BY c.Name, c.ID
    )
    SELECT
        *,
        -- Calculate margins
        CASE
            WHEN Revenue > 0 THEN (ReportedGrossProfit / Revenue) * 100
            ELSE 0
        END as ReportedMarginPercent,
        CASE
            WHEN Revenue > 0 THEN (ActualGrossProfit / Revenue) * 100
            ELSE 0
        END as ActualMarginPercent
    FROM ExciseSales
    WHERE Revenue > 0
    ORDER BY Revenue DESC
    """

    try:
        with SQLServerConnection() as db:
            df = db.execute_query(query, description="Category analysis with REAL excise data")

            if df.empty:
                logger.warning("No data returned")
                return None

            # Calculate overall metrics
            total_revenue = df['Revenue'].sum()
            total_reported_profit = df['ReportedGrossProfit'].sum()
            total_actual_profit = df['ActualGrossProfit'].sum()
            total_excise_tax = df['TotalExciseTax'].sum()

            # Calculate shares
            df['RevenueSharePercent'] = (df['Revenue'] / total_revenue * 100)
            df['MarginImpact'] = df['ActualMarginPercent'] - df['ReportedMarginPercent']

            # Print comprehensive report
            print("\n" + "="*130)
            print("CATEGORY ANALYSIS WITH **REAL** EXCISE TAX DATA FROM POS SYSTEM")
            print("="*130)
            print(f"Period: {start_12mo.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"Data Source: PUExciseEntry.PriceC (actual excise tax per unit)")

            print(f"\n📊 OVERALL BUSINESS METRICS:")
            print(f"  Total Revenue:              ${total_revenue:,.2f}")
            print(f"  Reported Gross Profit:      ${total_reported_profit:,.2f}  ({total_reported_profit/total_revenue*100:.2f}%)")
            print(f"  Total Excise Tax Paid:      ${total_excise_tax:,.2f}")
            print(f"  ACTUAL Gross Profit:        ${total_actual_profit:,.2f}  ({total_actual_profit/total_revenue*100:.2f}%)")
            print(f"  Profit Reduction from Tax:  ${total_reported_profit - total_actual_profit:,.2f}")
            print(f"  Margin Compression:         {(total_reported_profit - total_actual_profit)/total_revenue*100:.2f} percentage points")

            # Categories with excise tax
            tobacco_cats = df[df['TotalExciseTax'] > 0].sort_values('Revenue', ascending=False)

            if not tobacco_cats.empty:
                print("\n" + "="*130)
                print("TOBACCO CATEGORIES - ACTUAL EXCISE TAX IMPACT")
                print("="*130)
                print(f"{'Category':<30} {'Revenue':>15} {'Reported':>10} {'ACTUAL':>10} {'Impact':>10} {'Excise Tax $':>15}")
                print(f"{'':30} {'':15} {'Margin %':>10} {'Margin %':>10} {'':>10} {'(from POS)':>15}")
                print("-"*130)

                for _, row in tobacco_cats.iterrows():
                    print(f"{row['Category']:<30} "
                          f"${row['Revenue']:>14,.0f} "
                          f"{row['ReportedMarginPercent']:>9.2f}% "
                          f"{row['ActualMarginPercent']:>9.2f}% "
                          f"{row['MarginImpact']:>9.2f}% "
                          f"${row['TotalExciseTax']:>14,.2f}")

                print(f"\n{'TOTAL TOBACCO':<30} "
                      f"${tobacco_cats['Revenue'].sum():>14,.0f} "
                      f"{tobacco_cats['ReportedGrossProfit'].sum()/tobacco_cats['Revenue'].sum()*100:>9.2f}% "
                      f"{tobacco_cats['ActualGrossProfit'].sum()/tobacco_cats['Revenue'].sum()*100:>9.2f}% "
                      f"{(tobacco_cats['ActualGrossProfit'].sum() - tobacco_cats['ReportedGrossProfit'].sum())/tobacco_cats['Revenue'].sum()*100:>9.2f}% "
                      f"${tobacco_cats['TotalExciseTax'].sum():>14,.2f}")

            # ALL Categories comparison
            print("\n" + "="*130)
            print("ALL CATEGORIES - REPORTED vs ACTUAL MARGINS (with Real Excise Data)")
            print("="*130)
            print(f"{'Rank':<5} {'Category':<30} {'Revenue':>15} {'Reported %':>12} {'ACTUAL %':>12} {'Impact':>10} {'Excise Tax':>15}")
            print("-"*130)

            for idx, row in df.iterrows():
                rank = idx + 1
                impact_str = f"{row['MarginImpact']:+.2f}%" if row['TotalExciseTax'] > 0 else "--"
                excise_str = f"${row['TotalExciseTax']:,.0f}" if row['TotalExciseTax'] > 0 else "--"

                print(f"{rank:<5} {row['Category']:<30} "
                      f"${row['Revenue']:>14,.0f} "
                      f"{row['ReportedMarginPercent']:>11.2f}% "
                      f"{row['ActualMarginPercent']:>11.2f}% "
                      f"{impact_str:>10} "
                      f"{excise_str:>15}")

            # Key insights
            print("\n" + "="*130)
            print("🚨 KEY INSIGHTS - TRUTH REVEALED")
            print("="*130)

            # Categories that flip from profitable to unprofitable
            flipped = df[(df['ReportedMarginPercent'] > 0) & (df['ActualMarginPercent'] < 0)]
            if not flipped.empty:
                print(f"\n⚠️  CATEGORIES THAT ARE ACTUALLY LOSING MONEY (after excise):")
                for _, row in flipped.iterrows():
                    print(f"   • {row['Category']}: Reported {row['ReportedMarginPercent']:.1f}% → ACTUAL {row['ActualMarginPercent']:.1f}%")
                    print(f"     Revenue: ${row['Revenue']:,.0f} | Excise Cost: ${row['TotalExciseTax']:,.0f}")

            # Biggest margin compressions
            print(f"\n📉 BIGGEST MARGIN COMPRESSIONS:")
            worst_impact = df[df['TotalExciseTax'] > 0].nsmallest(5, 'MarginImpact')
            for _, row in worst_impact.iterrows():
                print(f"   • {row['Category']}: {row['MarginImpact']:.2f} percentage points")
                print(f"     ${row['Revenue']:,.0f} revenue @ {row['ActualMarginPercent']:.2f}% ACTUAL margin")

            # Strategic recommendations
            print(f"\n💡 STRATEGIC RECOMMENDATIONS:")
            print(f"\n1. PRICING ADJUSTMENTS NEEDED:")
            needs_repricing = df[(df['ActualMarginPercent'] < 10) & (df['ActualMarginPercent'] > 0) & (df['RevenueSharePercent'] > 1)]
            for _, row in needs_repricing.iterrows():
                # Calculate price increase needed to hit 10% margin
                target_margin = 0.10
                current_cogs = row['TotalCostWithExcise'] / row['Units']
                target_price = current_cogs / (1 - target_margin)
                current_price = row['Revenue'] / row['Units']
                price_increase = ((target_price - current_price) / current_price) * 100

                print(f"   • {row['Category']}: {row['ActualMarginPercent']:.2f}% actual margin")
                print(f"     → Need {price_increase:.1f}% price increase to hit 10% margin")
                print(f"     → Potential annual profit gain: ${row['Revenue'] * 0.10 - row['ActualGrossProfit']:,.0f}")

            print(f"\n2. CATEGORIES TO ELIMINATE:")
            kill_list = df[df['ActualMarginPercent'] < 0]
            for _, row in kill_list.iterrows():
                print(f"   ❌ {row['Category']}: LOSING ${abs(row['ActualGrossProfit']):,.2f}/year")

            # Export
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"category_analysis_REAL_excise_{timestamp}.csv"
            df.to_csv(output_file, index=False)

            print(f"\n💾 Data exported to: {output_file}")
            print("\n" + "="*130)
            print("This analysis uses ACTUAL excise tax from your POS system (PUExciseEntry.PriceC)")
            print("These are the TRUE margins - use these for all strategic decisions!")
            print("="*130)

            return df

    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    df = analyze_with_real_excise()

    if df is not None:
        print("\n✅ Analysis complete with REAL excise data from your POS!")
        print("\n🎯 Use the 'ACTUAL Margin %' column for all business decisions.")
        print("The 'Reported' margins are misleading - they don't include excise tax costs.")
