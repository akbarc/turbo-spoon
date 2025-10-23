"""
Georgia Dashboard REST API - Simple single-file version
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add src to path (same as app.py)
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import database connection (same as Streamlit app)
try:
    from database.sql_server_pyodbc import db
    print("✅ Using pyodbc for database connection")
except ImportError:
    from database.sql_server import db
    print("✅ Using pymssql for database connection")

from utils.excise_tax import calculate_excise_tax, calculate_excise_collected

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_period(period=None, start_date=None, end_date=None):
    """Parse period parameter into start and end dates."""
    today = datetime.now()

    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        return start, end

    if not period:
        period = 'today'

    period = period.lower()

    if period == 'today':
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == '7d':
        start = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == '30d':
        start = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'mtd':
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'ytd':
        start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'last_month':
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start = last_day_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_day_last_month.replace(hour=23, minute=59, second=59)
    else:
        raise ValueError(f"Unknown period: {period}")

    return start, end

def format_date_for_sql(dt):
    """Format datetime for SQL Server."""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    """API root endpoint."""
    return jsonify({
        "name": "Georgia Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "executive_summary": "/api/executive-summary",
            "sales_performance": "/api/sales-performance",
            "excise_tax": "/api/excise-tax"
        }
    })

@app.route('/api/health')
def health():
    """Health check endpoint."""
    try:
        success, message = db.test_connection()
        return jsonify({
            "status": "ok" if success else "error",
            "database": "connected" if success else "disconnected",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "database": "disconnected",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/executive-summary')
def executive_summary():
    """Executive summary with KPIs."""
    try:
        period = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Transaction metrics
        trans_query = f"""
        SELECT
            COUNT(DISTINCT TransactionNumber) as TotalTransactions,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            SUM(Total) as TotalSales,
            AVG(Total) as AvgTransactionValue
        FROM [Transaction]
        WHERE Time >= '{start_sql}' AND Time <= '{end_sql}'
        """

        trans_metrics = db.execute_query(trans_query)

        # Line item metrics
        lineitem_query = f"""
        SELECT
            SUM(te.Quantity) as TotalItemsSold,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfitBeforeExcise
        FROM TransactionEntry te
        INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber AND te.StoreID = t.StoreID
        WHERE t.Time >= '{start_sql}' AND t.Time <= '{end_sql}'
        """

        item_metrics = db.execute_query(lineitem_query)

        # Get excise tax
        excise_paid, _ = calculate_excise_tax(db, start_sql, end_sql)
        excise_collected, _ = calculate_excise_collected(db, start_sql, end_sql)

        excise_paid = excise_paid or 0
        excise_collected = excise_collected or 0

        # Build response
        if not trans_metrics.empty:
            revenue = float(trans_metrics['TotalSales'].iloc[0] or 0)
            transactions = int(trans_metrics['TotalTransactions'].iloc[0] or 0)
            customers = int(trans_metrics['UniqueCustomers'].iloc[0] or 0)
            avg_ticket = float(trans_metrics['AvgTransactionValue'].iloc[0] or 0)

            items_sold = float(item_metrics['TotalItemsSold'].iloc[0] or 0) if not item_metrics.empty else 0
            gross_profit_before = float(item_metrics['GrossProfitBeforeExcise'].iloc[0] or 0) if not item_metrics.empty else 0
            gross_profit = gross_profit_before - excise_collected
            gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0

            return jsonify({
                "revenue": round(revenue, 2),
                "transactions": transactions,
                "unique_customers": customers,
                "avg_ticket": round(avg_ticket, 2),
                "items_sold": round(items_sold, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_margin": round(gross_margin, 2),
                "excise_paid": round(excise_paid, 2),
                "excise_collected": round(excise_collected, 2),
                "period": {
                    "start": start.strftime('%Y-%m-%d'),
                    "end": end.strftime('%Y-%m-%d')
                }
            })
        else:
            return jsonify({"error": "No data found for period"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sales-performance')
def sales_performance():
    """Sales performance by product and category."""
    try:
        period = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 20))

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Top products
        product_query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            SUM(te.Quantity) as QuantitySold,
            SUM(te.Price * te.Quantity) as Sales,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM [Transaction] t WITH (NOLOCK)
        JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        WHERE t.Time >= '{start_sql}' AND t.Time <= '{end_sql}'
        GROUP BY i.Description, i.ItemLookupCode
        ORDER BY Sales DESC
        """

        products = db.execute_query(product_query)

        # Categories
        category_query = f"""
        SELECT
            c.Name as Category,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as QuantitySold,
            SUM(te.Price * te.Quantity) as Sales,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM [Transaction] t WITH (NOLOCK)
        JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        JOIN Item i WITH (NOLOCK)
            ON te.ItemID = i.ID
        JOIN Category c WITH (NOLOCK)
            ON i.CategoryID = c.ID
        WHERE t.Time >= '{start_sql}' AND t.Time <= '{end_sql}'
        GROUP BY c.Name
        ORDER BY Sales DESC
        """

        categories = db.execute_query(category_query)

        # Format response
        products_list = []
        if not products.empty:
            for _, row in products.iterrows():
                products_list.append({
                    "product": row['Product'],
                    "sku": row['SKU'],
                    "units_sold": int(row['QuantitySold']),
                    "revenue": round(float(row['Sales']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2)
                })

        categories_list = []
        if not categories.empty:
            for _, row in categories.iterrows():
                categories_list.append({
                    "category": row['Category'],
                    "transactions": int(row['Transactions']),
                    "units_sold": int(row['QuantitySold']),
                    "revenue": round(float(row['Sales']), 2),
                    "gross_profit": round(float(row['GrossProfit']), 2)
                })

        return jsonify({
            "products": products_list,
            "categories": categories_list,
            "period": {
                "start": start.strftime('%Y-%m-%d'),
                "end": end.strftime('%Y-%m-%d')
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/excise-tax')
def excise_tax():
    """Excise tax report."""
    try:
        period = request.args.get('period', 'last_month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Calculate excise tax
        excise_paid, _ = calculate_excise_tax(db, start_sql, end_sql)
        excise_collected, _ = calculate_excise_collected(db, start_sql, end_sql)

        excise_paid = excise_paid or 0
        excise_collected = excise_collected or 0
        difference = excise_collected - excise_paid
        recovery_rate = (excise_paid / excise_collected * 100) if excise_collected > 0 else 0

        return jsonify({
            "excise_paid": round(excise_paid, 2),
            "excise_collected": round(excise_collected, 2),
            "difference": round(difference, 2),
            "recovery_rate": round(recovery_rate, 2),
            "period": {
                "start": start.strftime('%Y-%m-%d'),
                "end": end.strftime('%Y-%m-%d')
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5000))
    host = os.getenv('API_HOST', '0.0.0.0')

    print(f"\n🚀 Starting Georgia Dashboard API on {host}:{port}")
    print(f"📍 Health check: http://localhost:{port}/api/health")
    print(f"📚 Documentation: http://localhost:{port}/\n")

    app.run(host=host, port=port, debug=False, threaded=True)
