"""
Customer Ledger API endpoints for Flask integration
Uses the accurate ledger implementation with correct balance calculation
"""

from flask import Blueprint, jsonify, request, send_file, Response
from app.customer_ledger import AccurateCustomerLedger
import pandas as pd
import io
import logging
from datetime import datetime
import csv

logger = logging.getLogger(__name__)

# Create Blueprint
ledger_bp = Blueprint('ledger', __name__)

# Initialize ledger instance
ledger_instance = AccurateCustomerLedger()

@ledger_bp.route('/api/ledger/customers', methods=['GET'])
def get_customers():
    """Get list of customers with search capability"""
    try:
        search = request.args.get('search', '')
        
        customers_df = ledger_instance.get_customer_list(search)
        
        # Convert to list of dicts for JSON
        customers = []
        for _, row in customers_df.iterrows():
            customers.append({
                'id': int(row['ID']),
                'account_number': row.get('AccountNumber', ''),
                'name': row.get('CustomerName', ''),
                'balance': float(row.get('CurrentBalance', 0)),
                'phone': row.get('PhoneNumber', ''),
                'email': row.get('EmailAddress', ''),
                'company': row.get('Company', ''),
                'credit_limit': float(row.get('CreditLimit', 0)) if row.get('CreditLimit') else 0
            })
        
        return jsonify({
            'success': True,
            'customers': customers,
            'count': len(customers)
        })
    
    except Exception as e:
        logger.error(f"Error getting customers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ledger_bp.route('/api/ledger/generate/<int:customer_id>', methods=['GET'])
def generate_ledger(customer_id):
    """Generate accurate ledger for specific customer"""
    try:
        days_back = request.args.get('days', None, type=int)
        
        # Get the accurate ledger with correct balance calculation
        result = ledger_instance.get_complete_ledger(customer_id, days_back)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.error(f"Error generating ledger: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ledger_bp.route('/api/ledger/export/<int:customer_id>', methods=['GET'])
def export_ledger(customer_id):
    """Export ledger to CSV or Excel format"""
    try:
        days_back = request.args.get('days', None, type=int)
        format_type = request.args.get('format', 'csv').lower()
        
        result = ledger_instance.get_complete_ledger(customer_id, days_back)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        # Prepare DataFrame
        df = pd.DataFrame(result['ledger'])
        
        if df.empty:
            df = pd.DataFrame(columns=[
                'TransactionDate', 'TransactionType', 'Category', 'RefNumber', 
                'Description', 'Debit', 'Credit', 'Amount', 'RunningBalance'
            ])
        
        # Generate filename
        customer_name = result['customer_info']['CustomerName'].replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            # Create CSV with proper formatting
            output = io.StringIO()
            
            # Write header information
            output.write("CUSTOMER LEDGER REPORT\n")
            output.write(f"Generated: {result['metadata']['generated_at']}\n")
            output.write(f"Customer: {result['customer_info']['CustomerName']}\n")
            output.write(f"Account: {result['customer_info']['AccountNumber']}\n")
            output.write(f"Starting Balance: $0.00\n")
            output.write(f"Ending Balance: ${result['verification']['ending_balance']:,.2f}\n")
            output.write(f"Current AR Balance: ${result['verification']['current_ar_balance']:,.2f}\n")
            output.write(f"Records: {result['metadata']['record_count']}\n")
            output.write("\n")
            
            # Write summary
            output.write("SUMMARY\n")
            summary = result['summary']
            output.write(f"Total Invoiced: ${summary['total_invoiced']:,.2f}\n")
            output.write(f"Total Payments: ${summary['total_payments']:,.2f}\n")
            output.write(f"Total NSF Fees: ${summary['total_nsf_fees']:,.2f}\n")
            output.write(f"Total NSF Returns: ${summary.get('total_nsf_returns', 0):,.2f}\n")
            output.write(f"Total Collection Fees: ${summary['total_collection_fees']:,.2f}\n")
            output.write(f"Total Adjustments: ${summary['total_adjustments']:,.2f}\n")
            output.write(f"Total Debits: ${summary['total_debits']:,.2f}\n")
            output.write(f"Total Credits: ${summary['total_credits']:,.2f}\n")
            output.write("\n")
            
            # Write active AR if any
            if result['active_ar']:
                output.write("ACTIVE AR RECORDS\n")
                ar_df = pd.DataFrame(result['active_ar'])
                ar_df.to_csv(output, index=False)
                output.write("\n")
            
            # Write ledger data
            output.write("DETAILED LEDGER\n")
            # Select and order columns for export
            export_columns = ['TransactionDate', 'TransactionType', 'Category', 'RefNumber', 
                            'Description', 'Debit', 'Credit', 'RunningBalance']
            if all(col in df.columns for col in export_columns):
                df[export_columns].to_csv(output, index=False)
            else:
                df.to_csv(output, index=False)
            
            # Prepare response
            output.seek(0)
            response = Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=ledger_{customer_name}_{timestamp}.csv'
                }
            )
            return response
        
        elif format_type == 'excel':
            # Create Excel file with multiple sheets
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Get workbook and add formats
                workbook = writer.book
                currency_format = workbook.add_format({'num_format': '$#,##0.00'})
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
                
                # Customer info sheet
                info_data = {
                    'Field': ['Customer ID', 'Name', 'Account', 'Starting Balance', 
                              'Ending Balance', 'Current AR Balance', 'Balance Matches',
                              'Credit Limit', 'Phone', 'Email', 'Generated'],
                    'Value': [
                        result['customer_info']['ID'],
                        result['customer_info']['CustomerName'],
                        result['customer_info']['AccountNumber'],
                        '$0.00',
                        f"${result['verification']['ending_balance']:,.2f}",
                        f"${result['verification']['current_ar_balance']:,.2f}",
                        'Yes' if result['verification']['balance_matches'] else 'No',
                        f"${result['customer_info']['CreditLimit']:,.2f}" if result['customer_info']['CreditLimit'] else 'N/A',
                        result['customer_info']['PhoneNumber'] or 'N/A',
                        result['customer_info']['EmailAddress'] or 'N/A',
                        result['metadata']['generated_at']
                    ]
                }
                info_df = pd.DataFrame(info_data)
                info_df.to_excel(writer, sheet_name='Customer Info', index=False)
                
                # Summary sheet
                summary = result['summary']  # Ensure summary is defined
                summary_data = {
                    'Category': ['Total Invoiced', 'Total Payments', 'Total NSF Fees', 
                                'Total NSF Returns', 'Total Collection Fees', 'Total Adjustments',
                                'Total Debits', 'Total Credits', 'Starting Balance', 
                                'Ending Balance', 'Active AR Count', 'Active AR Total'],
                    'Amount': [
                        summary.get('total_invoiced', 0),
                        summary.get('total_payments', 0),
                        summary.get('total_nsf_fees', 0),
                        summary.get('total_nsf_returns', 0),
                        summary.get('total_collection_fees', 0),
                        summary.get('total_adjustments', 0),
                        summary.get('total_debits', 0),
                        summary.get('total_credits', 0),
                        0.00,
                        result['verification']['ending_balance'],
                        summary.get('active_ar_count', 0),
                        summary.get('active_ar_total', 0)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Detailed ledger
                if not df.empty:
                    # Select columns for export
                    export_columns = ['TransactionDate', 'TransactionType', 'Category', 'RefNumber', 
                                    'Description', 'Debit', 'Credit', 'RunningBalance']
                    if all(col in df.columns for col in export_columns):
                        ledger_export = df[export_columns].copy()
                    else:
                        ledger_export = df.copy()
                    
                    ledger_export.to_excel(writer, sheet_name='Ledger', index=False)
                
                # Active AR sheet
                if result['active_ar']:
                    ar_df = pd.DataFrame(result['active_ar'])
                    ar_df.to_excel(writer, sheet_name='Active AR', index=False)
                
                # Category breakdown
                if 'category_breakdown' in summary:
                    cat_rows = []
                    for category, data in summary['category_breakdown'].items():
                        cat_rows.append({
                            'Category': category,
                            'Count': data['count'],
                            'Debits': data['debits'],
                            'Credits': data['credits'],
                            'Net': data['net']
                        })
                    if cat_rows:
                        cat_df = pd.DataFrame(cat_rows)
                        cat_df.to_excel(writer, sheet_name='Category Analysis', index=False)
            
            # Prepare response
            output.seek(0)
            response = Response(
                output.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename=ledger_{customer_name}_{timestamp}.xlsx'
                }
            )
            return response
        
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported format: {format_type}'
            }), 400
    
    except Exception as e:
        logger.error(f"Error exporting ledger: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ledger_bp.route('/api/ledger/verify/<int:customer_id>', methods=['GET'])
def verify_balance(customer_id):
    """Verify customer balance calculation"""
    try:
        result = ledger_instance.get_complete_ledger(customer_id)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
        
        verification = result['verification']
        summary = result['summary']
        
        return jsonify({
            'success': True,
            'verification': {
                'customer_id': customer_id,
                'customer_name': result['customer_info']['CustomerName'],
                'starting_balance': verification['starting_balance'],
                'ending_balance': verification['ending_balance'],
                'current_ar_balance': verification['current_ar_balance'],
                'balance_matches': verification['balance_matches'],
                'transaction_count': summary['transaction_count'],
                'total_debits': summary['total_debits'],
                'total_credits': summary['total_credits']
            }
        })
    
    except Exception as e:
        logger.error(f"Error verifying balance: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_ledger_routes(app):
    """Register ledger routes with the Flask app"""
    app.register_blueprint(ledger_bp)