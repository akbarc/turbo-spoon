#!/usr/bin/env python3
"""
Georgia Dashboard - Clean Business Overview with AI Assistant
Built from scratch with only essential functionality
"""

import os
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from flask import Flask, jsonify, request, Response, render_template
from flask_cors import CORS
import threading

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database imports
from database_pymssql import SQLServerConnection

# AI Assistant imports - Using new simplified version
from app.ai_sql_assistant import AISQLAssistant

# AR Dashboard imports
from app.ar_dashboard import register_ar_routes

# Cohort Analysis imports
from app.cohort_dashboard import register_cohort_routes

# Customer Ledger imports
from app.customer_ledger_api import register_ledger_routes

# Customer Balance API imports
from modules.customer_balance_api import customer_balance_api

# Transaction Detail API imports
from modules.transaction_detail_api import transaction_detail_api

# Professional Excel Export API imports
from modules.professional_excel_export import professional_excel_api

# GP Analysis imports
from modules.gp_analysis import GPAnalysis


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app with proper paths
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
CORS(app)

# Global database connection with simple caching
db = None
db_lock = threading.RLock()

# Simple query cache for performance
query_cache = {}
cache_timestamps = {}
CACHE_TTL = 300  # 5 minutes

# AI Assistant setup
AI_AVAILABLE = False
ai_assistant = None

def with_db_lock(func):
    """Decorator to ensure thread-safe database operations"""
    def wrapper(*args, **kwargs):
        with db_lock:
            return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def decimal_default(obj):
    """JSON encoder for Decimal and other non-serializable objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        # Try to decode bytes as UTF-8, otherwise convert to hex string
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return obj.hex()
    if hasattr(obj, 'isoformat'):  # datetime/Timestamp objects
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def init_database():
    """Initialize database connection"""
    global db
    try:
        db = SQLServerConnection()
        logger.info("✅ Database connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def init_ai_assistant():
    """Initialize AI assistant"""
    global AI_AVAILABLE, ai_assistant
    try:
        ai_assistant = AISQLAssistant()
        AI_AVAILABLE = True
        logger.info("✅ AI Assistant initialized successfully")
    except Exception as e:
        logger.error(f"❌ AI Assistant initialization failed: {e}")
        AI_AVAILABLE = False

# ===================
# MAIN ROUTES
# ===================

@app.route('/')
def home():
    """Executive Dashboard Frontend"""
    return render_template('executive_dashboard.html')

@app.route('/ai-assistant')
def ai_assistant_page():
    """AI Assistant Interface"""
    return render_template('ai_assistant.html')

@app.route('/customer-ledger')
def customer_ledger_page():
    """Customer Ledger Interface"""
    return render_template('customer_ledger.html')

@app.route('/sales-ops')
def sales_ops_page():
    """Sales/Payments/Operations Interface"""
    return render_template('sales_ops.html')

@app.route('/suppliers')
def suppliers_page():
    """Suppliers/Purchase Orders/Ordering Interface"""
    return render_template('suppliers.html')

@app.route('/wholesale-retail')
def wholesale_retail_page():
    """Wholesale vs Retail GP Analysis Interface"""
    return render_template('wholesale_retail_improved.html')

@app.route('/gp-analysis')
def gp_analysis_page():
    """GP Analysis Dashboard Interface"""
    return render_template('gp_analysis.html')

@app.route('/inventory')
def inventory_page():
    """Inventory Dashboard Interface"""
    return render_template('inventory.html')

@app.route('/ar-dashboard')
def ar_dashboard_page():
    """AR Dashboard Interface"""
    return render_template('ar_dashboard.html')

@app.route('/api')
def api_status():
    """API status endpoint"""
    return jsonify({
        'status': 'running',
        'message': 'Georgia Dashboard API is running',
        'ai_available': AI_AVAILABLE,
        'endpoints': {
            'dashboard': '/',
            'ai_query': '/api/ai/query',
            'executive_summary': '/api/business-overview/executive-summary',
            'sales_performance': '/api/business-overview/sales-performance',
            'inventory_health': '/api/business-overview/inventory-health',
            'customer_intelligence': '/api/business-overview/customer-intelligence',
            'performance_trends': '/api/business-overview/performance-trends'
        }
    })

# ===================
# AI ASSISTANT ROUTES
# ===================

@app.route('/api/ai/query', methods=['POST'])
@with_db_lock
def ai_sql_query():
    """Process natural language business questions using AI"""
    if not AI_AVAILABLE:
        return jsonify({
            'status': 'error',
            'error': 'AI Assistant is not available',
            'message': 'OpenAI API key may not be configured'
        }), 500
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'status': 'error', 'error': 'Question is required'}), 400
        
        # Check if streaming is requested
        if data.get('stream', False):
            def generate():
                feedback_messages = []
                
                def feedback_callback(message):
                    feedback_messages.append({
                        'timestamp': datetime.now().isoformat(),
                        'message': message
                    })
                    yield f"data: {json.dumps({'type': 'feedback', 'message': message})}\n\n"
                
                try:
                    # Process with feedback
                    result = ai_assistant.process_business_question(question, feedback_callback)
                    if result and 'error' not in result:
                        result['feedback_messages'] = feedback_messages
                        yield f"data: {json.dumps({'type': 'result', 'data': result}, default=decimal_default)}\n\n"
                    else:
                        error_msg = result.get('error', 'Unknown AI processing error') if result else 'AI processing failed'
                        yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                finally:
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        else:
            # Regular non-streaming response
            result = ai_assistant.process_business_question(question)
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"AI SQL query error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to process AI query'
        }), 500

@app.route('/api/ai/export/<query_id>')
def ai_export_results(query_id):
    """Export AI query results as CSV"""
    try:
        if not AI_AVAILABLE:
            return jsonify({'error': 'AI Assistant not available'}), 500
        
        results_df = ai_assistant.get_cached_results(query_id)
        if results_df is None:
            return jsonify({'error': 'Query results not found or expired'}), 404
        
        # Convert to CSV
        from io import StringIO
        output = StringIO()
        results_df.to_csv(output, index=False)
        csv_data = output.getvalue()
        
        response = Response(csv_data, mimetype='text/csv')
        response.headers["Content-Disposition"] = f"attachment; filename=query_results_{query_id}.csv"
        return response
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500

# New: refine an existing SQL with a natural-language instruction
@app.route('/api/ai/refine', methods=['POST'])
@with_db_lock
def ai_sql_refine():
    if not AI_AVAILABLE:
        return jsonify({'status': 'error', 'error': 'AI Assistant is not available'}), 500
    try:
        data = request.get_json() or {}
        instruction = data.get('instruction', '').strip()
        previous_sql = (data.get('previous_sql') or '').strip()
        query_id = (data.get('query_id') or '').strip()
        if not instruction:
            return jsonify({'status': 'error', 'error': 'instruction is required'}), 400
        # Resolve previous SQL
        if not previous_sql and query_id:
            prev = ai_assistant.get_cached_sql(query_id)
            if prev:
                previous_sql = prev
        if not previous_sql:
            return jsonify({'status': 'error', 'error': 'previous_sql or query_id required'}), 400
        # Process follow-up
        def generate():
            feedback_messages = []
            def feedback_callback(message):
                feedback_messages.append({'timestamp': datetime.now().isoformat(), 'message': message})
                yield f"data: {json.dumps({'type': 'feedback', 'message': message})}\n\n"
            try:
                result = ai_assistant.process_followup(previous_sql, instruction, feedback_callback)
                if result and 'error' not in result:
                    result['feedback_messages'] = feedback_messages
                    yield f"data: {json.dumps({'type': 'result', 'data': result}, default=decimal_default)}\n\n"
                else:
                    error_msg = result.get('error', 'Unknown AI processing error') if result else 'AI processing failed'
                    yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            finally:
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        # Stream if requested
        if data.get('stream', False):
            return Response(generate(), mimetype='text/event-stream')
        # Non-stream fallback
        result = ai_assistant.process_followup(previous_sql, instruction)
        return jsonify(result)
    except Exception as e:
        logger.error(f"AI SQL refine error: {e}")
        return jsonify({'status': 'error', 'error': str(e), 'message': 'Failed to refine AI query'}), 500

# Allow fetching cached SQL for a query
@app.route('/api/ai/sql/<query_id>')
@with_db_lock
def ai_get_sql(query_id):
    try:
        if not AI_AVAILABLE:
            return jsonify({'error': 'AI Assistant not available'}), 500
        sql_text = ai_assistant.get_cached_sql(query_id)
        if not sql_text:
            return jsonify({'error': 'SQL not found for query_id'}), 404
        return jsonify({'query_id': query_id, 'sql': sql_text})
    except Exception as e:
        logger.error(f"Get SQL error: {e}")
        return jsonify({'error': str(e)}), 500

# ===================
# BUSINESS OVERVIEW ROUTES
# ===================

@app.route('/api/business-overview/executive-summary')
@with_db_lock
def executive_summary():
    """Get executive summary data"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        period = request.args.get('period', 'today')
        custom_start = request.args.get('start_date')
        custom_end = request.args.get('end_date')
        
        # Calculate date range
        if custom_start and custom_end:
            # Custom date range provided
            try:
                start_date = datetime.strptime(custom_start, '%Y-%m-%d')
                end_date = datetime.strptime(custom_end, '%Y-%m-%d')
                # Set end date to end of day for inclusive range
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                logger.info(f"Using custom date range: {start_date} to {end_date}")
            except ValueError as e:
                logger.error(f"Invalid custom date format: {e}")
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            # Use predefined period
            end_date = datetime.now()
            if period == 'today':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == 'MTD':
                start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'YTD':
                start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate comparison period
        period_duration = end_date - start_date
        comp_start = start_date - period_duration
        comp_end = start_date
        
        # Current period metrics
        current_query = """
        SELECT 
            COALESCE(SUM(t.Total), 0) as revenue,
            COUNT(DISTINCT t.TransactionNumber) as transactions,
            COUNT(DISTINCT t.CustomerID) as unique_customers,
            COALESCE(AVG(t.Total), 0) as avg_ticket
        FROM [dbo].[Transaction] t
        WHERE t.Time >= %s AND t.Time <= %s
        """
        
        current_result = db.execute_query(current_query, (start_date, end_date), "Current Period Metrics")
        
        # Comparison period metrics
        comp_result = db.execute_query(current_query, (comp_start, comp_end), "Comparison Period Metrics")
        
        # Gross profit calculation
        profit_query = """
        SELECT 
            COALESCE(SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END), 0) as gross_profit,
            COALESCE(SUM(te.Price * te.Quantity), 0) as total_revenue
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        """
        
        current_profit = db.execute_query(profit_query, (start_date, end_date), "Current Period Profit")
        comp_profit = db.execute_query(profit_query, (comp_start, comp_end), "Comparison Period Profit")
        
        # AR and cash flow metrics
        ar_query = """
        SELECT 
            COALESCE(SUM(c.AccountBalance), 0) as ar_balance,
            COUNT(CASE WHEN c.AccountBalance > 0 THEN 1 END) as customers_with_balance
        FROM dbo.Customer c
        WHERE c.AccountBalance > 0
        """
        
        ar_result = db.execute_query(ar_query, description="AR Balance")
        
        # NSF tracking - proper patterns from documentation
        nsf_query = """
        WITH NSFFees AS (
            -- NSF fees from AccountReceivable ($65 entries with TransactionNumber = 0)
            SELECT 
                COUNT(*) as fee_count,
                SUM(OriginalAmount) as fee_total,
                COUNT(DISTINCT CustomerID) as fee_customers
            FROM dbo.AccountReceivable ar
            WHERE ar.OriginalAmount = 65.00 
                AND ar.TransactionNumber = 0
                AND ar.Date >= %s AND ar.Date <= %s
        ),
        ReturnedChecks AS (
            -- Returned check amounts (the actual bounced check values)
            SELECT 
                COUNT(DISTINCT ar.ID) as returned_count,
                SUM(ar.OriginalAmount) as returned_total,
                COUNT(DISTINCT ar.CustomerID) as returned_customers
            FROM dbo.AccountReceivable ar
            INNER JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
            WHERE (arh.Comment LIKE '%%NSF%%' 
                OR arh.Comment LIKE '%%RET%%' 
                OR arh.Comment LIKE '%%RETURN%%'
                OR arh.Comment LIKE '%%INSUFFICIENT%%'
                OR arh.Comment LIKE '%%BOUNCE%%')
                AND ar.OriginalAmount != 65.00  -- Exclude the fees
                AND ar.Date >= %s AND ar.Date <= %s
        )
        SELECT 
            COALESCE(nf.fee_count, 0) as nsf_count,
            COALESCE(nf.fee_total, 0) as nsf_fees,
            COALESCE(rc.returned_count, 0) as returned_check_count,
            COALESCE(rc.returned_total, 0) as returned_check_amount,
            COALESCE(nf.fee_total, 0) + COALESCE(rc.returned_total, 0) as nsf_total
        FROM NSFFees nf
        CROSS JOIN ReturnedChecks rc
        """
        
        nsf_result = db.execute_query(nsf_query, (start_date, end_date, start_date, end_date), "NSF Tracking")
        
        # Inventory summary
        inventory_query = """
        SELECT 
            COUNT(i.ID) as total_skus,
            COUNT(CASE WHEN i.Quantity > 0 THEN 1 END) as in_stock_skus,
            SUM(i.Quantity * i.Cost) as total_inventory_value,
            -- CORRECTED: Calculate inventory turnover = (COGS for period) / (average inventory value)
            -- Using annualized turnover rate: (COGS * 12) / inventory value for monthly data
            COALESCE((
                SELECT SUM(te.Quantity * i2.Cost)  -- Use COST not PRICE for COGS
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                JOIN dbo.Item i2 ON te.ItemID = i2.ID
                WHERE t.Time >= DATEADD(day, -30, GETDATE())
                AND te.Quantity > 0  -- Only sales, not returns
            ) * 12.0 / NULLIF(SUM(i.Quantity * i.Cost), 0), 0) as monthly_turnover
        FROM dbo.Item i
        WHERE i.Inactive = 0
        """
        
        inventory_result = db.execute_query(inventory_query, description="Inventory Summary")
        
        # CORRECTED AR analysis: Collections vs New AR issued
        # Collections = Customer payments against AR (excluding NSF) + Immediate cash collections
        # New AR issued = ONLY Store credit transactions (TenderID=5)
        ar_analysis_query = """
        SELECT 
            -- Collections: Customer payments against existing AR (excluding NSF)
            COALESCE((
                SELECT SUM(p.Amount) 
                FROM dbo.Payment p
                WHERE p.Time >= %s AND p.Time <= %s
                AND ISNULL(p.Comment, '') NOT LIKE '%NSF%'
            ), 0) +
            -- Plus immediate cash collections (all non-store-credit payments)
            COALESCE((
                SELECT SUM(te.Amount)
                FROM dbo.TenderEntry te
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE t.Time >= %s AND t.Time <= %s
                AND te.TenderID IN (1, 2, 3, 4, 6)  -- Cash, Check, Credit, Debit, Money Order
                AND te.Amount > 0
            ), 0) as collections,
            
            -- New AR issued: ONLY Store credit transactions (TenderID=5)
            COALESCE((
                SELECT SUM(te.Amount)
                FROM dbo.TenderEntry te
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE t.Time >= %s AND t.Time <= %s
                AND te.TenderID = 5  -- Store Credit only
                AND te.Amount > 0
            ), 0) as new_ar_issued,
            
            -- NSF impact (tracked separately)
            COALESCE((
                SELECT SUM(p.Amount)
                FROM dbo.Payment p
                WHERE p.Time >= %s AND p.Time <= %s
                AND p.Comment LIKE '%NSF%'
            ), 0) as nsf_impact,
            
            -- Total collections including NSF (for verification)
            COALESCE((
                SELECT SUM(p.Amount) 
                FROM dbo.Payment p
                WHERE p.Time >= %s AND p.Time <= %s
            ), 0) +
            COALESCE((
                SELECT SUM(te.Amount)
                FROM dbo.TenderEntry te
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE t.Time >= %s AND t.Time <= %s
                AND te.TenderID IN (1, 2, 3, 4, 6)
                AND te.Amount > 0
            ), 0) as total_collections_with_nsf
        """
        
        try:
            ar_analysis_result = db.execute_query(ar_analysis_query, (start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date, start_date, end_date), "AR Analysis")
            
            if not ar_analysis_result.empty:
                ar_analysis_data = ar_analysis_result.iloc[0]
                logger.info(f"AR Analysis: Collections=${ar_analysis_data['collections']}, New AR=${ar_analysis_data['new_ar_issued']}, NSF Impact=${ar_analysis_data['nsf_impact']}")
            else:
                raise Exception("AR analysis returned empty result")
                
        except Exception as e:
            logger.warning(f"AR analysis query failed: {e}, falling back to simple payments query")
            # Fallback to simple query
            payments_query = """
            SELECT COALESCE(SUM(p.Amount), 0) as payments_received
            FROM dbo.Payment p
            WHERE p.Time >= %s AND p.Time <= %s
            """
            payments_result = db.execute_query(payments_query, (start_date, end_date), "Payments Received")
            # Create fallback data structure
            ar_analysis_data = {
                'collections': payments_result.iloc[0]['payments_received'] if not payments_result.empty else 0,
                'new_ar_issued': 0,  # Unknown without tender info
                'nsf_impact': 0,  # Unknown without comment analysis
                'total_collections_with_nsf': payments_result.iloc[0]['payments_received'] if not payments_result.empty else 0
            }
        
        # Calculate trends and format response
        current = current_result.iloc[0] if not current_result.empty else {}
        comparison = comp_result.iloc[0] if not comp_result.empty else {}
        current_gp = current_profit.iloc[0] if not current_profit.empty else {}
        comp_gp = comp_profit.iloc[0] if not comp_profit.empty else {}
        ar_data = ar_result.iloc[0] if not ar_result.empty else {}
        inventory_data = inventory_result.iloc[0] if not inventory_result.empty else {}
        nsf_data = nsf_result.iloc[0] if not nsf_result.empty else {}
        
        # Calculate trends
        def calculate_trend(current_val, comp_val):
            if comp_val and comp_val > 0:
                return ((current_val - comp_val) / comp_val) * 100
            return 0
        
        revenue_trend = calculate_trend(current.get('revenue', 0), comparison.get('revenue', 0))
        profit_trend = calculate_trend(current_gp.get('gross_profit', 0), comp_gp.get('gross_profit', 0))
        transaction_trend = calculate_trend(current.get('transactions', 0), comparison.get('transactions', 0))
        customer_trend = calculate_trend(current.get('unique_customers', 0), comparison.get('unique_customers', 0))
        
        # Calculate profit margin
        total_rev = current_gp.get('total_revenue', 0)
        profit_margin = (current_gp.get('gross_profit', 0) / total_rev * 100) if total_rev > 0 else 0
        
        # Calculate average visits per customer
        avg_visits = current.get('transactions', 0) / current.get('unique_customers', 1) if current.get('unique_customers', 0) > 0 else 0
        
        # Create comparison text
        if custom_start and custom_end:
            comparison_text = f'vs same period range ({period_duration.days} days)'
        else:
            comparison_text = f'vs {period_duration.days} days ago'
        
        response = {
            'revenue': {
                'current': float(current.get('revenue', 0)),
                'trend': round(revenue_trend, 1),
                'comparison': comparison_text
            },
            'profit': {
                'current': float(current_gp.get('gross_profit', 0)),
                'margin': round(profit_margin, 1),
                'trend': round(profit_trend, 1)
            },
            'transactions': {
                'current': int(current.get('transactions', 0)),
                'avg_ticket': float(current.get('avg_ticket', 0)),
                'trend': round(transaction_trend, 1)
            },
            'customers': {
                'current': int(current.get('unique_customers', 0)),
                'avg_visits': round(avg_visits, 1),
                'trend': round(customer_trend, 1)
            },
            'cashflow': {
                'ar_balance': float(ar_data.get('ar_balance', 0)),
                'collections': float(ar_analysis_data.get('collections', 0)),
                'new_ar_issued': float(ar_analysis_data.get('new_ar_issued', 0)),
                'nsf_impact': float(ar_analysis_data.get('nsf_impact', 0)),
                'customers_with_balance': int(ar_data.get('customers_with_balance', 0)),
                'nsf_count': int(nsf_data.get('nsf_count', 0)),
                'nsf_fees': float(nsf_data.get('nsf_fees', 0)),
                'returned_check_count': int(nsf_data.get('returned_check_count', 0)),
                'returned_check_amount': float(nsf_data.get('returned_check_amount', 0)),
                'nsf_total': float(nsf_data.get('nsf_total', 0))
            },
            'inventory': {
                'total_value': float(inventory_data.get('total_inventory_value', 0)),
                'total_skus': int(inventory_data.get('total_skus', 0)),
                'in_stock_skus': int(inventory_data.get('in_stock_skus', 0)),
                'turnover': float(inventory_data.get('monthly_turnover', 0))
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Executive summary error: {e}")
        return jsonify({'error': str(e)}), 500

from functools import lru_cache
from time import time

# Simple cache for sales performance data
sales_performance_cache = {}
CACHE_TTL = 60  # 60 seconds cache

@app.route('/api/business-overview/sales-performance')
@with_db_lock
def sales_performance():
    """Get sales performance data including top products and categories with caching"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        period = request.args.get('period', 'today')
        custom_start = request.args.get('start_date')
        custom_end = request.args.get('end_date')
        
        # Check cache for common periods
        cache_key = f"{period}_{custom_start}_{custom_end}"
        if cache_key in sales_performance_cache:
            cached_data, timestamp = sales_performance_cache[cache_key]
            if time() - timestamp < CACHE_TTL:
                logger.info(f"Returning cached sales performance data for {cache_key}")
                return jsonify(cached_data)
        
        # Calculate date range
        if custom_start and custom_end:
            # Custom date range provided
            try:
                start_date = datetime.strptime(custom_start, '%Y-%m-%d')
                end_date = datetime.strptime(custom_end, '%Y-%m-%d')
                # Set end date to end of day for inclusive range
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                logger.info(f"Sales performance using custom date range: {start_date} to {end_date}")
            except ValueError as e:
                logger.error(f"Invalid custom date format: {e}")
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            # Use predefined period
            end_date = datetime.now()
            if period == 'today':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == 'MTD':
                start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'YTD':
                start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Top 10 Products by Revenue
        top_products_query = """
        SELECT TOP 10
            i.ID as item_id,
            i.Description as name,
            SUM(te.Price * te.Quantity) as revenue,
            SUM(te.Quantity) as units_sold,
            SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END) as gross_profit
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY i.ID, i.Description
        ORDER BY revenue DESC
        """
        
        top_products_result = db.execute_query(top_products_query, (start_date, end_date), "Top Products")
        
        # Optimized Category Performance with indexed columns
        category_performance_query = """
        WITH CategorySales AS (
            SELECT 
                COALESCE(c.Name, 'Uncategorized') as category_name,
                te.ItemID,
                te.Price * te.Quantity as line_revenue,
                te.Quantity as line_units,
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END as line_cost
            FROM [dbo].[Transaction] t WITH (NOLOCK)
            JOIN dbo.TransactionEntry te WITH (NOLOCK) ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i WITH (NOLOCK) ON te.ItemID = i.ID
            LEFT JOIN dbo.Category c WITH (NOLOCK) ON i.CategoryID = c.ID
            WHERE t.Time >= %s AND t.Time <= %s
        )
        SELECT 
            category_name,
            SUM(line_revenue) as revenue,
            SUM(line_units) as units_sold,
            COUNT(DISTINCT ItemID) as product_count,
            SUM(line_revenue - line_cost) as gross_profit
        FROM CategorySales
        GROUP BY category_name
        ORDER BY revenue DESC
        """
        
        category_result = db.execute_query(category_performance_query, (start_date, end_date), "Category Performance")
        
        # Format response
        top_products = []
        if not top_products_result.empty:
            for _, row in top_products_result.iterrows():
                top_products.append({
                    'item_id': int(row['item_id']),
                    'name': str(row['name']),
                    'revenue': float(row['revenue']),
                    'units_sold': float(row['units_sold']),
                    'gross_profit': float(row['gross_profit'])
                })
        
        categories = []
        if not category_result.empty:
            for _, row in category_result.iterrows():
                categories.append({
                    'category_name': str(row['category_name']),
                    'revenue': float(row['revenue']),
                    'units_sold': float(row['units_sold']),
                    'product_count': int(row['product_count']),
                    'gross_profit': float(row['gross_profit'])
                })
        
        result = {
            'top_products': top_products,
            'categories': categories
        }
        
        # Cache the result
        sales_performance_cache[cache_key] = (result, time())
        # Clean old cache entries
        if len(sales_performance_cache) > 10:
            oldest_keys = sorted(sales_performance_cache.keys(), 
                               key=lambda k: sales_performance_cache[k][1])[:5]
            for key in oldest_keys:
                del sales_performance_cache[key]
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Sales performance error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/business-overview/inventory-health')
@with_db_lock
def inventory_health():
    """Get inventory health data including low stock and deadstock"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Low Stock Items (quantity <= 5)
        low_stock_query = """
        SELECT TOP 20
            i.ID as item_id,
            i.Description as name,
            i.Quantity as current_qty,
            i.Price as selling_price,
            i.Cost as unit_cost,
            (i.Quantity * i.Cost) as inventory_value,
            i.LastSold
        FROM dbo.Item i
        WHERE i.Inactive = 0 AND i.Quantity <= 5 AND i.Quantity > 0
        ORDER BY i.Quantity ASC
        """
        
        low_stock_result = db.execute_query(low_stock_query, description="Low Stock Items")
        
        # Deadstock (not sold in 30+ days)
        deadstock_query = """
        SELECT TOP 20
            i.ID as item_id,
            i.Description as name,
            i.Quantity,
            i.LastSold,
            DATEDIFF(day, i.LastSold, GETDATE()) as days_since_sold,
            (i.Quantity * i.Cost) as inventory_value,
            i.Price as selling_price
        FROM dbo.Item i
        WHERE i.Inactive = 0 
        AND i.Quantity > 0 
        AND (i.LastSold IS NULL OR i.LastSold < DATEADD(day, -30, GETDATE()))
        ORDER BY inventory_value DESC
        """
        
        deadstock_result = db.execute_query(deadstock_query, description="Deadstock Items")
        
        # Fast/Slow Movers Analysis
        movers_query = """
        SELECT TOP 20
            i.ID as item_id,
            i.Description as name,
            i.Quantity as current_qty,
            SUM(te.Quantity) as sold_qty_30d,
            CASE 
                WHEN i.Quantity > 0 THEN SUM(te.Quantity) / NULLIF(i.Quantity, 0) * 30
                ELSE 0
            END as velocity_ratio,
            SUM(te.Price * te.Quantity) as revenue_30d
        FROM dbo.Item i
        LEFT JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        LEFT JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        AND t.Time >= DATEADD(day, -30, GETDATE())
        WHERE i.Inactive = 0 AND i.Quantity > 0
        GROUP BY i.ID, i.Description, i.Quantity
        HAVING SUM(te.Quantity) > 0
        ORDER BY velocity_ratio DESC
        """
        
        movers_result = db.execute_query(movers_query, description="Fast/Slow Movers")
        
        # Inventory Value by Category
        category_value_query = """
        SELECT 
            COALESCE(c.Name, 'Uncategorized') as category_name,
            COUNT(i.ID) as item_count,
            SUM(i.Quantity) as total_units,
            SUM(i.Quantity * i.Cost) as inventory_value
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE i.Inactive = 0 AND i.Quantity > 0
        GROUP BY c.Name
        ORDER BY inventory_value DESC
        """
        
        category_value_result = db.execute_query(category_value_query, description="Inventory Value by Category")
        
        # Format response
        low_stock = []
        if not low_stock_result.empty:
            for _, row in low_stock_result.iterrows():
                low_stock.append({
                    'item_id': int(row['item_id']),
                    'name': str(row['name']),
                    'current_qty': float(row['current_qty']),
                    'selling_price': float(row['selling_price']),
                    'unit_cost': float(row['unit_cost']),
                    'inventory_value': float(row['inventory_value']),
                    'last_sold': row['LastSold'].isoformat() if hasattr(row['LastSold'], 'isoformat') and row['LastSold'] else None
                })
        
        deadstock = []
        if not deadstock_result.empty:
            for _, row in deadstock_result.iterrows():
                deadstock.append({
                    'item_id': int(row['item_id']),
                    'name': str(row['name']),
                    'quantity': float(row['Quantity']),
                    'days_since_sold': int(row['days_since_sold']) if row['days_since_sold'] and not pd.isna(row['days_since_sold']) else None,
                    'inventory_value': float(row['inventory_value']),
                    'selling_price': float(row['selling_price'])
                })
        
        fast_movers = []
        slow_movers = []
        if not movers_result.empty:
            sorted_movers = movers_result.sort_values('velocity_ratio', ascending=False)
            total_items = len(sorted_movers)
            fast_threshold = total_items // 2
            
            for i, (_, row) in enumerate(sorted_movers.iterrows()):
                mover_data = {
                    'item_id': int(row['item_id']),
                    'name': str(row['name']),
                    'current_qty': float(row['current_qty']),
                    'sold_qty_30d': float(row['sold_qty_30d']),
                    'velocity_ratio': float(row['velocity_ratio']) if row['velocity_ratio'] and not pd.isna(row['velocity_ratio']) else 0,
                    'revenue_30d': float(row['revenue_30d'])
                }
                
                if i < fast_threshold and len(fast_movers) < 10:
                    fast_movers.append(mover_data)
                elif len(slow_movers) < 10:
                    slow_movers.append(mover_data)
        
        category_values = []
        if not category_value_result.empty:
            for _, row in category_value_result.iterrows():
                category_values.append({
                    'category_name': str(row['category_name']),
                    'item_count': int(row['item_count']),
                    'total_units': float(row['total_units']),
                    'inventory_value': float(row['inventory_value'])
                })
        
        return jsonify({
            'low_stock': low_stock,
            'deadstock': deadstock,
            'fast_movers': fast_movers,
            'slow_movers': slow_movers,
            'category_values': category_values
        })
        
    except Exception as e:
        logger.error(f"Inventory health error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/business-overview/customer-intelligence')
@with_db_lock
def customer_intelligence():
    """Get customer intelligence data"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        period = request.args.get('period', 'today')
        
        # Calculate date range
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == 'MTD':
            start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'YTD':
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Top Customers by Revenue in Period
        top_customers_query = """
        SELECT TOP 15
            c.ID as customer_id,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in Customer') as customer_name,
            SUM(t.Total) as revenue,
            COUNT(DISTINCT t.TransactionNumber) as transaction_count,
            AVG(t.Total) as avg_transaction,
            c.AccountBalance,
            MAX(t.Time) as last_visit
        FROM [dbo].[Transaction] t
        LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountBalance
        ORDER BY revenue DESC
        """
        
        top_customers_result = db.execute_query(top_customers_query, (start_date, end_date), "Top Customers")
        
        # New Customers (first transaction in period)
        new_customers_query = """
        SELECT 
            c.ID as customer_id,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in Customer') as customer_name,
            MIN(t.Time) as first_visit,
            COUNT(DISTINCT t.TransactionNumber) as transaction_count,
            SUM(t.Total) as total_spent
        FROM [dbo].[Transaction] t
        JOIN dbo.Customer c ON t.CustomerID = c.ID
        WHERE c.ID NOT IN (
            SELECT DISTINCT t2.CustomerID 
            FROM [dbo].[Transaction] t2 
            WHERE t2.Time < %s AND t2.CustomerID IS NOT NULL
        )
        AND t.Time >= %s AND t.Time <= %s
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ORDER BY first_visit DESC
        """
        
        new_customers_result = db.execute_query(new_customers_query, (start_date, start_date, end_date), "New Customers")
        
        # Format response
        top_customers = []
        if not top_customers_result.empty:
            for _, row in top_customers_result.iterrows():
                top_customers.append({
                    'customer_id': int(row['customer_id']) if row['customer_id'] else 0,
                    'customer_name': str(row['customer_name']),
                    'revenue': float(row['revenue']),
                    'transaction_count': int(row['transaction_count']),
                    'avg_transaction': float(row['avg_transaction']),
                    'account_balance': float(row['AccountBalance']) if row['AccountBalance'] else 0,
                    'last_visit': row['last_visit'].isoformat() if hasattr(row['last_visit'], 'isoformat') and row['last_visit'] else None
                })
        
        new_customers = []
        if not new_customers_result.empty:
            for _, row in new_customers_result.iterrows():
                new_customers.append({
                    'customer_id': int(row['customer_id']),
                    'customer_name': str(row['customer_name']),
                    'first_visit': row['first_visit'].isoformat() if hasattr(row['first_visit'], 'isoformat') else str(row['first_visit']),
                    'transaction_count': int(row['transaction_count']),
                    'total_spent': float(row['total_spent'])
                })
        
        return jsonify({
            'top_customers': top_customers,
            'new_customers': new_customers
        })
        
    except Exception as e:
        logger.error(f"Customer intelligence error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/business-overview/performance-trends')
@with_db_lock
def performance_trends():
    """Get performance trends and comparisons"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Week-over-Week Comparison
        current_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        current_week_end = current_week_start + timedelta(days=7)
        
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_end = current_week_start
        
        wow_query = """
        SELECT 
            'current' as period,
            COUNT(DISTINCT t.TransactionNumber) as transactions,
            COUNT(DISTINCT t.CustomerID) as customers,
            SUM(t.Total) as sales,
            AVG(t.Total) as avg_ticket
        FROM [dbo].[Transaction] t
        WHERE t.Time >= %s AND t.Time < %s
        UNION ALL
        SELECT 
            'previous' as period,
            COUNT(DISTINCT t.TransactionNumber) as transactions,
            COUNT(DISTINCT t.CustomerID) as customers,
            SUM(t.Total) as sales,
            AVG(t.Total) as avg_ticket
        FROM [dbo].[Transaction] t
        WHERE t.Time >= %s AND t.Time < %s
        """
        
        wow_result = db.execute_query(wow_query, (current_week_start, current_week_end, previous_week_start, previous_week_end), "Week over Week")
        
        # Profit Center Analysis (by Category)
        profit_centers_query = """
        SELECT TOP 10
            COALESCE(c.Name, 'Uncategorized') as center_name,
            SUM(te.Price * te.Quantity) as revenue,
            SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END) as gross_profit,
            COUNT(DISTINCT t.TransactionNumber) as transactions
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= DATEADD(day, -30, GETDATE())
        GROUP BY c.Name
        ORDER BY gross_profit DESC
        """
        
        profit_centers_result = db.execute_query(profit_centers_query, description="Profit Centers")
        
        # Process WoW data
        wow_comparison = {}
        if not wow_result.empty:
            current_data = wow_result[wow_result['period'] == 'current']
            previous_data = wow_result[wow_result['period'] == 'previous']
            
            if not current_data.empty and not previous_data.empty:
                current = current_data.iloc[0]
                previous = previous_data.iloc[0]
                
                def calc_change(curr, prev):
                    if prev and prev > 0:
                        return ((curr - prev) / prev) * 100
                    return 0
                
                wow_comparison = {
                    'sales_change': round(calc_change(current['sales'], previous['sales']), 1),
                    'transaction_change': round(calc_change(current['transactions'], previous['transactions']), 1),
                    'customer_change': round(calc_change(current['customers'], previous['customers']), 1),
                    'avg_ticket_change': round(calc_change(current['avg_ticket'], previous['avg_ticket']), 1),
                    'current_sales': float(current['sales']),
                    'previous_sales': float(previous['sales'])
                }
        
        # Format profit centers
        profit_centers = []
        if not profit_centers_result.empty:
            for _, row in profit_centers_result.iterrows():
                profit_margin = (row['gross_profit'] / row['revenue'] * 100) if row['revenue'] > 0 else 0
                profit_centers.append({
                    'center_name': str(row['center_name']),
                    'revenue': float(row['revenue']),
                    'gross_profit': float(row['gross_profit']),
                    'profit_margin': round(profit_margin, 1),
                    'transactions': int(row['transactions'])
                })
        
        return jsonify({
            'wow_comparison': wow_comparison,
            'profit_centers': profit_centers
        })
        
    except Exception as e:
        logger.error(f"Performance trends error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/business-overview/sales-trends')
@with_db_lock
def sales_trends():
    """Get daily sales trends for sparkline charts"""
    try:
        period = request.args.get('period', 'today')
        custom_start = request.args.get('custom_start')
        custom_end = request.args.get('custom_end')
        
        # Parse time period (copied from executive_summary logic)
        end_date = datetime.now()
        
        if period == 'custom' and custom_start and custom_end:
            try:
                start_date = datetime.strptime(custom_start, '%Y-%m-%d')
                end_date = datetime.strptime(custom_end, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                logger.info(f"Sales trends using custom date range: {start_date} to {end_date}")
            except ValueError as e:
                logger.warning(f"Invalid custom date format, using today: {e}")
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Standard time periods
            if period == 'today':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == 'MTD':
                start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'YTD':
                start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get daily trends for the period
        trends_query = """
        SELECT 
            CAST(t.Time AS DATE) as date,
            SUM(t.Total) as revenue,
            COUNT(DISTINCT t.TransactionNumber) as transactions,
            COUNT(DISTINCT t.CustomerID) as customers
        FROM [dbo].[Transaction] t
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY CAST(t.Time AS DATE)
        ORDER BY date ASC
        """
        
        # Get database connection (same pattern as other endpoints)
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
            
        trends_result = db.execute_query(trends_query, (start_date, end_date), "Sales Trends")
        
        # Format response for sparklines
        revenue_data = []
        transaction_data = []
        dates = []
        
        if not trends_result.empty:
            for _, row in trends_result.iterrows():
                dates.append(row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']))
                revenue_data.append(float(row['revenue']))
                transaction_data.append(int(row['transactions']))
        
        return jsonify({
            'dates': dates,
            'revenue_data': revenue_data,
            'transaction_data': transaction_data,
            'total_revenue': sum(revenue_data),
            'total_transactions': sum(transaction_data),
            'period': period
        })
        
    except Exception as e:
        logger.error(f"Sales trends error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory-health/low-stock')
@with_db_lock
def inventory_low_stock():
    """Get items with low stock based on sales velocity (< 1 week inventory)"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Calculate low stock items based on sales velocity
        # Items actively selling with less than 1 week of inventory on hand
        low_stock_query = """
        WITH SalesVelocity AS (
            -- Calculate average daily sales for each item over last 30 days
            SELECT 
                daily_totals.ItemID,
                AVG(daily_totals.daily_sales) as avg_daily_sales
            FROM (
                SELECT 
                    te.ItemID,
                    CAST(t.Time AS DATE) as sale_date,
                    SUM(te.Quantity) as daily_sales
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE t.Time >= DATEADD(day, -30, GETDATE())
                AND te.Quantity > 0  -- Only sales, not returns
                GROUP BY te.ItemID, CAST(t.Time AS DATE)
            ) daily_totals
            GROUP BY daily_totals.ItemID
            HAVING AVG(daily_totals.daily_sales) > 0  -- Only items that are actively selling
        ),
        StockAnalysis AS (
            SELECT 
                i.ID,
                i.Description,
                i.ItemLookupCode,
                i.Price,
                i.Cost,
                i.Quantity as current_stock,
                COALESCE(c.Name, 'Unknown') as category,
                i.LastSold,
                sv.avg_daily_sales,
                -- Calculate weeks of inventory remaining
                CASE 
                    WHEN sv.avg_daily_sales > 0 
                    THEN i.Quantity / (sv.avg_daily_sales * 7.0)
                    ELSE 999 
                END as weeks_remaining,
                -- Calculate inventory value
                (i.Quantity * i.Cost) as inventory_value
            FROM dbo.Item i
            LEFT JOIN SalesVelocity sv ON i.ID = sv.ItemID
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE i.Inactive = 0
            AND i.Quantity >= 0
            AND sv.avg_daily_sales IS NOT NULL  -- Only items with recent sales
        )
        SELECT TOP 50
            ID, Description, ItemLookupCode, Price, Cost, current_stock, 
            category, LastSold, avg_daily_sales, weeks_remaining, inventory_value
        FROM StockAnalysis
        WHERE weeks_remaining < 2  -- Less than 2 weeks of inventory
        AND current_stock > 0     -- Has some stock
        AND weeks_remaining IS NOT NULL  -- Filter out NaN values
        AND avg_daily_sales > 0   -- Ensure positive sales velocity
        ORDER BY weeks_remaining ASC, inventory_value DESC
        """
        
        result = db.execute_query(low_stock_query, description="Low Stock Analysis")
        
        low_stock_items = []
        if not result.empty:
            for _, row in result.iterrows():
                low_stock_items.append({
                    'item_id': int(row['ID']),
                    'name': str(row['Description']),
                    'lookup_code': str(row['ItemLookupCode']) if row['ItemLookupCode'] else '',
                    'category': str(row['category']),
                    'current_stock': float(row['current_stock']),
                    'price': float(row['Price']),
                    'cost': float(row['Cost']),
                    'inventory_value': float(row['inventory_value']),
                    'avg_daily_sales': float(row['avg_daily_sales']),
                    'weeks_remaining': float(row['weeks_remaining']),
                    'last_sold': row['LastSold'].isoformat() if hasattr(row['LastSold'], 'isoformat') and row['LastSold'] else None,
                    'urgency_level': 'critical' if row['weeks_remaining'] < 1 else 'warning' if row['weeks_remaining'] < 2 else 'low'
                })
        
        return jsonify({
            'low_stock_items': low_stock_items,
            'total_count': len(low_stock_items),
            'critical_count': sum(1 for item in low_stock_items if item['urgency_level'] == 'critical'),
            'warning_count': sum(1 for item in low_stock_items if item['urgency_level'] == 'warning')
        })
        
    except Exception as e:
        logger.error(f"Low stock analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory-health/deadstock')
@with_db_lock
def inventory_deadstock():
    """Get deadstock analysis for different aging periods"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
            
        days = int(request.args.get('days', 30))
        
        # First get total value of ALL deadstock items
        total_query = """
        SELECT 
            COUNT(*) as total_deadstock_count,
            SUM(i.Quantity * i.Cost) as total_value_all_deadstock
        FROM dbo.Item i
        WHERE i.Inactive = 0
        AND i.Quantity > 0
        AND (
            i.LastSold IS NULL 
            OR i.LastSold < DATEADD(day, -%s, GETDATE())
            OR (i.LastSold IS NULL AND i.LastReceived < DATEADD(day, -%s, GETDATE()))
        )
        """
        
        total_result = db.execute_query(total_query, (days, days), f"Total Deadstock Value ({days} days)")
        total_value_stuck = 0
        total_deadstock_count = 0
        
        if not total_result.empty:
            total_value_stuck = float(total_result.iloc[0]['total_value_all_deadstock'] or 0)
            total_deadstock_count = int(total_result.iloc[0]['total_deadstock_count'] or 0)
        
        # Then get TOP 25 items for display
        deadstock_query = """
        SELECT TOP 25
            i.ID,
            i.Description,
            i.ItemLookupCode,
            i.Price,
            i.Cost,
            i.Quantity as current_stock,
            COALESCE(c.Name, 'Unknown') as category,
            i.LastSold,
            DATEDIFF(day, ISNULL(i.LastSold, i.LastReceived), GETDATE()) as days_since_sold,
            (i.Quantity * i.Cost) as inventory_value,
            -- Get last 30 days sales to confirm it's truly dead
            COALESCE((
                SELECT SUM(te.Quantity)
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE te.ItemID = i.ID
                AND t.Time >= DATEADD(day, -30, GETDATE())
                AND te.Quantity > 0
            ), 0) as recent_sales
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE i.Inactive = 0
        AND i.Quantity > 0
        AND (
            i.LastSold IS NULL 
            OR i.LastSold < DATEADD(day, -%s, GETDATE())
            OR (i.LastSold IS NULL AND i.LastReceived < DATEADD(day, -%s, GETDATE()))
        )
        ORDER BY inventory_value DESC, days_since_sold DESC
        """
        
        result = db.execute_query(deadstock_query, (days, days), f"Deadstock Analysis ({days} days)")
        
        deadstock_items = []
        
        if not result.empty:
            for _, row in result.iterrows():
                inventory_value = float(row['inventory_value'])
                
                # Handle NaN values safely
                days_since_sold = None
                if row['days_since_sold'] is not None and not pd.isna(row['days_since_sold']):
                    try:
                        days_since_sold = int(row['days_since_sold'])
                    except (ValueError, TypeError):
                        days_since_sold = None
                
                deadstock_items.append({
                    'item_id': int(row['ID']),
                    'name': str(row['Description']),
                    'lookup_code': str(row['ItemLookupCode']) if row['ItemLookupCode'] else '',
                    'category': str(row['category']),
                    'current_stock': float(row['current_stock']),
                    'price': float(row['Price']),
                    'cost': float(row['Cost']),
                    'inventory_value': inventory_value,
                    'days_since_sold': days_since_sold,
                    'recent_sales': float(row['recent_sales']) if not pd.isna(row['recent_sales']) else 0,
                    'last_sold': row['LastSold'].isoformat() if hasattr(row['LastSold'], 'isoformat') and row['LastSold'] else None
                })
        
        # Get category breakdown
        category_query = """
        SELECT 
            COALESCE(c.Name, 'Unknown') as category,
            COUNT(*) as item_count,
            SUM(i.Quantity * i.Cost) as category_value
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE i.Inactive = 0
        AND i.Quantity > 0
        AND (
            i.LastSold IS NULL 
            OR i.LastSold < DATEADD(day, -%s, GETDATE())
            OR (i.LastSold IS NULL AND i.LastReceived < DATEADD(day, -%s, GETDATE()))
        )
        GROUP BY c.Name
        ORDER BY category_value DESC
        """
        
        category_result = db.execute_query(category_query, (days, days), f"Deadstock Categories ({days} days)")
        category_breakdown = []
        
        if not category_result.empty:
            for _, row in category_result.iterrows():
                category_breakdown.append({
                    'category': str(row['category']),
                    'item_count': int(row['item_count']),
                    'category_value': float(row['category_value'])
                })
        
        return jsonify({
            'deadstock_items': deadstock_items,
            'total_items': total_deadstock_count,  # Total count of ALL deadstock items
            'items_shown': len(deadstock_items),   # Count of items shown (TOP 25)
            'total_value_stuck': total_value_stuck, # Total value of ALL deadstock items
            'days_threshold': days,
            'category_breakdown': category_breakdown
        })
        
    except Exception as e:
        logger.error(f"Deadstock analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory-health/overstock')
@with_db_lock
def inventory_overstock():
    """Get overstock analysis - items with excess inventory based on sales velocity"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get overstock items - high inventory with low sales velocity
        overstock_query = """
        WITH SalesVelocity AS (
            SELECT 
                te.ItemID,
                AVG(te.Quantity) as avg_daily_sales,
                SUM(te.Quantity) as total_sold_30d,
                COUNT(DISTINCT CAST(t.Time AS DATE)) as active_days
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -30, GETDATE())
            AND te.Quantity > 0
            GROUP BY te.ItemID
        ),
        OverstockAnalysis AS (
            SELECT 
                i.ID,
                i.Description,
                i.ItemLookupCode,
                i.Price,
                i.Cost,
                i.Quantity as current_stock,
                COALESCE(c.Name, 'Unknown') as category,
                i.LastSold,
                COALESCE(sv.avg_daily_sales, 0) as avg_daily_sales,
                COALESCE(sv.total_sold_30d, 0) as sold_30d,
                COALESCE(sv.active_days, 0) as active_days,
                (i.Quantity * i.Cost) as inventory_value,
                -- Calculate days of inventory remaining at current sales rate
                CASE 
                    WHEN COALESCE(sv.avg_daily_sales, 0) > 0 
                    THEN i.Quantity / sv.avg_daily_sales
                    ELSE 999
                END as days_inventory_remaining,
                -- Excess inventory (over 42 days worth - 6 weeks)
                CASE 
                    WHEN COALESCE(sv.avg_daily_sales, 0) > 0 AND i.Quantity / sv.avg_daily_sales > 42
                    THEN (i.Quantity - (sv.avg_daily_sales * 42)) * i.Cost
                    ELSE 0
                END as excess_value
            FROM dbo.Item i
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            LEFT JOIN SalesVelocity sv ON i.ID = sv.ItemID
            WHERE i.Inactive = 0
            AND i.Quantity > 0
            AND (
                -- High inventory with low or no sales
                (COALESCE(sv.avg_daily_sales, 0) = 0 AND i.Quantity > 10) OR
                (COALESCE(sv.avg_daily_sales, 0) > 0 AND i.Quantity / sv.avg_daily_sales > 42)
            )
        )
        SELECT TOP 25 *
        FROM OverstockAnalysis
        ORDER BY excess_value DESC, inventory_value DESC
        """
        
        # Get total overstock value
        total_query = """
        WITH SalesVelocity AS (
            SELECT 
                te.ItemID,
                AVG(te.Quantity) as avg_daily_sales
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -30, GETDATE())
            AND te.Quantity > 0
            GROUP BY te.ItemID
        )
        SELECT 
            COUNT(*) as total_overstock_count,
            SUM(i.Quantity * i.Cost) as total_overstock_value,
            SUM(CASE 
                WHEN COALESCE(sv.avg_daily_sales, 0) > 0 AND i.Quantity / sv.avg_daily_sales > 42
                THEN (i.Quantity - (sv.avg_daily_sales * 42)) * i.Cost
                ELSE i.Quantity * i.Cost
            END) as total_excess_value
        FROM dbo.Item i
        LEFT JOIN SalesVelocity sv ON i.ID = sv.ItemID
        WHERE i.Inactive = 0
        AND i.Quantity > 0
        AND (
            (COALESCE(sv.avg_daily_sales, 0) = 0 AND i.Quantity > 10) OR
            (COALESCE(sv.avg_daily_sales, 0) > 0 AND i.Quantity / sv.avg_daily_sales > 42)
        )
        """
        
        # Execute queries
        result = db.execute_query(overstock_query, description="Overstock Analysis")
        total_result = db.execute_query(total_query, description="Total Overstock Value")
        
        overstock_items = []
        total_overstock_value = 0
        total_overstock_count = 0
        total_excess_value = 0
        
        if not total_result.empty:
            total_overstock_value = float(total_result.iloc[0]['total_overstock_value'] or 0)
            total_overstock_count = int(total_result.iloc[0]['total_overstock_count'] or 0)
            total_excess_value = float(total_result.iloc[0]['total_excess_value'] or 0)
        
        if not result.empty:
            for _, row in result.iterrows():
                inventory_value = float(row['inventory_value'])
                excess_value = float(row['excess_value'] or 0)
                days_remaining = float(row['days_inventory_remaining'] or 0)
                
                overstock_items.append({
                    'item_id': int(row['ID']),
                    'name': str(row['Description']),
                    'lookup_code': str(row['ItemLookupCode']) if row['ItemLookupCode'] else '',
                    'category': str(row['category']),
                    'current_stock': float(row['current_stock']),
                    'price': float(row['Price']),
                    'cost': float(row['Cost']),
                    'inventory_value': inventory_value,
                    'avg_daily_sales': float(row['avg_daily_sales'] or 0),
                    'sold_30d': float(row['sold_30d'] or 0),
                    'days_inventory_remaining': days_remaining,
                    'excess_value': excess_value,
                    'last_sold': row['LastSold'].isoformat() if hasattr(row['LastSold'], 'isoformat') and row['LastSold'] else None
                })
        
        # Get category breakdown
        category_query = """
        WITH SalesVelocity AS (
            SELECT 
                te.ItemID,
                AVG(te.Quantity) as avg_daily_sales
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -30, GETDATE())
            AND te.Quantity > 0
            GROUP BY te.ItemID
        )
        SELECT 
            COALESCE(c.Name, 'Unknown') as category,
            COUNT(*) as item_count,
            SUM(i.Quantity * i.Cost) as category_value,
            SUM(CASE 
                WHEN COALESCE(sv.avg_daily_sales, 0) > 0 AND i.Quantity / sv.avg_daily_sales > 42
                THEN (i.Quantity - (sv.avg_daily_sales * 42)) * i.Cost
                ELSE i.Quantity * i.Cost
            END) as excess_value
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        LEFT JOIN SalesVelocity sv ON i.ID = sv.ItemID
        WHERE i.Inactive = 0
        AND i.Quantity > 0
        AND (
            (COALESCE(sv.avg_daily_sales, 0) = 0 AND i.Quantity > 10) OR
            (COALESCE(sv.avg_daily_sales, 0) > 0 AND i.Quantity / sv.avg_daily_sales > 42)
        )
        GROUP BY c.Name
        ORDER BY excess_value DESC
        """
        
        category_result = db.execute_query(category_query, description="Overstock Categories")
        category_breakdown = []
        
        if not category_result.empty:
            for _, row in category_result.iterrows():
                category_breakdown.append({
                    'category': str(row['category']),
                    'item_count': int(row['item_count']),
                    'category_value': float(row['category_value']),
                    'excess_value': float(row['excess_value'])
                })
        
        return jsonify({
            'overstock_items': overstock_items,
            'total_items': total_overstock_count,
            'items_shown': len(overstock_items),
            'total_overstock_value': total_overstock_value,
            'total_excess_value': total_excess_value,
            'threshold_days': 42,
            'category_breakdown': category_breakdown
        })
        
    except Exception as e:
        logger.error(f"Overstock analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory-health/negative-quantity')
@with_db_lock
def inventory_negative_quantity():
    """Get items with negative quantity (backorders, theft, etc.)"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        negative_query = """
        WITH RecentActivity AS (
            SELECT 
                te.ItemID,
                SUM(CASE WHEN te.Quantity > 0 THEN te.Quantity ELSE 0 END) as recent_sales_30d,
                SUM(CASE WHEN te.Quantity < 0 THEN te.Quantity ELSE 0 END) as recent_receipts_30d
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -30, GETDATE())
            GROUP BY te.ItemID
        )
        SELECT 
            i.ID,
            i.Description,
            i.ItemLookupCode,
            i.Price,
            i.Cost,
            i.Quantity as current_stock,
            COALESCE(c.Name, 'Unknown') as category,
            i.LastSold,
            i.LastReceived,
            ABS(i.Quantity * i.Cost) as negative_value,
            COALESCE(ra.recent_sales_30d, 0) as recent_sales_30d,
            COALESCE(ra.recent_receipts_30d, 0) as recent_receipts_30d
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        LEFT JOIN RecentActivity ra ON i.ID = ra.ItemID
        WHERE i.Inactive = 0
        AND i.Quantity < 0
        ORDER BY i.Quantity ASC, negative_value DESC
        """
        
        # Get total negative quantity impact
        total_query = """
        SELECT 
            COUNT(*) as total_negative_count,
            SUM(ABS(i.Quantity * i.Cost)) as total_negative_value,
            SUM(i.Quantity) as total_negative_units
        FROM dbo.Item i
        WHERE i.Inactive = 0
        AND i.Quantity < 0
        """
        
        # Execute queries
        result = db.execute_query(negative_query, description="Negative Quantity Items")
        total_result = db.execute_query(total_query, description="Total Negative Quantity Impact")
        
        negative_items = []
        total_negative_value = 0
        total_negative_count = 0
        total_negative_units = 0
        
        if not total_result.empty:
            total_negative_value = float(total_result.iloc[0]['total_negative_value'] or 0)
            total_negative_count = int(total_result.iloc[0]['total_negative_count'] or 0)
            total_negative_units = float(total_result.iloc[0]['total_negative_units'] or 0)
        
        if not result.empty:
            for _, row in result.iterrows():
                negative_value = float(row['negative_value'])
                current_stock = float(row['current_stock'])
                
                # Determine likely cause
                recent_sales = float(row['recent_sales_30d'] or 0)
                recent_receipts = float(row['recent_receipts_30d'] or 0)
                
                likely_cause = "Unknown"
                if recent_sales > 0 and recent_receipts == 0:
                    likely_cause = "Backorder (High Demand)"
                elif recent_receipts > 0:
                    likely_cause = "Returns/Adjustments"
                elif recent_sales == 0:
                    likely_cause = "Inventory Shrinkage"
                
                negative_items.append({
                    'item_id': int(row['ID']),
                    'name': str(row['Description']),
                    'lookup_code': str(row['ItemLookupCode']) if row['ItemLookupCode'] else '',
                    'category': str(row['category']),
                    'current_stock': current_stock,
                    'price': float(row['Price']),
                    'cost': float(row['Cost']),
                    'negative_value': negative_value,
                    'recent_sales_30d': recent_sales,
                    'recent_receipts_30d': recent_receipts,
                    'likely_cause': likely_cause,
                    'last_sold': row['LastSold'].isoformat() if hasattr(row['LastSold'], 'isoformat') and row['LastSold'] else None,
                    'last_received': row['LastReceived'].isoformat() if hasattr(row['LastReceived'], 'isoformat') and row['LastReceived'] else None
                })
        
        # Get category breakdown
        category_query = """
        SELECT 
            COALESCE(c.Name, 'Unknown') as category,
            COUNT(*) as item_count,
            SUM(ABS(i.Quantity * i.Cost)) as category_value,
            SUM(i.Quantity) as total_negative_units
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE i.Inactive = 0
        AND i.Quantity < 0
        GROUP BY c.Name
        ORDER BY category_value DESC
        """
        
        category_result = db.execute_query(category_query, description="Negative Quantity Categories")
        category_breakdown = []
        
        if not category_result.empty:
            for _, row in category_result.iterrows():
                category_breakdown.append({
                    'category': str(row['category']),
                    'item_count': int(row['item_count']),
                    'category_value': float(row['category_value']),
                    'negative_units': float(row['total_negative_units'])
                })
        
        return jsonify({
            'negative_items': negative_items,
            'total_items': total_negative_count,
            'total_negative_value': total_negative_value,
            'total_negative_units': total_negative_units,
            'category_breakdown': category_breakdown
        })
        
    except Exception as e:
        logger.error(f"Negative quantity analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/ar-aging-optimized')
@with_db_lock  
def ar_aging_analysis_optimized():
    """Optimized AR aging analysis with NSF tracking"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Optimized AR aging query - only get top 20 customers and summary
        ar_aging_query = """
        WITH ARData AS (
            SELECT 
                ar.CustomerID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in Customer') as customer_name,
                ar.Date as invoice_date,
                ar.DueDate,
                ar.Balance,
                ar.OriginalAmount,
                ar.TransactionNumber,
                DATEDIFF(day, ar.Date, GETDATE()) as days_outstanding,
                CASE 
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 days'
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 days'
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 days'
                    ELSE '90+ days'
                END as aging_bucket
            FROM dbo.AccountReceivable ar
            LEFT JOIN dbo.Customer c ON ar.CustomerID = c.ID
            WHERE ar.Balance > 0
        )
        SELECT TOP 20 * FROM ARData ORDER BY Balance DESC
        """
        
        # Get NSF data using proper patterns from documentation
        nsf_query = """
        WITH NSFFees AS (
            -- NSF fees from AccountReceivable ($65 entries with TransactionNumber = 0)
            SELECT 
                COUNT(*) as fee_count,
                SUM(OriginalAmount) as fee_total,
                COUNT(DISTINCT CustomerID) as fee_customers
            FROM dbo.AccountReceivable ar
            WHERE ar.OriginalAmount = 65.00 
                AND ar.TransactionNumber = 0
                AND ar.Date >= DATEADD(day, -30, GETDATE())
        ),
        ReturnedChecks AS (
            -- Returned check amounts (the actual bounced check values)
            SELECT 
                COUNT(DISTINCT ar.ID) as returned_count,
                SUM(ar.OriginalAmount) as returned_total,
                COUNT(DISTINCT ar.CustomerID) as returned_customers
            FROM dbo.AccountReceivable ar
            INNER JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
            WHERE (arh.Comment LIKE '%NSF%' 
                OR arh.Comment LIKE '%RET%' 
                OR arh.Comment LIKE '%RETURN%'
                OR arh.Comment LIKE '%INSUFFICIENT%'
                OR arh.Comment LIKE '%BOUNCE%')
                AND ar.OriginalAmount != 65.00  -- Exclude the fees
                AND ar.Date >= DATEADD(day, -30, GETDATE())
        )
        SELECT 
            COALESCE(nf.fee_count, 0) as nsf_count,
            COALESCE(nf.fee_total, 0) as nsf_fees,
            COALESCE(rc.returned_count, 0) as returned_check_count,
            COALESCE(rc.returned_total, 0) as returned_check_amount,
            COALESCE(nf.fee_total, 0) + COALESCE(rc.returned_total, 0) as nsf_total,
            COALESCE(nf.fee_customers, 0) + COALESCE(rc.returned_customers, 0) as nsf_customers
        FROM NSFFees nf
        CROSS JOIN ReturnedChecks rc
        """
        
        # Execute both queries
        ar_result = db.execute_query(ar_aging_query, description="Optimized AR Aging")
        nsf_result = db.execute_query(nsf_query, description="NSF Tracking")
        
        ar_records = []
        aging_summary = {
            '0-30 days': {'count': 0, 'amount': 0},
            '31-60 days': {'count': 0, 'amount': 0}, 
            '61-90 days': {'count': 0, 'amount': 0},
            '90+ days': {'count': 0, 'amount': 0}
        }
        
        if not ar_result.empty:
            for _, row in ar_result.iterrows():
                balance = float(row['Balance'])
                bucket = row['aging_bucket']
                
                ar_records.append({
                    'customer_id': int(row['CustomerID']),
                    'customer_name': str(row['customer_name']),
                    'invoice_date': row['invoice_date'].isoformat() if hasattr(row['invoice_date'], 'isoformat') else str(row['invoice_date']),
                    'due_date': row['DueDate'].isoformat() if hasattr(row['DueDate'], 'isoformat') and row['DueDate'] else None,
                    'balance': balance,
                    'original_amount': float(row['OriginalAmount']),
                    'transaction_number': int(row['TransactionNumber']) if row['TransactionNumber'] else None,
                    'days_outstanding': int(row['days_outstanding']),
                    'aging_bucket': bucket
                })
                
                aging_summary[bucket]['count'] += 1
                aging_summary[bucket]['amount'] += balance
        
        # Get aging summary totals more efficiently
        aging_totals_query = """
        SELECT 
            CASE 
                WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN '0-30 days'
                WHEN DATEDIFF(day, Date, GETDATE()) <= 60 THEN '31-60 days'
                WHEN DATEDIFF(day, Date, GETDATE()) <= 90 THEN '61-90 days'
                ELSE '90+ days'
            END as bucket,
            COUNT(*) as cnt,
            SUM(Balance) as total
        FROM dbo.AccountReceivable
        WHERE Balance > 0
        GROUP BY CASE 
            WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN '0-30 days'
            WHEN DATEDIFF(day, Date, GETDATE()) <= 60 THEN '31-60 days'
            WHEN DATEDIFF(day, Date, GETDATE()) <= 90 THEN '61-90 days'
            ELSE '90+ days'
        END
        """
        
        totals_result = db.execute_query(aging_totals_query, description="AR Aging Totals")
        
        if not totals_result.empty:
            for _, row in totals_result.iterrows():
                bucket = row['bucket']
                if bucket in aging_summary:
                    aging_summary[bucket]['count'] = int(row['cnt'])
                    aging_summary[bucket]['amount'] = float(row['total'])
        
        # Calculate totals and percentages
        total_ar = sum(bucket['amount'] for bucket in aging_summary.values())
        total_invoices = sum(bucket['count'] for bucket in aging_summary.values())
        
        for bucket in aging_summary.values():
            bucket['percentage'] = (bucket['amount'] / total_ar * 100) if total_ar > 0 else 0
        
        # Add NSF data
        nsf_data = {
            'nsf_count': 0,
            'nsf_fees': 0,
            'returned_check_count': 0,
            'returned_check_amount': 0,
            'nsf_total': 0,
            'nsf_customers': 0
        }
        
        if not nsf_result.empty:
            nsf_data = {
                'nsf_count': int(nsf_result.iloc[0]['nsf_count']),
                'nsf_fees': float(nsf_result.iloc[0]['nsf_fees']),
                'returned_check_count': int(nsf_result.iloc[0]['returned_check_count']),
                'returned_check_amount': float(nsf_result.iloc[0]['returned_check_amount']),
                'nsf_total': float(nsf_result.iloc[0]['nsf_total']),
                'nsf_customers': int(nsf_result.iloc[0]['nsf_customers'])
            }
        
        return jsonify({
            'ar_records': ar_records,
            'aging_summary': aging_summary,
            'total_ar': total_ar,
            'total_invoices': total_invoices,
            'nsf_tracking': nsf_data
        })
        
    except Exception as e:
        logger.error(f"Optimized AR aging analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/ar-aging')
@with_db_lock  
def ar_aging_analysis():
    """Get proper AR aging analysis using AccountReceivable table"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get actual AR aging from AccountReceivable table
        ar_aging_query = """
        SELECT 
            ar.CustomerID,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in Customer') as customer_name,
            ar.Date as invoice_date,
            ar.DueDate,
            ar.Balance,
            ar.OriginalAmount,
            ar.TransactionNumber,
            DATEDIFF(day, ar.Date, GETDATE()) as days_outstanding,
            CASE 
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 days'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 days'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 days'
                ELSE '90+ days'
            END as aging_bucket
        FROM dbo.AccountReceivable ar
        LEFT JOIN dbo.Customer c ON ar.CustomerID = c.ID
        WHERE ar.Balance > 0
        ORDER BY ar.Balance DESC
        """
        
        result = db.execute_query(ar_aging_query, description="AR Aging Analysis")
        
        ar_records = []
        aging_summary = {
            '0-30 days': {'count': 0, 'amount': 0},
            '31-60 days': {'count': 0, 'amount': 0}, 
            '61-90 days': {'count': 0, 'amount': 0},
            '90+ days': {'count': 0, 'amount': 0}
        }
        
        if not result.empty:
            for _, row in result.iterrows():
                balance = float(row['Balance'])
                bucket = row['aging_bucket']
                
                ar_records.append({
                    'customer_id': int(row['CustomerID']),
                    'customer_name': str(row['customer_name']),
                    'invoice_date': row['invoice_date'].isoformat() if hasattr(row['invoice_date'], 'isoformat') else str(row['invoice_date']),
                    'due_date': row['DueDate'].isoformat() if hasattr(row['DueDate'], 'isoformat') and row['DueDate'] else None,
                    'balance': balance,
                    'original_amount': float(row['OriginalAmount']),
                    'transaction_number': int(row['TransactionNumber']) if row['TransactionNumber'] else None,
                    'days_outstanding': int(row['days_outstanding']),
                    'aging_bucket': bucket
                })
                
                aging_summary[bucket]['count'] += 1
                aging_summary[bucket]['amount'] += balance
        
        # Calculate totals and percentages
        total_ar = sum(bucket['amount'] for bucket in aging_summary.values())
        total_invoices = sum(bucket['count'] for bucket in aging_summary.values())
        
        for bucket in aging_summary.values():
            bucket['percentage'] = (bucket['amount'] / total_ar * 100) if total_ar > 0 else 0
        
        return jsonify({
            'ar_records': ar_records,
            'aging_summary': aging_summary,
            'total_ar': total_ar,
            'total_invoices': total_invoices
        })
        
    except Exception as e:
        logger.error(f"AR aging analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/nsf-details')
@with_db_lock
def nsf_details():
    """Get detailed NSF/returned check information"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        # Get date range from query params (default to last 30 days)
        days_back = int(request.args.get('days', 30))
        
        # Get detailed NSF information
        nsf_detail_query = """
        WITH NSFDetail AS (
            -- Get all NSF-related entries
            SELECT 
                ar.ID,
                ar.CustomerID,
                c.Company as CustomerName,
                ar.Date,
                ar.OriginalAmount,
                ar.Balance,
                arh.Comment,
                CASE 
                    WHEN ar.OriginalAmount = 65.00 AND ar.TransactionNumber = 0 THEN 'NSF_FEE'
                    WHEN arh.Comment LIKE '%%NSF%%' OR arh.Comment LIKE '%%RET%%' THEN 'RETURNED_CHECK'
                    ELSE 'OTHER'
                END as Type,
                DATEDIFF(day, ar.Date, GETDATE()) as DaysOld
            FROM dbo.AccountReceivable ar
            INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
            LEFT JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
            WHERE ar.Date >= DATEADD(day, -%s, GETDATE())
                AND (
                    (ar.OriginalAmount = 65.00 AND ar.TransactionNumber = 0)
                    OR arh.Comment LIKE '%%NSF%%'
                    OR arh.Comment LIKE '%%RET%%'
                    OR arh.Comment LIKE '%%RETURN%%'
                )
        )
        SELECT TOP 100 * FROM NSFDetail
        ORDER BY Date DESC, CustomerID
        """
        
        # Get summary statistics
        nsf_summary_query = """
        WITH NSFSummary AS (
            SELECT 
                COUNT(CASE WHEN ar.OriginalAmount = 65.00 THEN 1 END) as fee_count,
                SUM(CASE WHEN ar.OriginalAmount = 65.00 THEN ar.OriginalAmount ELSE 0 END) as fee_total,
                COUNT(CASE WHEN ar.OriginalAmount != 65.00 THEN 1 END) as check_count,
                SUM(CASE WHEN ar.OriginalAmount != 65.00 THEN ar.OriginalAmount ELSE 0 END) as check_total,
                COUNT(DISTINCT ar.CustomerID) as affected_customers,
                AVG(CASE WHEN ar.Balance > 0 THEN DATEDIFF(day, ar.Date, GETDATE()) END) as avg_days_outstanding
            FROM dbo.AccountReceivable ar
            LEFT JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
            WHERE ar.Date >= DATEADD(day, -%s, GETDATE())
                AND (
                    (ar.OriginalAmount = 65.00 AND ar.TransactionNumber = 0)
                    OR arh.Comment LIKE '%%NSF%%'
                    OR arh.Comment LIKE '%%RET%%'
                    OR arh.Comment LIKE '%%RETURN%%'
                )
        )
        SELECT * FROM NSFSummary
        """
        
        # Execute queries
        detail_result = db.execute_query(nsf_detail_query, (days_back,), "NSF Details")
        summary_result = db.execute_query(nsf_summary_query, (days_back,), "NSF Summary")
        
        # Process detail results
        nsf_details = []
        if not detail_result.empty:
            for _, row in detail_result.iterrows():
                nsf_details.append({
                    'id': int(row['ID']),
                    'customer_id': int(row['CustomerID']),
                    'customer_name': str(row['CustomerName']),
                    'date': row['Date'].isoformat() if hasattr(row['Date'], 'isoformat') else str(row['Date']),
                    'amount': float(row['OriginalAmount']),
                    'balance': float(row['Balance']),
                    'type': str(row['Type']),
                    'comment': str(row['Comment']) if row['Comment'] else '',
                    'days_old': int(row['DaysOld'])
                })
        
        # Process summary
        summary = {
            'fee_count': 0,
            'fee_total': 0,
            'check_count': 0,
            'check_total': 0,
            'total_impact': 0,
            'affected_customers': 0,
            'avg_days_outstanding': 0
        }
        
        if not summary_result.empty:
            row = summary_result.iloc[0]
            summary = {
                'fee_count': int(row['fee_count']),
                'fee_total': float(row['fee_total']),
                'check_count': int(row['check_count']),
                'check_total': float(row['check_total']),
                'total_impact': float(row['fee_total'] + row['check_total']),
                'affected_customers': int(row['affected_customers']),
                'avg_days_outstanding': float(row['avg_days_outstanding']) if row['avg_days_outstanding'] else 0
            }
        
        return jsonify({
            'summary': summary,
            'details': nsf_details,
            'period_days': days_back
        })
        
    except Exception as e:
        logger.error(f"NSF details error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory-health/velocity')
@with_db_lock
def inventory_velocity():
    """Get hot and slow moving products based on sales velocity"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
            
        view_type = request.args.get('view', 'hot')  # 'hot' or 'slow'
        
        velocity_query = """
        WITH CurrentPeriodSales AS (
            -- Last 30 days sales
            SELECT 
                te.ItemID,
                COUNT(DISTINCT CAST(t.Time AS DATE)) as active_days,
                SUM(te.Quantity) as total_sold_current,
                AVG(te.Quantity) as avg_per_transaction,
                COUNT(*) as transaction_count,
                -- Calculate daily velocity
                SUM(te.Quantity) / 30.0 as daily_velocity,
                -- Calculate turnover rate (sales / current stock)
                CASE 
                    WHEN i.Quantity > 0 
                    THEN (SUM(te.Quantity) / 30.0) / i.Quantity * 100
                    ELSE 0 
                END as turnover_rate
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            WHERE t.Time >= DATEADD(day, -30, GETDATE())
            AND te.Quantity > 0  -- Only sales, not returns
            AND i.Inactive = 0
            AND i.Quantity > 0   -- Has current stock
            GROUP BY te.ItemID, i.Quantity
            HAVING SUM(te.Quantity) > 0
        ),
        PreviousPeriodSales AS (
            -- Previous 30 days sales (days 31-60 ago)
            SELECT 
                te.ItemID,
                SUM(te.Quantity) as total_sold_previous
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            WHERE t.Time >= DATEADD(day, -60, GETDATE())
            AND t.Time < DATEADD(day, -30, GETDATE())
            AND te.Quantity > 0  -- Only sales, not returns
            AND i.Inactive = 0
            GROUP BY te.ItemID
        ),
        SalesVelocity AS (
            -- Combine current and previous period data
            SELECT 
                cp.*,
                COALESCE(pp.total_sold_previous, 0) as total_sold_previous,
                -- Calculate volume change
                CASE 
                    WHEN COALESCE(pp.total_sold_previous, 0) > 0 
                    THEN ((cp.total_sold_current - COALESCE(pp.total_sold_previous, 0)) * 100.0 / pp.total_sold_previous)
                    WHEN cp.total_sold_current > 0 AND COALESCE(pp.total_sold_previous, 0) = 0
                    THEN 999.0  -- New hot seller
                    ELSE 0
                END as volume_change_percent
            FROM CurrentPeriodSales cp
            LEFT JOIN PreviousPeriodSales pp ON cp.ItemID = pp.ItemID
        ),
        ItemAnalysis AS (
            SELECT 
                i.ID,
                i.Description,
                i.ItemLookupCode,
                i.Price,
                i.Cost,
                i.Quantity as current_stock,
                COALESCE(c.Name, 'Unknown') as category,
                i.LastSold,
                sv.daily_velocity,
                sv.turnover_rate,
                sv.total_sold_current as total_sold_30d,
                sv.total_sold_previous,
                sv.volume_change_percent,
                sv.transaction_count,
                sv.active_days,
                (i.Quantity * i.Cost) as inventory_value,
                -- ENHANCED: Calculate velocity score with volume and profit factors
                -- Score = 40% turnover rate + 30% volume + 20% profit margin + 10% sales frequency
                (sv.turnover_rate * 0.4 + 
                 (sv.total_sold_current / NULLIF((SELECT MAX(total_sold_current) FROM SalesVelocity), 0)) * 100 * 0.3 +
                 ((i.Price - i.Cost) / NULLIF(i.Price, 0)) * 100 * 0.2 +
                 sv.active_days * 0.1) as velocity_score,
                -- Also calculate profit per unit and total profit for hot products
                (i.Price - i.Cost) as profit_per_unit,
                sv.total_sold_current * (i.Price - i.Cost) as total_profit_30d
            FROM dbo.Item i
            LEFT JOIN SalesVelocity sv ON i.ID = sv.ItemID
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE i.Inactive = 0
            AND i.Quantity > 0
            AND sv.daily_velocity IS NOT NULL
        )
        SELECT TOP 25
            ID, Description, ItemLookupCode, Price, Cost, current_stock,
            category, LastSold, daily_velocity, turnover_rate, total_sold_30d,
            total_sold_previous, volume_change_percent, transaction_count, 
            active_days, inventory_value, velocity_score,
            profit_per_unit, total_profit_30d
        FROM ItemAnalysis
        WHERE velocity_score > 0
        ORDER BY 
            CASE WHEN %s = 'hot' THEN velocity_score END DESC,
            CASE WHEN %s = 'slow' THEN velocity_score END ASC
        """
        
        result = db.execute_query(velocity_query, (view_type, view_type), f"Velocity Analysis ({view_type})")
        
        velocity_items = []
        if not result.empty:
            for _, row in result.iterrows():
                velocity_items.append({
                    'item_id': int(row['ID']),
                    'name': str(row['Description']),
                    'lookup_code': str(row['ItemLookupCode']) if row['ItemLookupCode'] else '',
                    'category': str(row['category']),
                    'current_stock': float(row['current_stock']),
                    'price': float(row['Price']),
                    'cost': float(row['Cost']),
                    'inventory_value': float(row['inventory_value']),
                    'daily_velocity': float(row['daily_velocity']),
                    'turnover_rate': float(row['turnover_rate']),
                    'total_sold_30d': int(row['total_sold_30d']),
                    'total_sold_previous': int(row['total_sold_previous']) if row['total_sold_previous'] else 0,
                    'volume_change_percent': float(row['volume_change_percent']) if row['volume_change_percent'] is not None else 0,
                    'transaction_count': int(row['transaction_count']),
                    'active_days': int(row['active_days']),
                    'velocity_score': float(row['velocity_score']),
                    'profit_per_unit': float(row['profit_per_unit']) if row['profit_per_unit'] else 0,
                    'total_profit_30d': float(row['total_profit_30d']) if row['total_profit_30d'] else 0,
                    'last_sold': row['LastSold'].isoformat() if hasattr(row['LastSold'], 'isoformat') and row['LastSold'] else None
                })
        
        return jsonify({
            'velocity_items': velocity_items,
            'view_type': view_type,
            'total_count': len(velocity_items)
        })
        
    except Exception as e:
        logger.error(f"Velocity analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory-health/category-values')
@with_db_lock
def inventory_category_values():
    """Get inventory value breakdown by category"""
    try:
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        category_values_query = """
        SELECT 
            COALESCE(c.Name, 'Unknown') as category_name,
            COUNT(i.ID) as item_count,
            SUM(i.Quantity) as total_units,
            SUM(i.Quantity * i.Cost) as inventory_value,
            AVG(i.Cost) as avg_cost,
            AVG(i.Price) as avg_price,
            MIN(i.LastSold) as oldest_sale,
            MAX(i.LastSold) as newest_sale,
            -- Calculate category performance metrics
            SUM(CASE WHEN i.Quantity > 0 THEN 1 ELSE 0 END) as in_stock_items,
            SUM(CASE WHEN i.LastSold >= DATEADD(day, -30, GETDATE()) THEN 1 ELSE 0 END) as recently_sold_items,
            -- Get 30-day sales for this category
            COALESCE((
                SELECT SUM(te.Quantity * te.Price)
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                JOIN dbo.Item i2 ON te.ItemID = i2.ID
                WHERE i2.CategoryID = c.ID
                AND t.Time >= DATEADD(day, -30, GETDATE())
                AND te.Quantity > 0
            ), 0) as sales_30d
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE i.Inactive = 0
        AND i.Quantity > 0
        GROUP BY c.ID, c.Name
        HAVING SUM(i.Quantity * i.Cost) > 0
        ORDER BY inventory_value DESC
        """
        
        result = db.execute_query(category_values_query, description="Category Inventory Values")
        
        category_values = []
        total_inventory_value = 0
        
        if not result.empty:
            for _, row in result.iterrows():
                inventory_value = float(row['inventory_value'])
                total_inventory_value += inventory_value
                
                category_values.append({
                    'category_name': str(row['category_name']),
                    'item_count': int(row['item_count']),
                    'total_units': float(row['total_units']),
                    'inventory_value': inventory_value,
                    'avg_cost': float(row['avg_cost']),
                    'avg_price': float(row['avg_price']),
                    'in_stock_items': int(row['in_stock_items']),
                    'recently_sold_items': int(row['recently_sold_items']),
                    'sales_30d': float(row['sales_30d']),
                    'turnover_ratio': float(row['sales_30d']) / inventory_value if inventory_value > 0 else 0,
                    'oldest_sale': row['oldest_sale'].isoformat() if hasattr(row['oldest_sale'], 'isoformat') and row['oldest_sale'] else None,
                    'newest_sale': row['newest_sale'].isoformat() if hasattr(row['newest_sale'], 'isoformat') and row['newest_sale'] else None
                })
        
        # Calculate percentages
        for category in category_values:
            category['percentage_of_total'] = (category['inventory_value'] / total_inventory_value * 100) if total_inventory_value > 0 else 0
        
        return jsonify({
            'category_values': category_values,
            'total_inventory_value': total_inventory_value,
            'total_categories': len(category_values)
        })
        
    except Exception as e:
        logger.error(f"Category values analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/item/<int:item_id>/details')
@with_db_lock
def item_details(item_id):
    """Get detailed item information for drill-down"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Basic item info
        item_info_query = """
        SELECT 
            i.ID,
            i.Description,
            i.ItemLookupCode,
            i.Price,
            i.Cost,
            i.Quantity,
            i.LastSold,
            c.Name as CategoryName,
            d.Name as DepartmentName
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        LEFT JOIN dbo.Department d ON c.DepartmentID = d.ID
        WHERE i.ID = %s
        """
        
        item_info = db.execute_query(item_info_query, (item_id,), f"Item {item_id} Details")
        
        if item_info.empty:
            return jsonify({'error': 'Item not found'}), 404
        
        item = item_info.iloc[0]
        
        # Sales history (last 30 days)
        sales_history_query = """
        SELECT 
            CAST(t.Time AS DATE) as date,
            SUM(te.Quantity) as units_sold,
            SUM(te.Price * te.Quantity) as revenue,
            COUNT(DISTINCT t.TransactionNumber) as transactions
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE te.ItemID = %s
        AND t.Time >= DATEADD(day, -30, GETDATE())
        GROUP BY CAST(t.Time AS DATE)
        ORDER BY date DESC
        """
        
        sales_history = db.execute_query(sales_history_query, (item_id,), f"Item {item_id} Sales History")
        
        # Recent transactions
        recent_transactions_query = """
        SELECT TOP 10
            t.TransactionNumber,
            t.Time,
            te.Quantity,
            te.Price,
            (te.Price * te.Quantity) as line_total,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in') as customer_name
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
        WHERE te.ItemID = %s
        ORDER BY t.Time DESC
        """
        
        recent_transactions = db.execute_query(recent_transactions_query, (item_id,), f"Item {item_id} Recent Transactions")
        
        # Format response
        response = {
            'item_info': {
                'id': int(item['ID']),
                'description': str(item['Description']),
                'lookup_code': str(item['ItemLookupCode']) if item['ItemLookupCode'] else '',
                'price': float(item['Price']),
                'cost': float(item['Cost']),
                'quantity': float(item['Quantity']),
                'last_sold': item['LastSold'].isoformat() if hasattr(item['LastSold'], 'isoformat') and item['LastSold'] else None,
                'category': str(item['CategoryName']) if item['CategoryName'] else 'Uncategorized',
                'department': str(item['DepartmentName']) if item['DepartmentName'] else 'N/A'
            },
            'sales_history': [],
            'recent_transactions': []
        }
        
        # Add sales history
        if not sales_history.empty:
            for _, row in sales_history.iterrows():
                response['sales_history'].append({
                    'date': row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date']),
                    'units_sold': float(row['units_sold']),
                    'revenue': float(row['revenue']),
                    'transactions': int(row['transactions'])
                })
        
        # Add recent transactions
        if not recent_transactions.empty:
            for _, row in recent_transactions.iterrows():
                response['recent_transactions'].append({
                    'transaction_number': int(row['TransactionNumber']),
                    'time': row['Time'].isoformat() if hasattr(row['Time'], 'isoformat') else str(row['Time']),
                    'quantity': float(row['Quantity']),
                    'price': float(row['Price']),
                    'line_total': float(row['line_total']),
                    'customer_name': str(row['customer_name'])
                })
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Item details error: {e}")
        return jsonify({'error': str(e)}), 500

# ===================
# SALES/PAYMENTS/OPS ROUTES
# ===================

@app.route('/api/sales-ops/overview')
@with_db_lock
def sales_ops_overview():
    """Get sales/payments/operations overview for a specific date"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get date parameter (default to today)
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Set date range for the full day
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Sales Overview Query
        sales_query = """
        SELECT 
            COUNT(DISTINCT t.TransactionNumber) as total_transactions,
            COALESCE(SUM(te.Price * te.Quantity), 0) as total_sales,
            COALESCE(SUM(te.Quantity), 0) as total_units,
            COALESCE(AVG(te.Price * te.Quantity), 0) as avg_transaction,
            COUNT(DISTINCT t.CustomerID) as unique_customers
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        """
        
        # Payments Overview Query
        payments_query = """
        SELECT 
            COUNT(*) as total_payments,
            COALESCE(SUM(Amount), 0) as total_payment_amount,
            COUNT(DISTINCT CustomerID) as customers_paid
        FROM dbo.Payment
        WHERE Time >= %s AND Time <= %s
          AND (Comment IS NULL OR Comment NOT LIKE '%NSF%')
        """
        
        # Operations Query - Transaction types and cashier activity
        ops_query = """
        SELECT 
            t.CashierID,
            COUNT(DISTINCT t.TransactionNumber) as transactions_processed,
            COALESCE(SUM(te.Price * te.Quantity), 0) as sales_processed
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY t.CashierID
        ORDER BY sales_processed DESC
        """
        
        # Execute queries
        sales_result = db.execute_query(sales_query, [start_date, end_date])
        payments_result = db.execute_query(payments_query, [start_date, end_date])
        ops_result = db.execute_query(ops_query, [start_date, end_date])
        
        # Format response
        response = {
            'date': date_str,
            'sales': {
                'total_transactions': int(sales_result.iloc[0]['total_transactions']) if not sales_result.empty else 0,
                'total_sales': float(sales_result.iloc[0]['total_sales']) if not sales_result.empty else 0.0,
                'total_units': int(sales_result.iloc[0]['total_units']) if not sales_result.empty else 0,
                'avg_transaction': float(sales_result.iloc[0]['avg_transaction']) if not sales_result.empty else 0.0,
                'unique_customers': int(sales_result.iloc[0]['unique_customers']) if not sales_result.empty else 0
            },
            'payments': {
                'total_payments': int(payments_result.iloc[0]['total_payments']) if not payments_result.empty else 0,
                'total_amount': float(payments_result.iloc[0]['total_payment_amount']) if not payments_result.empty else 0.0,
                'customers_paid': int(payments_result.iloc[0]['customers_paid']) if not payments_result.empty else 0
            },
            'operations': {
                'cashier_activity': []
            }
        }
        
        # Add cashier data
        if not ops_result.empty:
            for _, row in ops_result.iterrows():
                response['operations']['cashier_activity'].append({
                    'cashier_id': int(row['CashierID']) if pd.notna(row['CashierID']) else 0,
                    'transactions': int(row['transactions_processed']),
                    'sales_volume': float(row['sales_processed'])
                })
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Sales ops overview error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-ops/sales-detail')
@with_db_lock
def sales_ops_sales_detail():
    """Get detailed sales transactions for a specific date"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get parameters
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        limit = min(int(request.args.get('limit', 100)), 500)  # Max 500 records
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        query = """
        SELECT TOP %s
            t.TransactionNumber,
            t.Time,
            t.Total,
            t.SalesTax,
            COALESCE(c.FirstName + ' ' + c.LastName, c.Company, 'Cash Sale') as CustomerName,
            c.ID as CustomerID,
            COUNT(te.ID) as LineItemCount,
            SUM(te.Quantity) as TotalUnits
        FROM [dbo].[Transaction] t
        LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
        LEFT JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY t.TransactionNumber, t.Time, t.Total, t.SalesTax, c.FirstName, c.LastName, c.Company, c.ID
        ORDER BY t.Time DESC
        """
        
        result = db.execute_query(query, [limit, start_date, end_date])
        
        transactions = []
        if not result.empty:
            for _, row in result.iterrows():
                transactions.append({
                    'transaction_number': int(row['TransactionNumber']),
                    'time': row['Time'].strftime('%H:%M:%S'),
                    'total': float(row['Total']),
                    'sales_tax': float(row['SalesTax']),
                    'customer_name': str(row['CustomerName']),
                    'customer_id': int(row['CustomerID']) if pd.notna(row['CustomerID']) else None,
                    'line_items': int(row['LineItemCount']),
                    'total_units': int(row['TotalUnits'])
                })
        
        return jsonify({
            'date': date_str,
            'transactions': transactions,
            'total_count': len(transactions)
        })
        
    except Exception as e:
        logger.error(f"Sales detail error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-ops/payments-detail')
@with_db_lock
def sales_ops_payments_detail():
    """Get detailed payment transactions for a specific date"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get parameters
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        limit = min(int(request.args.get('limit', 100)), 500)
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        query = """
        SELECT TOP %s
            p.ID as PaymentID,
            p.Time,
            p.Amount,
            p.Type,
            p.Number as CheckNumber,
            p.Comment,
            COALESCE(c.FirstName + ' ' + c.LastName, c.Company, 'Unknown') as CustomerName,
            c.ID as CustomerID,
            c.AccountNumber
        FROM dbo.Payment p
        LEFT JOIN dbo.Customer c ON p.CustomerID = c.ID
        WHERE p.Time >= %s AND p.Time <= %s
        ORDER BY p.Time DESC
        """
        
        result = db.execute_query(query, [limit, start_date, end_date])
        
        payments = []
        if not result.empty:
            for _, row in result.iterrows():
                payments.append({
                    'payment_id': int(row['PaymentID']),
                    'time': row['Time'].strftime('%H:%M:%S'),
                    'amount': float(row['Amount']),
                    'type': int(row['Type']) if pd.notna(row['Type']) else None,
                    'check_number': str(row['CheckNumber']) if pd.notna(row['CheckNumber']) else None,
                    'comment': str(row['Comment']) if pd.notna(row['Comment']) else None,
                    'customer_name': str(row['CustomerName']),
                    'customer_id': int(row['CustomerID']) if pd.notna(row['CustomerID']) else None,
                    'account_number': str(row['AccountNumber']) if pd.notna(row['AccountNumber']) else None
                })
        
        return jsonify({
            'date': date_str,
            'payments': payments,
            'total_count': len(payments)
        })
        
    except Exception as e:
        logger.error(f"Payments detail error: {e}")
        return jsonify({'error': str(e)}), 500

# ===================
# SUPPLIER/PURCHASE ORDER ROUTES
# ===================

@app.route('/api/suppliers/overview')
@with_db_lock
def suppliers_overview():
    """Get suppliers overview with statistics"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get supplier counts and stats
        overview_query = """
        SELECT 
            COUNT(DISTINCT s.ID) as total_suppliers,
            COUNT(DISTINCT CASE WHEN po.DateCreated >= DATEADD(day, -30, GETDATE()) THEN s.ID END) as active_suppliers_30d,
            COUNT(DISTINCT po.ID) as total_purchase_orders,
            COUNT(DISTINCT CASE WHEN po.DateCreated >= DATEADD(day, -30, GETDATE()) THEN po.ID END) as recent_pos_30d,
            COUNT(DISTINCT CASE WHEN po.Status = 0 THEN po.ID END) as open_pos,
            SUM(CASE WHEN po.DateCreated >= DATEADD(day, -30, GETDATE()) THEN poe.Price * poe.QuantityOrdered ELSE 0 END) as spending_30d
        FROM dbo.Supplier s
        LEFT JOIN dbo.PurchaseOrder po ON s.ID = po.SupplierID
        LEFT JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
        """
        
        result = db.execute_query(overview_query, [], "Suppliers overview")
        
        if not result.empty:
            row = result.iloc[0]
            response = {
                'total_suppliers': int(row['total_suppliers']),
                'active_suppliers_30d': int(row['active_suppliers_30d']),
                'total_purchase_orders': int(row['total_purchase_orders']),
                'recent_pos_30d': int(row['recent_pos_30d']),
                'open_pos': int(row['open_pos']),
                'spending_30d': float(row['spending_30d']) if pd.notna(row['spending_30d']) else 0.0
            }
        else:
            response = {
                'total_suppliers': 0,
                'active_suppliers_30d': 0,
                'total_purchase_orders': 0,
                'recent_pos_30d': 0,
                'open_pos': 0,
                'spending_30d': 0.0
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Suppliers overview error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers/list')
@with_db_lock
def suppliers_list():
    """Get list of suppliers with recent activity"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get parameters
        limit = min(int(request.args.get('limit', 50)), 200)
        category_filter = request.args.get('category', '')
        
        # Build query based on filters
        where_clause = ""
        params = [limit]
        
        if category_filter:
            where_clause = """
            AND EXISTS (
                SELECT 1 FROM dbo.PurchaseOrder po2
                JOIN dbo.PurchaseOrderEntry poe2 ON po2.ID = poe2.PurchaseOrderID
                JOIN dbo.Item i2 ON poe2.ItemID = i2.ID
                JOIN dbo.Category c2 ON i2.CategoryID = c2.ID
                WHERE po2.SupplierID = s.ID AND c2.Name = %s
            )
            """
            params.append(category_filter)
        
        query = f"""
        SELECT TOP %s
            s.ID,
            s.SupplierName,
            s.ContactName,
            s.PhoneNumber,
            s.EmailAddress,
            s.City,
            s.State,
            COUNT(DISTINCT po.ID) as total_pos,
            COUNT(DISTINCT CASE WHEN po.DateCreated >= DATEADD(day, -90, GETDATE()) THEN po.ID END) as recent_pos,
            MAX(po.DateCreated) as last_order_date,
            SUM(CASE WHEN po.DateCreated >= DATEADD(day, -30, GETDATE()) THEN poe.Price * poe.QuantityOrdered ELSE 0 END) as spending_30d,
            COUNT(DISTINCT CASE WHEN po.Status = 0 THEN po.ID END) as open_pos
        FROM dbo.Supplier s
        LEFT JOIN dbo.PurchaseOrder po ON s.ID = po.SupplierID
        LEFT JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
        WHERE 1=1 {where_clause}
        GROUP BY s.ID, s.SupplierName, s.ContactName, s.PhoneNumber, s.EmailAddress, s.City, s.State
        ORDER BY ISNULL(MAX(po.DateCreated), '1900-01-01') DESC, SUM(CASE WHEN po.DateCreated >= DATEADD(day, -30, GETDATE()) THEN poe.Price * poe.QuantityOrdered ELSE 0 END) DESC
        """
        
        result = db.execute_query(query, params, "Suppliers list")
        
        suppliers = []
        if not result.empty:
            for _, row in result.iterrows():
                suppliers.append({
                    'id': int(row['ID']),
                    'name': str(row['SupplierName']),
                    'contact': str(row['ContactName']) if pd.notna(row['ContactName']) else '',
                    'phone': str(row['PhoneNumber']) if pd.notna(row['PhoneNumber']) else '',
                    'email': str(row['EmailAddress']) if pd.notna(row['EmailAddress']) else '',
                    'location': f"{row['City']}, {row['State']}" if pd.notna(row['City']) and pd.notna(row['State']) else '',
                    'total_pos': int(row['total_pos']),
                    'recent_pos': int(row['recent_pos']),
                    'last_order_date': row['last_order_date'].strftime('%Y-%m-%d') if pd.notna(row['last_order_date']) else None,
                    'spending_30d': float(row['spending_30d']) if pd.notna(row['spending_30d']) else 0.0,
                    'open_pos': int(row['open_pos'])
                })
        
        return jsonify({
            'suppliers': suppliers,
            'total_count': len(suppliers)
        })
        
    except Exception as e:
        logger.error(f"Suppliers list error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers/purchase-orders')
@with_db_lock
def purchase_orders_list():
    """Get list of purchase orders with filtering"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get parameters
        limit = min(int(request.args.get('limit', 100)), 500)
        status_filter = request.args.get('status', 'all')  # all, open, closed
        supplier_id = request.args.get('supplier_id')
        days = int(request.args.get('days', 30))
        
        # Build where clause
        where_conditions = [f"po.DateCreated >= DATEADD(day, -{days}, GETDATE())"]
        params = [limit]
        
        if status_filter == 'open':
            where_conditions.append("po.Status = 0")
        elif status_filter == 'closed':
            where_conditions.append("po.Status = 1")
        
        if supplier_id:
            where_conditions.append("po.SupplierID = %s")
            params.append(int(supplier_id))
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT TOP %s
            po.ID,
            po.PONumber,
            po.DateCreated,
            po.Status,
            po.RequiredDate,
            s.SupplierName,
            s.ID as SupplierID,
            COUNT(poe.ID) as item_count,
            SUM(poe.QuantityOrdered) as total_quantity,
            SUM(poe.QuantityReceived) as received_quantity,
            SUM(poe.Price * poe.QuantityOrdered) as total_value,
            po.Remarks
        FROM dbo.PurchaseOrder po
        JOIN dbo.Supplier s ON po.SupplierID = s.ID
        LEFT JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
        WHERE {where_clause}
        GROUP BY po.ID, po.PONumber, po.DateCreated, po.Status, po.RequiredDate, s.SupplierName, s.ID, po.Remarks
        ORDER BY po.DateCreated DESC
        """
        
        result = db.execute_query(query, params, "Purchase orders list")
        
        purchase_orders = []
        if not result.empty:
            for _, row in result.iterrows():
                status_map = {0: 'Open', 1: 'Closed', 2: 'Cancelled'}
                status_name = status_map.get(row['Status'], f'Status-{row["Status"]}')
                
                completion_pct = 0
                if row['total_quantity'] and row['total_quantity'] > 0:
                    completion_pct = (row['received_quantity'] / row['total_quantity']) * 100
                
                purchase_orders.append({
                    'id': int(row['ID']),
                    'po_number': str(row['PONumber']),
                    'date_created': row['DateCreated'].strftime('%Y-%m-%d'),
                    'status': status_name,
                    'status_id': int(row['Status']),
                    'supplier_name': str(row['SupplierName']),
                    'supplier_id': int(row['SupplierID']),
                    'item_count': int(row['item_count']),
                    'total_quantity': float(row['total_quantity']) if pd.notna(row['total_quantity']) else 0,
                    'received_quantity': float(row['received_quantity']) if pd.notna(row['received_quantity']) else 0,
                    'completion_pct': round(completion_pct, 1),
                    'total_value': float(row['total_value']) if pd.notna(row['total_value']) else 0,
                    'required_date': row['RequiredDate'].strftime('%Y-%m-%d') if pd.notna(row['RequiredDate']) else None,
                    'remarks': str(row['Remarks']) if pd.notna(row['Remarks']) else ''
                })
        
        return jsonify({
            'purchase_orders': purchase_orders,
            'total_count': len(purchase_orders)
        })
        
    except Exception as e:
        logger.error(f"Purchase orders list error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers/inventory-alerts')
@with_db_lock
def inventory_alerts():
    """Get low stock and ordering alerts for cigarettes/tobacco"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Get low stock cigarettes and tobacco
        low_stock_query = """
        SELECT TOP 20
            i.ID,
            i.Description,
            i.Quantity as current_stock,
            i.Cost,
            i.Price,
            i.LastSold,
            c.Name as category,
            DATEDIFF(day, i.LastSold, GETDATE()) as days_since_sold,
            -- Calculate suggested reorder based on recent sales
            CASE 
                WHEN i.LastSold IS NULL THEN 0
                WHEN DATEDIFF(day, i.LastSold, GETDATE()) <= 7 THEN 50
                WHEN DATEDIFF(day, i.LastSold, GETDATE()) <= 30 THEN 25
                ELSE 10
            END as suggested_reorder
        FROM dbo.Item i
        JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE c.Name IN ('CIGARETTE', 'CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'T7 SMOKELESS GA', 'ECIG - PODS')
          AND i.Quantity <= 20
          AND i.Inactive = 0
        ORDER BY 
            CASE WHEN i.Quantity <= 0 THEN 0 ELSE 1 END,
            i.Quantity ASC,
            ISNULL(i.LastSold, '1900-01-01') DESC
        """
        
        result = db.execute_query(low_stock_query, [], "Low stock alerts")
        
        alerts = []
        if not result.empty:
            for _, row in result.iterrows():
                alert_level = 'critical' if row['current_stock'] <= 0 else ('warning' if row['current_stock'] <= 5 else 'info')
                
                alerts.append({
                    'item_id': int(row['ID']),
                    'description': str(row['Description']),
                    'current_stock': float(row['current_stock']),
                    'category': str(row['category']),
                    'cost': float(row['Cost']),
                    'price': float(row['Price']),
                    'last_sold': row['LastSold'].strftime('%Y-%m-%d') if pd.notna(row['LastSold']) else None,
                    'days_since_sold': int(row['days_since_sold']) if pd.notna(row['days_since_sold']) else None,
                    'suggested_reorder': int(row['suggested_reorder']),
                    'alert_level': alert_level
                })
        
        return jsonify({
            'alerts': alerts,
            'total_count': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Inventory alerts error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers/top-products')
@with_db_lock
def top_ordered_products():
    """Get top ordered cigarette/tobacco products"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        days = int(request.args.get('days', 90))
        limit = min(int(request.args.get('limit', 20)), 100)
        
        query = f"""
        SELECT TOP %s
            i.ID,
            i.Description,
            c.Name as category,
            SUM(poe.QuantityOrdered) as total_ordered,
            COUNT(DISTINCT po.ID) as order_count,
            AVG(poe.Price) as avg_cost,
            MAX(po.DateCreated) as last_ordered,
            i.Quantity as current_stock,
            -- Calculate velocity (orders per week)
            CAST(SUM(poe.QuantityOrdered) as FLOAT) / NULLIF(DATEDIFF(week, MIN(po.DateCreated), MAX(po.DateCreated)), 0) as weekly_velocity
        FROM dbo.PurchaseOrderEntry poe
        JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
        JOIN dbo.Item i ON poe.ItemID = i.ID
        JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE c.Name IN ('CIGARETTE', 'CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'T7 SMOKELESS GA', 'ECIG - PODS')
          AND po.DateCreated >= DATEADD(day, -{days}, GETDATE())
        GROUP BY i.ID, i.Description, c.Name, i.Quantity
        ORDER BY total_ordered DESC
        """
        
        result = db.execute_query(query, [limit], "Top ordered products")
        
        products = []
        if not result.empty:
            for _, row in result.iterrows():
                products.append({
                    'item_id': int(row['ID']),
                    'description': str(row['Description']),
                    'category': str(row['category']),
                    'total_ordered': float(row['total_ordered']),
                    'order_count': int(row['order_count']),
                    'avg_cost': float(row['avg_cost']),
                    'last_ordered': row['last_ordered'].strftime('%Y-%m-%d'),
                    'current_stock': float(row['current_stock']),
                    'weekly_velocity': float(row['weekly_velocity']) if pd.notna(row['weekly_velocity']) else 0
                })
        
        return jsonify({
            'products': products,
            'total_count': len(products),
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Top ordered products error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wholesale-retail/analysis')
@with_db_lock
def wholesale_retail_analysis():
    """Get wholesale vs retail analysis with FIXED calculations and proper aggregation"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Import the fixed wholesale retail module
        from modules.wholesale_retail_fixed import WholesaleRetailAnalysis
        
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period_type = request.args.get('period', 'ytd')  # ytd, custom, comparative
        
        # Create analyzer with fixed calculations
        analyzer = WholesaleRetailAnalysis(db)
        
        # Get analysis based on period type
        if period_type == 'comparative':
            # Use the fixed comparative analysis
            results = analyzer.get_comparative_analysis()
        else:
            # Get YTD analysis using fixed module
            results = analyzer.get_comparative_analysis()  # Returns list with current YTD
            if results:
                results = [results[0]]  # Just current year
        
        return jsonify({
            'status': 'success',
            'analysis_type': period_type,
            'periods': results,
            'summary': {
                'total_sales': sum(p.get('total_sales', 0) for p in results),
                'total_gp': sum(p.get('total_gp', 0) for p in results),
                'wholesale_sales': sum(p.get('wholesale_sales', 0) for p in results),
                'retail_sales': sum(p.get('retail_sales', 0) for p in results)
            }
        })
        
    except Exception as e:
        logger.error(f"Wholesale retail analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wholesale-retail/ytd-comparison')
@with_db_lock
def wholesale_retail_ytd_comparison():
    """Get YTD comparison across multiple years"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        years = [2025, 2024, 2023, 2022, 2021]
        results = []
        
        for year in years:
            start_date = f'{year}-01-01'
            end_date = f'{year}-08-18'
            
            query = f"""
            WITH TransactionSummary AS (
                SELECT 
                    SUM(te.Price * te.Quantity) as line_revenue,
                    SUM(
                        CASE 
                            WHEN c.Name IN ('CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'LITTLE CIGAR-GA') 
                            THEN te.Cost * te.Quantity * 1.23
                            ELSE te.Cost * te.Quantity
                        END
                    ) as line_cost,
                    CASE 
                        WHEN (cust.Company LIKE '%WHOLESALE%' OR cust.Company LIKE '%WHSL%' OR cust.Company LIKE '%DIST%')
                             OR (AVG(te.Quantity) >= 30 AND COUNT(te.ID) <= 8)
                             AND NOT (COUNT(te.ID) >= 20 AND AVG(te.Quantity) < 10)
                        THEN 'WHOLESALE'
                        ELSE 'RETAIL'
                    END as transaction_type
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                JOIN dbo.Item i ON te.ItemID = i.ID
                LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
                LEFT JOIN dbo.Customer cust ON t.CustomerID = cust.ID
                WHERE t.Time >= '{start_date}' AND t.Time <= '{end_date}'
                  AND t.Total > 0
                GROUP BY t.TransactionNumber, cust.Company
            )
            SELECT 
                transaction_type,
                SUM(line_revenue) as total_sales,
                SUM(line_revenue - line_cost) as gross_profit
            FROM TransactionSummary
            GROUP BY transaction_type
            """
            
            year_result = db.execute_query(query, [], f'YTD {year}')
            
            year_data = {
                'year': year,
                'wholesale_sales': 0,
                'retail_sales': 0,
                'wholesale_gp': 0,
                'retail_gp': 0
            }
            
            if not year_result.empty:
                for _, row in year_result.iterrows():
                    trans_type = row['transaction_type'].lower()
                    year_data[f'{trans_type}_sales'] = float(row['total_sales']) if pd.notna(row['total_sales']) else 0
                    year_data[f'{trans_type}_gp'] = float(row['gross_profit']) if pd.notna(row['gross_profit']) else 0
            
            year_data['total_sales'] = year_data['wholesale_sales'] + year_data['retail_sales']
            year_data['total_gp'] = year_data['wholesale_gp'] + year_data['retail_gp']
            
            results.append(year_data)
        
        return jsonify({
            'status': 'success',
            'ytd_comparison': results
        })
        
    except Exception as e:
        logger.error(f"YTD comparison error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wholesale-retail/wholesale-customers')
@with_db_lock
def wholesale_customers_detail():
    """Get detailed wholesale customer breakdown with FIXED calculations"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Import fixed module
        from modules.wholesale_retail_fixed import WholesaleRetailAnalysis
        
        limit = min(int(request.args.get('limit', 50)), 200)
        
        # Create analyzer and get wholesale customers
        analyzer = WholesaleRetailAnalysis(db)
        customers = analyzer.get_wholesale_customers(limit)
        
        return jsonify({
            'status': 'success',
            'wholesale_customers': customers,
            'total_count': len(customers)
        })
        
    except Exception as e:
        logger.error(f'Wholesale customers detail error: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/wholesale-retail/monthly/<int:year>')
@with_db_lock
def wholesale_retail_monthly(year):
    """Get monthly breakdown for specified year with FIXED calculations"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        # Import fixed module
        from modules.wholesale_retail_fixed import WholesaleRetailAnalysis
        
        # Create analyzer and get monthly data
        analyzer = WholesaleRetailAnalysis(db)
        monthly_data = analyzer.get_monthly_analysis(year)
        
        return jsonify({
            'status': 'success',
            'year': year,
            'monthly_data': monthly_data
        })
        
    except Exception as e:
        logger.error(f'Monthly {year} error: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ===================
# GP ANALYSIS ROUTES
# ===================

@app.route('/api/gp/executive-summary')
@with_db_lock
def gp_executive_summary():
    """Get GP executive summary metrics"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 'YTD')
        gp_analyzer = GPAnalysis(db)
        summary = gp_analyzer.get_executive_summary(timeframe)
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error in GP executive summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/trending')
@with_db_lock
def gp_trending():
    """Get GP trending data"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 'YTD')
        gp_analyzer = GPAnalysis(db)
        trending_data = gp_analyzer.get_gp_trending(timeframe)
        
        return jsonify(trending_data)
        
    except Exception as e:
        logger.error(f"Error in GP trending: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/categories')
@with_db_lock
def gp_categories():
    """Get GP by category analysis"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 'YTD')
        gp_analyzer = GPAnalysis(db)
        category_data = gp_analyzer.get_category_gp_analysis(timeframe)
        
        return jsonify(category_data)
        
    except Exception as e:
        logger.error(f"Error in GP category analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/customers')
@with_db_lock
def gp_customers():
    """Get GP by customer analysis"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 'YTD')
        limit = int(request.args.get('limit', 100))
        gp_analyzer = GPAnalysis(db)
        customer_data = gp_analyzer.get_customer_gp_analysis(timeframe, limit)
        
        return jsonify(customer_data)
        
    except Exception as e:
        logger.error(f"Error in GP customer analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/products')
@with_db_lock
def gp_products():
    """Get GP by product analysis"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 'YTD')
        gp_analyzer = GPAnalysis(db)
        
        # Get both top and low margin products
        top_products = gp_analyzer.get_product_gp_analysis(timeframe, top_n=20)
        low_products = gp_analyzer.get_low_margin_products(timeframe, limit=20)
        
        return jsonify({
            'top_products': top_products,
            'low_margin_products': low_products
        })
        
    except Exception as e:
        logger.error(f"Error in GP product analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gp/opportunities')
@with_db_lock
def gp_opportunities():
    """Get GP improvement opportunities"""
    try:
        if not db:
            return jsonify({'error': 'Database not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 'YTD')
        gp_analyzer = GPAnalysis(db)
        opportunities = gp_analyzer.get_gp_opportunities(timeframe)
        
        return jsonify(opportunities)
        
    except Exception as e:
        logger.error(f"Error in GP opportunities: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Register AR routes
register_ar_routes(app)
register_cohort_routes(app)
register_ledger_routes(app)

# Register customer balance API
app.register_blueprint(customer_balance_api)

# Register transaction detail API
app.register_blueprint(transaction_detail_api)

# Register professional excel export API
app.register_blueprint(professional_excel_api)


# Initialize database and AI assistant on module load
logger.info("🚀 Initializing Georgia Business Dashboard")

# Initialize database
if init_database():
    logger.info("📊 Database: Connected")
else:
    logger.error("❌ Database: Failed to connect")

# Initialize AI Assistant
init_ai_assistant()

# Run app if executed directly
if __name__ == '__main__':
    # Start the application
    port = int(os.environ.get('PORT', 8081))
    logger.info(f"🌐 Server starting on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)