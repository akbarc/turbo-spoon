"""
Business overview endpoints - executive summary, sales performance, trends.

These endpoints extract and wrap logic from the Streamlit Executive Dashboard page.
"""
import sys
from pathlib import Path
from flask import Blueprint, jsonify, request
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Try pyodbc first (works better on macOS), fall back to pymssql
try:
    from database.sql_server_pyodbc import db
except ImportError:
    from database.sql_server import db
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected
from utils.date_utils import parse_period, get_comparison_period, format_date_for_sql

business_bp = Blueprint('business_overview', __name__)

@business_bp.route('/executive-summary', methods=['GET'])
def executive_summary():
    """
    GET /api/business-overview/executive-summary

    Primary dashboard API returning all key business metrics with automatic
    period-over-period comparisons.

    Query Parameters:
        period (str): Predefined period (today, 7d, 30d, MTD, YTD) - default: today
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)

    Returns:
        JSON with current period metrics, comparison period metrics, and changes

    Example:
        GET /api/business-overview/executive-summary?period=30d

        Response:
        {
            "current_period": {
                "revenue": 125430.50,
                "transactions": 2450,
                "unique_customers": 180,
                "avg_ticket": 51.20,
                "items_sold": 15420,
                "gross_profit": 31357.63,
                "gross_profit_margin": 25.0,
                "excise_paid": 12500.00,
                "excise_collected": 15000.00
            },
            "comparison_period": { ... },
            "changes": {
                "revenue_change": 5.23,
                "transactions_change": 2.94,
                ...
            },
            "period_info": {
                "start_date": "2025-09-23",
                "end_date": "2025-10-23",
                "days_in_period": 31
            }
        }
    """
    try:
        # Parse date range
        period = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        start, end = parse_period(period, start_date, end_date)
        comp_start, comp_end = get_comparison_period(start, end)

        # Format for SQL
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)
        comp_start_sql = format_date_for_sql(comp_start)
        comp_end_sql = format_date_for_sql(comp_end)

        # Current period metrics
        current_metrics = _get_period_metrics(start_sql, end_sql)

        # Comparison period metrics
        comparison_metrics = _get_period_metrics(comp_start_sql, comp_end_sql)

        # Calculate changes
        changes = _calculate_changes(current_metrics, comparison_metrics)

        # Period info
        days_in_period = (end - start).days + 1

        return jsonify({
            "current_period": current_metrics,
            "comparison_period": comparison_metrics,
            "changes": changes,
            "period_info": {
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d'),
                "days_in_period": days_in_period,
                "comparison_start_date": comp_start.strftime('%Y-%m-%d'),
                "comparison_end_date": comp_end.strftime('%Y-%m-%d')
            }
        })

    except ValueError as e:
        return jsonify({"error": "Invalid parameters", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal error", "message": str(e)}), 500

def _get_period_metrics(start_sql: str, end_sql: str) -> dict:
    """
    Get all metrics for a specific period.

    Extracted from Executive_Dashboard.py lines 104-166.
    """
    # Transaction-level metrics (no joins to avoid multiplication)
    transaction_query = f"""
    SELECT
        COUNT(DISTINCT TransactionNumber) as TotalTransactions,
        COUNT(DISTINCT CustomerID) as UniqueCustomers,
        SUM(Total) as TotalSales,
        AVG(Total) as AvgTransactionValue
    FROM [Transaction]
    WHERE Time >= '{start_sql}'
      AND Time <= '{end_sql}'
    """

    # Line item metrics (for quantities and profit BEFORE excise tax)
    lineitem_query = f"""
    SELECT
        SUM(te.Quantity) as TotalItemsSold,
        SUM((te.Price - te.Cost) * te.Quantity) as GrossProfitBeforeExcise
    FROM TransactionEntry te
    INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber AND te.StoreID = t.StoreID
    WHERE t.Time >= '{start_sql}'
      AND t.Time <= '{end_sql}'
    """

    trans_metrics = db.execute_query(transaction_query)
    item_metrics = db.execute_query(lineitem_query)

    # Combine results
    metrics = {}

    if not trans_metrics.empty and trans_metrics['TotalTransactions'].iloc[0] is not None:
        metrics['transactions'] = int(trans_metrics['TotalTransactions'].iloc[0] or 0)
        metrics['unique_customers'] = int(trans_metrics['UniqueCustomers'].iloc[0] or 0)
        metrics['revenue'] = float(trans_metrics['TotalSales'].iloc[0] or 0)
        metrics['avg_ticket'] = float(trans_metrics['AvgTransactionValue'].iloc[0] or 0)
    else:
        metrics['transactions'] = 0
        metrics['unique_customers'] = 0
        metrics['revenue'] = 0.0
        metrics['avg_ticket'] = 0.0

    if not item_metrics.empty:
        metrics['items_sold'] = float(item_metrics['TotalItemsSold'].iloc[0] or 0)
        metrics['gross_profit_before_excise'] = float(item_metrics['GrossProfitBeforeExcise'].iloc[0] or 0)
    else:
        metrics['items_sold'] = 0.0
        metrics['gross_profit_before_excise'] = 0.0

    # Calculate excise tax
    excise_paid, _ = calculate_excise_tax(db, start_sql, end_sql)
    excise_collected, _ = calculate_excise_collected(db, start_sql, end_sql)

    metrics['excise_paid'] = float(excise_paid or 0)
    metrics['excise_collected'] = float(excise_collected or 0)

    # Calculate net profit (gross profit - excise collected)
    metrics['gross_profit'] = metrics['gross_profit_before_excise'] - metrics['excise_collected']
    metrics['gross_profit_margin'] = (metrics['gross_profit'] / metrics['revenue'] * 100) if metrics['revenue'] > 0 else 0.0

    # Round to 2 decimal places
    for key in ['revenue', 'avg_ticket', 'items_sold', 'gross_profit_before_excise',
                'excise_paid', 'excise_collected', 'gross_profit', 'gross_profit_margin']:
        if key in metrics:
            metrics[key] = round(metrics[key], 2)

    return metrics

def _calculate_changes(current: dict, comparison: dict) -> dict:
    """
    Calculate percentage changes between current and comparison periods.
    """
    changes = {}

    metrics_to_compare = [
        'revenue', 'transactions', 'unique_customers', 'avg_ticket',
        'items_sold', 'gross_profit', 'excise_paid', 'excise_collected'
    ]

    for metric in metrics_to_compare:
        current_val = current.get(metric, 0)
        comparison_val = comparison.get(metric, 0)

        if comparison_val == 0:
            change = 0.0 if current_val == 0 else 100.0
        else:
            change = ((current_val - comparison_val) / comparison_val) * 100

        changes[f"{metric}_change"] = round(change, 2)

    return changes

@business_bp.route('/sales-performance', methods=['GET'])
def sales_performance():
    """
    GET /api/business-overview/sales-performance

    Detailed sales breakdown by ALL products and categories with gross profit analysis.

    Query Parameters:
        period (str): Predefined period (today, 7d, 30d, MTD, YTD) - default: today
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)
        limit (int): Limit number of products returned (default: 100, max: 1000)

    Returns:
        JSON with top products and category performance
    """
    try:
        # Parse date range
        period = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))

        if limit > 1000:
            limit = 1000

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Top products query (from Executive_Dashboard.py:353-375)
        product_query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            SUM(te.Quantity) as QuantitySold,
            SUM(te.Price * te.Quantity) as Sales,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                THEN pue.PriceC * pue.Quantity
                ELSE 0 END), 0) as ExciseTax
        FROM [Transaction] t WITH (NOLOCK)
        JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
            ON t.TransactionNumber = pue.TransactionNumber
            AND te.ItemID = pue.ItemID
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        GROUP BY i.Description, i.ItemLookupCode
        ORDER BY Sales DESC
        """

        products = db.execute_query(product_query)

        # Category performance query (from Executive_Dashboard.py:303-327)
        category_query = f"""
        SELECT
            c.Name as Category,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as QuantitySold,
            SUM(te.Price * te.Quantity) as Sales,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                THEN pue.PriceC * pue.Quantity
                ELSE 0 END), 0) as ExciseTax
        FROM [Transaction] t WITH (NOLOCK)
        JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        JOIN Category c WITH (NOLOCK)
            ON i.CategoryID = c.ID
        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
            ON t.TransactionNumber = pue.TransactionNumber
            AND te.ItemID = pue.ItemID
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        GROUP BY c.Name
        ORDER BY Sales DESC
        """

        categories = db.execute_query(category_query)

        # Format products
        products_list = []
        if not products.empty:
            for _, row in products.iterrows():
                net_profit = row['GrossProfit'] - row['ExciseTax']
                net_margin = (net_profit / row['Sales'] * 100) if row['Sales'] > 0 else 0

                products_list.append({
                    "product": row['Product'],
                    "sku": row['SKU'],
                    "units_sold": int(row['QuantitySold']),
                    "revenue": round(float(row['Sales']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2),
                    "excise_tax": round(float(row['ExciseTax']), 2),
                    "net_profit": round(float(net_profit), 2),
                    "net_margin": round(float(net_margin), 2)
                })

        # Format categories
        categories_list = []
        total_sales = 0
        if not categories.empty:
            total_sales = categories['Sales'].sum()

            for _, row in categories.iterrows():
                net_profit = row['GrossProfit'] - row['ExciseTax']
                net_margin = (net_profit / row['Sales'] * 100) if row['Sales'] > 0 else 0
                pct_of_total = (row['Sales'] / total_sales * 100) if total_sales > 0 else 0

                categories_list.append({
                    "category_name": row['Category'],
                    "revenue": round(float(row['Sales']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2),
                    "excise_tax": round(float(row['ExciseTax']), 2),
                    "net_profit": round(float(net_profit), 2),
                    "net_margin": round(float(net_margin), 2),
                    "units_sold": int(row['QuantitySold']),
                    "transaction_count": int(row['Transactions']),
                    "pct_of_total": round(float(pct_of_total), 2)
                })

        return jsonify({
            "top_products": products_list,
            "categories": categories_list,
            "period_info": {
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d')
            }
        })

    except ValueError as e:
        return jsonify({"error": "Invalid parameters", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal error", "message": str(e)}), 500

@business_bp.route('/sales-trends', methods=['GET'])
def sales_trends():
    """
    GET /api/business-overview/sales-trends

    Returns daily sales data for creating trend line charts.

    Query Parameters:
        period (str): Predefined period (today, 7d, 30d, MTD, YTD) - default: 30d
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)

    Returns:
        JSON with daily trends and summary statistics
    """
    try:
        # Parse date range
        period = request.args.get('period', '30d')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Daily sales trend query (from Executive_Dashboard.py:260-270)
        trend_query = f"""
        SELECT
            CAST(t.Time as DATE) as SalesDate,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(t.Total) as DailySales,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers
        FROM [Transaction] t WITH (NOLOCK)
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        GROUP BY CAST(t.Time as DATE)
        ORDER BY SalesDate
        """

        trend = db.execute_query(trend_query)

        # Format trends
        trends_list = []
        if not trend.empty:
            for _, row in trend.iterrows():
                trends_list.append({
                    "date": row['SalesDate'].strftime('%Y-%m-%d'),
                    "revenue": round(float(row['DailySales']), 2),
                    "transactions": int(row['Transactions']),
                    "customers": int(row['UniqueCustomers'])
                })

            # Calculate summary statistics
            total_days = len(trends_list)
            avg_daily_revenue = trend['DailySales'].mean()
            avg_daily_transactions = trend['Transactions'].mean()

            best_day_idx = trend['DailySales'].idxmax()
            worst_day_idx = trend['DailySales'].idxmin()

            best_day = {
                "date": trend.loc[best_day_idx, 'SalesDate'].strftime('%Y-%m-%d'),
                "revenue": round(float(trend.loc[best_day_idx, 'DailySales']), 2)
            }

            worst_day = {
                "date": trend.loc[worst_day_idx, 'SalesDate'].strftime('%Y-%m-%d'),
                "revenue": round(float(trend.loc[worst_day_idx, 'DailySales']), 2)
            }

            summary = {
                "total_days": total_days,
                "avg_daily_revenue": round(float(avg_daily_revenue), 2),
                "avg_daily_transactions": round(float(avg_daily_transactions), 2),
                "best_day": best_day,
                "worst_day": worst_day
            }
        else:
            summary = {
                "total_days": 0,
                "avg_daily_revenue": 0.0,
                "avg_daily_transactions": 0.0,
                "best_day": None,
                "worst_day": None
            }

        return jsonify({
            "trends": trends_list,
            "summary": summary,
            "period_info": {
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d')
            }
        })

    except ValueError as e:
        return jsonify({"error": "Invalid parameters", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal error", "message": str(e)}), 500
