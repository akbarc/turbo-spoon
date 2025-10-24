"""
Sales Dashboard V2 - Backend API Module
Optimized queries and advanced analytics for sales dashboard
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
from functools import lru_cache
import json
from decimal import Decimal

logger = logging.getLogger(__name__)

# Create Blueprint
sales_api = Blueprint('sales_api', __name__, url_prefix='/api/v2/sales')

# Cache for frequently accessed data
class SalesCache:
    def __init__(self):
        self.cache = {}
        self.last_update = {}
        self.ttl = 300  # 5 minutes TTL

    def get(self, key):
        if key in self.cache:
            if datetime.now().timestamp() - self.last_update.get(key, 0) < self.ttl:
                return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value
        self.last_update[key] = datetime.now().timestamp()

    def clear(self):
        self.cache.clear()
        self.last_update.clear()

cache = SalesCache()

def decimal_encoder(obj):
    """JSON encoder for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

@sales_api.route('/dashboard-summary')
def dashboard_summary():
    """Get comprehensive dashboard summary with all KPIs"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        period = request.args.get('period', 'today')
        start_date, end_date = get_date_range(period)

        # Check cache
        cache_key = f"summary_{period}_{start_date}_{end_date}"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        response = {
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'kpis': get_kpis(db, start_date, end_date),
            'trends': get_trends(db, start_date, end_date),
            'comparisons': get_comparisons(db, start_date, end_date)
        }

        cache.set(cache_key, response)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        return jsonify({'error': str(e)}), 500

@sales_api.route('/real-time-feed')
def real_time_feed():
    """Get real-time sales feed for live updates"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Get last 20 transactions from today
        query = """
        SELECT TOP 20
            t.TransactionNumber,
            t.Time,
            t.Total,
            COALESCE(c.FirstName + ' ' + c.LastName, c.Company, 'Walk-in') as CustomerName,
            COUNT(te.ID) as ItemCount,
            STUFF((
                SELECT ', ' + i2.Description
                FROM dbo.TransactionEntry te2
                JOIN dbo.Item i2 ON te2.ItemID = i2.ID
                WHERE te2.TransactionNumber = t.TransactionNumber
                FOR XML PATH('')
            ), 1, 2, '') as Items
        FROM [dbo].[Transaction] t
        LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
        LEFT JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        LEFT JOIN dbo.Item i ON te.ItemID = i.ID
        WHERE t.Time >= CAST(GETDATE() AS DATE)
        GROUP BY t.TransactionNumber, t.Time, t.Total, c.FirstName, c.LastName, c.Company
        ORDER BY t.Time DESC
        """

        result = db.execute_query(query)

        transactions = []
        for _, row in result.iterrows():
            transactions.append({
                'id': int(row['TransactionNumber']),
                'time': row['Time'].strftime('%H:%M:%S') if hasattr(row['Time'], 'strftime') else str(row['Time']),
                'amount': float(row['Total']),
                'customer': row['CustomerName'],
                'items': int(row['ItemCount']),
                'preview': row['Items'][:50] + '...' if len(str(row['Items'])) > 50 else row['Items']
            })

        return jsonify({'transactions': transactions})

    except Exception as e:
        logger.error(f"Real-time feed error: {e}")
        return jsonify({'error': str(e)}), 500

@sales_api.route('/hourly-analysis')
def hourly_analysis():
    """Get hourly sales analysis for heatmap visualization"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        days = int(request.args.get('days', 7))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        query = """
        SELECT
            DATEPART(HOUR, t.Time) as Hour,
            DATENAME(WEEKDAY, t.Time) as DayOfWeek,
            DATEPART(WEEKDAY, t.Time) as DayNum,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            COALESCE(SUM(te.Price * te.Quantity), 0) as Sales
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY DATEPART(HOUR, t.Time), DATENAME(WEEKDAY, t.Time), DATEPART(WEEKDAY, t.Time)
        ORDER BY DayNum, Hour
        """

        result = db.execute_query(query, [start_date, end_date])

        # Create heatmap data structure
        heatmap_data = []
        days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        for day in days_of_week:
            day_data = result[result['DayOfWeek'] == day]
            for hour in range(24):
                hour_data = day_data[day_data['Hour'] == hour]
                if not hour_data.empty:
                    heatmap_data.append({
                        'day': day,
                        'hour': hour,
                        'sales': float(hour_data.iloc[0]['Sales']),
                        'transactions': int(hour_data.iloc[0]['Transactions'])
                    })
                else:
                    heatmap_data.append({
                        'day': day,
                        'hour': hour,
                        'sales': 0,
                        'transactions': 0
                    })

        return jsonify({'heatmap': heatmap_data})

    except Exception as e:
        logger.error(f"Hourly analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@sales_api.route('/customer-segments')
def customer_segments():
    """Get customer segmentation analysis"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        period = request.args.get('period', '30d')
        start_date, end_date = get_date_range(period)

        query = """
        WITH CustomerMetrics AS (
            SELECT
                c.ID,
                COALESCE(c.FirstName + ' ' + c.LastName, c.Company, 'Unknown') as CustomerName,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COALESCE(SUM(te.Price * te.Quantity), 0) as TotalSpent,
                COALESCE(AVG(te.Price * te.Quantity), 0) as AvgOrderValue,
                MAX(t.Time) as LastPurchase,
                DATEDIFF(DAY, MAX(t.Time), GETDATE()) as DaysSinceLastPurchase
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
            LEFT JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= %s AND t.Time <= %s
            GROUP BY c.ID, c.FirstName, c.LastName, c.Company
        )
        SELECT
            CustomerName,
            Transactions,
            TotalSpent,
            AvgOrderValue,
            DaysSinceLastPurchase,
            CASE
                WHEN TotalSpent > 10000 AND Transactions > 20 THEN 'VIP'
                WHEN TotalSpent > 5000 OR Transactions > 10 THEN 'Regular'
                WHEN DaysSinceLastPurchase > 60 THEN 'At Risk'
                WHEN DaysSinceLastPurchase > 30 THEN 'Dormant'
                ELSE 'Active'
            END as Segment
        FROM CustomerMetrics
        ORDER BY TotalSpent DESC
        """

        result = db.execute_query(query, [start_date, end_date])

        # Aggregate by segment
        segments = result.groupby('Segment').agg({
            'CustomerName': 'count',
            'TotalSpent': 'sum',
            'Transactions': 'sum',
            'AvgOrderValue': 'mean'
        }).reset_index()

        segments_data = []
        for _, seg in segments.iterrows():
            segments_data.append({
                'segment': seg['Segment'],
                'customer_count': int(seg['CustomerName']),
                'total_revenue': float(seg['TotalSpent']),
                'total_transactions': int(seg['Transactions']),
                'avg_order_value': float(seg['AvgOrderValue'])
            })

        return jsonify({'segments': segments_data})

    except Exception as e:
        logger.error(f"Customer segments error: {e}")
        return jsonify({'error': str(e)}), 500

@sales_api.route('/product-performance')
def product_performance():
    """Get detailed product performance metrics"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        period = request.args.get('period', '7d')
        start_date, end_date = get_date_range(period)
        limit = int(request.args.get('limit', 20))

        query = """
        WITH ProductMetrics AS (
            SELECT
                i.ID,
                i.Description as ProductName,
                c.Name as Category,
                i.SalePrice as CurrentPrice,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
                AVG(te.Price) as AvgSellingPrice,
                STDEV(te.Price) as PriceVariation
            FROM dbo.Item i
            LEFT JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            LEFT JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE t.Time >= %s AND t.Time <= %s
            GROUP BY i.ID, i.Description, c.Name, i.SalePrice
        )
        SELECT TOP %s
            *,
            CASE
                WHEN Revenue > 0 THEN GrossProfit / Revenue * 100
                ELSE 0
            END as ProfitMargin,
            UnitsSold * 1.0 / NULLIF(DATEDIFF(DAY, %s, %s), 0) as DailyVelocity
        FROM ProductMetrics
        ORDER BY Revenue DESC
        """

        result = db.execute_query(query, [start_date, end_date, limit, start_date, end_date])

        products = []
        for _, row in result.iterrows():
            products.append({
                'id': int(row['ID']),
                'name': row['ProductName'],
                'category': row['Category'] or 'Uncategorized',
                'price': float(row['CurrentPrice'] or 0),
                'transactions': int(row['Transactions'] or 0),
                'units_sold': int(row['UnitsSold'] or 0),
                'revenue': float(row['Revenue'] or 0),
                'profit': float(row['GrossProfit'] or 0),
                'margin': float(row['ProfitMargin'] or 0),
                'velocity': float(row['DailyVelocity'] or 0),
                'price_variation': float(row['PriceVariation'] or 0)
            })

        return jsonify({'products': products})

    except Exception as e:
        logger.error(f"Product performance error: {e}")
        return jsonify({'error': str(e)}), 500

@sales_api.route('/sales-forecast')
def sales_forecast():
    """Generate sales forecast based on historical data"""
    try:
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()

        # Get historical data for last 30 days
        query = """
        SELECT
            CAST(t.Time AS DATE) as Date,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            COALESCE(SUM(te.Price * te.Quantity), 0) as DailySales
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
        GROUP BY CAST(t.Time AS DATE)
        ORDER BY Date
        """

        result = db.execute_query(query)

        if not result.empty:
            # Simple moving average forecast
            sales_values = result['DailySales'].values
            ma_7 = np.convolve(sales_values, np.ones(7)/7, mode='valid')

            # Calculate trend
            if len(ma_7) > 1:
                trend = (ma_7[-1] - ma_7[0]) / len(ma_7)
            else:
                trend = 0

            # Generate 7-day forecast
            last_avg = ma_7[-1] if len(ma_7) > 0 else sales_values.mean()
            forecast = []

            for i in range(1, 8):
                date = datetime.now() + timedelta(days=i)
                # Add some weekly seasonality
                day_of_week = date.weekday()
                seasonality = 1.0
                if day_of_week == 5:  # Saturday
                    seasonality = 1.2
                elif day_of_week == 6:  # Sunday
                    seasonality = 0.8

                predicted_value = (last_avg + trend * i) * seasonality
                forecast.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'predicted_sales': float(predicted_value),
                    'confidence_lower': float(predicted_value * 0.8),
                    'confidence_upper': float(predicted_value * 1.2)
                })

            # Historical data for chart
            historical = []
            for _, row in result.tail(14).iterrows():
                historical.append({
                    'date': row['Date'].strftime('%Y-%m-%d'),
                    'actual_sales': float(row['DailySales'])
                })

            return jsonify({
                'historical': historical,
                'forecast': forecast,
                'trend': 'increasing' if trend > 0 else 'decreasing'
            })

        return jsonify({'error': 'Insufficient data for forecast'}), 400

    except Exception as e:
        logger.error(f"Sales forecast error: {e}")
        return jsonify({'error': str(e)}), 500

# Helper functions
def get_date_range(period):
    """Calculate date range based on period"""
    now = datetime.now()
    end_date = now

    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'yesterday':
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == '7d':
        start_date = now - timedelta(days=7)
    elif period == '30d':
        start_date = now - timedelta(days=30)
    elif period == 'MTD':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'YTD':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return start_date, end_date

def get_kpis(db, start_date, end_date):
    """Get KPI metrics"""
    query = """
    SELECT
        COUNT(DISTINCT t.TransactionNumber) as transactions,
        COUNT(DISTINCT t.CustomerID) as customers,
        COALESCE(SUM(te.Price * te.Quantity), 0) as revenue,
        COALESCE(SUM(te.Quantity), 0) as units,
        COALESCE(AVG(te.Price * te.Quantity), 0) as avg_order,
        COALESCE(SUM(te.Price * te.Quantity - te.Cost * te.Quantity), 0) as gross_profit
    FROM [dbo].[Transaction] t
    JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= %s AND t.Time <= %s
    """

    result = db.execute_query(query, [start_date, end_date])

    if not result.empty:
        row = result.iloc[0]
        profit_margin = (row['gross_profit'] / row['revenue'] * 100) if row['revenue'] > 0 else 0

        return {
            'total_revenue': float(row['revenue']),
            'total_transactions': int(row['transactions']),
            'unique_customers': int(row['customers']),
            'units_sold': int(row['units']),
            'avg_order_value': float(row['avg_order']),
            'gross_profit': float(row['gross_profit']),
            'profit_margin': float(profit_margin)
        }

    return {}

def get_trends(db, start_date, end_date):
    """Get trend data for charts"""
    # Daily trends
    daily_query = """
    SELECT
        CAST(t.Time AS DATE) as Date,
        COUNT(DISTINCT t.TransactionNumber) as Transactions,
        COALESCE(SUM(te.Price * te.Quantity), 0) as Sales
    FROM [dbo].[Transaction] t
    JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= %s AND t.Time <= %s
    GROUP BY CAST(t.Time AS DATE)
    ORDER BY Date
    """

    daily_result = db.execute_query(daily_query, [start_date, end_date])

    daily_trend = []
    for _, row in daily_result.iterrows():
        daily_trend.append({
            'date': row['Date'].strftime('%Y-%m-%d'),
            'sales': float(row['Sales']),
            'transactions': int(row['Transactions'])
        })

    # Hourly trends for today
    hourly_query = """
    SELECT
        DATEPART(HOUR, t.Time) as Hour,
        COUNT(DISTINCT t.TransactionNumber) as Transactions,
        COALESCE(SUM(te.Price * te.Quantity), 0) as Sales
    FROM [dbo].[Transaction] t
    JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE CAST(t.Time AS DATE) = CAST(GETDATE() AS DATE)
    GROUP BY DATEPART(HOUR, t.Time)
    ORDER BY Hour
    """

    hourly_result = db.execute_query(hourly_query)

    hourly_trend = []
    for hour in range(24):
        hour_data = hourly_result[hourly_result['Hour'] == hour]
        if not hour_data.empty:
            hourly_trend.append({
                'hour': hour,
                'sales': float(hour_data.iloc[0]['Sales']),
                'transactions': int(hour_data.iloc[0]['Transactions'])
            })
        else:
            hourly_trend.append({
                'hour': hour,
                'sales': 0,
                'transactions': 0
            })

    return {
        'daily': daily_trend,
        'hourly': hourly_trend
    }

def get_comparisons(db, start_date, end_date):
    """Get period-over-period comparisons"""
    period_length = (end_date - start_date).days + 1
    prev_start = start_date - timedelta(days=period_length)
    prev_end = end_date - timedelta(days=period_length)

    comparison_query = """
    SELECT
        'current' as Period,
        COUNT(DISTINCT t.TransactionNumber) as Transactions,
        COALESCE(SUM(te.Price * te.Quantity), 0) as Revenue,
        COUNT(DISTINCT t.CustomerID) as Customers
    FROM [dbo].[Transaction] t
    JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= %s AND t.Time <= %s
    UNION ALL
    SELECT
        'previous' as Period,
        COUNT(DISTINCT t.TransactionNumber) as Transactions,
        COALESCE(SUM(te.Price * te.Quantity), 0) as Revenue,
        COUNT(DISTINCT t.CustomerID) as Customers
    FROM [dbo].[Transaction] t
    JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= %s AND t.Time <= %s
    """

    result = db.execute_query(comparison_query, [start_date, end_date, prev_start, prev_end])

    current = result[result['Period'] == 'current']
    previous = result[result['Period'] == 'previous']

    if not current.empty and not previous.empty:
        curr = current.iloc[0]
        prev = previous.iloc[0]

        def calc_change(current_val, previous_val):
            if previous_val > 0:
                return ((current_val - previous_val) / previous_val) * 100
            return 0 if current_val == 0 else 100

        return {
            'revenue_change': float(calc_change(curr['Revenue'], prev['Revenue'])),
            'transaction_change': float(calc_change(curr['Transactions'], prev['Transactions'])),
            'customer_change': float(calc_change(curr['Customers'], prev['Customers']))
        }

    return {
        'revenue_change': 0,
        'transaction_change': 0,
        'customer_change': 0
    }