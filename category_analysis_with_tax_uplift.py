#!/usr/bin/env python3
"""
Category Analysis with Georgia Tobacco Tax Uplift Adjustments
Accounts for actual cost of tax stamps and other tobacco-related uplifts
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Georgia Tobacco Tax Uplift Configuration
# Adjust these based on actual stamp costs and other uplifts
TAX_UPLIFT_CONFIG = {
    'CIGARETTE': {
        'stamp_cost_per_pack': 0.37,  # GA cigarette tax stamp cost per pack
        'additional_cost_pct': 0.0,   # Any additional % uplift
        'description': 'Cigarettes - $0.37/pack stamp + MSA fees'
    },
    'CIGARS': {
        'stamp_cost_per_unit': 0.23,  # Estimated cigar stamp cost
        'additional_cost_pct': 0.05,  # 5% additional for handling
        'description': 'Cigars - Stamp + 5% handling'
    },
    'LT-TAX-COLLECTED': {
        'stamp_cost_per_unit': 0.15,  # Little cigar tax
        'additional_cost_pct': 0.03,
        'description': 'Little Cigars Tax Collected - Stamp + 3%'
    },
    'LT-TAX PAID': {
        'stamp_cost_per_unit': 0.15,
        'additional_cost_pct': 0.03,
        'description': 'Little Cigars Tax Paid - Stamp + 3%'
    },
    'CIGAR GA': {
        'stamp_cost_per_unit': 0.20,
        'additional_cost_pct': 0.04,
        'description': 'GA Cigars - Stamp + 4%'
    },
    'LIT CIGARS 003251': {
        'stamp_cost_per_unit': 0.15,
        'additional_cost_pct': 0.03,
        'description': 'Little Cigars - Stamp + 3%'
    },
    'T7 SMOKELESS GA': {
        'stamp_cost_per_unit': 0.0,
        'additional_cost_pct': 0.08,  # 8% uplift for smokeless
        'description': 'Smokeless Tobacco - 8% uplift'
    }
}

def analyze_with_tax_uplift():
    """Run category analysis with tax uplift adjustments"""

    end_date = datetime.now()
    start_12mo = end_date - timedelta(days=365)
    start_24mo = end_date - timedelta(days=730)

    query = f"""
    WITH CurrentPeriod AS (
        SELECT
            ISNULL(c.Name, 'Uncategorized') as Category,
            c.ID as CategoryID,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as Units,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as ReportedTotalCost,
            SUM((te.Price - te.Cost) * te.Quantity) as ReportedGrossProfit,
            -- We'll adjust these after
            AVG(te.Price) as AvgPrice,
            AVG(te.Cost) as AvgCost
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_12mo.strftime('%Y-%m-%d')}'
            AND t.[Time] <= '{end_date.strftime('%Y-%m-%d')}'
            AND te.Price > 0
        GROUP BY c.Name, c.ID
    ),
    PreviousPeriod AS (
        SELECT
            ISNULL(c.Name, 'Uncategorized') as Category,
            SUM(te.Price * te.Quantity) as PrevRevenue,
            SUM((te.Price - te.Cost) * te.Quantity) as PrevGrossProfit
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_24mo.strftime('%Y-%m-%d')}'
            AND t.[Time] < '{start_12mo.strftime('%Y-%m-%d')}'
            AND te.Price > 0
        GROUP BY c.Name
    )
    SELECT
        c.Category,
        c.CategoryID,
        c.Transactions,
        c.Units,
        c.Revenue,
        c.ReportedTotalCost,
        c.ReportedGrossProfit,
        c.AvgPrice,
        c.AvgCost,
        ISNULL(p.PrevRevenue, 0) as PrevYearRevenue,
        ISNULL(p.PrevGrossProfit, 0) as PrevYearGrossProfit
    FROM CurrentPeriod c
    LEFT JOIN PreviousPeriod p ON c.Category = p.Category
    WHERE c.Revenue > 0
    ORDER BY c.Revenue DESC
    """

    try:
        with SQLServerConnection() as db:
            df = db.execute_query(query, description="Category analysis with tax data")

            if df.empty:
                logger.warning("No data returned")
                return None

            # Apply tax uplifts
            df['TaxUpliftAmount'] = 0.0
            df['AdjustedTotalCost'] = df['ReportedTotalCost']
            df['AdjustedGrossProfit'] = df['ReportedGrossProfit']

            for category, config in TAX_UPLIFT_CONFIG.items():
                mask = df['Category'] == category
                if mask.any():
                    row = df[mask].iloc[0]

                    # Calculate stamp costs
                    stamp_cost = 0
                    if 'stamp_cost_per_unit' in config:
                        stamp_cost = config['stamp_cost_per_unit'] * row['Units']
                    elif 'stamp_cost_per_pack' in config:
                        stamp_cost = config['stamp_cost_per_pack'] * row['Units']

                    # Calculate percentage uplift
                    pct_uplift = row['ReportedTotalCost'] * config.get('additional_cost_pct', 0)

                    # Total uplift
                    total_uplift = stamp_cost + pct_uplift

                    # Apply adjustments
                    df.loc[mask, 'TaxUpliftAmount'] = total_uplift
                    df.loc[mask, 'AdjustedTotalCost'] = row['ReportedTotalCost'] + total_uplift
                    df.loc[mask, 'AdjustedGrossProfit'] = row['Revenue'] - (row['ReportedTotalCost'] + total_uplift)

                    logger.info(f"{category}: Tax uplift = ${total_uplift:,.2f}")

            # Calculate margins
            df['ReportedMarginPercent'] = (df['ReportedGrossProfit'] / df['Revenue'] * 100).fillna(0)
            df['AdjustedMarginPercent'] = (df['AdjustedGrossProfit'] / df['Revenue'] * 100).fillna(0)
            df['MarginImpact'] = df['AdjustedMarginPercent'] - df['ReportedMarginPercent']

            # Calculate shares
            total_revenue = df['Revenue'].sum()
            total_reported_profit = df['ReportedGrossProfit'].sum()
            total_adjusted_profit = df['AdjustedGrossProfit'].sum()

            df['RevenueSharePercent'] = (df['Revenue'] / total_revenue * 100)
            df['ReportedProfitContribution'] = (df['ReportedGrossProfit'] / total_reported_profit * 100)
            df['AdjustedProfitContribution'] = (df['AdjustedGrossProfit'] / total_adjusted_profit * 100)

            # Calculate growth
            df['RevenueGrowthPercent'] = ((df['Revenue'] - df['PrevYearRevenue']) / df['PrevYearRevenue'].replace(0, 1) * 100).fillna(0)

            # Print report
            print("\n" + "="*120)
            print("CATEGORY ANALYSIS WITH GEORGIA TOBACCO TAX UPLIFT ADJUSTMENTS")
            print("="*120)
            print(f"Period: {start_12mo.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

            print(f"\n📊 OVERALL METRICS:")
            print(f"  Total Revenue:              ${total_revenue:,.2f}")
            print(f"  Reported Gross Profit:      ${total_reported_profit:,.2f}  ({total_reported_profit/total_revenue*100:.1f}%)")
            print(f"  Total Tax Uplift Costs:     ${df['TaxUpliftAmount'].sum():,.2f}")
            print(f"  Adjusted Gross Profit:      ${total_adjusted_profit:,.2f}  ({total_adjusted_profit/total_revenue*100:.1f}%)")
            print(f"  Profit Impact from Uplifts: ${total_adjusted_profit - total_reported_profit:,.2f}")

            # Categories with tax uplifts
            tobacco_cats = df[df['TaxUpliftAmount'] > 0].sort_values('Revenue', ascending=False)

            if not tobacco_cats.empty:
                print("\n" + "="*120)
                print("TOBACCO CATEGORIES - TAX UPLIFT IMPACT")
                print("="*120)
                print(f"{'Category':<30} {'Revenue':>15} {'Reported':>10} {'Adjusted':>10} {'Impact':>10} {'Uplift $':>15}")
                print(f"{'':30} {'':15} {'Margin %':>10} {'Margin %':>10} {'':>10} {'':>15}")
                print("-"*120)

                for _, row in tobacco_cats.iterrows():
                    print(f"{row['Category']:<30} "
                          f"${row['Revenue']:>14,.0f} "
                          f"{row['ReportedMarginPercent']:>9.1f}% "
                          f"{row['AdjustedMarginPercent']:>9.1f}% "
                          f"{row['MarginImpact']:>9.1f}% "
                          f"${row['TaxUpliftAmount']:>14,.0f}")

                # Configuration used
                print("\n" + "="*120)
                print("TAX UPLIFT CONFIGURATION")
                print("="*120)
                for cat, config in TAX_UPLIFT_CONFIG.items():
                    if df[df['Category'] == cat].shape[0] > 0:
                        print(f"\n{cat}:")
                        print(f"  {config['description']}")
                        if 'stamp_cost_per_pack' in config:
                            print(f"  Stamp Cost: ${config['stamp_cost_per_pack']}/pack")
                        elif 'stamp_cost_per_unit' in config:
                            print(f"  Stamp Cost: ${config['stamp_cost_per_unit']}/unit")
                        if config.get('additional_cost_pct'):
                            print(f"  Additional: {config['additional_cost_pct']*100}%")

            # Top categories comparison
            print("\n" + "="*120)
            print("TOP 20 CATEGORIES - REPORTED vs ADJUSTED MARGINS")
            print("="*120)
            print(f"{'Category':<30} {'Revenue':>15} {'Reported %':>12} {'Adjusted %':>12} {'Impact':>10} {'Rev Share':>10}")
            print("-"*120)

            for _, row in df.head(20).iterrows():
                impact_str = f"{row['MarginImpact']:+.1f}%" if row['TaxUpliftAmount'] > 0 else "--"
                print(f"{row['Category']:<30} "
                      f"${row['Revenue']:>14,.0f} "
                      f"{row['ReportedMarginPercent']:>11.1f}% "
                      f"{row['AdjustedMarginPercent']:>11.1f}% "
                      f"{impact_str:>10} "
                      f"{row['RevenueSharePercent']:>9.1f}%")

            # Export
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"category_analysis_tax_adjusted_{timestamp}.csv"
            df.to_csv(output_file, index=False)

            print(f"\n💾 Data exported to: {output_file}")
            print("\n" + "="*120)
            print("NOTE: Review the TAX_UPLIFT_CONFIG at the top of this script to adjust")
            print("stamp costs and percentages based on your actual costs.")
            print("="*120)

            return df

    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: This analysis applies tax uplift adjustments to tobacco categories.")
    print("Please review and adjust the TAX_UPLIFT_CONFIG at the top of the script")
    print("to match your actual tax stamp costs and other tobacco-related uplifts.\n")

    df = analyze_with_tax_uplift()

    if df is not None:
        print("\n✅ Analysis complete!")
        print("\nKey takeaway: Tax uplifts significantly impact tobacco category profitability.")
        print("Use the 'Adjusted' margins for make strategic keep/kill decisions.")
