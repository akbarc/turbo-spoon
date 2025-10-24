#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging
import warnings
warnings.filterwarnings('ignore')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set style for better-looking charts
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def analyze_category_performance_ttm():
    """Analyze and chart category performance over trailing twelve months"""
    
    # Calculate date range - TTM
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Analyzing category performance from {start_date_str} to {end_date_str}")
    
    # Query for monthly category performance
    monthly_query = f"""
    SELECT 
        YEAR(t.[Time]) as Year,
        MONTH(t.[Time]) as Month,
        DATENAME(month, t.[Time]) + ' ' + CAST(YEAR(t.[Time]) as varchar) as MonthYear,
        ISNULL(c.Name, 'Uncategorized') as Category,
        COUNT(DISTINCT t.TransactionNumber) as Transactions,
        SUM(te.Quantity) as UnitsSold,
        SUM(te.Price * te.Quantity) as Revenue,
        SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
        AVG(te.Price) as AvgPrice,
        CASE 
            WHEN SUM(te.Price * te.Quantity) > 0 
            THEN (SUM((te.Price - te.Cost) * te.Quantity) / SUM(te.Price * te.Quantity)) * 100 
            ELSE 0 
        END as MarginPercent
    FROM [Transaction] t
    INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    LEFT JOIN Category c ON i.CategoryID = c.ID
    WHERE t.[Time] >= '{start_date_str}'
        AND t.[Time] <= '{end_date_str}'
        AND te.Quantity > 0
        AND te.Price > 0
    GROUP BY 
        YEAR(t.[Time]), 
        MONTH(t.[Time]), 
        DATENAME(month, t.[Time]),
        c.Name
    ORDER BY Year, Month, Category
    """
    
    # Query for top categories
    top_categories_query = f"""
    SELECT TOP 15
        ISNULL(c.Name, 'Uncategorized') as Category,
        SUM(te.Price * te.Quantity) as TotalRevenue,
        SUM(te.Quantity) as TotalUnits,
        COUNT(DISTINCT t.TransactionNumber) as TotalTransactions
    FROM [Transaction] t
    INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    LEFT JOIN Category c ON i.CategoryID = c.ID
    WHERE t.[Time] >= '{start_date_str}'
        AND t.[Time] <= '{end_date_str}'
        AND te.Quantity > 0
        AND te.Price > 0
    GROUP BY c.Name
    ORDER BY SUM(te.Price * te.Quantity) DESC
    """
    
    try:
        with SQLServerConnection() as db:
            # Fetch data
            logger.info("Fetching monthly category performance data...")
            df_monthly = db.execute_query(monthly_query, description="Monthly category performance")
            
            logger.info("Fetching top categories...")
            df_top = db.execute_query(top_categories_query, description="Top categories")
            
            if df_monthly.empty:
                logger.warning("No data found for the period")
                return None
            
            # Create month-year column for proper sorting
            df_monthly['Date'] = pd.to_datetime(df_monthly['Year'].astype(str) + '-' + 
                                               df_monthly['Month'].astype(str) + '-01')
            df_monthly = df_monthly.sort_values('Date')
            
            # Get top 10 categories for focused analysis
            top_10_categories = df_top.head(10)['Category'].tolist()
            
            # Create visualizations
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create figure with multiple subplots
            fig = plt.figure(figsize=(20, 24))
            
            # 1. Top Categories Revenue Bar Chart
            ax1 = plt.subplot(4, 2, 1)
            top_10_data = df_top.head(10)
            bars = ax1.barh(range(len(top_10_data)), top_10_data['TotalRevenue'].values)
            ax1.set_yticks(range(len(top_10_data)))
            ax1.set_yticklabels(top_10_data['Category'].values)
            ax1.set_xlabel('Revenue ($)')
            ax1.set_title('Top 10 Categories by Revenue (TTM)', fontsize=14, fontweight='bold')
            ax1.invert_yaxis()
            # Add value labels on bars
            for i, (bar, val) in enumerate(zip(bars, top_10_data['TotalRevenue'].values)):
                ax1.text(val, i, f' ${val:,.0f}', va='center')
            
            # 2. Revenue Trend for Top 5 Categories
            ax2 = plt.subplot(4, 2, 2)
            top_5_categories = top_10_categories[:5]
            for category in top_5_categories:
                cat_data = df_monthly[df_monthly['Category'] == category].groupby('Date')['Revenue'].sum()
                ax2.plot(cat_data.index, cat_data.values, marker='o', label=category[:20], linewidth=2)
            ax2.set_xlabel('Month')
            ax2.set_ylabel('Revenue ($)')
            ax2.set_title('Revenue Trend - Top 5 Categories', fontsize=14, fontweight='bold')
            ax2.legend(loc='best', fontsize=8)
            ax2.tick_params(axis='x', rotation=45)
            
            # 3. Market Share Pie Chart
            ax3 = plt.subplot(4, 2, 3)
            top_8_revenue = df_top.head(8)['TotalRevenue'].values
            top_8_names = df_top.head(8)['Category'].values
            other_revenue = df_top.iloc[8:]['TotalRevenue'].sum() if len(df_top) > 8 else 0
            
            if other_revenue > 0:
                pie_values = list(top_8_revenue) + [other_revenue]
                pie_labels = [name[:15] for name in top_8_names] + ['Others']
            else:
                pie_values = top_8_revenue
                pie_labels = [name[:15] for name in top_8_names]
            
            wedges, texts, autotexts = ax3.pie(pie_values, labels=pie_labels, autopct='%1.1f%%',
                                                startangle=90)
            ax3.set_title('Category Market Share (TTM)', fontsize=14, fontweight='bold')
            
            # 4. Monthly Revenue Stacked Area Chart
            ax4 = plt.subplot(4, 2, 4)
            pivot_revenue = df_monthly[df_monthly['Category'].isin(top_10_categories)].pivot_table(
                index='Date', columns='Category', values='Revenue', aggfunc='sum', fill_value=0
            )
            pivot_revenue.plot(kind='area', stacked=True, ax=ax4, alpha=0.7)
            ax4.set_xlabel('Month')
            ax4.set_ylabel('Revenue ($)')
            ax4.set_title('Stacked Revenue by Category', fontsize=14, fontweight='bold')
            ax4.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=8)
            
            # 5. Margin Analysis
            ax5 = plt.subplot(4, 2, 5)
            margin_data = df_monthly.groupby('Category').agg({
                'Revenue': 'sum',
                'MarginPercent': 'mean'
            }).nlargest(15, 'Revenue')
            
            x_pos = np.arange(len(margin_data))
            bars = ax5.bar(x_pos, margin_data['MarginPercent'].values)
            ax5.set_xticks(x_pos)
            ax5.set_xticklabels([cat[:10] for cat in margin_data.index], rotation=45, ha='right')
            ax5.set_ylabel('Margin %')
            ax5.set_title('Average Margin % by Category (Top 15)', fontsize=14, fontweight='bold')
            ax5.axhline(y=margin_data['MarginPercent'].mean(), color='r', linestyle='--', 
                       label=f'Avg: {margin_data["MarginPercent"].mean():.1f}%')
            ax5.legend()
            
            # Color bars based on margin level
            for bar, margin in zip(bars, margin_data['MarginPercent'].values):
                if margin > 25:
                    bar.set_color('green')
                elif margin > 15:
                    bar.set_color('yellow')
                else:
                    bar.set_color('red')
            
            # 6. Units Sold Trend
            ax6 = plt.subplot(4, 2, 6)
            for category in top_5_categories:
                cat_data = df_monthly[df_monthly['Category'] == category].groupby('Date')['UnitsSold'].sum()
                ax6.plot(cat_data.index, cat_data.values, marker='s', label=category[:20], linewidth=2)
            ax6.set_xlabel('Month')
            ax6.set_ylabel('Units Sold')
            ax6.set_title('Units Sold Trend - Top 5 Categories', fontsize=14, fontweight='bold')
            ax6.legend(loc='best', fontsize=8)
            ax6.tick_params(axis='x', rotation=45)
            
            # 7. Growth Rate Analysis
            ax7 = plt.subplot(4, 2, 7)
            growth_data = []
            for category in top_10_categories:
                cat_monthly = df_monthly[df_monthly['Category'] == category].sort_values('Date')
                if len(cat_monthly) >= 6:
                    first_half = cat_monthly.head(6)['Revenue'].sum()
                    second_half = cat_monthly.tail(6)['Revenue'].sum()
                    if first_half > 0:
                        growth = ((second_half - first_half) / first_half) * 100
                        growth_data.append({'Category': category, 'Growth': growth})
            
            if growth_data:
                growth_df = pd.DataFrame(growth_data).sort_values('Growth')
                colors = ['red' if x < 0 else 'green' for x in growth_df['Growth']]
                bars = ax7.barh(range(len(growth_df)), growth_df['Growth'].values, color=colors)
                ax7.set_yticks(range(len(growth_df)))
                ax7.set_yticklabels([cat[:20] for cat in growth_df['Category']])
                ax7.set_xlabel('Growth Rate (%)')
                ax7.set_title('6-Month Growth Rate Comparison', fontsize=14, fontweight='bold')
                ax7.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
                # Add value labels
                for i, (bar, val) in enumerate(zip(bars, growth_df['Growth'].values)):
                    ax7.text(val, i, f' {val:.1f}%', va='center', 
                            ha='left' if val > 0 else 'right')
            
            # 8. Transaction Count Trend
            ax8 = plt.subplot(4, 2, 8)
            monthly_trans = df_monthly.groupby('Date')['Transactions'].sum()
            ax8.plot(monthly_trans.index, monthly_trans.values, marker='o', linewidth=2, color='navy')
            ax8.fill_between(monthly_trans.index, monthly_trans.values, alpha=0.3)
            ax8.set_xlabel('Month')
            ax8.set_ylabel('Number of Transactions')
            ax8.set_title('Total Transactions Trend (All Categories)', fontsize=14, fontweight='bold')
            ax8.tick_params(axis='x', rotation=45)
            ax8.grid(True, alpha=0.3)
            
            plt.suptitle('Category Performance Analysis - Trailing Twelve Months', 
                        fontsize=16, fontweight='bold', y=1.02)
            plt.tight_layout()
            
            # Save the chart
            chart_file = f'category_performance_charts_{timestamp}.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            logger.info(f"Charts saved to {chart_file}")
            
            # Create detailed Excel report
            excel_file = f'category_performance_ttm_{timestamp}.xlsx'
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Summary sheet
                summary = df_top.copy()
                summary['Revenue_Share_%'] = (summary['TotalRevenue'] / summary['TotalRevenue'].sum() * 100).round(2)
                summary['Avg_Transaction_Value'] = (summary['TotalRevenue'] / summary['TotalTransactions']).round(2)
                summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # Monthly trends
                pivot_monthly = df_monthly.pivot_table(
                    index='Date', 
                    columns='Category', 
                    values='Revenue', 
                    aggfunc='sum'
                ).fillna(0)
                pivot_monthly.to_excel(writer, sheet_name='Monthly Revenue')
                
                # Margin analysis
                margin_analysis = df_monthly.groupby('Category').agg({
                    'Revenue': 'sum',
                    'GrossProfit': 'sum',
                    'MarginPercent': 'mean',
                    'UnitsSold': 'sum',
                    'Transactions': 'sum'
                }).round(2).sort_values('Revenue', ascending=False)
                margin_analysis.to_excel(writer, sheet_name='Margin Analysis')
                
                # Growth metrics
                if growth_data:
                    pd.DataFrame(growth_data).sort_values('Growth', ascending=False).to_excel(
                        writer, sheet_name='Growth Rates', index=False
                    )
            
            # Print summary
            print("\n" + "="*80)
            print("CATEGORY PERFORMANCE ANALYSIS - TTM")
            print("="*80)
            print(f"Period: {start_date_str} to {end_date_str}")
            print(f"Total Revenue: ${df_monthly['Revenue'].sum():,.2f}")
            print(f"Total Categories: {df_monthly['Category'].nunique()}")
            
            print("\n📊 TOP 5 CATEGORIES BY REVENUE:")
            for idx, row in df_top.head(5).iterrows():
                share = row['TotalRevenue'] / df_top['TotalRevenue'].sum() * 100
                print(f"  {idx+1}. {row['Category'][:30]:<30} ${row['TotalRevenue']:>12,.0f} ({share:>5.1f}%)")
            
            print("\n📈 GROWTH LEADERS (6-month comparison):")
            if growth_data:
                growth_df_sorted = pd.DataFrame(growth_data).sort_values('Growth', ascending=False)
                for _, row in growth_df_sorted.head(5).iterrows():
                    if row['Growth'] > 0:
                        print(f"  • {row['Category'][:30]:<30} +{row['Growth']:>6.1f}%")
            
            print("\n💰 HIGHEST MARGIN CATEGORIES:")
            high_margin = margin_analysis.nlargest(5, 'MarginPercent')
            for cat, row in high_margin.iterrows():
                print(f"  • {cat[:30]:<30} {row['MarginPercent']:>6.1f}%")
            
            print(f"\n📊 FILES GENERATED:")
            print(f"  • Charts: {chart_file}")
            print(f"  • Excel Report: {excel_file}")
            
            return chart_file, excel_file
            
    except Exception as e:
        logger.error(f"Error analyzing category performance: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    chart_file, excel_file = analyze_category_performance_ttm()
    
    if chart_file:
        print("\n✅ Analysis completed successfully!")
        print(f"📊 View charts in: {chart_file}")
        print(f"📈 Detailed data in: {excel_file}")
    else:
        print("\n❌ Analysis failed. Please check the logs.")