"""
Customer Balance API Endpoints
Provides REST API for the validated customer balance calculation methodology
"""

from flask import Blueprint, jsonify, request
import logging
from decimal import Decimal
from datetime import datetime
from modules.customer_balance_engine import customer_balance_engine
import json

logger = logging.getLogger(__name__)

# Create Blueprint
customer_balance_api = Blueprint('customer_balance_api', __name__)

def json_converter(obj):
    """Convert non-serializable objects for JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):  # datetime/timestamp objects
        return obj.isoformat()
    elif hasattr(obj, 'item'):  # numpy types
        return obj.item()
    elif hasattr(obj, 'tolist'):  # numpy arrays
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@customer_balance_api.route('/api/customer/<int:customer_id>/balance', methods=['GET'])
def get_customer_balance(customer_id):
    """Get current customer balance (validated method)"""
    try:
        balance = customer_balance_engine.get_current_balance(customer_id)
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'current_balance': float(balance),
                'methodology': 'AR_HISTORY_SUM',
                'confidence': 'HIGH',
                'last_updated': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting customer balance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/comprehensive', methods=['GET'])
def get_comprehensive_balance(customer_id):
    """Get comprehensive balance analysis"""
    try:
        data = customer_balance_engine.get_customer_balance_comprehensive(customer_id)
        
        # Use json.dumps with custom converter for proper serialization
        import json
        json_data = json.dumps({
            'success': True,
            'data': data
        }, default=json_converter)
        
        from flask import Response
        return Response(json_data, content_type='application/json')
    except Exception as e:
        logger.error(f"Error getting comprehensive balance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/timeline', methods=['GET'])
def get_balance_timeline(customer_id):
    """Get complete balance timeline"""
    try:
        timeline = customer_balance_engine._get_balance_timeline(customer_id)
        
        # Optional date filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date or end_date:
            filtered_timeline = []
            for entry in timeline:
                entry_date = datetime.fromisoformat(entry['date']) if entry['date'] else None
                
                if entry_date:
                    include = True
                    if start_date:
                        start = datetime.fromisoformat(start_date)
                        include = include and entry_date >= start
                    if end_date:
                        end = datetime.fromisoformat(end_date)
                        include = include and entry_date <= end
                    
                    if include:
                        filtered_timeline.append(entry)
            
            timeline = filtered_timeline
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'timeline': timeline,
                'total_entries': len(timeline),
                'filters_applied': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
        })
    except Exception as e:
        logger.error(f"Error getting balance timeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/verification', methods=['GET'])
def verify_balance_accuracy(customer_id):
    """Verify balance accuracy using multiple methods"""
    try:
        verification = customer_balance_engine._verify_balance_accuracy(customer_id)
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'verification': verification,
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error verifying balance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/events', methods=['GET'])
def get_balance_events(customer_id):
    """Get decoded business events from AR History"""
    try:
        events = customer_balance_engine._decode_ar_history(customer_id)
        
        # Optional event type filtering
        event_type = request.args.get('event_type')
        if event_type:
            filtered_events = [
                event for event in events['events'] 
                if event['event_type'] == event_type.upper()
            ]
            events['events'] = filtered_events
            events['filtered_by'] = event_type
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'events': events,
                'available_event_types': [
                    'SALE_INVOICE',
                    'PAYMENT_RECEIVED', 
                    'ADJUSTMENT',
                    'NSF_RETURNED_CHECK',
                    'NSF_FEE',
                    'TRANSFER_NSF',
                    'OTHER_FEES'
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error getting balance events: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/patterns', methods=['GET'])
def get_balance_patterns(customer_id):
    """Get customer balance and payment patterns"""
    try:
        patterns = customer_balance_engine._analyze_patterns(customer_id)
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'patterns': patterns
            }
        })
    except Exception as e:
        logger.error(f"Error getting balance patterns: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/ar-breakdown', methods=['GET'])
def get_ar_breakdown(customer_id):
    """Get detailed AR breakdown with aging"""
    try:
        breakdown = customer_balance_engine._get_ar_breakdown(customer_id)
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'ar_breakdown': breakdown
            }
        })
    except Exception as e:
        logger.error(f"Error getting AR breakdown: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/balance/summary', methods=['GET'])
def get_balance_summary(customer_id):
    """Get balance summary statistics"""
    try:
        summary = customer_balance_engine._get_balance_summary(customer_id)
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'summary': summary
            }
        })
    except Exception as e:
        logger.error(f"Error getting balance summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customers/balances', methods=['GET'])
def get_multiple_customer_balances():
    """Get balances for multiple customers"""
    try:
        # Get customer IDs from query params
        customer_ids_str = request.args.get('customer_ids')
        if not customer_ids_str:
            return jsonify({
                'success': False,
                'error': 'customer_ids parameter required (comma-separated list)'
            }), 400
        
        try:
            customer_ids = [int(id.strip()) for id in customer_ids_str.split(',')]
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid customer_ids format. Use comma-separated integers.'
            }), 400
        
        if len(customer_ids) > 100:
            return jsonify({
                'success': False,
                'error': 'Maximum 100 customers per request'
            }), 400
        
        results = []
        for customer_id in customer_ids:
            try:
                balance = customer_balance_engine.get_current_balance(customer_id)
                results.append({
                    'customer_id': customer_id,
                    'balance': float(balance),
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'customer_id': customer_id,
                    'balance': None,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'data': {
                'customers': results,
                'total_requested': len(customer_ids),
                'successful': len([r for r in results if r['status'] == 'success']),
                'failed': len([r for r in results if r['status'] == 'error'])
            }
        })
    except Exception as e:
        logger.error(f"Error getting multiple balances: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/balance-methodology', methods=['GET'])
def get_balance_methodology():
    """Get information about the balance calculation methodology"""
    try:
        methodology = customer_balance_engine._get_methodology_info()
        
        return jsonify({
            'success': True,
            'data': methodology
        })
    except Exception as e:
        logger.error(f"Error getting methodology info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customers/balances/summary', methods=['GET'])
def get_all_balances_summary():
    """Get summary of all customer balances"""
    try:
        from database_pymssql import quick_query
        
        # Get overall statistics
        query = """
        WITH CustomerBalances AS (
            SELECT 
                ar.CustomerID,
                SUM(arh.Amount) as Balance
            FROM [dbo].[AccountReceivableHistory] arh
            JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
            GROUP BY ar.CustomerID
            HAVING SUM(arh.Amount) != 0
        )
        SELECT 
            COUNT(*) as TotalCustomersWithBalance,
            COUNT(CASE WHEN Balance > 0 THEN 1 END) as CustomersWithPositiveBalance,
            COUNT(CASE WHEN Balance < 0 THEN 1 END) as CustomersWithCreditBalance,
            SUM(CASE WHEN Balance > 0 THEN Balance ELSE 0 END) as TotalARBalance,
            SUM(CASE WHEN Balance < 0 THEN ABS(Balance) ELSE 0 END) as TotalCreditBalance,
            AVG(CASE WHEN Balance > 0 THEN Balance END) as AvgPositiveBalance,
            MAX(Balance) as HighestBalance,
            MIN(Balance) as LowestBalance
        FROM CustomerBalances
        """
        
        result = quick_query(query)
        
        if result.empty:
            summary = {
                'total_customers_with_balance': 0,
                'customers_with_positive_balance': 0,
                'customers_with_credit_balance': 0,
                'total_ar_balance': 0.0,
                'total_credit_balance': 0.0,
                'avg_positive_balance': 0.0,
                'highest_balance': 0.0,
                'lowest_balance': 0.0
            }
        else:
            data = result.iloc[0]
            summary = {
                'total_customers_with_balance': int(data['TotalCustomersWithBalance'] or 0),
                'customers_with_positive_balance': int(data['CustomersWithPositiveBalance'] or 0),
                'customers_with_credit_balance': int(data['CustomersWithCreditBalance'] or 0),
                'total_ar_balance': float(data['TotalARBalance'] or 0),
                'total_credit_balance': float(data['TotalCreditBalance'] or 0),
                'avg_positive_balance': float(data['AvgPositiveBalance'] or 0),
                'highest_balance': float(data['HighestBalance'] or 0),
                'lowest_balance': float(data['LowestBalance'] or 0)
            }
        
        return jsonify({
            'success': True,
            'data': {
                'summary': summary,
                'methodology': 'AR_HISTORY_SUM',
                'last_updated': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error getting balances summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer_balance_api.route('/api/customer/<int:customer_id>/overview', methods=['GET'])
def get_comprehensive_customer_overview(customer_id):
    """Get comprehensive customer overview with all details and metrics"""
    try:
        data = customer_balance_engine.get_comprehensive_customer_overview(customer_id)
        
        # Use json.dumps with custom converter for proper serialization
        import json
        json_data = json.dumps({
            'success': True,
            'data': data
        }, default=json_converter)
        
        from flask import Response
        return Response(json_data, content_type='application/json')
    except Exception as e:
        logger.error(f"Error getting comprehensive customer overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
