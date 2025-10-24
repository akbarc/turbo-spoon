#!/usr/bin/env python3
"""
Risk Analysis API Module
Provides endpoints for customer risk analysis and statistics
"""

from flask import Blueprint, jsonify, request
from modules.fast_risk_analysis import FastRiskAnalysis
from database_pymssql import SQLServerConnection
import pandas as pd
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
risk_analysis_api = Blueprint('risk_analysis_api', __name__)

# Initialize fast risk analysis
risk_analyzer = FastRiskAnalysis()

def json_converter(obj):
    """JSON serializer for objects not serializable by default"""
    import decimal
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    elif hasattr(obj, 'item'):  # numpy types
        return obj.item()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif pd.isna(obj):
        return None
    elif obj is None:
        return None
    elif isinstance(obj, (int, float, str, bool)):
        return obj
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@risk_analysis_api.route('/api/risk/overview', methods=['GET'])
def get_risk_overview():
    """Get fast risk analysis overview with actionable categories"""
    try:
        logger.info("Getting fast risk analysis overview")
        
        # Get parameters from query string
        days_no_payment = request.args.get('days_no_payment', 90, type=int)
        balance_multiplier = request.args.get('balance_multiplier', 2.0, type=float)
        
        # Get comprehensive risk overview
        overview = risk_analyzer.get_risk_overview(
            days_no_payment=days_no_payment, 
            balance_multiplier=balance_multiplier
        )
        
        if 'error' in overview:
            return jsonify({
                'success': False,
                'error': overview['error']
            }), 500
        
        from flask import Response
        import json
        
        return Response(
            json.dumps({
                'success': True,
                'data': overview
            }, default=json_converter),
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Error getting risk overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_analysis_api.route('/api/risk/batch-assessment', methods=['GET'])
def get_batch_risk_assessment():
    """Get risk assessment for multiple customers"""
    try:
        limit = request.args.get('limit', 50, type=int)
        risk_level = request.args.get('risk_level', None)
        
        logger.info(f"Getting batch risk assessment for {limit} customers")
        
        # Get high-value customers for assessment
        with SQLServerConnection() as db:
            query = """
            SELECT TOP {} ID, COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
                   AccountBalance, TotalSales, AccountNumber
            FROM dbo.Customer 
            WHERE AccountBalance > 1000 OR TotalSales > 10000
            ORDER BY AccountBalance DESC
            """.format(limit)
            
            customers_result = db.execute_query(query)
            
        if customers_result.empty:
            return jsonify({
                'success': True,
                'data': [],
                'summary': {'total_assessed': 0}
            })
        
        # Perform risk assessment
        assessments = []
        risk_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        
        for _, customer in customers_result.iterrows():
            try:
                assessment = risk_predictor.calculate_risk_score(customer['ID'])
                
                if 'risk_level' in assessment:
                    # Add customer info to assessment
                    assessment.update({
                        'account_number': customer['AccountNumber'],
                        'account_balance': float(customer['AccountBalance']),
                        'total_sales': float(customer['TotalSales']) if pd.notna(customer['TotalSales']) else 0
                    })
                    
                    # Count risk levels
                    risk_level_key = assessment['risk_level']
                    if risk_level_key in risk_counts:
                        risk_counts[risk_level_key] += 1
                    
                    # Filter by risk level if specified
                    if risk_level is None or assessment['risk_level'] == risk_level.upper():
                        assessments.append(assessment)
                        
            except Exception as e:
                logger.error(f"Error assessing customer {customer['ID']}: {e}")
                continue
        
        # Sort by risk score (highest first)
        assessments.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        
        summary = {
            'total_assessed': len(customers_result),
            'risk_distribution': risk_counts,
            'high_risk_percentage': round((risk_counts['HIGH'] + risk_counts['CRITICAL']) / max(len(customers_result), 1) * 100, 1)
        }
        
        return jsonify({
            'success': True,
            'data': assessments,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error in batch risk assessment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_analysis_api.route('/api/risk/customer/<int:customer_id>', methods=['GET'])
def get_customer_risk_assessment(customer_id):
    """Get fast risk assessment for a specific customer"""
    try:
        logger.info(f"Getting risk assessment for customer {customer_id}")
        
        assessment = risk_analyzer.get_customer_risk_summary(customer_id)
        
        return jsonify({
            'success': True,
            'data': assessment
        })
        
    except Exception as e:
        logger.error(f"Error getting customer risk assessment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_analysis_api.route('/api/risk/statistics', methods=['GET'])
def get_risk_statistics():
    """Get detailed risk analysis statistics"""
    try:
        logger.info("Getting detailed risk statistics")
        
        with SQLServerConnection() as db:
            # Days since last payment distribution
            payment_aging_query = """
            SELECT 
                CASE 
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 30 THEN '0-30 days'
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 60 THEN '31-60 days'
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 90 THEN '61-90 days'
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 180 THEN '91-180 days'
                    ELSE '180+ days'
                END as payment_age_bucket,
                COUNT(DISTINCT c.ID) as customer_count,
                SUM(c.AccountBalance) as total_balance
            FROM dbo.Customer c
            LEFT JOIN dbo.Payment p ON c.ID = p.CustomerID
            WHERE c.AccountBalance > 0
            GROUP BY 
                CASE 
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 30 THEN '0-30 days'
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 60 THEN '31-60 days'
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 90 THEN '61-90 days'
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 180 THEN '91-180 days'
                    ELSE '180+ days'
                END
            ORDER BY 
                CASE 
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 30 THEN 1
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 60 THEN 2
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 90 THEN 3
                    WHEN DATEDIFF(day, MAX(p.Time), GETDATE()) <= 180 THEN 4
                    ELSE 5
                END
            """
            
            aging_result = db.execute_query(payment_aging_query)
            payment_aging = aging_result.to_dict('records') if not aging_result.empty else []
            
            # Balance distribution
            balance_distribution_query = """
            SELECT 
                CASE 
                    WHEN AccountBalance <= 1000 THEN '$0 - $1K'
                    WHEN AccountBalance <= 5000 THEN '$1K - $5K'
                    WHEN AccountBalance <= 10000 THEN '$5K - $10K'
                    WHEN AccountBalance <= 25000 THEN '$10K - $25K'
                    WHEN AccountBalance <= 50000 THEN '$25K - $50K'
                    WHEN AccountBalance <= 100000 THEN '$50K - $100K'
                    ELSE '$100K+'
                END as balance_bucket,
                COUNT(*) as customer_count,
                SUM(AccountBalance) as total_balance
            FROM dbo.Customer
            WHERE AccountBalance > 0
            GROUP BY 
                CASE 
                    WHEN AccountBalance <= 1000 THEN '$0 - $1K'
                    WHEN AccountBalance <= 5000 THEN '$1K - $5K'
                    WHEN AccountBalance <= 10000 THEN '$5K - $10K'
                    WHEN AccountBalance <= 25000 THEN '$10K - $25K'
                    WHEN AccountBalance <= 50000 THEN '$25K - $50K'
                    WHEN AccountBalance <= 100000 THEN '$50K - $100K'
                    ELSE '$100K+'
                END
            ORDER BY SUM(AccountBalance) DESC
            """
            
            balance_result = db.execute_query(balance_distribution_query)
            balance_distribution = balance_result.to_dict('records') if not balance_result.empty else []
            
            # NSF trends over time
            nsf_trends_query = """
            SELECT 
                YEAR(Date) as year,
                MONTH(Date) as month,
                COUNT(*) as nsf_count,
                COUNT(DISTINCT CustomerID) as affected_customers,
                SUM(Amount) as total_amount
            FROM dbo.AccountReceivableHistory
            WHERE HistoryType IN ('NSF Fee', 'NSF Returned Check')
                AND Date >= DATEADD(month, -12, GETDATE())
            GROUP BY YEAR(Date), MONTH(Date)
            ORDER BY YEAR(Date), MONTH(Date)
            """
            
            nsf_result = db.execute_query(nsf_trends_query)
            nsf_trends = nsf_result.to_dict('records') if not nsf_result.empty else []
            
        statistics = {
            'payment_aging_distribution': payment_aging,
            'balance_distribution': balance_distribution,
            'nsf_trends': nsf_trends,
            'calculated_at': datetime.now().isoformat()
        }
        
        return json.dumps({
            'success': True,
            'data': statistics
        }, default=json_converter)
        
    except Exception as e:
        logger.error(f"Error getting risk statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@risk_analysis_api.route('/api/risk/recommendations', methods=['GET'])
def get_risk_recommendations():
    """Get actionable recommendations based on risk analysis"""
    try:
        logger.info("Getting risk-based recommendations")
        
        with SQLServerConnection() as db:
            # Find customers needing immediate attention
            critical_customers_query = """
            SELECT TOP 10
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                c.AccountNumber,
                c.AccountBalance,
                DATEDIFF(day, ISNULL(last_payment.LastPayment, c.LastVisit), GETDATE()) as days_since_payment
            FROM dbo.Customer c
            LEFT JOIN (
                SELECT CustomerID, MAX(Time) as LastPayment
                FROM dbo.Payment
                GROUP BY CustomerID
            ) last_payment ON c.ID = last_payment.CustomerID
            WHERE c.AccountBalance > 5000
            ORDER BY 
                CASE 
                    WHEN DATEDIFF(day, ISNULL(last_payment.LastPayment, c.LastVisit), GETDATE()) > 180 THEN 1
                    WHEN c.AccountBalance > 50000 THEN 2
                    ELSE 3
                END,
                c.AccountBalance DESC
            """
            
            critical_result = db.execute_query(critical_customers_query)
            critical_customers = critical_result.to_dict('records') if not critical_result.empty else []
            
            # Generate recommendations
            recommendations = []
            
            if critical_customers:
                recommendations.append({
                    'category': 'IMMEDIATE_ACTION',
                    'title': 'Customers Requiring Immediate Attention',
                    'priority': 'HIGH',
                    'description': f'{len(critical_customers)} customers with high balances need immediate contact',
                    'action_items': [
                        'Contact customers with 180+ days since payment',
                        'Review customers with $50K+ outstanding balances',
                        'Implement payment plans for high-risk accounts',
                        'Consider legal action for non-responsive accounts'
                    ],
                    'customers': critical_customers[:5]  # Show top 5
                })
            
            # NSF management recommendation
            recommendations.append({
                'category': 'NSF_MANAGEMENT',
                'title': 'NSF Risk Mitigation',
                'priority': 'MEDIUM',
                'description': 'Implement stricter payment methods for NSF-prone customers',
                'action_items': [
                    'Require certified payment methods for customers with 3+ NSF incidents',
                    'Implement NSF fees to discourage bad payment behavior',
                    'Set up automatic payment reminders',
                    'Consider cash-only terms for repeat offenders'
                ]
            })
            
            # Credit limit optimization
            recommendations.append({
                'category': 'CREDIT_OPTIMIZATION',
                'title': 'Credit Limit Optimization',
                'priority': 'MEDIUM',
                'description': 'Adjust credit limits based on payment behavior',
                'action_items': [
                    'Reduce credit limits for customers with poor payment history',
                    'Increase limits for reliable customers to grow business',
                    'Implement dynamic credit scoring',
                    'Regular credit limit reviews quarterly'
                ]
            })
            
        return jsonify({
            'success': True,
            'data': {
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
