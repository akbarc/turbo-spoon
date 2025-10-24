#!/usr/bin/env python3
"""
Advanced Cigarette Analytics & Ordering Intelligence
Comprehensive analysis with actionable insights
"""

from database_pymssql import SQLServerConnection
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class AdvancedCigaretteAnalytics:
    def __init__(self):
        self.db = SQLServerConnection()
        
    def run_comprehensive_analysis(self):
        """Run complete analysis across multiple dimensions"""
        
        # 1. Brand Performance Analysis
        brand_query = """
        WITH BrandAnalysis AS (
            SELECT 
                -- Extract brand from description
                CASE 
                    WHEN Description LIKE 'NEWPORT%' THEN 'NEWPORT'
                    WHEN Description LIKE 'MARL%' THEN 'MARLBORO'
                    WHEN Description LIKE '24/7%' THEN '24/7'
                    WHEN Description LIKE 'CAMEL%' THEN 'CAMEL'
                    WHEN Description LIKE 'AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                    WHEN Description LIKE 'PALL MALL%' THEN 'PALL MALL'
                    WHEN Description LIKE 'KOOL%' THEN 'KOOL'
                    WHEN Description LIKE 'BASIC%' THEN 'BASIC'
                    WHEN Description LIKE 'MAVERICK%' THEN 'MAVERICK'
                    WHEN Description LIKE 'WINSTON%' THEN 'WINSTON'
                    WHEN Description LIKE 'LUCKY STRIKE%' THEN 'LUCKY STRIKE'
                    WHEN Description LIKE 'SENECA%' THEN 'SENECA'
                    WHEN Description LIKE 'MONTEGO%' THEN 'MONTEGO'
                    WHEN Description LIKE 'CROWNS%' THEN 'CROWNS'
                    WHEN Description LIKE 'LD%' THEN 'LD'
                    WHEN Description LIKE 'VIRGINIA SLIMS%' THEN 'VIRGINIA SLIMS'
                    WHEN Description LIKE 'PARLIAMENT%' THEN 'PARLIAMENT'
                    ELSE 'OTHER'
                END as Brand,
                i.Description,
                i.ItemLookupCode as SKU,
                i.Quantity as CurrentStock,
                te.Quantity as UnitsSold,
                te.Price - te.Cost as Margin,
                t.Time as SaleDate,
                DATEPART(week, t.Time) as WeekNum,
                DATEPART(month, t.Time) as MonthNum,
                -- Customer segment
                CASE 
                    WHEN cust.Company IS NOT NULL AND LEN(cust.Company) > 2 THEN 'WHOLESALE'
                    ELSE 'RETAIL'
                END as CustomerType
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            LEFT JOIN dbo.Customer cust ON t.CustomerID = cust.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(month, -6, GETDATE())
              AND i.Inactive = 0
        )
        SELECT 
            Brand,
            COUNT(DISTINCT SKU) as SKU_Count,
            SUM(UnitsSold) as Total_Units_6mo,
            SUM(UnitsSold * Margin) as Total_Profit_6mo,
            AVG(Margin) as Avg_Margin,
            SUM(CASE WHEN CustomerType = 'WHOLESALE' THEN UnitsSold ELSE 0 END) * 100.0 / SUM(UnitsSold) as Wholesale_Pct,
            SUM(CASE WHEN CustomerType = 'RETAIL' THEN UnitsSold ELSE 0 END) * 100.0 / SUM(UnitsSold) as Retail_Pct,
            -- Monthly trend
            SUM(CASE WHEN MonthNum = MONTH(GETDATE()) THEN UnitsSold ELSE 0 END) as Current_Month,
            SUM(CASE WHEN MonthNum = MONTH(DATEADD(month, -1, GETDATE())) THEN UnitsSold ELSE 0 END) as Last_Month,
            SUM(CASE WHEN MonthNum = MONTH(DATEADD(month, -2, GETDATE())) THEN UnitsSold ELSE 0 END) as Two_Months_Ago
        FROM BrandAnalysis
        GROUP BY Brand
        ORDER BY Total_Units_6mo DESC
        """
        
        # 2. Day of Week Pattern Analysis
        dow_query = """
        SELECT 
            DATENAME(weekday, t.Time) as DayOfWeek,
            DATEPART(weekday, t.Time) as DayNum,
            COUNT(DISTINCT t.TransactionNumber) as Transaction_Count,
            SUM(te.Quantity) as Total_Units,
            AVG(te.Quantity) as Avg_Units_Per_Transaction,
            SUM(te.Price - te.Cost) as Total_Profit
        FROM dbo.Item i
        JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE c.Name = 'CIGARETTE'
          AND t.Time >= DATEADD(week, -8, GETDATE())
        GROUP BY DATENAME(weekday, t.Time), DATEPART(weekday, t.Time)
        ORDER BY DayNum
        """
        
        # 3. Stock-out Risk Analysis
        stockout_query = """
        WITH RecentMovement AS (
            SELECT 
                i.ID,
                i.Description,
                i.ItemLookupCode as SKU,
                i.Quantity as CurrentStock,
                -- Weekly averages
                SUM(te.Quantity) / 8.0 as Avg_Weekly_Sales,
                STDEV(te.Quantity) as Sales_StdDev,
                MAX(te.Quantity) as Max_Daily_Sales,
                -- Calculate coefficient of variation
                CASE 
                    WHEN AVG(CAST(te.Quantity as float)) > 0 
                    THEN STDEV(te.Quantity) / AVG(CAST(te.Quantity as float))
                    ELSE 0 
                END as CV,
                -- Last purchase info
                (SELECT TOP 1 po.DateCreated 
                 FROM dbo.PurchaseOrder po
                 JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
                 WHERE poe.ItemID = i.ID
                 ORDER BY po.DateCreated DESC) as Last_Order_Date,
                -- Average delivery time (default to 3 days)
                3 as Avg_Lead_Time
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(week, -8, GETDATE())
              AND i.Inactive = 0
            GROUP BY i.ID, i.Description, i.ItemLookupCode, i.Quantity
        )
        SELECT 
            Description,
            SKU,
            CurrentStock,
            ROUND(Avg_Weekly_Sales, 1) as Weekly_Sales,
            ROUND(Sales_StdDev, 1) as Sales_Volatility,
            ROUND(CV, 2) as Coefficient_Variation,
            -- Calculate days until stockout
            CASE 
                WHEN Avg_Weekly_Sales > 0 THEN ROUND(CurrentStock / (Avg_Weekly_Sales / 7.0), 1)
                ELSE 999
            END as Days_Until_Stockout,
            -- Risk score (0-100)
            CASE
                WHEN CurrentStock <= 0 THEN 100
                WHEN Avg_Weekly_Sales > 0 AND CurrentStock / (Avg_Weekly_Sales / 7.0) <= 3 THEN 90
                WHEN Avg_Weekly_Sales > 0 AND CurrentStock / (Avg_Weekly_Sales / 7.0) <= 7 THEN 70
                WHEN Avg_Weekly_Sales > 0 AND CurrentStock / (Avg_Weekly_Sales / 7.0) <= 14 THEN 50
                WHEN Avg_Weekly_Sales > 0 AND CurrentStock / (Avg_Weekly_Sales / 7.0) <= 21 THEN 30
                ELSE 10
            END as Risk_Score,
            ISNULL(Avg_Lead_Time, 3) as Lead_Time_Days,
            -- Recommended order point (lead time + safety stock)
            CEILING(Avg_Weekly_Sales / 7.0 * (ISNULL(Avg_Lead_Time, 3) + 7) + Sales_StdDev * 2) as Reorder_Point,
            -- Economic order quantity approximation
            CEILING(SQRT(2 * Avg_Weekly_Sales * 52 * 10 / (0.2 * CurrentStock + 1))) as EOQ
        FROM RecentMovement
        WHERE Avg_Weekly_Sales > 0
        ORDER BY Risk_Score DESC, Weekly_Sales DESC
        """
        
        # 4. Price Analysis (simplified for SQL 2008)
        elasticity_query = """
        SELECT 
            i.Description,
            COUNT(DISTINCT te.Price) as Price_Points,
            MIN(te.Price) as Min_Price,
            MAX(te.Price) as Max_Price,
            AVG(te.Price) as Avg_Price,
            STDEV(te.Price) as Price_StdDev,
            AVG(te.Quantity) as Avg_Quantity,
            SUM(te.Quantity * (te.Price - te.Cost)) as Total_Profit
        FROM dbo.Item i
        JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE c.Name = 'CIGARETTE'
          AND t.Time >= DATEADD(month, -3, GETDATE())
        GROUP BY i.Description
        HAVING COUNT(*) > 10
        ORDER BY Total_Profit DESC
        """
        
        # Execute all queries
        brand_data = self.db.execute_query(brand_query, [], 'Brand Performance Analysis')
        dow_data = self.db.execute_query(dow_query, [], 'Day of Week Analysis')
        stockout_data = self.db.execute_query(stockout_query, [], 'Stock-out Risk Analysis')
        elasticity_data = self.db.execute_query(elasticity_query, [], 'Price Elasticity Analysis')
        
        return {
            'brand_performance': brand_data,
            'day_patterns': dow_data,
            'stockout_risk': stockout_data,
            'price_elasticity': elasticity_data
        }
    
    def generate_intelligent_order(self, analytics_data):
        """Generate order with intelligent recommendations"""
        
        stockout_data = analytics_data['stockout_risk']
        
        # Filter items needing orders (risk score > 50 or days until stockout < 7)
        items_to_order = stockout_data[
            (stockout_data['Risk_Score'] >= 50) | 
            (stockout_data['Days_Until_Stockout'] < 7)
        ].copy()
        
        # Calculate intelligent order quantities
        items_to_order['Smart_Order_Qty'] = items_to_order.apply(
            lambda row: max(
                row['Reorder_Point'] - row['CurrentStock'],  # To reach reorder point
                row['Weekly_Sales'],  # At least 1 week supply
                row['EOQ'] if row['Risk_Score'] >= 70 else row['Weekly_Sales'] * 1.5  # EOQ for high risk
            ), axis=1
        )
        
        return items_to_order
    
    def generate_comprehensive_report(self, analytics_data, order_data):
        """Generate comprehensive analysis report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create detailed JSON report
        report = {
            'generated_at': datetime.now().isoformat(),
            'executive_summary': {},
            'brand_insights': [],
            'operational_insights': [],
            'financial_insights': [],
            'recommendations': []
        }
        
        # Brand Performance Insights
        brand_data = analytics_data['brand_performance']
        top_brands = brand_data.head(5)
        
        report['brand_insights'] = [
            {
                'brand': row['Brand'],
                'market_share': f"{row['Total_Units_6mo'] / brand_data['Total_Units_6mo'].sum() * 100:.1f}%",
                'units_sold_6mo': int(row['Total_Units_6mo']),
                'profit_6mo': f"${row['Total_Profit_6mo']:,.2f}",
                'avg_margin': f"${row['Avg_Margin']:.2f}",
                'wholesale_mix': f"{row['Wholesale_Pct']:.1f}%",
                'trend': 'UP' if row['Current_Month'] > row['Last_Month'] else 'DOWN',
                'month_over_month': f"{(row['Current_Month'] / row['Last_Month'] - 1) * 100:.1f}%" if row['Last_Month'] > 0 else 'N/A'
            }
            for _, row in top_brands.iterrows()
        ]
        
        # Day of Week Patterns
        dow_data = analytics_data['day_patterns']
        peak_day = dow_data.loc[dow_data['Total_Units'].idxmax()]
        low_day = dow_data.loc[dow_data['Total_Units'].idxmin()]
        
        report['operational_insights'].append({
            'type': 'Sales Patterns',
            'peak_day': peak_day['DayOfWeek'],
            'peak_units': int(peak_day['Total_Units']),
            'low_day': low_day['DayOfWeek'],
            'low_units': int(low_day['Total_Units']),
            'weekend_vs_weekday': f"{dow_data[dow_data['DayNum'].isin([1,7])]['Total_Units'].sum() / dow_data[dow_data['DayNum'].isin([2,3,4,5,6])]['Total_Units'].sum() * 100:.1f}% of weekday sales"
        })
        
        # Stock-out Risk Summary
        stockout_data = analytics_data['stockout_risk']
        critical_items = stockout_data[stockout_data['Risk_Score'] >= 90]
        high_risk = stockout_data[stockout_data['Risk_Score'] >= 70]
        
        report['operational_insights'].append({
            'type': 'Inventory Risk',
            'critical_stockouts': len(critical_items),
            'high_risk_items': len(high_risk),
            'avg_days_coverage': stockout_data[stockout_data['Days_Until_Stockout'] < 999]['Days_Until_Stockout'].mean(),
            'items_below_reorder_point': len(stockout_data[stockout_data['CurrentStock'] < stockout_data['Reorder_Point']])
        })
        
        # Financial Summary
        if not order_data.empty:
            total_order_value = (order_data['Smart_Order_Qty'] * order_data['Weekly_Sales'] * 8.5).sum()  # Approximate value
            
            report['financial_insights'] = [
                {'metric': 'Recommended Order Value', 'value': f"${total_order_value:,.2f}"},
                {'metric': 'Items to Order', 'value': len(order_data)},
                {'metric': 'Total Units', 'value': f"{order_data['Smart_Order_Qty'].sum():,.0f}"},
                {'metric': 'Avg Risk Score', 'value': f"{order_data['Risk_Score'].mean():.1f}"}
            ]
        
        # Smart Recommendations
        recommendations = []
        
        # Brand recommendations
        declining_brands = brand_data[brand_data['Current_Month'] < brand_data['Two_Months_Ago'] * 0.8]
        if not declining_brands.empty:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Brand Management',
                'action': f"Review pricing/promotion for declining brands: {', '.join(declining_brands['Brand'].head(3))}",
                'impact': 'Potential to recover 10-15% sales volume'
            })
        
        # Inventory recommendations
        if len(critical_items) > 5:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Inventory',
                'action': f"Immediate reorder needed for {len(critical_items)} items at critical stock levels",
                'impact': f"Prevent stockouts affecting ${critical_items['Weekly_Sales'].sum() * 9:.0f}/week in sales"
            })
        
        # Volatility recommendations
        high_volatility = stockout_data[stockout_data['Coefficient_Variation'] > 1.0]
        if len(high_volatility) > 10:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Forecasting',
                'action': f"Increase safety stock for {len(high_volatility)} high-volatility items",
                'impact': 'Reduce stockout risk by 30-40%'
            })
        
        # Day of week recommendation
        if peak_day['Total_Units'] > low_day['Total_Units'] * 2:
            recommendations.append({
                'priority': 'LOW',
                'category': 'Operations',
                'action': f"Ensure extra staff/inventory for {peak_day['DayOfWeek']} (peak day)",
                'impact': f"Better service for {int(peak_day['Total_Units'] - dow_data['Total_Units'].mean())} extra units"
            })
        
        report['recommendations'] = recommendations
        
        # Save reports
        json_filename = f"cigarette_analytics_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        csv_filename = f"cigarette_smart_order_{timestamp}.csv"
        if not order_data.empty:
            order_data.to_csv(csv_filename, index=False)
        
        return report, json_filename, csv_filename
    
    def print_executive_dashboard(self, report):
        """Print executive dashboard view"""
        
        print("\n" + "="*100)
        print("🎯 CIGARETTE INVENTORY INTELLIGENCE DASHBOARD")
        print("="*100)
        
        print("\n📊 TOP 5 BRAND PERFORMANCE (6-Month Analysis)")
        print("-"*80)
        print(f"{'Brand':<20} {'Market Share':<15} {'Profit':<15} {'Trend':<10} {'MoM Change':<15}")
        print("-"*80)
        for brand in report['brand_insights'][:5]:
            trend_symbol = "📈" if brand['trend'] == 'UP' else "📉"
            print(f"{brand['brand']:<20} {brand['market_share']:<15} {brand['profit_6mo']:<15} {trend_symbol:<10} {brand['month_over_month']:<15}")
        
        print("\n⚠️  INVENTORY RISK ASSESSMENT")
        print("-"*80)
        for insight in report['operational_insights']:
            if insight['type'] == 'Inventory Risk':
                print(f"🔴 Critical Stockouts: {insight['critical_stockouts']} items")
                print(f"🟡 High Risk Items: {insight['high_risk_items']} items")
                print(f"📅 Average Days Coverage: {insight['avg_days_coverage']:.1f} days")
                print(f"📦 Below Reorder Point: {insight['items_below_reorder_point']} items")
        
        print("\n📈 SALES PATTERNS (Last 8 Weeks)")
        print("-"*80)
        for insight in report['operational_insights']:
            if insight['type'] == 'Sales Patterns':
                print(f"Peak Day: {insight['peak_day']} ({insight['peak_units']:,} units)")
                print(f"Low Day: {insight['low_day']} ({insight['low_units']:,} units)")
                print(f"Weekend Performance: {insight['weekend_vs_weekday']}")
        
        print("\n💰 FINANCIAL SUMMARY")
        print("-"*80)
        for metric in report.get('financial_insights', []):
            print(f"{metric['metric']:<30} {metric['value']:>20}")
        
        print("\n🎯 STRATEGIC RECOMMENDATIONS")
        print("-"*80)
        for i, rec in enumerate(report['recommendations'], 1):
            priority_symbol = {"CRITICAL": "🔴", "HIGH": "🟡", "MEDIUM": "🟠", "LOW": "🟢"}.get(rec['priority'], "⚪")
            print(f"\n{i}. {priority_symbol} [{rec['priority']}] {rec['category']}")
            print(f"   Action: {rec['action']}")
            print(f"   Impact: {rec['impact']}")
        
        print("\n" + "="*100)

def main():
    analytics = AdvancedCigaretteAnalytics()
    
    print("🔍 Running Comprehensive Cigarette Analytics...")
    print("Analyzing: Brand Performance | Stock Risk | Sales Patterns | Price Elasticity")
    
    # Run analysis
    analytics_data = analytics.run_comprehensive_analysis()
    
    # Generate intelligent order
    order_data = analytics.generate_intelligent_order(analytics_data)
    
    # Generate comprehensive report
    report, json_file, csv_file = analytics.generate_comprehensive_report(analytics_data, order_data)
    
    # Print executive dashboard
    analytics.print_executive_dashboard(report)
    
    print(f"\n📁 Detailed Reports Saved:")
    print(f"   • Analytics Report: {json_file}")
    print(f"   • Order List: {csv_file}")

if __name__ == '__main__':
    main()