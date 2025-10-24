"""
Customer Analytics API Endpoints
Provides REST API for customer analytics module
Updated with validated balance calculation methodology
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
import pandas as pd
from modules.customer_analytics import CustomerAnalytics, get_customer_risk_scores
from modules.customer_balance_engine import customer_balance_engine

logger = logging.getLogger(__name__)

# Create Blueprint
customer_api = Blueprint('customer_api', __name__)

# Initialize analytics engine
analytics = CustomerAnalytics()

@customer_api.route('/api/customer/<int:customer_id>/360-view', methods=['GET'])
def get_customer_360_view(customer_id):
    """Get comprehensive 360-degree view of customer"""
    try:
        data = analytics.get_customer_360_view(customer_id)
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logger.error(f"Error getting customer 360 view: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/summary', methods=['GET'])
def get_customer_summary(customer_id):
    """Get customer summary for quick display"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        
        # Get validated balance
        try:
            validated_balance = float(customer_balance_engine.get_current_balance(customer_id))
        except:
            validated_balance = full_data.get('receivables', {}).get('aging_summary', {}).get('total_ar', 0)
        
        # Extract key summary metrics
        summary = {
            'customer_info': full_data.get('customer', {}),
            'ar_balance': validated_balance,  # UPDATED: Use validated balance
            'ar_balance_source': 'VALIDATED_AR_HISTORY',  # NEW: Indicate source
            'payment_behavior': full_data.get('payments', {}).get('behavior_classification', 'Unknown'),
            'risk_score': full_data.get('risk', {}).get('risk_assessment', {}).get('risk_score', 0),
            'risk_level': full_data.get('risk', {}).get('risk_assessment', {}).get('risk_level', 'Unknown'),
            'avg_days_to_pay': full_data.get('payments', {}).get('summary', {}).get('avg_days_to_pay', 0),
            'nsf_count': full_data.get('payments', {}).get('summary', {}).get('nsf_count', 0),
            'last_payment': full_data.get('payments', {}).get('summary', {}).get('last_payment_date'),
            'recent_sales': full_data.get('sales', {}).get('overview', {}).get('quarterly_growth_rate', 0),
            'recommendations': full_data.get('recommendations', [])[:3]  # Top 3 recommendations
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error getting customer summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/sales', methods=['GET'])
def get_customer_sales(customer_id):
    """Get customer sales analytics"""
    try:
        period = request.args.get('period', '12')  # months
        
        full_data = analytics.get_customer_360_view(customer_id)
        sales_data = full_data.get('sales', {})
        
        return jsonify({
            'success': True,
            'data': sales_data
        })
    except Exception as e:
        logger.error(f"Error getting customer sales: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/payments', methods=['GET'])
def get_customer_payments(customer_id):
    """Get customer payment analytics"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        payment_data = full_data.get('payments', {})
        
        return jsonify({
            'success': True,
            'data': payment_data
        })
    except Exception as e:
        logger.error(f"Error getting customer payments: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/receivables', methods=['GET'])
def get_customer_receivables(customer_id):
    """Get customer receivables analytics with aging"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        receivables_data = full_data.get('receivables', {})
        
        return jsonify({
            'success': True,
            'data': receivables_data
        })
    except Exception as e:
        logger.error(f"Error getting customer receivables: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/patterns', methods=['GET'])
def get_customer_patterns(customer_id):
    """Get customer behavioral patterns"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        patterns_data = full_data.get('patterns', {})
        
        return jsonify({
            'success': True,
            'data': patterns_data
        })
    except Exception as e:
        logger.error(f"Error getting customer patterns: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/risk', methods=['GET'])
def get_customer_risk(customer_id):
    """Get customer risk assessment"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        risk_data = full_data.get('risk', {})
        
        return jsonify({
            'success': True,
            'data': risk_data
        })
    except Exception as e:
        logger.error(f"Error getting customer risk: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/predictions', methods=['GET'])
def get_customer_predictions(customer_id):
    """Get predictive analytics for customer"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        predictions = full_data.get('predictions', {})
        
        return jsonify({
            'success': True,
            'data': predictions
        })
    except Exception as e:
        logger.error(f"Error getting customer predictions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customer/<int:customer_id>/recommendations', methods=['GET'])
def get_customer_recommendations(customer_id):
    """Get actionable recommendations for customer"""
    try:
        full_data = analytics.get_customer_360_view(customer_id)
        recommendations = full_data.get('recommendations', [])
        
        return jsonify({
            'success': True,
            'data': recommendations
        })
    except Exception as e:
        logger.error(f"Error getting customer recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customers/risk-matrix', methods=['GET'])
def get_risk_matrix():
    """Get risk matrix for all customers with AR balance"""
    try:
        # Get optional filters
        min_balance = request.args.get('min_balance', type=float, default=0)
        risk_level = request.args.get('risk_level')
        
        # Get all customers with metrics
        df = analytics.get_bulk_customer_metrics()
        
        # Apply filters
        if min_balance > 0:
            df = df[df['ar_balance'] >= min_balance]
        
        # Categorize risk levels
        df['risk_level'] = pd.cut(
            df['risk_score'], 
            bins=[-1, 25, 50, 75, 101],
            labels=['Low', 'Medium', 'High', 'Critical']
        )
        
        if risk_level:
            df = df[df['risk_level'] == risk_level]
        
        # Convert to dict for JSON
        result = {
            'total_customers': len(df),
            'total_ar': float(df['ar_balance'].sum()),
            'avg_risk_score': float(df['risk_score'].mean()),
            'risk_distribution': df['risk_level'].value_counts().to_dict(),
            'customers': df.to_dict('records')
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting risk matrix: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customers/payment-performance', methods=['GET'])
def get_payment_performance():
    """Get payment performance metrics across all customers"""
    try:
        # Get period filter
        days = request.args.get('days', type=int, default=90)
        
        with analytics.db:
            query = """
            WITH PaymentPerformance AS (
                SELECT 
                    c.ID,
                    c.Company,
                    c.AccountBalance,
                    -- Payment metrics
                    (SELECT AVG(DATEDIFF(day, ar.Date, p.Time))
                     FROM dbo.Payment p
                     JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                     WHERE p.CustomerID = c.ID 
                     AND p.Time >= DATEADD(day, -%s, GETDATE())) as avg_days_to_pay,
                    (SELECT COUNT(*) 
                     FROM dbo.Payment 
                     WHERE CustomerID = c.ID 
                     AND Time >= DATEADD(day, -%s, GETDATE())) as payment_count,
                    (SELECT SUM(Amount) 
                     FROM dbo.Payment 
                     WHERE CustomerID = c.ID 
                     AND Time >= DATEADD(day, -%s, GETDATE())) as total_paid,
                    (SELECT COUNT(*) 
                     FROM dbo.Payment 
                     WHERE CustomerID = c.ID 
                     AND (Comment LIKE '%%NSF%%' OR Comment LIKE '%%RETURN%%')
                     AND Time >= DATEADD(day, -%s, GETDATE())) as nsf_count
                FROM dbo.Customer c
                WHERE c.AccountBalance > 0
            )
            SELECT 
                ID as customer_id,
                Company as company,
                AccountBalance as ar_balance,
                avg_days_to_pay,
                payment_count,
                total_paid,
                nsf_count,
                CASE 
                    WHEN avg_days_to_pay IS NULL THEN 'No Payments'
                    WHEN avg_days_to_pay <= 30 THEN 'Excellent'
                    WHEN avg_days_to_pay <= 45 THEN 'Good'
                    WHEN avg_days_to_pay <= 60 THEN 'Fair'
                    WHEN avg_days_to_pay <= 90 THEN 'Poor'
                    ELSE 'Critical'
                END as payment_rating
            FROM PaymentPerformance
            ORDER BY avg_days_to_pay DESC
            """
            
            df = analytics.db.execute_query(query, [days] * 4)
            
            # Calculate summary statistics
            summary = {
                'total_customers': len(df),
                'total_ar': float(df['ar_balance'].sum()),
                'avg_days_to_pay': float(df['avg_days_to_pay'].mean()) if not df['avg_days_to_pay'].isna().all() else 0,
                'total_payments': float(df['total_paid'].sum()) if not df['total_paid'].isna().all() else 0,
                'total_nsf': int(df['nsf_count'].sum()) if not df['nsf_count'].isna().all() else 0,
                'payment_ratings': df['payment_rating'].value_counts().to_dict()
            }
            
            return jsonify({
                'success': True,
                'data': {
                    'summary': summary,
                    'customers': df.to_dict('records')
                }
            })
    except Exception as e:
        logger.error(f"Error getting payment performance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customers/collection-forecast', methods=['GET'])
def get_collection_forecast():
    """Get collection forecast for all outstanding AR"""
    try:
        # Get forecast period
        days = request.args.get('days', type=int, default=90)
        
        with analytics.db:
            # Get AR aging and apply collection probabilities
            query = """
            WITH ARForecast AS (
                SELECT 
                    CustomerID,
                    SUM(Balance) as total_ar,
                    -- Apply collection probabilities based on age
                    SUM(CASE 
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 30 
                        THEN Balance * 0.95
                        ELSE 0 
                    END) as collectible_30_days,
                    SUM(CASE 
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 30 
                        THEN Balance * 0.95
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 60 
                        THEN Balance * 0.85
                        ELSE 0 
                    END) as collectible_60_days,
                    SUM(CASE 
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 30 
                        THEN Balance * 0.95
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 60 
                        THEN Balance * 0.85
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 90 
                        THEN Balance * 0.70
                        WHEN DATEDIFF(day, Date, GETDATE()) <= 120 
                        THEN Balance * 0.50
                        ELSE Balance * 0.20
                    END) as collectible_90_days
                FROM dbo.AccountReceivable
                WHERE Balance > 0
                GROUP BY CustomerID
            )
            SELECT 
                COUNT(DISTINCT CustomerID) as customer_count,
                SUM(total_ar) as total_outstanding,
                SUM(collectible_30_days) as forecast_30_days,
                SUM(collectible_60_days) as forecast_60_days,
                SUM(collectible_90_days) as forecast_90_days
            FROM ARForecast
            """
            
            result = analytics.db.execute_query(query)
            
            if not result.empty:
                data = result.iloc[0]
                
                forecast = {
                    'total_outstanding': float(data['total_outstanding'] or 0),
                    'customer_count': int(data['customer_count'] or 0),
                    'forecast': {
                        '30_days': {
                            'amount': float(data['forecast_30_days'] or 0),
                            'percentage': float(data['forecast_30_days'] / data['total_outstanding'] * 100) if data['total_outstanding'] > 0 else 0
                        },
                        '60_days': {
                            'amount': float(data['forecast_60_days'] or 0),
                            'percentage': float(data['forecast_60_days'] / data['total_outstanding'] * 100) if data['total_outstanding'] > 0 else 0
                        },
                        '90_days': {
                            'amount': float(data['forecast_90_days'] or 0),
                            'percentage': float(data['forecast_90_days'] / data['total_outstanding'] * 100) if data['total_outstanding'] > 0 else 0
                        }
                    },
                    'at_risk_amount': float(data['total_outstanding'] - data['forecast_90_days']) if data['total_outstanding'] and data['forecast_90_days'] else 0
                }
                
                return jsonify({
                    'success': True,
                    'data': forecast
                })
            
            return jsonify({
                'success': True,
                'data': {}
            })
    except Exception as e:
        logger.error(f"Error getting collection forecast: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_api.route('/api/customers/top-risks', methods=['GET'])
def get_top_risk_customers():
    """Get top risk customers requiring attention"""
    try:
        limit = request.args.get('limit', type=int, default=10)
        
        # Get risk scores for all customers
        df = analytics.get_bulk_customer_metrics()
        
        # Filter to customers with AR balance
        df = df[df['ar_balance'] > 0]
        
        # Sort by risk score
        df = df.nlargest(limit, 'risk_score')
        
        # Add risk reasons
        for idx, row in df.iterrows():
            reasons = []
            if row['nsf_count'] > 0:
                reasons.append(f"{int(row['nsf_count'])} NSF/returned checks")
            if row['ar_over_90'] and row['ar_over_90'] > 0:
                reasons.append(f"${row['ar_over_90']:,.0f} over 90 days")
            if row['avg_days_to_pay'] and row['avg_days_to_pay'] > 60:
                reasons.append(f"Avg {row['avg_days_to_pay']:.0f} days to pay")
            if row['days_since_last_visit'] and row['days_since_last_visit'] > 90:
                reasons.append(f"No activity for {row['days_since_last_visit']} days")
            
            df.at[idx, 'risk_reasons'] = reasons
        
        return jsonify({
            'success': True,
            'data': df.to_dict('records')
        })
    except Exception as e:
        logger.error(f"Error getting top risk customers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500