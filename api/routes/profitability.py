"""
Profitability analysis endpoints.

These endpoints extract and wrap logic from the Streamlit Profitability Analysis page.
"""
import sys
from pathlib import Path
from flask import Blueprint, jsonify, request

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Try pyodbc first (works better on macOS), fall back to pymssql
try:
    from database.sql_server_pyodbc import db
except ImportError:
    from database.sql_server import db
from utils.excise_tax import calculate_excise_collected
from utils.date_utils import parse_period, format_date_for_sql

profitability_bp = Blueprint('profitability', __name__)

@profitability_bp.route('/analysis', methods=['GET'])
def profitability_analysis():
    """
    GET /api/profitability/analysis

    Overall profitability metrics and breakdown by category.

    Query Parameters:
        period (str): Predefined period (today, 7d, 30d, MTD, YTD) - default: 30d
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)

    Returns:
        JSON with overall profitability and category breakdown

    Example:
        GET /api/profitability/analysis?period=30d

        Response:
        {
            "overall": {
                "total_revenue": 285000.00,
                "total_cost": 214500.00,
                "gross_profit": 70500.00,
                "excise_collected": 15000.00,
                "net_profit": 55500.00,
                "gross_margin": 24.74,
                "net_margin": 19.47
            },
            "categories": [...]
        }
    """
    try:
        # Parse date range
        period = request.args.get('period', '30d')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Overall profitability (from Profitability_Analysis.py:105-114)
        overall_query = f"""
        SELECT
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM [Transaction] t WITH (NOLOCK)
        INNER JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        """

        overall = db.execute_query(overall_query)

        if overall.empty or overall['TotalRevenue'].iloc[0] is None:
            return jsonify({
                "overall": {
                    "total_revenue": 0.0,
                    "total_cost": 0.0,
                    "gross_profit": 0.0,
                    "excise_collected": 0.0,
                    "net_profit": 0.0,
                    "gross_margin": 0.0,
                    "net_margin": 0.0,
                    "average_markup": 0.0
                },
                "categories": [],
                "period_info": {
                    "start_date": start.strftime('%Y-%m-%d'),
                    "end_date": end.strftime('%Y-%m-%d')
                }
            })

        revenue = float(overall['TotalRevenue'].iloc[0])
        cost = float(overall['TotalCost'].iloc[0])
        gross_profit = float(overall['GrossProfit'].iloc[0])

        # Get excise tax collected
        excise_collected, _ = calculate_excise_collected(db, start_sql, end_sql)
        excise_collected = excise_collected or 0

        # Calculate net profit
        net_profit = gross_profit - excise_collected
        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
        net_margin = (net_profit / revenue * 100) if revenue > 0 else 0
        avg_markup = ((revenue - cost) / cost * 100) if cost > 0 else 0

        # Category profitability (from Profitability_Analysis.py:246-271)
        category_query = f"""
        SELECT
            c.Name as Category,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as Cost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                THEN pue.PriceC * pue.Quantity
                ELSE 0 END), 0) as ExciseTax
        FROM [Transaction] t WITH (NOLOCK)
        INNER JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        INNER JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        INNER JOIN Category c WITH (NOLOCK)
            ON i.CategoryID = c.ID
        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
            ON t.TransactionNumber = pue.TransactionNumber
            AND te.ItemID = pue.ItemID
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        GROUP BY c.Name
        ORDER BY GrossProfit DESC
        """

        categories = db.execute_query(category_query)

        # Format categories
        categories_list = []
        if not categories.empty:
            for _, row in categories.iterrows():
                cat_net_profit = row['GrossProfit'] - row['ExciseTax']
                cat_gross_margin = (row['GrossProfit'] / row['Revenue'] * 100) if row['Revenue'] > 0 else 0
                cat_net_margin = (cat_net_profit / row['Revenue'] * 100) if row['Revenue'] > 0 else 0
                pct_of_revenue = (row['Revenue'] / revenue * 100) if revenue > 0 else 0

                categories_list.append({
                    "category": row['Category'],
                    "transactions": int(row['Transactions']),
                    "units_sold": float(row['UnitsSold']),
                    "revenue": round(float(row['Revenue']), 2),
                    "cost": round(float(row['Cost']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2),
                    "excise_tax": round(float(row['ExciseTax']), 2),
                    "net_profit": round(float(cat_net_profit), 2),
                    "gross_margin": round(float(cat_gross_margin), 2),
                    "net_margin": round(float(cat_net_margin), 2),
                    "pct_of_revenue": round(float(pct_of_revenue), 2)
                })

        return jsonify({
            "overall": {
                "total_revenue": round(revenue, 2),
                "total_cost": round(cost, 2),
                "gross_profit": round(gross_profit, 2),
                "excise_collected": round(excise_collected, 2),
                "net_profit": round(net_profit, 2),
                "gross_margin": round(gross_margin, 2),
                "net_margin": round(net_margin, 2),
                "average_markup": round(avg_markup, 2)
            },
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

@profitability_bp.route('/top-products', methods=['GET'])
def top_products():
    """
    GET /api/profitability/top-products

    Top products by profit with detailed margin analysis.

    Query Parameters:
        period (str): Predefined period (default: 30d)
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)
        limit (int): Number of products (default: 20, max: 100)

    Returns:
        JSON with top products by net profit
    """
    try:
        # Parse parameters
        period = request.args.get('period', '30d')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 20))

        if limit > 100:
            limit = 100

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Top products query (from Profitability_Analysis.py:320-348)
        product_query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            c.Name as Category,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as Cost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                THEN pue.PriceC * pue.Quantity
                ELSE 0 END), 0) as ExciseTax,
            AVG(te.Price) as AvgPrice,
            AVG(te.Cost) as AvgCost
        FROM [Transaction] t WITH (NOLOCK)
        INNER JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        INNER JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        INNER JOIN Category c WITH (NOLOCK)
            ON i.CategoryID = c.ID
        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
            ON t.TransactionNumber = pue.TransactionNumber
            AND te.ItemID = pue.ItemID
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        GROUP BY i.Description, i.ItemLookupCode, c.Name
        ORDER BY GrossProfit DESC
        """

        products = db.execute_query(product_query)

        # Format products
        products_list = []
        if not products.empty:
            for _, row in products.iterrows():
                net_profit = row['GrossProfit'] - row['ExciseTax']
                gross_margin = (row['GrossProfit'] / row['Revenue'] * 100) if row['Revenue'] > 0 else 0
                net_margin = (net_profit / row['Revenue'] * 100) if row['Revenue'] > 0 else 0
                markup = ((row['AvgPrice'] - row['AvgCost']) / row['AvgCost'] * 100) if row['AvgCost'] > 0 else 0

                products_list.append({
                    "product": row['Product'],
                    "sku": row['SKU'],
                    "category": row['Category'],
                    "units_sold": float(row['UnitsSold']),
                    "revenue": round(float(row['Revenue']), 2),
                    "cost": round(float(row['Cost']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2),
                    "excise_tax": round(float(row['ExciseTax']), 2),
                    "net_profit": round(float(net_profit), 2),
                    "gross_margin": round(float(gross_margin), 2),
                    "net_margin": round(float(net_margin), 2),
                    "avg_price": round(float(row['AvgPrice']), 2),
                    "avg_cost": round(float(row['AvgCost']), 2),
                    "markup": round(float(markup), 2)
                })

        return jsonify({
            "products": products_list,
            "period_info": {
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d')
            }
        })

    except ValueError as e:
        return jsonify({"error": "Invalid parameters", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal error", "message": str(e)}), 500

@profitability_bp.route('/loss-leaders', methods=['GET'])
def loss_leaders():
    """
    GET /api/profitability/loss-leaders

    Products with lowest profit margins but decent sales volume.

    Query Parameters:
        period (str): Predefined period (default: 30d)
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)
        limit (int): Number of products (default: 20, max: 100)
        min_quantity (int): Minimum quantity sold to include (default: 5)

    Returns:
        JSON with loss leader products
    """
    try:
        # Parse parameters
        period = request.args.get('period', '30d')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 20))
        min_quantity = int(request.args.get('min_quantity', 5))

        if limit > 100:
            limit = 100

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Loss leaders query (from Profitability_Analysis.py:381-409)
        query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            c.Name as Category,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as Cost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                THEN pue.PriceC * pue.Quantity
                ELSE 0 END), 0) as ExciseTax,
            AVG(te.Price) as AvgPrice,
            AVG(te.Cost) as AvgCost
        FROM [Transaction] t WITH (NOLOCK)
        INNER JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        INNER JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        INNER JOIN Category c WITH (NOLOCK)
            ON i.CategoryID = c.ID
        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
            ON t.TransactionNumber = pue.TransactionNumber
            AND te.ItemID = pue.ItemID
        WHERE t.Time >= '{start_sql}'
          AND t.Time <= '{end_sql}'
        GROUP BY i.Description, i.ItemLookupCode, c.Name
        HAVING SUM(te.Quantity) > {min_quantity}
        ORDER BY ((SUM((te.Price - te.Cost) * te.Quantity) - ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL' THEN pue.PriceC * pue.Quantity ELSE 0 END), 0)) / NULLIF(SUM(te.Price * te.Quantity), 0)) ASC
        """

        products = db.execute_query(query)

        # Format products
        products_list = []
        if not products.empty:
            for _, row in products.iterrows():
                net_profit = row['GrossProfit'] - row['ExciseTax']
                gross_margin = (row['GrossProfit'] / row['Revenue'] * 100) if row['Revenue'] > 0 else 0
                net_margin = (net_profit / row['Revenue'] * 100) if row['Revenue'] > 0 else 0
                markup = ((row['AvgPrice'] - row['AvgCost']) / row['AvgCost'] * 100) if row['AvgCost'] > 0 else 0

                products_list.append({
                    "product": row['Product'],
                    "sku": row['SKU'],
                    "category": row['Category'],
                    "units_sold": float(row['UnitsSold']),
                    "revenue": round(float(row['Revenue']), 2),
                    "cost": round(float(row['Cost']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2),
                    "excise_tax": round(float(row['ExciseTax']), 2),
                    "net_profit": round(float(net_profit), 2),
                    "gross_margin": round(float(gross_margin), 2),
                    "net_margin": round(float(net_margin), 2),
                    "avg_price": round(float(row['AvgPrice']), 2),
                    "avg_cost": round(float(row['AvgCost']), 2),
                    "markup": round(float(markup), 2)
                })

        return jsonify({
            "products": products_list,
            "note": "These products have the lowest NET profit margins but decent sales volume. Consider price increases or promotions.",
            "period_info": {
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d')
            }
        })

    except ValueError as e:
        return jsonify({"error": "Invalid parameters", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal error", "message": str(e)}), 500
