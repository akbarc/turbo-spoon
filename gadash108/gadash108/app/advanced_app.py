#!/usr/bin/env python3
"""
Advanced GA Dashboard - Enterprise Business Intelligence Platform
Comprehensive analytics with AI-powered insights and real-time monitoring
"""

import logging
import os
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, Response, send_file
from flask_cors import CORS
from database_pymssql import SQLServerConnection, DatabaseConnectionError
from advanced_analytics import AdvancedAnalytics
import io
import base64
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# Initialize global variables
analytics_engine = None
advanced_analytics = None

def initialize_analytics():
    """Initialize analytics engines"""
    global analytics_engine, advanced_analytics
    
    try:
        # Initialize database connection
        db = SQLServerConnection()
        if not db.connect():
            raise DatabaseConnectionError("Failed to connect to database")
        
        # Initialize advanced analytics
        advanced_analytics = AdvancedAnalytics(db)
        
        logger.info("✅ Advanced Analytics initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize analytics: {e}")
        return False

# Initialize on startup
if not initialize_analytics():
    logger.error("❌ Critical: Analytics initialization failed")

# =================
# ROUTE HANDLERS
# =================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('advanced_dashboard.html')

@app.route('/classic')
def classic_dashboard():
    """Classic dashboard for compatibility"""
    return render_template('unified_dashboard.html')

# =================
# HEALTH & STATUS
# =================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        db = SQLServerConnection()
        db_connected = db.connect()
        
        if db_connected:
            # Test with a simple query
            result = db.execute_query("SELECT 1 as test", description="Health Check")
            db.close()
            
            return jsonify({
                'status': 'healthy',
                'database_connected': True,
                'timestamp': datetime.now().isoformat(),
                'version': '2.0'
            })
        else:
            return jsonify({
                'status': 'degraded',
                'database_connected': False,
                'timestamp': datetime.now().isoformat(),
                'version': '2.0'
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database_connected': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'version': '2.0'
        }), 500

@app.route('/api/database/status')
def database_status():
    """Database connection status"""
    try:
        db = SQLServerConnection()
        connected = db.connect()
        
        if connected:
            test_result = db.execute_query(
                "SELECT @@SERVERNAME as server, DB_NAME() as database, GETDATE() as timestamp",
                description="Database Status"
            )
            db.close()
            
            return jsonify({
                'status': 'connected',
                'server_info': test_result.to_dict('records')[0] if not test_result.empty else {},
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# =================
# EXECUTIVE DASHBOARD
# =================

@app.route('/api/executive-dashboard')
def executive_dashboard():
    """Get comprehensive executive dashboard data"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        # Get parameters
        period = request.args.get('period', 'today')
        comparison = request.args.get('comparison', 'previous')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Get comprehensive dashboard data
        data = advanced_analytics.get_executive_dashboard_data(
            period=period,
            comparison=comparison,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Executive dashboard error: {e}")
        return jsonify({
            'error': 'Failed to load executive dashboard',
            'details': str(e)
        }), 500

@app.route('/api/kpi-details/<kpi_type>')
def kpi_details(kpi_type):
    """Get detailed KPI information"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        # Mock detailed KPI data - in production would fetch real detailed analytics
        kpi_data = {
            'revenue': {
                'title': 'Revenue Analysis',
                'current_value': 125000,
                'target': 150000,
                'progress': 83.3,
                'breakdown': [
                    {'category': 'Tobacco Products', 'value': 75000, 'percentage': 60},
                    {'category': 'Beverages', 'value': 25000, 'percentage': 20},
                    {'category': 'Snacks', 'value': 15000, 'percentage': 12},
                    {'category': 'Other', 'value': 10000, 'percentage': 8}
                ],
                'trends': {
                    'daily': [1200, 1350, 1100, 1450, 1600, 1400, 1550],
                    'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                }
            },
            'profit': {
                'title': 'Profit Margin Analysis',
                'current_value': 28.5,
                'target': 30.0,
                'progress': 95.0,
                'breakdown': [
                    {'category': 'High Margin Items', 'value': 35.2, 'percentage': 45},
                    {'category': 'Medium Margin Items', 'value': 25.8, 'percentage': 35},
                    {'category': 'Low Margin Items', 'value': 15.3, 'percentage': 20}
                ]
            }
        }
        
        if kpi_type in kpi_data:
            return jsonify(kpi_data[kpi_type])
        else:
            return jsonify({'error': 'KPI type not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# REAL-TIME MONITORING
# =================

@app.route('/api/realtime-data')
def realtime_data():
    """Get real-time dashboard data"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        data = advanced_analytics.get_realtime_data()
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Real-time data error: {e}")
        return jsonify({
            'error': 'Failed to load real-time data',
            'details': str(e)
        }), 500

# =================
# SALES INTELLIGENCE
# =================

@app.route('/api/sales-intelligence')
def sales_intelligence():
    """Get AI-powered sales intelligence"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        period = request.args.get('period', '30d')
        data = advanced_analytics.get_sales_intelligence(period)
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Sales intelligence error: {e}")
        return jsonify({
            'error': 'Failed to load sales intelligence',
            'details': str(e)
        }), 500

@app.route('/api/predictive-analytics')
def predictive_analytics():
    """Get predictive analytics and forecasts"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        # Mock predictive data - in production would use ML models
        predictions = {
            'sales_forecast': {
                'next_30_days': {
                    'predicted_revenue': 450000,
                    'confidence_interval': {'lower': 420000, 'upper': 480000},
                    'confidence_level': 85,
                    'key_drivers': [
                        'Seasonal trend (+12%)',
                        'New product launches (+8%)',
                        'Market conditions (-3%)'
                    ]
                },
                'daily_predictions': [
                    {'date': '2025-01-01', 'predicted': 15200, 'lower': 14100, 'upper': 16300},
                    {'date': '2025-01-02', 'predicted': 15450, 'lower': 14350, 'upper': 16550},
                    # ... more daily predictions
                ]
            },
            'inventory_recommendations': [
                {
                    'item': 'Premium Cigars',
                    'current_stock': 120,
                    'predicted_demand': 180,
                    'recommendation': 'Increase stock by 60 units',
                    'confidence': 0.92
                }
            ],
            'customer_insights': {
                'churn_risk': {
                    'high_risk_customers': 15,
                    'total_value_at_risk': 125000,
                    'top_factors': ['Reduced frequency', 'Seasonal patterns', 'Competitive pressure']
                }
            }
        }
        
        return jsonify(predictions)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# CUSTOMER ANALYTICS
# =================

@app.route('/api/customer-analytics')
def customer_analytics():
    """Get comprehensive customer analytics"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        data = advanced_analytics.get_customer_analytics()
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Customer analytics error: {e}")
        return jsonify({
            'error': 'Failed to load customer analytics',
            'details': str(e)
        }), 500

@app.route('/api/customer-segmentation')
def customer_segmentation():
    """Get customer segmentation analysis"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        # Get RFM analysis and segmentation
        rfm_data = advanced_analytics._perform_rfm_analysis()
        segments = advanced_analytics._segment_customers(rfm_data)
        
        return jsonify({
            'segments': segments,
            'customers': rfm_data[:100],  # Return top 100 for performance
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# INVENTORY OPTIMIZATION
# =================

@app.route('/api/inventory-optimization')
def inventory_optimization():
    """Get inventory optimization insights"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        data = advanced_analytics.get_inventory_optimization()
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Inventory optimization error: {e}")
        return jsonify({
            'error': 'Failed to load inventory optimization',
            'details': str(e)
        }), 500

# =================
# FINANCIAL INSIGHTS
# =================

@app.route('/api/financial-insights')
def financial_insights():
    """Get comprehensive financial insights"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        # Mock financial insights - in production would calculate from real data
        insights = {
            'cash_flow': {
                'current_month': 125000,
                'projected_next_month': 135000,
                'trend': 'positive',
                'key_factors': ['Increased sales', 'Improved collections', 'Seasonal uptick']
            },
            'profitability': {
                'gross_margin': 32.5,
                'net_margin': 18.7,
                'margin_trend': 'improving',
                'top_profit_drivers': [
                    {'category': 'Premium Tobacco', 'contribution': 45.2},
                    {'category': 'Beverages', 'contribution': 23.8},
                    {'category': 'Accessories', 'contribution': 18.5}
                ]
            },
            'working_capital': {
                'current_ratio': 2.3,
                'inventory_turnover': 4.5,
                'ar_turnover': 12.8,
                'days_sales_outstanding': 28.5
            },
            'cost_analysis': {
                'total_cogs': 425000,
                'cost_trends': {
                    'tobacco_tax_impact': 23500,
                    'supplier_cost_changes': -8200,
                    'operational_efficiency': 15600
                }
            }
        }
        
        return jsonify(insights)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# ALERTS & NOTIFICATIONS
# =================

@app.route('/api/alerts')
def get_alerts():
    """Get system alerts and notifications"""
    try:
        if not advanced_analytics:
            return jsonify({'error': 'Analytics engine not initialized'}), 500
        
        # Mock alerts - in production would check real thresholds
        alerts = [
            {
                'id': 'stock_001',
                'title': '23 Items Low on Stock',
                'message': 'Multiple items require immediate reordering',
                'severity': 'critical',
                'timestamp': datetime.now().isoformat(),
                'category': 'inventory',
                'action_required': True
            },
            {
                'id': 'ar_002',
                'title': 'High AR Balance Alert',
                'message': 'Accounts receivable has increased 15% this month',
                'severity': 'warning',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                'category': 'finance',
                'action_required': False
            },
            {
                'id': 'performance_003',
                'title': 'Daily Sales Target Achieved',
                'message': 'Today\'s sales exceeded target by 12%',
                'severity': 'info',
                'timestamp': (datetime.now() - timedelta(hours=4)).isoformat(),
                'category': 'sales',
                'action_required': False
            }
        ]
        
        # Filter by severity if requested
        severity_filter = request.args.get('severity')
        if severity_filter:
            alerts = [a for a in alerts if a['severity'] == severity_filter]
        
        return jsonify({
            'alerts': alerts,
            'total_count': len(alerts),
            'critical_count': len([a for a in alerts if a['severity'] == 'critical']),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<alert_id>/dismiss', methods=['POST'])
def dismiss_alert(alert_id):
    """Dismiss a specific alert"""
    try:
        # In production, would update alert status in database
        return jsonify({
            'success': True,
            'message': f'Alert {alert_id} dismissed',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# EXPORT & REPORTING
# =================

@app.route('/api/export-dashboard')
def export_dashboard():
    """Export dashboard data in various formats"""
    try:
        export_format = request.args.get('format', 'json')
        view = request.args.get('view', 'executive')
        
        if export_format == 'json':
            # Get dashboard data
            if view == 'executive' and advanced_analytics:
                data = advanced_analytics.get_executive_dashboard_data()
                
                # Add export metadata
                export_data = {
                    'export_info': {
                        'exported_at': datetime.now().isoformat(),
                        'view': view,
                        'format': export_format,
                        'version': '2.0'
                    },
                    'data': data
                }
                
                return jsonify(export_data)
            
        elif export_format == 'csv':
            # Mock CSV export
            output = io.StringIO()
            output.write('Date,Revenue,Profit,Transactions,Customers\n')
            output.write(f'{datetime.now().date()},125000,35000,450,87\n')
            
            response = Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=dashboard_export_{datetime.now().strftime("%Y%m%d")}.csv'}
            )
            return response
            
        elif export_format == 'pdf':
            # Mock PDF export
            return jsonify({
                'message': 'PDF export functionality coming soon',
                'format': 'pdf',
                'status': 'not_implemented'
            }), 501
            
        else:
            return jsonify({'error': 'Unsupported export format'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# PERFORMANCE METRICS
# =================

@app.route('/api/performance-metrics')
def performance_metrics():
    """Get system performance metrics"""
    try:
        # Mock performance data
        metrics = {
            'api_performance': {
                'avg_response_time': 185,  # ms
                'total_requests': 1247,
                'error_rate': 0.02,  # 2%
                'cache_hit_rate': 0.78  # 78%
            },
            'database_performance': {
                'connection_pool_usage': 0.65,
                'query_avg_time': 95,  # ms
                'active_connections': 3,
                'max_connections': 10
            },
            'system_resources': {
                'cpu_usage': 35.2,  # %
                'memory_usage': 62.8,  # %
                'disk_usage': 78.5  # %
            },
            'business_metrics': {
                'data_freshness': 'real-time',
                'last_calculation': datetime.now().isoformat(),
                'total_records_processed': 4670963
            }
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# SEARCH & FILTERING
# =================

@app.route('/api/search')
def global_search():
    """Global search across all data"""
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Mock search results
        results = {
            'customers': [
                {
                    'id': 'cust_001',
                    'name': 'ABC Convenience Store',
                    'type': 'customer',
                    'score': 0.95,
                    'summary': 'High-value customer with $45K annual sales'
                }
            ],
            'products': [
                {
                    'id': 'prod_001', 
                    'name': 'Premium Cigars - Cuban Blend',
                    'type': 'product',
                    'score': 0.88,
                    'summary': 'Top-selling cigar with 32% margin'
                }
            ],
            'transactions': [
                {
                    'id': 'trans_001',
                    'number': 'TXN-2025-001234',
                    'type': 'transaction',
                    'score': 0.82,
                    'summary': 'Large transaction on 2025-01-15 - $2,450'
                }
            ]
        }
        
        # Filter by type if specified
        if search_type != 'all' and search_type in results:
            filtered_results = {search_type: results[search_type]}
        else:
            filtered_results = results
        
        return jsonify({
            'query': query,
            'results': filtered_results,
            'total_results': sum(len(v) for v in filtered_results.values()),
            'search_time': 45  # ms
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# SETTINGS & CONFIGURATION
# =================

@app.route('/api/settings')
def get_settings():
    """Get dashboard settings"""
    try:
        settings = {
            'dashboard': {
                'refresh_interval': 300,  # seconds
                'auto_refresh_enabled': True,
                'theme': 'professional',
                'density': 'comfortable'
            },
            'alerts': {
                'low_stock_threshold': 5,
                'high_ar_threshold': 50000,
                'margin_warning_threshold': 20.0,
                'email_notifications': True
            },
            'display': {
                'currency': 'USD',
                'number_format': 'US',
                'date_format': 'MM/DD/YYYY',
                'timezone': 'America/New_York'
            },
            'features': {
                'predictive_analytics': True,
                'real_time_monitoring': True,
                'advanced_exports': True,
                'ai_insights': True
            }
        }
        
        return jsonify(settings)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update dashboard settings"""
    try:
        settings = request.json
        
        # In production, would validate and save settings
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# BACKWARD COMPATIBILITY
# =================

# Keep existing API endpoints for backward compatibility
@app.route('/api/overview/complete')
def overview_complete():
    """Legacy overview endpoint"""
    try:
        if advanced_analytics:
            data = advanced_analytics.get_executive_dashboard_data()
            return jsonify(data)
        else:
            return jsonify({'error': 'Service unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales-analytics/complete')
def sales_analytics_complete():
    """Legacy sales analytics endpoint"""
    try:
        return jsonify({
            'overview': {'total_sales': 125000, 'unique_customers': 87},
            'daily_trend': {'trend_data': []},
            'segments': []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =================
# ERROR HANDLERS
# =================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(DatabaseConnectionError)
def database_error(error):
    return jsonify({
        'error': 'Database connection failed',
        'details': str(error),
        'timestamp': datetime.now().isoformat()
    }), 503

# =================
# STARTUP & MAIN
# =================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Starting GA Analytics Pro Advanced Dashboard on port {port}")
    logger.info(f"🐛 Debug mode: {debug}")
    
    if advanced_analytics:
        logger.info("✅ Advanced analytics engine ready")
    else:
        logger.warning("⚠️ Advanced analytics engine not available - some features will be limited")
    
    app.run(host='0.0.0.0', port=port, debug=debug)