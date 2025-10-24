#!/usr/bin/env python3
"""
Smart Cigarette Order Generator with Trend Analysis
Uses 12-month history with weighted recent performance
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime
import numpy as np

class SmartCigaretteOrder:
    def __init__(self):
        self.db = SQLServerConnection()
        
    def analyze_and_order(self):
        """Analyze 12 months of data with weighted recent trends"""
        
        query = """
        WITH MonthlyData AS (
            -- Get monthly sales for last 12 months
            SELECT 
                i.ID as ItemID,
                i.Description,
                i.ItemLookupCode as SKU,
                i.Quantity as current_stock,
                YEAR(t.Time) as sale_year,
                MONTH(t.Time) as sale_month,
                SUM(te.Quantity) as monthly_sales
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(month, -12, GETDATE())
              AND i.Inactive = 0
            GROUP BY i.ID, i.Description, i.ItemLookupCode, i.Quantity, 
                     YEAR(t.Time), MONTH(t.Time)
        ),
        WeeklyRecent AS (
            -- Get weekly data for last 8 weeks (more granular recent data)
            SELECT 
                i.ID as ItemID,
                DATEPART(week, t.Time) as week_num,
                SUM(te.Quantity) as weekly_sales
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(week, -8, GETDATE())
              AND i.Inactive = 0
            GROUP BY i.ID, DATEPART(week, t.Time)
        ),
        Analysis AS (
            SELECT 
                md.ItemID,
                md.Description,
                md.SKU,
                md.current_stock,
                
                -- 12-month average (baseline)
                AVG(md.monthly_sales) / 4.33 as avg_weekly_12mo,
                
                -- Last 3 months average (recent trend)
                (SELECT AVG(monthly_sales) / 4.33 
                 FROM MonthlyData md2 
                 WHERE md2.ItemID = md.ItemID 
                   AND md2.sale_year * 100 + md2.sale_month >= 
                       YEAR(DATEADD(month, -3, GETDATE())) * 100 + MONTH(DATEADD(month, -3, GETDATE()))
                ) as avg_weekly_3mo,
                
                -- Last 8 weeks average (most recent)
                (SELECT AVG(weekly_sales) 
                 FROM WeeklyRecent wr 
                 WHERE wr.ItemID = md.ItemID
                ) as avg_weekly_8wk,
                
                -- Peak week in last 8 weeks
                (SELECT MAX(weekly_sales) 
                 FROM WeeklyRecent wr 
                 WHERE wr.ItemID = md.ItemID
                ) as peak_week_recent,
                
                -- Minimum week in last 8 weeks
                (SELECT MIN(weekly_sales) 
                 FROM WeeklyRecent wr 
                 WHERE wr.ItemID = md.ItemID
                ) as min_week_recent,
                
                -- Standard deviation for volatility
                (SELECT STDEV(weekly_sales) 
                 FROM WeeklyRecent wr 
                 WHERE wr.ItemID = md.ItemID
                ) as weekly_stdev,
                
                -- Month-over-month growth (last 3 months)
                (SELECT 
                    CASE 
                        WHEN COUNT(*) >= 2 THEN
                            (MAX(CASE WHEN rn = 1 THEN monthly_sales END) - 
                             MAX(CASE WHEN rn = 3 THEN monthly_sales END)) / 
                            NULLIF(MAX(CASE WHEN rn = 3 THEN monthly_sales END), 0) * 100
                        ELSE 0
                    END
                 FROM (
                    SELECT monthly_sales,
                           ROW_NUMBER() OVER (ORDER BY sale_year DESC, sale_month DESC) as rn
                    FROM MonthlyData md3
                    WHERE md3.ItemID = md.ItemID
                 ) recent_months
                 WHERE rn <= 3
                ) as three_month_growth_pct,
                
                -- Get cost for calculations
                (SELECT TOP 1 poe.Price
                 FROM dbo.PurchaseOrderEntry poe
                 JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
                 WHERE poe.ItemID = md.ItemID
                 ORDER BY po.DateCreated DESC) as unit_cost,
                 
                -- Get margin data
                (SELECT AVG(te2.Price - te2.Cost)
                 FROM dbo.TransactionEntry te2
                 JOIN [dbo].[Transaction] t2 ON te2.TransactionNumber = t2.TransactionNumber
                 WHERE te2.ItemID = md.ItemID
                   AND t2.Time >= DATEADD(week, -8, GETDATE())
                ) as avg_margin
                
            FROM MonthlyData md
            GROUP BY md.ItemID, md.Description, md.SKU, md.current_stock
        )
        SELECT 
            Description,
            SKU,
            current_stock,
            
            -- Weighted average: 50% last 8 weeks, 30% last 3 months, 20% last 12 months
            ROUND(
                COALESCE(avg_weekly_8wk, 0) * 0.5 + 
                COALESCE(avg_weekly_3mo, 0) * 0.3 + 
                COALESCE(avg_weekly_12mo, 0) * 0.2, 
            1) as weighted_weekly_avg,
            
            -- Calculate suggested order (1 week + safety stock based on volatility)
            CEILING(
                (COALESCE(avg_weekly_8wk, 0) * 0.5 + 
                 COALESCE(avg_weekly_3mo, 0) * 0.3 + 
                 COALESCE(avg_weekly_12mo, 0) * 0.2) * 
                (1 + COALESCE(weekly_stdev, 0) / NULLIF(avg_weekly_8wk, 0) * 0.2)
            ) as suggested_order,
            
            -- Trend indicators
            CASE 
                WHEN three_month_growth_pct > 10 THEN 'UP ↑'
                WHEN three_month_growth_pct < -10 THEN 'DOWN ↓'
                ELSE 'STABLE →'
            END as trend,
            
            ROUND(three_month_growth_pct, 1) as growth_pct,
            
            -- Performance metrics
            ROUND(avg_weekly_8wk, 1) as last_8wk_avg,
            ROUND(avg_weekly_3mo, 1) as last_3mo_avg,
            ROUND(avg_weekly_12mo, 1) as last_12mo_avg,
            ROUND(peak_week_recent, 0) as peak_week,
            ROUND(min_week_recent, 0) as min_week,
            
            -- Volatility indicator
            CASE 
                WHEN weekly_stdev / NULLIF(avg_weekly_8wk, 0) > 0.5 THEN 'HIGH'
                WHEN weekly_stdev / NULLIF(avg_weekly_8wk, 0) > 0.25 THEN 'MED'
                ELSE 'LOW'
            END as volatility,
            
            -- Stock coverage
            CASE 
                WHEN avg_weekly_8wk > 0 THEN ROUND(current_stock / avg_weekly_8wk, 1)
                ELSE 999
            END as weeks_coverage,
            
            -- Financial metrics
            ROUND(COALESCE(unit_cost, 0), 2) as unit_cost,
            ROUND(COALESCE(avg_margin, 0), 2) as margin,
            ROUND(COALESCE(avg_margin, 0) * COALESCE(avg_weekly_8wk, 0), 2) as weekly_profit
            
        FROM Analysis
        WHERE COALESCE(avg_weekly_8wk, 0) + COALESCE(avg_weekly_3mo, 0) + COALESCE(avg_weekly_12mo, 0) > 0
        ORDER BY 
            weighted_weekly_avg DESC,
            weekly_profit DESC
        """
        
        result = self.db.execute_query(query, [], 'Smart Cigarette Order Analysis')
        return result
    
    def generate_order_report(self, data):
        """Generate detailed order report with analysis"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cigarette_smart_order_{timestamp}.csv"
        
        # Convert decimal columns to float
        data['unit_cost'] = pd.to_numeric(data['unit_cost'], errors='coerce').fillna(0)
        data['margin'] = pd.to_numeric(data['margin'], errors='coerce').fillna(0)
        data['suggested_order'] = pd.to_numeric(data['suggested_order'], errors='coerce').fillna(0)
        
        # Calculate totals
        total_items = len(data)
        total_order_qty = data['suggested_order'].sum()
        total_value = (data['suggested_order'] * data['unit_cost']).sum()
        
        # Categorize items
        trending_up = data[data['growth_pct'] > 10]
        trending_down = data[data['growth_pct'] < -10]
        high_volume = data[data['weighted_weekly_avg'] > 50]
        low_stock = data[data['weeks_coverage'] < 1]
        high_margin = data.nlargest(20, 'margin')
        
        print("\n" + "="*80)
        print("📊 SMART CIGARETTE ORDER ANALYSIS - 1 WEEK SUPPLY")
        print("="*80)
        
        print(f"\n📈 MARKET TRENDS:")
        print(f"  • {len(trending_up)} items trending UP (>10% growth)")
        print(f"  • {len(trending_down)} items trending DOWN (<-10% decline)")
        print(f"  • {len(data[data['volatility'] == 'HIGH'])} items with HIGH volatility")
        
        print(f"\n📦 ORDER SUMMARY:")
        print(f"  • Total SKUs: {total_items}")
        print(f"  • Total Units: {total_order_qty:,.0f}")
        print(f"  • Total Value: ${total_value:,.2f}")
        print(f"  • Avg units/SKU: {total_order_qty/total_items:.1f}")
        
        print(f"\n⚠️  ATTENTION ITEMS:")
        print(f"  • {len(low_stock)} items with <1 week coverage")
        print(f"  • {len(high_volume)} high-volume items (>50/week)")
        
        # Export to CSV
        with open(filename, 'w') as f:
            # Header info
            f.write("SMART CIGARETTE ORDER - 1 WEEK SUPPLY\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Analysis based on 12-month trends, weighted toward recent 8 weeks\n")
            f.write(f"Total Order: {total_order_qty:,.0f} units, ${total_value:,.2f}\n\n")
            
            # Column headers with better formatting
            headers = [
                "Description", "SKU", "Order Qty", "Current Stock", "Weeks Cover",
                "8wk Avg", "3mo Avg", "12mo Avg", "Trend", "Growth %",
                "Peak Wk", "Min Wk", "Volatility", "Unit Cost", "Margin", "Weekly Profit"
            ]
            f.write(",".join(headers) + "\n")
            
            # Write data
            for _, row in data.iterrows():
                line = [
                    row['Description'],
                    row['SKU'],
                    f"{row['suggested_order']:.0f}",
                    f"{row['current_stock']:.0f}",
                    f"{row['weeks_coverage']:.1f}",
                    f"{row['last_8wk_avg']:.1f}",
                    f"{row['last_3mo_avg']:.1f}",
                    f"{row['last_12mo_avg']:.1f}",
                    row['trend'],
                    f"{row['growth_pct']:.1f}%",
                    f"{row['peak_week']:.0f}",
                    f"{row['min_week']:.0f}",
                    row['volatility'],
                    f"${row['unit_cost']:.2f}",
                    f"${row['margin']:.2f}",
                    f"${row['weekly_profit']:.2f}"
                ]
                f.write(",".join(str(x) for x in line) + "\n")
        
        print(f"\n💡 TOP TRENDING UP (Fastest Growing):")
        for _, item in trending_up.head(5).iterrows():
            print(f"  • {item['Description'][:40]:<40} +{item['growth_pct']:.1f}% growth")
        
        print(f"\n📉 TOP TRENDING DOWN (Declining):")
        for _, item in trending_down.head(5).iterrows():
            print(f"  • {item['Description'][:40]:<40} {item['growth_pct']:.1f}% decline")
        
        print(f"\n💰 HIGHEST MARGIN ITEMS:")
        for _, item in high_margin.head(5).iterrows():
            print(f"  • {item['Description'][:40]:<40} ${item['margin']:.2f}/unit, ${item['weekly_profit']:.2f}/week")
        
        print(f"\n✅ Order saved to: {filename}")
        print("\nWeighting Formula: 50% last 8 weeks + 30% last 3 months + 20% last 12 months")
        print("Safety stock adjusted based on sales volatility")
        
        return filename

def main():
    order_system = SmartCigaretteOrder()
    
    print("🚬 GENERATING SMART CIGARETTE ORDER")
    print("Analyzing 12 months of data with weighted recent performance...")
    
    # Analyze and generate order
    order_data = order_system.analyze_and_order()
    
    if order_data.empty:
        print("❌ No data available")
        return
    
    # Generate report
    filename = order_system.generate_order_report(order_data)
    
    print("\n📋 Order ready for review and submission")

if __name__ == '__main__':
    main()