#!/usr/bin/env python3
"""
Category Analysis Dashboard Module
Provides interactive category performance analysis with filtering and visualization
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, jsonify, request, render_template
import pandas as pd
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

# Create blueprint
category_analysis_bp = Blueprint('category_analysis', __name__)

def decimal_default(obj):
    """JSON encoder for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@category_analysis_bp.route('/category-analysis')
def category_analysis_page():
    """Category Analysis Dashboard Page"""
    return render_template('category_analysis.html')

@category_analysis_bp.route('/api/category-analysis/data')
def get_category_data():
    """Get comprehensive category analysis data with optional filters"""
    try:
        # Get filter parameters
        days = request.args.get('days', 365, type=int)
        min_margin = request.args.get('min_margin', type=float)
        max_margin = request.args.get('max_margin', type=float)
        min_revenue = request.args.get('min_revenue', type=float)
        classification = request.args.get('classification')
        sort_by = request.args.get('sort_by', 'revenue')
        sort_order = request.args.get('sort_order', 'desc')

        # Date ranges
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        prev_start_date = end_date - timedelta(days=days*2)
        prev_end_date = start_date

        # Main query
        query = f"""
        WITH CurrentPeriod AS (
            SELECT
                ISNULL(c.Name, 'Uncategorized') as Category,
                c.ID as CategoryID,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(te.Quantity) as Units,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as TotalCost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                AVG(te.Price * te.Quantity) as AvgTransactionValue,
                COUNT(DISTINCT CAST(t.[Time] AS DATE)) as DaysWithSales,
                MIN(t.[Time]) as FirstSale,
                MAX(t.[Time]) as LastSale
            FROM [Transaction] t
            INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            INNER JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category c ON i.CategoryID = c.ID
            WHERE t.[Time] >= '{start_date.strftime('%Y-%m-%d')}'
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
            WHERE t.[Time] >= '{prev_start_date.strftime('%Y-%m-%d')}'
                AND t.[Time] < '{prev_end_date.strftime('%Y-%m-%d')}'
                AND te.Price > 0
            GROUP BY c.Name
        ),
        TotalMetrics AS (
            SELECT
                SUM(Revenue) as TotalRevenue,
                SUM(GrossProfit) as TotalGrossProfit
            FROM CurrentPeriod
        )
        SELECT
            c.Category,
            c.CategoryID,
            c.Transactions,
            c.Units,
            c.Revenue,
            c.TotalCost,
            c.GrossProfit,
            CASE
                WHEN c.Revenue > 0 THEN (c.GrossProfit / c.Revenue) * 100
                ELSE 0
            END as MarginPercent,
            CASE
                WHEN t.TotalRevenue > 0 THEN (c.Revenue / t.TotalRevenue) * 100
                ELSE 0
            END as RevenueSharePercent,
            CASE
                WHEN t.TotalGrossProfit > 0 THEN (c.GrossProfit / t.TotalGrossProfit) * 100
                ELSE 0
            END as ProfitContributionPercent,
            c.AvgTransactionValue,
            c.DaysWithSales,
            ISNULL(p.PrevRevenue, 0) as PrevYearRevenue,
            ISNULL(p.PrevGrossProfit, 0) as PrevYearGrossProfit,
            CASE
                WHEN ISNULL(p.PrevRevenue, 0) > 0
                THEN ((c.Revenue - p.PrevRevenue) / p.PrevRevenue) * 100
                ELSE 0
            END as RevenueGrowthPercent,
            c.FirstSale,
            c.LastSale,
            DATEDIFF(day, c.LastSale, GETDATE()) as DaysSinceLastSale
        FROM CurrentPeriod c
        CROSS JOIN TotalMetrics t
        LEFT JOIN PreviousPeriod p ON c.Category = p.Category
        WHERE c.Revenue > 0
        """

        # Add filters
        filters = []
        if min_margin is not None:
            filters.append(f"(c.GrossProfit / c.Revenue) * 100 >= {min_margin}")
        if max_margin is not None:
            filters.append(f"(c.GrossProfit / c.Revenue) * 100 <= {max_margin}")
        if min_revenue is not None:
            filters.append(f"c.Revenue >= {min_revenue}")

        if filters:
            query += " AND " + " AND ".join(filters)

        # Add sorting
        sort_columns = {
            'revenue': 'c.Revenue',
            'margin': '(c.GrossProfit / c.Revenue) * 100',
            'growth': '((c.Revenue - ISNULL(p.PrevRevenue, 0)) / NULLIF(ISNULL(p.PrevRevenue, 1), 0)) * 100',
            'transactions': 'c.Transactions',
            'units': 'c.Units',
            'category': 'c.Category'
        }

        sort_col = sort_columns.get(sort_by, 'c.Revenue')
        order = 'DESC' if sort_order == 'desc' else 'ASC'
        query += f" ORDER BY {sort_col} {order}"

        with SQLServerConnection() as db:
            df = db.execute_query(query, description="Category analysis data")

            if df.empty:
                return jsonify({
                    'status': 'success',
                    'data': [],
                    'summary': {},
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                })

            # Calculate classifications
            def classify_category(row):
                margin = row['MarginPercent']
                revenue_share = row['RevenueSharePercent']
                profit_contrib = row['ProfitContributionPercent']

                if (margin > 20 and revenue_share > 1) or (margin > 15 and revenue_share > 5):
                    return 'MONEY_MAKER'
                elif margin > 5 and revenue_share > 5:
                    return 'STRATEGIC'
                elif margin < 5 and profit_contrib < 1:
                    return 'MONEY_LOSER'
                elif revenue_share < 1 and row['RevenueGrowthPercent'] < -10:
                    return 'UNDERPERFORMER'
                else:
                    return 'INVESTIGATE'

            df['Classification'] = df.apply(classify_category, axis=1)

            # Filter by classification if specified
            if classification and classification != 'all':
                df = df[df['Classification'] == classification.upper()]

            # Calculate summary statistics
            total_revenue = df['Revenue'].sum()
            total_profit = df['GrossProfit'].sum()
            overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

            summary = {
                'total_revenue': float(total_revenue),
                'total_profit': float(total_profit),
                'overall_margin': float(overall_margin),
                'total_transactions': int(df['Transactions'].sum()),
                'total_units': float(df['Units'].sum()),
                'category_count': len(df),
                'classification_breakdown': df.groupby('Classification').agg({
                    'Revenue': 'sum',
                    'GrossProfit': 'sum',
                    'Category': 'count'
                }).to_dict('index')
            }

            # Convert DataFrame to list of dicts
            categories = df.to_dict('records')

            # Convert to JSON-serializable format
            response_data = {
                'status': 'success',
                'data': categories,
                'summary': summary,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'filters': {
                    'days': days,
                    'min_margin': min_margin,
                    'max_margin': max_margin,
                    'min_revenue': min_revenue,
                    'classification': classification,
                    'sort_by': sort_by,
                    'sort_order': sort_order
                }
            }

            # Use json.dumps with custom encoder, then jsonify the result
            import json
            json_str = json.dumps(response_data, default=decimal_default)
            return json_str, 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"Error getting category data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@category_analysis_bp.route('/api/category-analysis/top-products/<category_name>')
def get_category_top_products(category_name):
    """Get top products for a specific category"""
    try:
        days = request.args.get('days', 365, type=int)
        limit = request.args.get('limit', 20, type=int)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            SUM(te.Quantity) as UnitsSold,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            CASE
                WHEN SUM(te.Price * te.Quantity) > 0
                THEN (SUM((te.Price - te.Cost) * te.Quantity) / SUM(te.Price * te.Quantity)) * 100
                ELSE 0
            END as MarginPercent,
            AVG(te.Price) as AvgPrice,
            AVG(te.Cost) as AvgCost
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        INNER JOIN Category c ON i.CategoryID = c.ID
        WHERE c.Name = ?
            AND t.[Time] >= ?
            AND t.[Time] <= ?
            AND te.Price > 0
        GROUP BY i.Description, i.ItemLookupCode
        ORDER BY SUM(te.Price * te.Quantity) DESC
        """

        with SQLServerConnection() as db:
            df = db.execute_query(
                query,
                params=[category_name, start_date, end_date],
                description=f"Top products for {category_name}"
            )

            if df.empty:
                return jsonify({
                    'status': 'success',
                    'category': category_name,
                    'products': []
                })

            products = df.to_dict('records')

            response_data = {
                'status': 'success',
                'category': category_name,
                'products': products,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }

            import json
            json_str = json.dumps(response_data, default=decimal_default)
            return json_str, 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"Error getting top products: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

def register_category_routes(app):
    """Register category analysis routes with the Flask app"""
    app.register_blueprint(category_analysis_bp)
    logger.info("✅ Category analysis routes registered")
