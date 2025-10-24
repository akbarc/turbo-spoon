"""
AR Dashboard Flask Routes
Handles all AR-related endpoints
"""

from flask import Flask, render_template, jsonify, request, send_file
from io import BytesIO
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from modules.ar import ARManager, CashFlowPredictor
from modules.ar.simple_name_grouping import SimpleNameGrouper
from modules.ar.optimized_customer_groups import OptimizedCustomerGrouper  # New optimized module
from modules.pd_check_parser import PDCheckParser
from modules.customer_analytics import CustomerAnalytics
from modules.customer_api import customer_api
from modules.risk_analysis_api import risk_analysis_api

logger = logging.getLogger(__name__)

def replace_nan_values(obj):
    """Recursively replace NaN values with None in nested data structures and handle bytes"""
    if isinstance(obj, dict):
        return {k: replace_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_values(item) for item in obj]
    elif isinstance(obj, float) and np.isnan(obj):
        return None
    elif isinstance(obj, bytes):
        # Convert bytes to hex string or skip
        return None  # Skip binary data for JSON serialization
    else:
        return obj

def register_ar_routes(app):
    """Register AR routes with the Flask app"""
    
    ar_manager = ARManager()
    grouper = SimpleNameGrouper()  # Using simple name-only fuzzy matching (OLD - will be archived)
    optimized_grouper = OptimizedCustomerGrouper()  # NEW optimized grouper with lazy loading
    predictor = CashFlowPredictor()
    customer_analytics = CustomerAnalytics()
    
    # Register customer API blueprint
    app.register_blueprint(customer_api)
    
    # Register risk analysis API blueprint
    app.register_blueprint(risk_analysis_api)
    
    @app.route('/ar-dashboard')
    def ar_dashboard():
        """Main AR dashboard page"""
        return render_template('ar_dashboard_new.html')

    @app.route('/customer-groups-optimized')
    def customer_groups_optimized():
        """New optimized customer groups page with lazy loading"""
        return render_template('customer_groups_optimized.html')
    
    @app.route('/api/ar/summary')
    def ar_summary():
        """Get AR summary data"""
        try:
            summary = ar_manager.get_ar_summary()
            return jsonify(summary)
        except Exception as e:
            logger.error(f"Error in ar_summary: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/customers')
    def ar_customers():
        """Get customer AR list"""
        try:
            min_balance = float(request.args.get('min_balance', 0))
            days_overdue = request.args.get('days_overdue', None)
            if days_overdue:
                days_overdue = int(days_overdue)
            sort_by = request.args.get('sort_by', 'balance_desc')
            
            customers = ar_manager.get_customer_ar_list(
                min_balance=min_balance,
                days_overdue=days_overdue,
                sort_by=sort_by
            )
            
            # Convert to dict for JSON response, handling datetime conversion and NaN values
            if not customers.empty:
                # Handle datetime columns
                for col in customers.columns:
                    if pd.api.types.is_datetime64_any_dtype(customers[col]):
                        customers[col] = customers[col].apply(lambda x: x.isoformat() if pd.notna(x) else None)
                
                # Replace NaN values with None (which becomes null in JSON)
                customers = customers.replace({np.nan: None})
                result = customers.to_dict('records')
            else:
                result = []
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in ar_customers: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/customer/<int:customer_id>')
    def ar_customer_detail(customer_id):
        """Get detailed AR info for a customer"""
        try:
            detail = ar_manager.get_customer_ar_detail(customer_id)
            
            # Handle NaN values in nested data structures
            detail = replace_nan_values(detail)
            return jsonify(detail)
        except Exception as e:
            logger.error(f"Error in ar_customer_detail: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/aging')
    def ar_aging():
        """Get aging report data"""
        try:
            aging = ar_manager.get_aging_report()
            if not aging.empty:
                # Replace NaN values with None (which becomes null in JSON)
                aging = aging.replace({np.nan: None})
                result = aging.to_dict('records')
            else:
                result = []
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in ar_aging: {e}")
            return jsonify({'error': str(e)}), 500
    
    # ============================================
    # NEW OPTIMIZED CUSTOMER GROUPS ENDPOINTS (v2)
    # ============================================

    @app.route('/api/ar/groups/v2/summary')
    def get_groups_summary_v2():
        """Get lightweight customer groups summary with pagination"""
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            min_balance = request.args.get('min_balance', 0, type=float)

            summary = optimized_grouper.get_groups_summary(
                page=page,
                limit=limit,
                min_balance=min_balance
            )
            return jsonify(summary)
        except Exception as e:
            logger.error(f"Error getting groups summary v2: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ar/groups/v2/<group_key>/preview')
    def get_group_preview_v2(group_key):
        """Get group preview with member names only"""
        try:
            preview = optimized_grouper.get_group_preview(group_key)
            return jsonify(preview)
        except Exception as e:
            logger.error(f"Error getting group preview v2: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ar/groups/v2/<group_key>/full')
    def get_group_full_v2(group_key):
        """Get complete group details with payment history"""
        try:
            days_filter = request.args.get('days', 30, type=int)
            details = optimized_grouper.get_group_full_details(
                group_key,
                days_filter=days_filter
            )
            return jsonify(details)
        except Exception as e:
            logger.error(f"Error getting group full details v2: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ar/groups/v2/search')
    def search_groups_v2():
        """Fast search for customer groups"""
        try:
            search_term = request.args.get('q', '')
            limit = request.args.get('limit', 10, type=int)

            results = optimized_grouper.search_groups(
                search_term=search_term,
                limit=limit
            )
            return jsonify(results)
        except Exception as e:
            logger.error(f"Error searching groups v2: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ar/groups/v2/cache/stats')
    def get_cache_stats_v2():
        """Get cache statistics for monitoring"""
        try:
            stats = optimized_grouper.get_cache_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ar/groups/v2/cache/clear', methods=['POST'])
    def clear_cache_v2():
        """Clear the cache (admin function)"""
        try:
            optimized_grouper.clear_cache()
            return jsonify({'success': True, 'message': 'Cache cleared'})
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return jsonify({'error': str(e)}), 500

    # ============================================
    # OLD CUSTOMER GROUPS ENDPOINTS (ARCHIVED)
    # Keeping these for backward compatibility
    # ============================================

    @app.route('/api/ar/groups/find')
    def find_customer_groups():
        """[ARCHIVED] Find customer groups based on fuzzy name matching"""
        try:
            days_filter = request.args.get('days', 30, type=int)
            groups = grouper.find_name_groups(days_filter=days_filter)
            return jsonify(groups)
        except Exception as e:
            logger.error(f"Error finding groups: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/groups/export')
    def export_customer_groups():
        """Export comprehensive customer groups data"""
        try:
            days_filter = request.args.get('days', 30, type=int)
            export_data = grouper.export_all_groups_detailed(days_filter=days_filter)
            return jsonify({
                'success': True,
                'data': export_data,
                'total_groups': len(export_data),
                'total_customers': sum(g['customer_count'] for g in export_data),
                'exported_at': datetime.now().isoformat(),
                'days_filter': days_filter
            })
        except Exception as e:
            logger.error(f"Error exporting groups: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/groups/export/excel')
    def export_customer_groups_excel():
        """Export customer groups to Excel file"""
        try:
            from modules.customer_groups_excel_export import CustomerGroupsExcelExporter
            from flask import send_file
            
            # Get the comprehensive export data
            days_filter = request.args.get('days', 30, type=int)
            export_data = grouper.export_all_groups_detailed(days_filter=days_filter)
            
            # Create Excel file
            exporter = CustomerGroupsExcelExporter()
            file_path = exporter.export_groups_to_excel(export_data)
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"customer_groups_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            logger.error(f"Error creating Excel export: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/groups/saved')
    def get_saved_groups():
        """Get saved customer groups"""
        try:
            groups = grouper.get_saved_groups()
            return jsonify(groups)
        except Exception as e:
            logger.error(f"Error getting saved groups: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/groups/detail', methods=['POST'])
    def get_group_detail():
        """Get comprehensive details for a customer group"""
        try:
            data = request.get_json()
            customer_ids = data.get('customer_ids', [])
            days_filter = data.get('days_filter', 30)
            detail = grouper.get_group_details(customer_ids, days_filter)
            return jsonify(detail)
        except Exception as e:
            logger.error(f"Error getting group detail: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/cashflow/simple')
    def simple_cash_flow():
        """Get simple cash flow predictions based on PD checks and historical averages"""
        try:
            days = int(request.args.get('days', 30))
            
            from database_pymssql import SQLServerConnection
            from datetime import date, timedelta
            
            with SQLServerConnection() as db:
                # Get scheduled PD checks for the next N days
                query_pd = """
                SELECT 
                    p.Time as payment_date,
                    p.Amount as amount,
                    p.Comment as comment,
                    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as customer_name
                FROM dbo.Payment p
                INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
                WHERE (
                    UPPER(p.Comment) LIKE '%%PD%%'
                    OR UPPER(p.Comment) LIKE '%%POST DATE%%'
                    OR p.Comment LIKE '%%/%%/%%'
                )
                AND p.Amount > 0
                AND p.Time >= DATEADD(day, -30, GETDATE())
                ORDER BY p.Time DESC
                """
                
                pd_df = db.execute_query(query_pd)
                
                # Get historical daily collection averages by day of week
                query_historical = """
                SELECT 
                    DATEPART(dw, p.Time) as day_of_week,
                    AVG(p.Amount) as avg_daily_amount,
                    COUNT(*) as payment_count,
                    SUM(p.Amount) as total_amount
                FROM dbo.Payment p
                WHERE p.Time >= DATEADD(month, -6, GETDATE())
                    AND p.Amount > 0
                    AND UPPER(p.Comment) NOT LIKE '%%NSF%%'
                    AND UPPER(p.Comment) NOT LIKE '%%RETURN%%'
                GROUP BY DATEPART(dw, p.Time)
                ORDER BY day_of_week
                """
                
                historical_df = db.execute_query(query_historical)
                
                # Create daily predictions
                predictions = []
                today = date.today()
                
                # Build day of week averages
                dow_averages = {}
                if not historical_df.empty:
                    for _, row in historical_df.iterrows():
                        dow_averages[int(row['day_of_week'])] = float(row['avg_daily_amount'])
                
                # Default average if no data
                overall_avg = sum(dow_averages.values()) / len(dow_averages) if dow_averages else 5000
                
                # Parse PD checks with dates
                pd_amounts = {}
                for _, row in pd_df.iterrows():
                    pd_info = PDCheckParser.extract_pd_info(row['comment'])
                    if pd_info.get('deposit_date') and pd_info.get('days_until_deposit', 0) >= 0:
                        pd_date = pd_info['deposit_date']
                        if isinstance(pd_date, str):
                            pd_date = datetime.strptime(pd_date, '%Y-%m-%d').date()
                        if pd_date not in pd_amounts:
                            pd_amounts[pd_date] = 0
                        pd_amounts[pd_date] += float(row['amount'])
                
                cumulative_cash_flow = 0
                for i in range(days):
                    current_date = today + timedelta(days=i)
                    day_of_week = current_date.isoweekday()  # 1=Monday, 7=Sunday
                    
                    # Convert to SQL Server day of week (1=Sunday, 7=Saturday)
                    sql_dow = 1 if day_of_week == 7 else day_of_week + 1
                    
                    # Base prediction from historical average
                    base_amount = dow_averages.get(sql_dow, overall_avg)
                    
                    # Add scheduled PD checks
                    pd_amount = pd_amounts.get(current_date, 0)
                    
                    # Total predicted amount
                    total_predicted = base_amount + pd_amount
                    cumulative_cash_flow += total_predicted
                    
                    predictions.append({
                        'date': current_date.isoformat(),
                        'day_of_week': current_date.strftime('%A'),
                        'base_prediction': round(base_amount, 2),
                        'pd_checks': round(pd_amount, 2),
                        'total_predicted': round(total_predicted, 2),
                        'cumulative': round(cumulative_cash_flow, 2),
                        'confidence': 'medium' if pd_amount > 0 else 'low'
                    })
                
                # Calculate summary
                total_30_day = sum(p['total_predicted'] for p in predictions)
                avg_daily = total_30_day / len(predictions) if predictions else 0
                pd_total = sum(p['pd_checks'] for p in predictions)
                
                return jsonify({
                    'success': True,
                    'predictions': predictions,
                    'summary': {
                        'total_30_day_forecast': round(total_30_day, 2),
                        'avg_daily_forecast': round(avg_daily, 2),
                        'scheduled_pd_checks': round(pd_total, 2),
                        'base_collections': round(total_30_day - pd_total, 2)
                    }
                })
                
        except Exception as e:
            logger.error(f"Error generating simple cash flow: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/cashflow/simple')
    def get_simple_cashflow():
        """Get cash flow based on PD checks and historical collection/sales ratios"""
        try:
            from database_pymssql import SQLServerConnection
            from datetime import datetime, timedelta
            import json
            
            days = int(request.args.get('days', 30))
            
            # Get scheduled PD checks for next N days
            pd_query = """
            SELECT 
                CAST(p.Time as DATE) as payment_date,
                p.Amount,
                p.Comment,
                c.Company as customer_name
            FROM dbo.Payment p
            INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
            WHERE (
                UPPER(p.Comment) LIKE '%PD%' OR 
                UPPER(p.Comment) LIKE '%POST DATE%' OR
                p.Comment LIKE '%/%/%'
            )
            AND p.Amount > 0
            AND p.Time >= DATEADD(day, -30, GETDATE())
            ORDER BY p.Time
            """
            
            # Calculate historical collection ratio (collections as % of prior period sales)
            collection_ratio_query = """
            WITH PeriodMetrics AS (
                -- Get weekly sales and collections for last 12 weeks
                SELECT 
                    DATEPART(week, t.Time) as week_num,
                    DATEPART(year, t.Time) as year_num,
                    SUM(CASE WHEN t.Type = 'Sale' THEN t.Total ELSE 0 END) as weekly_sales,
                    SUM(CASE WHEN t.Type = 'Payment' AND t.Total > 0 
                        AND NOT (UPPER(t.Comment) LIKE '%NSF%' OR UPPER(t.Comment) LIKE '%PD%')
                        THEN t.Total ELSE 0 END) as weekly_collections
                FROM dbo.[Transaction] t
                WHERE t.Time >= DATEADD(week, -12, GETDATE())
                GROUP BY DATEPART(week, t.Time), DATEPART(year, t.Time)
            ),
            LaggedMetrics AS (
                SELECT 
                    week_num,
                    year_num,
                    weekly_sales,
                    weekly_collections,
                    LAG(weekly_sales, 1) OVER (ORDER BY year_num, week_num) as prior_week_sales,
                    LAG(weekly_sales, 2) OVER (ORDER BY year_num, week_num) as two_weeks_ago_sales
                FROM PeriodMetrics
            )
            SELECT 
                AVG(CASE 
                    WHEN prior_week_sales > 0 
                    THEN weekly_collections / prior_week_sales 
                    ELSE 0 
                END) as one_week_collection_ratio,
                AVG(CASE 
                    WHEN two_weeks_ago_sales > 0 
                    THEN weekly_collections / two_weeks_ago_sales 
                    ELSE 0 
                END) as two_week_collection_ratio,
                AVG(weekly_collections) as avg_weekly_collections,
                AVG(weekly_sales) as avg_weekly_sales
            FROM LaggedMetrics
            WHERE prior_week_sales IS NOT NULL
            """
            
            # Get recent sales for projection base
            recent_sales_query = """
            SELECT 
                CAST(Time as DATE) as sale_date,
                SUM(Total) as daily_sales
            FROM dbo.[Transaction]
            WHERE Type = 'Sale'
                AND Time >= DATEADD(day, -14, GETDATE())
            GROUP BY CAST(Time as DATE)
            ORDER BY sale_date DESC
            """
            
            with SQLServerConnection() as db:
                # Get PD checks
                pd_df = db.execute_query(pd_query)
                
                # Get collection ratios
                ratio_df = db.execute_query(collection_ratio_query)
                if not ratio_df.empty:
                    one_week_ratio = float(ratio_df.iloc[0]['one_week_collection_ratio'] or 0.15)
                    two_week_ratio = float(ratio_df.iloc[0]['two_week_collection_ratio'] or 0.10)
                    avg_weekly = float(ratio_df.iloc[0]['avg_weekly_collections'] or 0)
                else:
                    one_week_ratio = 0.15  # Default 15% of sales collected after 1 week
                    two_week_ratio = 0.10  # Default 10% of sales collected after 2 weeks
                    avg_weekly = 50000
                
                # Get recent sales
                sales_df = db.execute_query(recent_sales_query)
                sales_by_date = {}
                for _, row in sales_df.iterrows():
                    sales_by_date[row['sale_date']] = float(row['daily_sales'])
                
                # Build daily forecast
                today = datetime.now().date()
                forecast = []
                
                for i in range(days):
                    date = today + timedelta(days=i)
                    dow = (date.weekday() + 2) % 7  # SQL Server day of week
                    
                    # Calculate expected collections based on prior sales
                    # Collections = (Sales from 7 days ago * 1-week ratio) + (Sales from 14 days ago * 2-week ratio)
                    week_ago = date - timedelta(days=7)
                    two_weeks_ago = date - timedelta(days=14)
                    
                    week_ago_sales = sales_by_date.get(week_ago, avg_weekly/7)
                    two_weeks_ago_sales = sales_by_date.get(two_weeks_ago, avg_weekly/7)
                    
                    # Expected collections from prior period sales
                    expected_from_sales = (week_ago_sales * one_week_ratio) + (two_weeks_ago_sales * two_week_ratio)
                    
                    # Add a base amount for same-day/walk-in payments (20% of daily average)
                    same_day_expected = avg_weekly / 7 * 0.20
                    
                    # Reduce expectations on weekends
                    if dow in [1, 7]:  # Sunday or Saturday
                        expected_from_sales *= 0.3
                        same_day_expected *= 0.2
                    
                    base_amount = expected_from_sales + same_day_expected
                    
                    # Add scheduled PD checks for this date
                    pd_amount = 0
                    pd_checks = []
                    
                    # Parse PD check dates and match to forecast date
                    for _, check in pd_df.iterrows():
                        pd_info = PDCheckParser.extract_pd_info(check['Comment'])
                        if pd_info['deposit_date'] and pd_info['deposit_date'] == date:
                            pd_amount += float(check['Amount'])
                            pd_checks.append({
                                'customer': check['customer_name'],
                                'amount': float(check['Amount'])
                            })
                    
                    forecast.append({
                        'date': date.isoformat(),
                        'day_name': date.strftime('%A'),
                        'expected_collections': base_amount,
                        'pd_checks_amount': pd_amount,
                        'total_expected': base_amount + pd_amount,
                        'pd_checks': pd_checks,
                        'is_weekend': dow in [1, 7],
                        'breakdown': {
                            'from_week_old_sales': week_ago_sales * one_week_ratio,
                            'from_two_week_old_sales': two_weeks_ago_sales * two_week_ratio,
                            'same_day_collections': same_day_expected
                        }
                    })
                
                # Calculate cumulative totals
                cumulative = 0
                for day in forecast:
                    cumulative += day['total_expected']
                    day['cumulative_total'] = cumulative
                
                return jsonify({
                    'success': True,
                    'forecast': forecast,
                    'summary': {
                        'total_expected': sum(d['total_expected'] for d in forecast),
                        'pd_checks_total': sum(d['pd_checks_amount'] for d in forecast),
                        'avg_daily': sum(d['expected_collections'] for d in forecast) / len(forecast) if forecast else 0,
                        'collection_ratios': {
                            'one_week': f"{one_week_ratio*100:.1f}%",
                            'two_week': f"{two_week_ratio*100:.1f}%"
                        }
                    }
                })
                
        except Exception as e:
            logger.error(f"Error getting simple cash flow: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/risks')
    def get_payment_risks():
        """Get customers with payment risks"""
        try:
            risks = predictor.identify_payment_risks()
            return jsonify(risks)
        except Exception as e:
            logger.error(f"Error identifying risks: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/export/<export_type>')
    def export_ar_data(export_type):
        """Export AR data as CSV"""
        try:
            customer_id = request.args.get('customer_id', None)
            if customer_id:
                customer_id = int(customer_id)
            
            content, filename = ar_manager.export_ar_data(
                data_type=export_type,
                format='csv',
                customer_id=customer_id
            )
            
            if content:
                return send_file(
                    BytesIO(content),
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=filename
                )
            else:
                return jsonify({'error': 'No data to export'}), 404
                
        except Exception as e:
            logger.error(f"Error exporting AR data: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/metrics')
    def get_ar_metrics():
        """Get AR performance metrics"""
        try:
            period = int(request.args.get('period', 30))
            
            # Get DSO
            dso = ar_manager.calculate_dso(period)
            
            # Get collection metrics
            metrics = ar_manager.get_collection_metrics(period)
            
            # Add DSO to metrics
            metrics['dso'] = dso
            
            return jsonify(metrics)
            
        except Exception as e:
            logger.error(f"Error getting AR metrics: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/ar/model-accuracy')
    def get_model_accuracy():
        """Get cash flow model accuracy metrics"""
        try:
            accuracy = predictor.get_prediction_accuracy(lookback_days=30)
            return jsonify({
                'success': True,
                'accuracy': accuracy
            })
        except Exception as e:
            logger.error(f"Error getting model accuracy: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/ar/nsf-returns')
    def get_nsf_returns():
        """Get NSF and returned checks data"""
        try:
            from database_pymssql import SQLServerConnection
            from datetime import date, timedelta
            
            period = int(request.args.get('period', 30))  # days
            
            # Query for NSF/returned checks
            query = """
            SELECT 
                p.ID as payment_id,
                p.Time as nsf_date,
                p.Amount as amount,
                p.Comment as comment,
                c.ID as customer_id,
                c.Company as company,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as customer_name,
                c.FirstName,
                c.LastName,
                c.AccountBalance as account_balance,
                c.PhoneNumber,
                CASE 
                    WHEN UPPER(p.Comment) LIKE '%NSF%' THEN 'NSF'
                    WHEN UPPER(p.Comment) LIKE '%RETURN%' THEN 'RETURNED'
                    WHEN UPPER(p.Comment) LIKE '%BOUNCE%' THEN 'BOUNCED'
                    WHEN UPPER(p.Comment) LIKE '%INSUFFICIENT%' THEN 'NSF'
                    WHEN UPPER(p.Comment) LIKE '%NON SUFFICIENT%' THEN 'NSF'
                    ELSE 'OTHER'
                END as nsf_type,
                CASE 
                    WHEN UPPER(p.Comment) LIKE '%FEE%' THEN 'FEE'
                    ELSE 'CHECK'
                END as entry_type,
                DATEDIFF(day, p.Time, GETDATE()) as days_old
            FROM dbo.Payment p
            INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
            WHERE p.Time >= DATEADD(day, -%s, GETDATE())
                AND (
                    UPPER(p.Comment) LIKE '%%NSF%%'
                    OR UPPER(p.Comment) LIKE '%%RETURN%%'
                    OR UPPER(p.Comment) LIKE '%%BOUNCE%%'
                    OR UPPER(p.Comment) LIKE '%%INSUFFICIENT%%'
                    OR UPPER(p.Comment) LIKE '%%NON SUFFICIENT%%'
                    OR UPPER(p.Comment) LIKE '%%DECLINED%%'
                    OR UPPER(p.Comment) LIKE '%%DISHONOR%%'
                )
            ORDER BY p.Time DESC
            """
            
            with SQLServerConnection() as db:
                df = db.execute_query(query, [period])
            
                nsf_data = []
                nsf_fees = []
                customers_affected = set()
                
                for _, row in df.iterrows():
                    record = {
                        'payment_id': int(row['payment_id']),
                        'nsf_date': row['nsf_date'].strftime('%Y-%m-%d') if pd.notna(row['nsf_date']) else None,
                        'amount': float(row['amount']),
                        'comment': row['comment'],
                        'customer_id': int(row['customer_id']) if pd.notna(row['customer_id']) else None,
                        'company': row['company'],
                        'customer_name': row['customer_name'],
                        'first_name': row['FirstName'],
                        'last_name': row['LastName'],
                        'account_balance': float(row['account_balance']) if pd.notna(row['account_balance']) else 0,
                        'phone_number': row['PhoneNumber'],
                        'nsf_type': row['nsf_type'],
                        'entry_type': row['entry_type'],
                        'days_old': int(row['days_old']) if pd.notna(row['days_old']) else 0
                    }
                    
                    if record['entry_type'] == 'FEE':
                        nsf_fees.append(record)
                    else:
                        nsf_data.append(record)
                    
                    customers_affected.add(record['customer_id'])
                
                # Calculate summary statistics
                total_check_amount = sum(item['amount'] for item in nsf_data)
                total_fee_amount = sum(item['amount'] for item in nsf_fees)
                
                # Group by customer for customer analysis
                customer_summary = {}
                for item in nsf_data + nsf_fees:
                    cid = item['customer_id']
                    if cid not in customer_summary:
                        customer_summary[cid] = {
                            'customer_name': item['customer_name'],
                            'account_balance': item['account_balance'],
                            'phone_number': item['phone_number'],
                            'returned_checks': 0,
                            'check_amount': 0,
                            'nsf_fees': 0,
                            'fee_amount': 0,
                            'last_nsf_date': None,
                            'days_since_last': 0
                        }
                    
                    if item['entry_type'] == 'FEE':
                        customer_summary[cid]['nsf_fees'] += 1
                        customer_summary[cid]['fee_amount'] += item['amount']
                    else:
                        customer_summary[cid]['returned_checks'] += 1
                        customer_summary[cid]['check_amount'] += item['amount']
                        
                    # Track most recent NSF date
                    if not customer_summary[cid]['last_nsf_date'] or item['nsf_date'] > customer_summary[cid]['last_nsf_date']:
                        customer_summary[cid]['last_nsf_date'] = item['nsf_date']
                        customer_summary[cid]['days_since_last'] = item['days_old']
                
                # Convert to list and calculate totals
                customer_analysis = []
                for cid, data in customer_summary.items():
                    data['customer_id'] = cid
                    data['total_impact'] = data['check_amount'] + data['fee_amount']
                    customer_analysis.append(data)
                
                # Sort by total impact descending
                customer_analysis.sort(key=lambda x: x['total_impact'], reverse=True)
                
                summary = {
                    'returned_check_count': len(nsf_data),
                    'returned_check_amount': total_check_amount,
                    'nsf_fee_count': len(nsf_fees),
                    'nsf_fee_amount': total_fee_amount,
                    'total_impact': total_check_amount + total_fee_amount,
                    'customers_affected': len(customers_affected),
                    'avg_days_old': sum(item['days_old'] for item in nsf_data + nsf_fees) / len(nsf_data + nsf_fees) if nsf_data + nsf_fees else 0
                }
                
                return jsonify({
                    'success': True,
                    'summary': summary,
                    'nsf_data': nsf_data,
                    'nsf_fees': nsf_fees,
                    'customer_analysis': customer_analysis,
                    'recent_activity': (nsf_data + nsf_fees)[:50]  # Last 50 for recent activity
                })
            
        except Exception as e:
            logger.error(f"Error getting NSF returns: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/ar/nsf-data')
    def get_nsf_data():
        """Get NSF and returned checks data"""
        try:
            from database_pymssql import SQLServerConnection
            
            days = int(request.args.get('days', 30))
            
            # Query for NSF/returned checks
            query = """
            SELECT 
                p.ID as payment_id,
                p.Time as payment_date,
                p.Amount as amount,
                p.Comment as comment,
                c.ID as customer_id,
                c.Company as company,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as customer_name,
                c.AccountBalance as account_balance,
                c.PhoneNumber as phone,
                -- Extract check number from Comment field if available
                CASE 
                    WHEN p.Comment LIKE '%[#]%' THEN 
                        SUBSTRING(p.Comment, CHARINDEX('#', p.Comment) + 1, 
                            CASE 
                                WHEN CHARINDEX(' ', p.Comment, CHARINDEX('#', p.Comment)) > 0 
                                THEN CHARINDEX(' ', p.Comment, CHARINDEX('#', p.Comment)) - CHARINDEX('#', p.Comment) - 1
                                ELSE LEN(p.Comment) - CHARINDEX('#', p.Comment)
                            END
                        )
                    WHEN p.Comment LIKE '%Check%[0-9]%' THEN 
                        SUBSTRING(p.Comment, PATINDEX('%[0-9]%', p.Comment), 
                            CASE 
                                WHEN PATINDEX('%[^0-9]%', SUBSTRING(p.Comment, PATINDEX('%[0-9]%', p.Comment), LEN(p.Comment))) > 0
                                THEN PATINDEX('%[^0-9]%', SUBSTRING(p.Comment, PATINDEX('%[0-9]%', p.Comment), LEN(p.Comment))) - 1
                                ELSE LEN(p.Comment)
                            END
                        )
                    ELSE 'N/A'
                END as check_number,
                CASE 
                    WHEN UPPER(p.Comment) LIKE '%NSF%' THEN 'NSF'
                    WHEN UPPER(p.Comment) LIKE '%RETURN%' THEN 'RETURNED'
                    WHEN UPPER(p.Comment) LIKE '%BOUNCE%' THEN 'BOUNCED'
                    WHEN UPPER(p.Comment) LIKE '%INSUFFICIENT%' THEN 'NSF'
                    WHEN UPPER(p.Comment) LIKE '%DISHONOR%' THEN 'DISHONORED'
                    ELSE 'NSF'
                END as nsf_type,
                -- Check if recovered (has payment after NSF from same customer)
                CASE WHEN EXISTS (
                    SELECT 1 FROM dbo.Payment p2 
                    WHERE p2.CustomerID = p.CustomerID 
                    AND p2.Time > p.Time 
                    AND p2.Amount >= p.Amount * 0.9
                    AND UPPER(p2.Comment) NOT LIKE '%NSF%'
                    AND UPPER(p2.Comment) NOT LIKE '%RETURN%'
                ) THEN 1 ELSE 0 END as is_recovered
            FROM dbo.Payment p
            INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
            WHERE (
                UPPER(p.Comment) LIKE '%NSF%'
                OR UPPER(p.Comment) LIKE '%RETURN%'
                OR UPPER(p.Comment) LIKE '%BOUNCE%'
                OR UPPER(p.Comment) LIKE '%INSUFFICIENT%'
                OR UPPER(p.Comment) LIKE '%DISHONOR%'
            )
            AND p.Time >= DATEADD(day, -%s, GETDATE())
            ORDER BY p.Time DESC
            """
            
            with SQLServerConnection() as db:
                df = db.execute_query(query, [days])
                
                nsf_list = []
                customer_counts = {}
                
                for _, row in df.iterrows():
                    customer_id = row['customer_id']
                    if customer_id not in customer_counts:
                        customer_counts[customer_id] = 0
                    customer_counts[customer_id] += 1
                    
                    nsf_list.append({
                        'payment_id': int(row['payment_id']),
                        'payment_date': row['payment_date'].strftime('%Y-%m-%d') if pd.notna(row['payment_date']) else None,
                        'amount': float(row['amount']),
                        'comment': row['comment'],
                        'customer_id': int(customer_id) if pd.notna(customer_id) else None,
                        'customer_name': row['customer_name'],
                        'company': row['company'],
                        'phone': row['phone'],
                        'account_balance': float(row['account_balance']) if pd.notna(row['account_balance']) else 0,
                        'check_number': row['check_number'],
                        'nsf_type': row['nsf_type'],
                        'is_recovered': bool(row['is_recovered']),
                        'is_repeat_offender': False  # Will update below
                    })
                
                # Mark repeat offenders
                for nsf in nsf_list:
                    if customer_counts.get(nsf['customer_id'], 0) > 1:
                        nsf['is_repeat_offender'] = True
                
                # Calculate summary statistics
                total_nsf = len(nsf_list)
                total_amount = sum(nsf['amount'] for nsf in nsf_list)
                unique_customers = len(customer_counts)
                repeat_offenders = sum(1 for count in customer_counts.values() if count > 1)
                recovered_count = sum(1 for nsf in nsf_list if nsf['is_recovered'])
                recovery_rate = (recovered_count / total_nsf * 100) if total_nsf > 0 else 0
                
                summary = {
                    'total_count': total_nsf,
                    'total_amount': total_amount,
                    'unique_customers': unique_customers,
                    'repeat_offenders': repeat_offenders,
                    'recovered_count': recovered_count,
                    'recovery_rate': recovery_rate,
                    'avg_nsf_amount': total_amount / total_nsf if total_nsf > 0 else 0
                }
                
                return jsonify({
                    'success': True,
                    'nsf_checks': nsf_list,
                    'summary': summary
                })
                
        except Exception as e:
            logger.error(f"Error getting NSF data: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/ar/pd-checks')
    def get_pd_checks():
        """Get post-dated checks data"""
        try:
            from database_pymssql import SQLServerConnection
            from datetime import date
            
            period = request.args.get('period', 'all')
            
            # Query for payments with PD check comments - include historical data
            query = """
            SELECT TOP 1000
                p.ID as payment_id,
                p.Time as payment_date,
                p.Amount as amount,
                p.Comment as comment,
                c.ID as customer_id,
                c.Company as company,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as customer_name,
                c.AccountBalance as account_balance,
                CASE 
                    WHEN UPPER(p.Comment) LIKE '%NSF%' THEN 'NSF'
                    WHEN UPPER(p.Comment) LIKE '%RETURN%' THEN 'RETURNED'
                    WHEN UPPER(p.Comment) LIKE '%BOUNCE%' THEN 'BOUNCED'
                    ELSE 'PD_CHECK'
                END as check_type
            FROM dbo.Payment p
            INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
            WHERE (
                UPPER(p.Comment) LIKE '%PD%'
                OR UPPER(p.Comment) LIKE '%POST DATE%'
                OR UPPER(p.Comment) LIKE '%P D%'
                OR UPPER(p.Comment) LIKE '%POSTDATE%'
                OR UPPER(p.Comment) LIKE '%NSF%'
                OR p.Comment LIKE '%/%/%'
                OR p.Comment LIKE '%-%-%'
            )
            AND p.Amount > 0
            ORDER BY p.Time DESC
            """
            
            with SQLServerConnection() as db:
                df = db.execute_query(query)
            
                pd_checks = []
                today = date.today()
                
                for _, row in df.iterrows():
                    # Parse the PD check information
                    pd_info = PDCheckParser.extract_pd_info(row['comment'])
                    
                    # Check if it's NSF/returned
                    check_type = row.get('check_type', 'PD_CHECK')
                    is_nsf = check_type in ['NSF', 'RETURNED', 'BOUNCED']
                    
                    if pd_info['is_pd_check'] or is_nsf:
                        check_data = {
                            'payment_id': int(row['payment_id']),
                            'payment_date': row['payment_date'].strftime('%Y-%m-%d') if pd.notna(row['payment_date']) else None,
                            'amount': float(row['amount']),
                            'comment': row['comment'],
                            'customer_id': int(row['customer_id']) if pd.notna(row['customer_id']) else None,
                            'company': row['company'],
                            'customer_name': row['customer_name'],
                            'account_balance': float(row['account_balance']) if pd.notna(row['account_balance']) else 0,
                            'deposit_date': pd_info['deposit_date'].isoformat() if pd_info['deposit_date'] else None,
                            'parsed_successfully': pd_info['parsed_successfully'],
                            'days_until_deposit': pd_info.get('days_until_deposit'),
                            'is_past_due': pd_info.get('is_past_due', False),
                            'is_due_soon': pd_info.get('is_due_soon', False),
                            'check_type': check_type,
                            'is_nsf': is_nsf
                        }
                        
                        # Filter based on period
                        # Only show past due checks from the last 7 days (likely still pending)
                        # Older past due checks are assumed to be already deposited
                        if period == 'week' and pd_info['deposit_date']:
                            if pd_info['days_until_deposit'] is not None and -7 <= pd_info['days_until_deposit'] <= 7:
                                pd_checks.append(check_data)
                        elif period == 'month' and pd_info['deposit_date']:
                            if pd_info['days_until_deposit'] is not None and -7 <= pd_info['days_until_deposit'] <= 30:
                                pd_checks.append(check_data)
                        elif period == 'past_due' and pd_info['deposit_date']:
                            # Only show recent past due (within last 7 days)
                            if pd_info.get('is_past_due') and pd_info['days_until_deposit'] >= -7:
                                pd_checks.append(check_data)
                        elif period == 'all':
                            # For 'all', show upcoming PD checks and recent past due only (exclude NSF)
                            if not is_nsf and pd_info['deposit_date'] and pd_info['days_until_deposit'] >= -7:
                                pd_checks.append(check_data)
                        elif period == 'history':
                            # Special period to see all historical data
                            pd_checks.append(check_data)
            
            # Categorize the checks
            categories = PDCheckParser.categorize_pd_checks(pd_checks)
            
            # Filter out NSF/returned checks completely from PD checks display
            regular_pd_checks = [c for c in pd_checks if not c.get('is_nsf', False)]
            
            # For table display: exclude past due checks (but keep them for calendar)
            table_pd_checks = [c for c in regular_pd_checks if not c.get('is_past_due', False)]
            
            # Track past due checks that might have been deposited
            historical_pd_checks = [c for c in regular_pd_checks if c.get('is_past_due', False)]
            
            # Calculate summary statistics
            summary = {
                'total_count': len(regular_pd_checks),
                'total_amount': sum(check['amount'] for check in regular_pd_checks),
                'past_due_count': len(categories['past_due']),
                'past_due_amount': sum(check['amount'] for check in categories['past_due']),
                'due_today_count': len(categories['due_today']),
                'due_today_amount': sum(check['amount'] for check in categories['due_today']),
                'due_this_week_count': len(categories['due_this_week']),
                'due_this_week_amount': sum(check['amount'] for check in categories['due_this_week']),
                'unparseable_count': len(categories['unparseable']),
                'historical_count': len(historical_pd_checks)
            }
            
            # Format for calendar if requested
            calendar_events = []
            if request.args.get('format') == 'calendar':
                calendar_events = PDCheckParser.format_for_calendar(pd_checks)
            
            return jsonify({
                'success': True,
                'checks': table_pd_checks[:100],  # Table: exclude past due checks
                'all_checks': pd_checks[:100],    # Calendar: include all checks
                'categories': {k: v[:20] for k, v in categories.items()},  # Limit each category
                'summary': summary,
                'calendar_events': calendar_events
            })
            
        except Exception as e:
            logger.error(f"Error getting PD checks: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return app