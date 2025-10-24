"""
Advanced Analytics Engine for Sales Dashboard
Comprehensive business intelligence and predictive analytics
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
analytics_api = Blueprint('analytics_api', __name__, url_prefix='/api/v2/analytics')

@analytics_api.route('/inventory-intelligence')
def inventory_intelligence():
    """Advanced inventory analysis with predictive insights"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Multi-dimensional inventory analysis
        query = """
        WITH InventoryMetrics AS (
            SELECT
                i.ID,
                i.Description as ProductName,
                c.Name as Category,
                i.Quantity as CurrentStock,
                i.ReorderPoint,
                i.ReorderQuantity,
                i.Cost as UnitCost,
                i.SalePrice,
                i.SalePrice - i.Cost as UnitProfit,
                (i.SalePrice - i.Cost) / NULLIF(i.Cost, 0) * 100 as MarkupPercent,
                -- Calculate velocity
                (SELECT COUNT(*) FROM dbo.TransactionEntry te
                 WHERE te.ItemID = i.ID AND te.TransactionNumber IN
                    (SELECT TransactionNumber FROM [dbo].[Transaction]
                     WHERE Time >= DATEADD(DAY, -30, GETDATE()))) as Sales30Days,
                -- Calculate average daily sales
                (SELECT AVG(te.Quantity) FROM dbo.TransactionEntry te
                 WHERE te.ItemID = i.ID AND te.TransactionNumber IN
                    (SELECT TransactionNumber FROM [dbo].[Transaction]
                     WHERE Time >= DATEADD(DAY, -30, GETDATE()))) as AvgDailySales,
                -- Last sale date
                (SELECT MAX(t.Time) FROM [dbo].[Transaction] t
                 JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                 WHERE te.ItemID = i.ID) as LastSaleDate,
                -- Last purchase date
                (SELECT MAX(po.Date) FROM dbo.PurchaseOrder po
                 JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
                 WHERE poe.ItemID = i.ID) as LastPurchaseDate
            FROM dbo.Item i
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE i.Quantity IS NOT NULL
        ),
        AnalyzedInventory AS (
            SELECT
                *,
                -- Days of supply
                CASE
                    WHEN AvgDailySales > 0 THEN CurrentStock / AvgDailySales
                    ELSE 999
                END as DaysOfSupply,
                -- Stock status
                CASE
                    WHEN CurrentStock <= 0 THEN 'Out of Stock'
                    WHEN CurrentStock <= ReorderPoint THEN 'Critical'
                    WHEN CurrentStock <= ReorderPoint * 1.5 THEN 'Low'
                    WHEN CurrentStock > ReorderPoint * 5 THEN 'Overstock'
                    ELSE 'Healthy'
                END as StockStatus,
                -- Turnover rate (annualized)
                CASE
                    WHEN CurrentStock > 0 AND Sales30Days > 0 THEN
                        (Sales30Days * 12.0) / CurrentStock
                    ELSE 0
                END as TurnoverRate,
                -- Days since last sale
                DATEDIFF(DAY, LastSaleDate, GETDATE()) as DaysSinceLastSale,
                -- Stock value
                CurrentStock * UnitCost as StockValue,
                -- Potential revenue
                CurrentStock * SalePrice as PotentialRevenue,
                -- Dead stock risk
                CASE
                    WHEN DATEDIFF(DAY, LastSaleDate, GETDATE()) > 90 THEN 'High'
                    WHEN DATEDIFF(DAY, LastSaleDate, GETDATE()) > 60 THEN 'Medium'
                    WHEN DATEDIFF(DAY, LastSaleDate, GETDATE()) > 30 THEN 'Low'
                    ELSE 'None'
                END as DeadStockRisk
            FROM InventoryMetrics
        )
        SELECT * FROM AnalyzedInventory
        ORDER BY StockValue DESC
        """

        result = db.execute_query(query)

        # Aggregate metrics
        total_value = result['StockValue'].sum()
        total_potential = result['PotentialRevenue'].sum()

        # Critical items
        critical_items = result[result['StockStatus'].isin(['Critical', 'Out of Stock'])]
        overstock_items = result[result['StockStatus'] == 'Overstock']
        dead_stock = result[result['DeadStockRisk'].isin(['High', 'Medium'])]

        # Calculate optimal reorder points using safety stock formula
        reorder_suggestions = []
        for _, item in critical_items.head(10).iterrows():
            if item['AvgDailySales'] and item['AvgDailySales'] > 0:
                lead_time = 3  # Assumed 3-day lead time
                safety_stock = item['AvgDailySales'] * lead_time * 1.5  # 50% safety factor
                optimal_reorder = item['AvgDailySales'] * lead_time + safety_stock

                reorder_suggestions.append({
                    'product': item['ProductName'],
                    'current_stock': int(item['CurrentStock']),
                    'days_remaining': round(item['DaysOfSupply'], 1),
                    'suggested_order': int(max(optimal_reorder - item['CurrentStock'], item['ReorderQuantity'])),
                    'urgency': 'HIGH' if item['DaysOfSupply'] < 3 else 'MEDIUM'
                })

        # ABC Analysis
        sorted_items = result.sort_values('Sales30Days', ascending=False)
        total_sales = sorted_items['Sales30Days'].sum()

        abc_analysis = {
            'A': {'count': 0, 'value': 0, 'items': []},
            'B': {'count': 0, 'value': 0, 'items': []},
            'C': {'count': 0, 'value': 0, 'items': []}
        }

        cumulative_sales = 0
        for _, item in sorted_items.iterrows():
            cumulative_sales += item['Sales30Days']
            percentage = (cumulative_sales / total_sales * 100) if total_sales > 0 else 0

            if percentage <= 80:
                category = 'A'
            elif percentage <= 95:
                category = 'B'
            else:
                category = 'C'

            abc_analysis[category]['count'] += 1
            abc_analysis[category]['value'] += item['StockValue']
            if len(abc_analysis[category]['items']) < 5:
                abc_analysis[category]['items'].append(item['ProductName'])

        response = {
            'summary': {
                'total_skus': len(result),
                'total_value': float(total_value),
                'potential_revenue': float(total_potential),
                'avg_turnover': float(result['TurnoverRate'].mean()),
                'critical_items': len(critical_items),
                'overstock_items': len(overstock_items),
                'dead_stock_items': len(dead_stock),
                'dead_stock_value': float(dead_stock['StockValue'].sum())
            },
            'reorder_suggestions': reorder_suggestions,
            'abc_analysis': abc_analysis,
            'stock_health': {
                'healthy': len(result[result['StockStatus'] == 'Healthy']),
                'low': len(result[result['StockStatus'] == 'Low']),
                'critical': len(result[result['StockStatus'] == 'Critical']),
                'out_of_stock': len(result[result['StockStatus'] == 'Out of Stock']),
                'overstock': len(overstock_items)
            },
            'top_dead_stock': dead_stock.head(5)[['ProductName', 'CurrentStock', 'StockValue', 'DaysSinceLastSale']].to_dict('records')
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Inventory intelligence error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_api.route('/profit-optimization')
def profit_optimization():
    """Identify profit optimization opportunities"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Comprehensive profit analysis
        query = """
        WITH ProfitAnalysis AS (
            SELECT
                i.ID,
                i.Description as ProductName,
                c.Name as Category,
                i.Cost,
                i.SalePrice,
                i.SalePrice - i.Cost as UnitProfit,
                (i.SalePrice - i.Cost) / NULLIF(i.Cost, 0) * 100 as Margin,
                -- Sales data
                COUNT(DISTINCT te.TransactionNumber) as Transactions,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                AVG(te.Price) as AvgSellingPrice,
                MIN(te.Price) as MinPrice,
                MAX(te.Price) as MaxPrice,
                STDEV(te.Price) as PriceStdDev,
                -- Price elasticity indicator
                CASE
                    WHEN COUNT(DISTINCT te.Price) > 1 THEN
                        (MAX(te.Quantity) - MIN(te.Quantity)) / NULLIF(MAX(te.Price) - MIN(te.Price), 0)
                    ELSE 0
                END as PriceElasticity
            FROM dbo.Item i
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            LEFT JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            LEFT JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
            GROUP BY i.ID, i.Description, c.Name, i.Cost, i.SalePrice
        ),
        OpportunityAnalysis AS (
            SELECT
                *,
                -- Identify opportunities
                CASE
                    WHEN Margin < 20 AND UnitsSold > 50 THEN 'Increase Price - High Volume Low Margin'
                    WHEN Margin > 50 AND UnitsSold < 10 THEN 'Reduce Price - Low Volume High Margin'
                    WHEN PriceStdDev > AvgSellingPrice * 0.1 THEN 'Standardize Pricing'
                    WHEN AvgSellingPrice < SalePrice * 0.9 THEN 'Review Discounting'
                    WHEN AvgSellingPrice > SalePrice THEN 'Update List Price'
                    ELSE 'Optimal'
                END as Opportunity,
                -- Calculate potential impact
                CASE
                    WHEN Margin < 20 THEN UnitsSold * UnitProfit * 0.1  -- 10% price increase impact
                    WHEN Margin > 50 AND UnitsSold < 10 THEN 5 * UnitProfit  -- Selling 5 more units
                    ELSE 0
                END as PotentialImpact
            FROM ProfitAnalysis
        )
        SELECT * FROM OpportunityAnalysis
        WHERE UnitsSold > 0
        ORDER BY PotentialImpact DESC
        """

        result = db.execute_query(query)

        # Group opportunities
        opportunities = result.groupby('Opportunity').agg({
            'ProductName': 'count',
            'PotentialImpact': 'sum',
            'GrossProfit': 'sum'
        }).reset_index()

        # Top optimization candidates
        top_opportunities = result[result['Opportunity'] != 'Optimal'].head(20)

        # Category profit analysis
        category_profit = result.groupby('Category').agg({
            'Revenue': 'sum',
            'GrossProfit': 'sum',
            'UnitsSold': 'sum'
        }).reset_index()
        category_profit['Margin'] = (category_profit['GrossProfit'] / category_profit['Revenue'] * 100).round(2)

        # Pricing recommendations
        pricing_recommendations = []
        for _, item in result[result['Opportunity'].str.contains('Price')].head(10).iterrows():
            recommendation = {
                'product': item['ProductName'],
                'current_price': float(item['SalePrice']),
                'avg_selling_price': float(item['AvgSellingPrice']),
                'margin': float(item['Margin']),
                'opportunity': item['Opportunity'],
                'potential_monthly_impact': float(item['PotentialImpact'])
            }

            if 'Increase' in item['Opportunity']:
                recommendation['suggested_price'] = float(item['SalePrice']) * 1.1
                recommendation['action'] = 'INCREASE'
            elif 'Reduce' in item['Opportunity']:
                recommendation['suggested_price'] = float(item['SalePrice']) * 0.95
                recommendation['action'] = 'DECREASE'
            else:
                recommendation['suggested_price'] = float(item['AvgSellingPrice'])
                recommendation['action'] = 'ADJUST'

            pricing_recommendations.append(recommendation)

        response = {
            'summary': {
                'total_revenue': float(result['Revenue'].sum()),
                'total_profit': float(result['GrossProfit'].sum()),
                'overall_margin': float(result['GrossProfit'].sum() / result['Revenue'].sum() * 100),
                'total_opportunities': len(result[result['Opportunity'] != 'Optimal']),
                'potential_monthly_impact': float(result['PotentialImpact'].sum())
            },
            'opportunities_breakdown': opportunities.to_dict('records'),
            'pricing_recommendations': pricing_recommendations,
            'category_performance': category_profit.to_dict('records'),
            'low_margin_products': result[result['Margin'] < 15].head(10)[
                ['ProductName', 'Margin', 'UnitsSold', 'Revenue']
            ].to_dict('records'),
            'high_margin_low_volume': result[(result['Margin'] > 40) & (result['UnitsSold'] < 20)].head(10)[
                ['ProductName', 'Margin', 'UnitsSold', 'PotentialImpact']
            ].to_dict('records')
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Profit optimization error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_api.route('/customer-lifetime-value')
def customer_lifetime_value():
    """Calculate customer lifetime value and retention metrics"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # CLV and retention analysis
        query = """
        WITH CustomerHistory AS (
            SELECT
                c.ID as CustomerID,
                COALESCE(c.FirstName + ' ' + c.LastName, c.Company, 'Unknown') as CustomerName,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase,
                COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
                COUNT(DISTINCT CAST(t.Time as DATE)) as ActiveDays,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                SUM((te.Price - te.Cost) * te.Quantity) as TotalProfit,
                AVG(te.Price * te.Quantity) as AvgOrderValue,
                DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) + 1 as CustomerLifespan,
                DATEDIFF(DAY, MAX(t.Time), GETDATE()) as DaysSinceLastOrder
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(YEAR, -2, GETDATE())
            GROUP BY c.ID, c.FirstName, c.LastName, c.Company
        ),
        CLVAnalysis AS (
            SELECT
                *,
                -- Purchase frequency (orders per month)
                CASE
                    WHEN CustomerLifespan > 0 THEN
                        TotalTransactions * 30.0 / CustomerLifespan
                    ELSE 0
                END as PurchaseFrequency,
                -- Customer status
                CASE
                    WHEN DaysSinceLastOrder <= 30 THEN 'Active'
                    WHEN DaysSinceLastOrder <= 60 THEN 'At Risk'
                    WHEN DaysSinceLastOrder <= 90 THEN 'Dormant'
                    ELSE 'Lost'
                END as CustomerStatus,
                -- Churn probability (simplified)
                CASE
                    WHEN DaysSinceLastOrder <= 30 THEN 0.1
                    WHEN DaysSinceLastOrder <= 60 THEN 0.3
                    WHEN DaysSinceLastOrder <= 90 THEN 0.6
                    ELSE 0.9
                END as ChurnProbability,
                -- Value segment
                CASE
                    WHEN TotalRevenue > 50000 THEN 'Platinum'
                    WHEN TotalRevenue > 20000 THEN 'Gold'
                    WHEN TotalRevenue > 5000 THEN 'Silver'
                    ELSE 'Bronze'
                END as ValueSegment
            FROM CustomerHistory
        )
        SELECT *,
            -- Calculate CLV (simplified: AOV * Purchase Frequency * Expected Lifetime)
            AvgOrderValue * PurchaseFrequency * 12 * (1 - ChurnProbability) as PredictedCLV
        FROM CLVAnalysis
        """

        result = db.execute_query(query)

        # Segment analysis
        segments = result.groupby('CustomerStatus').agg({
            'CustomerID': 'count',
            'TotalRevenue': 'sum',
            'PredictedCLV': 'sum',
            'AvgOrderValue': 'mean',
            'PurchaseFrequency': 'mean'
        }).reset_index()

        # Value segment analysis
        value_segments = result.groupby('ValueSegment').agg({
            'CustomerID': 'count',
            'TotalRevenue': 'sum',
            'TotalProfit': 'sum',
            'PredictedCLV': 'mean',
            'ChurnProbability': 'mean'
        }).reset_index()

        # At-risk customers
        at_risk = result[result['CustomerStatus'].isin(['At Risk', 'Dormant'])]
        at_risk_value = at_risk['TotalRevenue'].sum()

        # Win-back candidates (high-value lost customers)
        winback = result[(result['CustomerStatus'] == 'Lost') &
                        (result['ValueSegment'].isin(['Platinum', 'Gold']))]

        # Retention cohorts
        cohort_query = """
        SELECT
            FORMAT(MIN(t.Time), 'yyyy-MM') as Cohort,
            COUNT(DISTINCT c.ID) as Customers,
            AVG(CASE WHEN t2.Time IS NOT NULL THEN 1.0 ELSE 0.0 END) as Month1Retention,
            AVG(CASE WHEN t3.Time IS NOT NULL THEN 1.0 ELSE 0.0 END) as Month3Retention,
            AVG(CASE WHEN t6.Time IS NOT NULL THEN 1.0 ELSE 0.0 END) as Month6Retention
        FROM dbo.Customer c
        JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        LEFT JOIN [dbo].[Transaction] t2 ON c.ID = t2.CustomerID
            AND t2.Time BETWEEN DATEADD(MONTH, 1, MIN(t.Time)) AND DATEADD(MONTH, 2, MIN(t.Time))
        LEFT JOIN [dbo].[Transaction] t3 ON c.ID = t3.CustomerID
            AND t3.Time BETWEEN DATEADD(MONTH, 3, MIN(t.Time)) AND DATEADD(MONTH, 4, MIN(t.Time))
        LEFT JOIN [dbo].[Transaction] t6 ON c.ID = t6.CustomerID
            AND t6.Time BETWEEN DATEADD(MONTH, 6, MIN(t.Time)) AND DATEADD(MONTH, 7, MIN(t.Time))
        WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
        GROUP BY c.ID
        """

        response = {
            'summary': {
                'total_customers': len(result),
                'active_customers': len(result[result['CustomerStatus'] == 'Active']),
                'avg_clv': float(result['PredictedCLV'].mean()),
                'total_clv': float(result['PredictedCLV'].sum()),
                'at_risk_customers': len(at_risk),
                'at_risk_value': float(at_risk_value),
                'avg_purchase_frequency': float(result['PurchaseFrequency'].mean()),
                'avg_order_value': float(result['AvgOrderValue'].mean())
            },
            'customer_segments': segments.to_dict('records'),
            'value_segments': value_segments.to_dict('records'),
            'top_customers': result.nlargest(10, 'PredictedCLV')[
                ['CustomerName', 'TotalRevenue', 'TotalTransactions', 'PredictedCLV', 'CustomerStatus']
            ].to_dict('records'),
            'at_risk_high_value': at_risk.nlargest(10, 'TotalRevenue')[
                ['CustomerName', 'TotalRevenue', 'DaysSinceLastOrder', 'ChurnProbability']
            ].to_dict('records'),
            'winback_targets': winback.head(10)[
                ['CustomerName', 'TotalRevenue', 'ValueSegment', 'DaysSinceLastOrder']
            ].to_dict('records')
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"CLV analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_api.route('/demand-forecast')
def demand_forecast():
    """Advanced demand forecasting with seasonality"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Get historical sales data
        query = """
        SELECT
            i.ID as ItemID,
            i.Description as ProductName,
            c.Name as Category,
            CAST(t.Time as DATE) as SaleDate,
            DATEPART(WEEKDAY, t.Time) as DayOfWeek,
            DATEPART(WEEK, t.Time) as WeekOfYear,
            DATEPART(MONTH, t.Time) as Month,
            SUM(te.Quantity) as Quantity,
            SUM(te.Price * te.Quantity) as Revenue
        FROM dbo.Item i
        JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= DATEADD(DAY, -180, GETDATE())
        GROUP BY i.ID, i.Description, c.Name, CAST(t.Time as DATE),
                 DATEPART(WEEKDAY, t.Time), DATEPART(WEEK, t.Time), DATEPART(MONTH, t.Time)
        """

        result = db.execute_query(query)

        # Aggregate by product
        product_forecast = []
        top_products = result.groupby('ItemID')['Quantity'].sum().nlargest(20).index

        for item_id in top_products:
            item_data = result[result['ItemID'] == item_id].copy()
            item_name = item_data['ProductName'].iloc[0]

            # Calculate daily average
            daily_avg = item_data.groupby('SaleDate')['Quantity'].sum().mean()

            # Calculate day-of-week seasonality
            dow_seasonality = item_data.groupby('DayOfWeek')['Quantity'].mean()
            dow_factors = dow_seasonality / dow_seasonality.mean()

            # Calculate monthly seasonality
            monthly_seasonality = item_data.groupby('Month')['Quantity'].mean()
            monthly_factors = monthly_seasonality / monthly_seasonality.mean()

            # Simple trend analysis
            dates = pd.to_datetime(item_data['SaleDate'].unique())
            if len(dates) > 7:
                x = np.arange(len(dates))
                y = item_data.groupby('SaleDate')['Quantity'].sum().values
                trend = np.polyfit(x, y, 1)[0]  # Linear trend
            else:
                trend = 0

            # Generate 14-day forecast
            forecast = []
            for i in range(14):
                future_date = datetime.now() + timedelta(days=i+1)
                dow = future_date.weekday() + 1
                month = future_date.month

                # Apply seasonality and trend
                base_demand = daily_avg
                dow_factor = dow_factors.get(dow, 1.0)
                month_factor = monthly_factors.get(month, 1.0)
                trend_factor = 1 + (trend * i / 100)  # Small trend adjustment

                predicted_quantity = base_demand * dow_factor * month_factor * trend_factor

                forecast.append({
                    'date': future_date.strftime('%Y-%m-%d'),
                    'predicted': round(predicted_quantity, 1),
                    'confidence_lower': round(predicted_quantity * 0.7, 1),
                    'confidence_upper': round(predicted_quantity * 1.3, 1)
                })

            product_forecast.append({
                'product': item_name,
                'avg_daily_demand': round(daily_avg, 1),
                'trend': 'increasing' if trend > 0 else 'decreasing',
                'forecast': forecast[:7]  # Next 7 days
            })

        # Category-level forecast
        category_forecast = result.groupby(['Category', 'SaleDate'])['Revenue'].sum().reset_index()
        category_summary = []

        for category in category_forecast['Category'].unique():
            if category:
                cat_data = category_forecast[category_forecast['Category'] == category]
                daily_revenue = cat_data['Revenue'].mean()

                category_summary.append({
                    'category': category,
                    'avg_daily_revenue': float(daily_revenue),
                    'predicted_weekly': float(daily_revenue * 7),
                    'predicted_monthly': float(daily_revenue * 30)
                })

        response = {
            'product_forecasts': product_forecast[:10],
            'category_forecasts': sorted(category_summary, key=lambda x: x['avg_daily_revenue'], reverse=True)[:10],
            'forecast_summary': {
                'forecast_period': '14 days',
                'confidence_level': '70-130%',
                'last_updated': datetime.now().isoformat()
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Demand forecast error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_api.route('/cross-sell-recommendations')
def cross_sell_recommendations():
    """Generate cross-sell and upsell recommendations based on basket analysis"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Market basket analysis
        query = """
        WITH BasketAnalysis AS (
            SELECT
                te1.ItemID as Product1ID,
                i1.Description as Product1,
                te2.ItemID as Product2ID,
                i2.Description as Product2,
                COUNT(DISTINCT te1.TransactionNumber) as CoOccurrences,
                AVG(te2.Price * te2.Quantity) as AvgCrossSellValue
            FROM dbo.TransactionEntry te1
            JOIN dbo.TransactionEntry te2 ON te1.TransactionNumber = te2.TransactionNumber
                AND te1.ItemID != te2.ItemID
            JOIN dbo.Item i1 ON te1.ItemID = i1.ID
            JOIN dbo.Item i2 ON te2.ItemID = i2.ID
            JOIN [dbo].[Transaction] t ON te1.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= DATEADD(DAY, -90, GETDATE())
            GROUP BY te1.ItemID, i1.Description, te2.ItemID, i2.Description
            HAVING COUNT(DISTINCT te1.TransactionNumber) > 5
        ),
        ProductPopularity AS (
            SELECT
                ItemID,
                COUNT(DISTINCT TransactionNumber) as TotalTransactions
            FROM dbo.TransactionEntry te
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= DATEADD(DAY, -90, GETDATE())
            GROUP BY ItemID
        )
        SELECT
            ba.Product1,
            ba.Product2,
            ba.CoOccurrences,
            ba.AvgCrossSellValue,
            p1.TotalTransactions as Product1Transactions,
            p2.TotalTransactions as Product2Transactions,
            -- Calculate confidence (probability of Product2 given Product1)
            CAST(ba.CoOccurrences AS FLOAT) / p1.TotalTransactions * 100 as Confidence,
            -- Calculate lift (how much more likely Product2 is bought with Product1)
            (CAST(ba.CoOccurrences AS FLOAT) / p1.TotalTransactions) /
            (CAST(p2.TotalTransactions AS FLOAT) /
                (SELECT COUNT(DISTINCT TransactionNumber) FROM [dbo].[Transaction]
                 WHERE Time >= DATEADD(DAY, -90, GETDATE()))) as Lift
        FROM BasketAnalysis ba
        JOIN ProductPopularity p1 ON ba.Product1ID = p1.ItemID
        JOIN ProductPopularity p2 ON ba.Product2ID = p2.ItemID
        WHERE ba.CoOccurrences > 10
        ORDER BY Lift DESC, Confidence DESC
        """

        result = db.execute_query(query)

        # Group recommendations by product
        recommendations = {}
        for _, row in result.head(100).iterrows():
            product = row['Product1']
            if product not in recommendations:
                recommendations[product] = []

            if len(recommendations[product]) < 5:  # Max 5 recommendations per product
                recommendations[product].append({
                    'recommended_product': row['Product2'],
                    'confidence': round(row['Confidence'], 1),
                    'lift': round(row['Lift'], 2),
                    'avg_value': float(row['AvgCrossSellValue']),
                    'frequency': int(row['CoOccurrences'])
                })

        # Upsell opportunities (higher-value alternatives)
        upsell_query = """
        WITH ProductCategories AS (
            SELECT
                i.ID,
                i.Description,
                i.SalePrice,
                c.Name as Category,
                AVG(te.Price * te.Quantity) as AvgSaleValue,
                COUNT(DISTINCT te.TransactionNumber) as Transactions
            FROM dbo.Item i
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            LEFT JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            LEFT JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= DATEADD(DAY, -90, GETDATE())
            GROUP BY i.ID, i.Description, i.SalePrice, c.Name
        )
        SELECT
            p1.Description as BaseProduct,
            p2.Description as UpsellProduct,
            p1.SalePrice as BasePrice,
            p2.SalePrice as UpsellPrice,
            p2.SalePrice - p1.SalePrice as PriceIncrease,
            (p2.SalePrice - p1.SalePrice) / p1.SalePrice * 100 as PercentIncrease,
            p2.Transactions as UpsellPopularity
        FROM ProductCategories p1
        JOIN ProductCategories p2 ON p1.Category = p2.Category
            AND p2.SalePrice > p1.SalePrice
            AND p2.SalePrice <= p1.SalePrice * 1.5  -- Max 50% price increase
            AND p2.Transactions > 10
        WHERE p1.Transactions > 20
        ORDER BY p1.Transactions DESC, PercentIncrease ASC
        """

        upsell_result = db.execute_query(upsell_query)

        # Group upsell opportunities
        upsell_opportunities = {}
        for _, row in upsell_result.head(50).iterrows():
            product = row['BaseProduct']
            if product not in upsell_opportunities:
                upsell_opportunities[product] = {
                    'product': row['UpsellProduct'],
                    'price_increase': float(row['PriceIncrease']),
                    'percent_increase': round(row['PercentIncrease'], 1),
                    'popularity': int(row['UpsellPopularity'])
                }

        response = {
            'cross_sell_recommendations': recommendations,
            'upsell_opportunities': upsell_opportunities,
            'top_bundles': result.head(10)[['Product1', 'Product2', 'Confidence', 'Lift']].to_dict('records'),
            'summary': {
                'total_associations': len(result),
                'products_with_recommendations': len(recommendations),
                'products_with_upsell': len(upsell_opportunities)
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Cross-sell recommendations error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_api.route('/sales-team-performance')
def sales_team_performance():
    """Analyze sales team performance and commission tracking"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Sales team performance metrics
        query = """
        WITH SalesMetrics AS (
            SELECT
                t.CashierID,
                COALESCE(c.Name, 'Cashier ' + CAST(t.CashierID as VARCHAR)) as CashierName,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT CAST(t.Time as DATE)) as ActiveDays,
                SUM(te.Price * te.Quantity) as TotalSales,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                AVG(te.Price * te.Quantity) as AvgTransactionValue,
                SUM(te.Quantity) as ItemsSold,
                -- Time-based metrics
                MIN(t.Time) as FirstTransaction,
                MAX(t.Time) as LastTransaction,
                COUNT(DISTINCT DATEPART(HOUR, t.Time)) as ActiveHours
            FROM [dbo].[Transaction] t
            LEFT JOIN dbo.Cashier c ON t.CashierID = c.ID
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
            GROUP BY t.CashierID, c.Name
        ),
        PerformanceAnalysis AS (
            SELECT
                *,
                TotalSales / NULLIF(ActiveDays, 0) as AvgDailySales,
                Transactions / NULLIF(ActiveDays, 0) as AvgDailyTransactions,
                GrossProfit / NULLIF(TotalSales, 0) * 100 as ProfitMargin,
                ItemsSold / NULLIF(Transactions, 0) as ItemsPerTransaction,
                -- Commission calculation (example: 2% of gross profit)
                GrossProfit * 0.02 as EstimatedCommission,
                -- Performance score (weighted metrics)
                (
                    (TotalSales / (SELECT MAX(TotalSales) FROM SalesMetrics)) * 40 +
                    (Transactions / (SELECT MAX(Transactions) FROM SalesMetrics)) * 30 +
                    (GrossProfit / (SELECT MAX(GrossProfit) FROM SalesMetrics)) * 30
                ) as PerformanceScore
            FROM SalesMetrics
        )
        SELECT * FROM PerformanceAnalysis
        ORDER BY PerformanceScore DESC
        """

        result = db.execute_query(query)

        # Hourly productivity analysis
        hourly_query = """
        SELECT
            DATEPART(HOUR, t.Time) as Hour,
            t.CashierID,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Price * te.Quantity) as Sales
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= DATEADD(DAY, -7, GETDATE())
        GROUP BY DATEPART(HOUR, t.Time), t.CashierID
        """

        hourly_result = db.execute_query(hourly_query)

        # Peak performance hours by cashier
        peak_hours = {}
        for cashier_id in result['CashierID'].unique():
            cashier_hourly = hourly_result[hourly_result['CashierID'] == cashier_id]
            if not cashier_hourly.empty:
                peak_hour = cashier_hourly.loc[cashier_hourly['Sales'].idxmax(), 'Hour']
                peak_hours[int(cashier_id)] = int(peak_hour)

        # Category specialization
        category_query = """
        SELECT
            t.CashierID,
            c.Name as Category,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Price * te.Quantity) as Sales
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
        GROUP BY t.CashierID, c.Name
        """

        category_result = db.execute_query(category_query)

        # Find top category for each cashier
        top_categories = {}
        for cashier_id in result['CashierID'].unique():
            cashier_cats = category_result[category_result['CashierID'] == cashier_id]
            if not cashier_cats.empty:
                top_cat = cashier_cats.loc[cashier_cats['Sales'].idxmax(), 'Category']
                top_categories[int(cashier_id)] = top_cat

        # Format response
        team_performance = []
        for _, row in result.iterrows():
            cashier_id = int(row['CashierID'])
            team_performance.append({
                'cashier_id': cashier_id,
                'name': row['CashierName'],
                'total_sales': float(row['TotalSales']),
                'transactions': int(row['Transactions']),
                'gross_profit': float(row['GrossProfit']),
                'avg_daily_sales': float(row['AvgDailySales']),
                'performance_score': round(row['PerformanceScore'], 1),
                'commission': float(row['EstimatedCommission']),
                'peak_hour': peak_hours.get(cashier_id, 'N/A'),
                'top_category': top_categories.get(cashier_id, 'N/A'),
                'active_days': int(row['ActiveDays']),
                'unique_customers': int(row['UniqueCustomers'])
            })

        response = {
            'team_performance': team_performance,
            'summary': {
                'total_sales': float(result['TotalSales'].sum()),
                'total_profit': float(result['GrossProfit'].sum()),
                'total_commission': float(result['EstimatedCommission'].sum()),
                'avg_performance_score': float(result['PerformanceScore'].mean()),
                'top_performer': team_performance[0]['name'] if team_performance else 'N/A'
            },
            'leaderboard': {
                'sales': result.nlargest(3, 'TotalSales')[['CashierName', 'TotalSales']].to_dict('records'),
                'transactions': result.nlargest(3, 'Transactions')[['CashierName', 'Transactions']].to_dict('records'),
                'profit': result.nlargest(3, 'GrossProfit')[['CashierName', 'GrossProfit']].to_dict('records')
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Sales team performance error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_api.route('/automated-alerts')
def automated_alerts():
    """Generate automated alerts for critical business conditions"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        alerts = []

        # 1. Low stock alerts
        stock_query = """
        SELECT
            i.Description,
            i.Quantity as QuantityOnHand,
            i.ReorderPoint,
            AVG(te.Quantity) as AvgDailySales
        FROM dbo.Item i
        LEFT JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        LEFT JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= DATEADD(DAY, -7, GETDATE())
            AND i.Quantity <= i.ReorderPoint
        GROUP BY i.Description, i.QuantityOnHand, i.ReorderPoint
        """

        stock_result = db.execute_query(stock_query)
        for _, item in stock_result.iterrows():
            days_remaining = float(item['QuantityOnHand']) / float(item['AvgDailySales']) if item['AvgDailySales'] and item['AvgDailySales'] > 0 else 0
            alerts.append({
                'type': 'CRITICAL' if days_remaining < 2 else 'WARNING',
                'category': 'Inventory',
                'message': f"{item['Description']} - Only {int(item['QuantityOnHand'])} units left ({days_remaining:.1f} days supply)",
                'action': 'Reorder immediately',
                'priority': 1 if days_remaining < 2 else 2
            })

        # 2. Unusual sales patterns
        sales_query = """
        WITH DailySales AS (
            SELECT
                CAST(t.Time as DATE) as Date,
                SUM(te.Price * te.Quantity) as DailySales
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
            GROUP BY CAST(t.Time as DATE)
        )
        SELECT
            Date,
            DailySales,
            (SELECT AVG(d2.DailySales)
            FROM DailySales d2
            WHERE d2.Date BETWEEN DATEADD(DAY, -7, d.Date) AND DATEADD(DAY, -1, d.Date)) as AvgPrevWeek
        FROM DailySales d
        WHERE Date = CAST(GETDATE() as DATE)
        """

        sales_result = db.execute_query(sales_query)
        if not sales_result.empty:
            today_sales = sales_result.iloc[0]['DailySales']
            avg_sales = sales_result.iloc[0]['AvgPrevWeek']
            if avg_sales > 0:
                variance = ((today_sales - avg_sales) / avg_sales) * 100
                if abs(variance) > 30:
                    alerts.append({
                        'type': 'INFO',
                        'category': 'Sales',
                        'message': f"Today's sales are {variance:+.1f}% vs. 7-day average",
                        'action': 'Monitor closely',
                        'priority': 3
                    })

        # 3. Customer churn alerts
        churn_query = """
        SELECT
            COUNT(*) as AtRiskCustomers,
            SUM(TotalRevenue) as AtRiskRevenue
        FROM (
            SELECT
                c.ID,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                MAX(t.Time) as LastPurchase,
                DATEDIFF(DAY, MAX(t.Time), GETDATE()) as DaysSince
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID
            HAVING DATEDIFF(DAY, MAX(t.Time), GETDATE()) BETWEEN 45 AND 60
                AND SUM(te.Price * te.Quantity) > 1000
        ) AtRisk
        """

        churn_result = db.execute_query(churn_query)
        if not churn_result.empty and churn_result.iloc[0]['AtRiskCustomers'] > 0:
            alerts.append({
                'type': 'WARNING',
                'category': 'Customer',
                'message': f"{int(churn_result.iloc[0]['AtRiskCustomers'])} high-value customers at risk of churning",
                'action': 'Launch retention campaign',
                'priority': 2
            })

        # 4. Profit margin alerts
        margin_query = """
        SELECT
            AVG((te.Price - te.Cost) / NULLIF(te.Price, 0) * 100) as AvgMargin
        FROM dbo.TransactionEntry te
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= DATEADD(DAY, -1, GETDATE())
        """

        margin_result = db.execute_query(margin_query)
        if not margin_result.empty:
            avg_margin = margin_result.iloc[0]['AvgMargin']
            if avg_margin < 20:
                alerts.append({
                    'type': 'WARNING',
                    'category': 'Profit',
                    'message': f"Average profit margin dropped to {avg_margin:.1f}%",
                    'action': 'Review pricing strategy',
                    'priority': 2
                })

        # Sort alerts by priority
        alerts.sort(key=lambda x: x['priority'])

        response = {
            'alerts': alerts[:20],  # Top 20 alerts
            'summary': {
                'critical': len([a for a in alerts if a['type'] == 'CRITICAL']),
                'warning': len([a for a in alerts if a['type'] == 'WARNING']),
                'info': len([a for a in alerts if a['type'] == 'INFO']),
                'total': len(alerts)
            },
            'generated_at': datetime.now().isoformat()
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Automated alerts error: {e}")
        return jsonify({'error': str(e)}), 500