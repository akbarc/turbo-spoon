"""
Excise tax reporting endpoints.

These endpoints extract and wrap logic from the Streamlit Excise Tax Reporting page.
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
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected, get_excise_breakdown
from utils.date_utils import parse_period, format_date_for_sql

excise_bp = Blueprint('excise_tax', __name__)

@excise_bp.route('/report', methods=['GET'])
def excise_tax_report():
    """
    GET /api/excise-tax/report

    Comprehensive excise tax reporting with PAID/COLLECTED breakdown by category.

    Query Parameters:
        period (str): Predefined period (today, 7d, 30d, MTD, YTD) - default: last_month
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)

    Returns:
        JSON with excise tax summary, category breakdowns, and compliance status

    Example:
        GET /api/excise-tax/report?period=last_month

        Response:
        {
            "summary": {
                "excise_paid": 30568.20,
                "excise_collected": 66828.73,
                "difference": 36260.53,
                "recovery_rate": 45.7
            },
            "paid_breakdown": [...],
            "collected_breakdown": [...],
            "compliance_status": "OK",
            "notes": [...]
        }
    """
    try:
        # Parse date range (default to last month for tax reporting)
        period = request.args.get('period', 'last_month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Calculate excise tax totals (from Excise_Tax_Reporting.py:105-118)
        excise_paid, paid_error = calculate_excise_tax(db, start_sql, end_sql)
        excise_collected, coll_error = calculate_excise_collected(db, start_sql, end_sql)

        excise_paid = excise_paid or 0
        excise_collected = excise_collected or 0

        # Calculate summary metrics
        difference = excise_collected - excise_paid
        diff_pct = (difference / excise_collected * 100) if excise_collected > 0 else 0
        recovery_rate = (excise_paid / excise_collected * 100) if excise_collected > 0 else 0

        # Get category breakdowns (from Excise_Tax_Reporting.py:212-252)
        paid_breakdown, _ = get_excise_breakdown(db, start_sql, end_sql, 'PAID')
        coll_breakdown, _ = get_excise_breakdown(db, start_sql, end_sql, 'COLL')

        # Format paid breakdown
        paid_list = []
        if paid_breakdown is not None and not paid_breakdown.empty:
            total_paid = paid_breakdown['TotalExcise'].sum()
            for _, row in paid_breakdown.iterrows():
                percentage = (row['TotalExcise'] / total_paid * 100) if total_paid > 0 else 0
                paid_list.append({
                    "category": row['Category'],
                    "description": _get_tax_category_description(row['Category']),
                    "total_excise": round(float(row['TotalExcise']), 2),
                    "entry_count": int(row['EntryCount']),
                    "percentage": round(float(percentage), 2)
                })

        # Format collected breakdown
        coll_list = []
        if coll_breakdown is not None and not coll_breakdown.empty:
            total_coll = coll_breakdown['TotalExcise'].sum()
            for _, row in coll_breakdown.iterrows():
                percentage = (row['TotalExcise'] / total_coll * 100) if total_coll > 0 else 0
                coll_list.append({
                    "category": row['Category'],
                    "description": _get_tax_category_description(row['Category']),
                    "total_excise": round(float(row['TotalExcise']), 2),
                    "entry_count": int(row['EntryCount']),
                    "percentage": round(float(percentage), 2)
                })

        # Determine compliance status
        if difference < 0:
            compliance_status = "WARNING"
            compliance_message = "Tax PAID exceeds tax COLLECTED - review data"
        elif excise_paid == 0 and excise_collected == 0:
            compliance_status = "NO_DATA"
            compliance_message = "No excise tax data for this period"
        else:
            compliance_status = "OK"
            compliance_message = f"Tax reconciliation OK: Collecting ${difference:,.2f} more than paying"

        return jsonify({
            "summary": {
                "excise_paid": round(float(excise_paid), 2),
                "excise_collected": round(float(excise_collected), 2),
                "difference": round(float(difference), 2),
                "difference_pct": round(float(diff_pct), 2),
                "recovery_rate": round(float(recovery_rate), 2)
            },
            "paid_breakdown": paid_list,
            "collected_breakdown": coll_list,
            "compliance_status": compliance_status,
            "compliance_message": compliance_message,
            "notes": [
                "Excise PAID = Tax paid to state (reduce gross profit)",
                "Excise COLLECTED = Tax from customers (remit to state)",
                "Recovery Rate = What % of collected tax you pay to state"
            ],
            "period_info": {
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d')
            }
        })

    except ValueError as e:
        return jsonify({"error": "Invalid parameters", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal error", "message": str(e)}), 500

@excise_bp.route('/products', methods=['GET'])
def excise_tax_products():
    """
    GET /api/excise-tax/products

    Product-level excise tax details showing which products generate the most tax.

    Query Parameters:
        period (str): Predefined period (default: last_month)
        start_date (str): Custom start date (YYYY-MM-DD)
        end_date (str): Custom end date (YYYY-MM-DD)
        limit (int): Limit number of products (default: 20, max: 100)

    Returns:
        JSON with top products by excise tax
    """
    try:
        # Parse parameters
        period = request.args.get('period', 'last_month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 20))

        if limit > 100:
            limit = 100

        start, end = parse_period(period, start_date, end_date)
        start_sql = format_date_for_sql(start)
        end_sql = format_date_for_sql(end)

        # Product-level excise query (from Excise_Tax_Reporting.py:284-302)
        product_query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            pue.SubDescription3 as TaxCategory,
            COUNT(*) as Transactions,
            SUM(pue.Quantity) as TotalQuantity,
            SUM(pue.PriceC * pue.Quantity) as TotalExciseTax,
            AVG(pue.PriceC) as AvgTaxPerUnit,
            SUM(pue.Price * pue.Quantity) as TotalSales
        FROM PUExciseEntry pue WITH (NOLOCK)
        INNER JOIN Item i WITH (NOLOCK)
            ON pue.ItemID = i.ID
        WHERE pue.TransactionTime >= '{start_sql}'
          AND pue.TransactionTime <= '{end_sql}'
          AND pue.SubDescription3 LIKE '%PAID'
        GROUP BY i.Description, i.ItemLookupCode, pue.SubDescription3
        ORDER BY TotalExciseTax DESC
        """

        products = db.execute_query(product_query)

        # Format products
        products_list = []
        if not products.empty:
            for _, row in products.iterrows():
                tax_pct_of_sales = (row['TotalExciseTax'] / row['TotalSales'] * 100) if row['TotalSales'] > 0 else 0

                products_list.append({
                    "product": row['Product'],
                    "sku": row['SKU'],
                    "tax_category": row['TaxCategory'],
                    "tax_description": _get_tax_category_description(row['TaxCategory']),
                    "transactions": int(row['Transactions']),
                    "total_quantity": float(row['TotalQuantity']),
                    "total_excise_tax": round(float(row['TotalExciseTax']), 2),
                    "avg_tax_per_unit": round(float(row['AvgTaxPerUnit']), 2),
                    "total_sales": round(float(row['TotalSales']), 2),
                    "tax_pct_of_sales": round(float(tax_pct_of_sales), 2)
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

@excise_bp.route('/categories', methods=['GET'])
def tax_categories():
    """
    GET /api/excise-tax/categories

    Returns reference information about tax categories and rates.

    Returns:
        JSON with tax category descriptions and approximate rates
    """
    categories = [
        {
            "code": "LC23PAID/COLL",
            "description": "Large Cigars",
            "approx_rate": "~23%",
            "note": "Based on product cost"
        },
        {
            "code": "LC25PAID/COLL",
            "description": "Little Cigars",
            "approx_rate": "~25%",
            "note": "Based on product cost"
        },
        {
            "code": "LT10PAID/COLL",
            "description": "Loose Tobacco",
            "approx_rate": "~10%",
            "note": "Based on product cost"
        },
        {
            "code": "SL10PAID/COLL",
            "description": "Smokeless Tobacco",
            "approx_rate": "~10%",
            "note": "Based on product cost"
        },
        {
            "code": "VD07PAID/COLL",
            "description": "Vape Device",
            "approx_rate": "~7%",
            "note": "Based on product cost"
        },
        {
            "code": "VO07PAID/COLL",
            "description": "Vapors Open",
            "approx_rate": "~7%",
            "note": "Based on product cost"
        },
        {
            "code": "VC05PAID/COLL",
            "description": "Vapors Closed",
            "approx_rate": "~5%",
            "note": "Based on product cost"
        }
    ]

    return jsonify({
        "categories": categories,
        "notes": [
            "PAID suffix = Tax paid to state (subtract from gross profit)",
            "COLL suffix = Tax collected from customers (must remit to state)",
            "Rates are approximate - actual tax calculated from PUExciseEntry.PriceC field"
        ]
    })

def _get_tax_category_description(category_code: str) -> str:
    """Get human-readable description for tax category code."""
    descriptions = {
        "LC23PAID": "Large Cigars (~23%) - PAID",
        "LC23COLL": "Large Cigars (~23%) - COLLECTED",
        "LC25PAID": "Little Cigars (~25%) - PAID",
        "LC25COLL": "Little Cigars (~25%) - COLLECTED",
        "LT10PAID": "Loose Tobacco (~10%) - PAID",
        "LT10COLL": "Loose Tobacco (~10%) - COLLECTED",
        "SL10PAID": "Smokeless Tobacco (~10%) - PAID",
        "SL10COLL": "Smokeless Tobacco (~10%) - COLLECTED",
        "VD07PAID": "Vape Device (~7%) - PAID",
        "VD07COLL": "Vape Device (~7%) - COLLECTED",
        "VO07PAID": "Vapors Open (~7%) - PAID",
        "VO07COLL": "Vapors Open (~7%) - COLLECTED",
        "VC05PAID": "Vapors Closed (~5%) - PAID",
        "VC05COLL": "Vapors Closed (~5%) - COLLECTED"
    }

    return descriptions.get(category_code, category_code)
