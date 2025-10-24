"""
Transaction Detail API
Provides detailed invoice/transaction information for the customer ledger
"""

from flask import Blueprint, jsonify, request
import logging
import pandas as pd
from datetime import datetime
from database_pymssql import quick_query

logger = logging.getLogger(__name__)

# Create Blueprint
transaction_detail_api = Blueprint('transaction_detail_api', __name__)

@transaction_detail_api.route('/api/transaction/<transaction_number>/details', methods=['GET'])
def get_transaction_details(transaction_number):
    """Get detailed transaction/invoice information"""
    try:
        # Get transaction header information
        transaction_query = """
        SELECT 
            t.TransactionNumber,
            t.Time,
            t.BatchNumber,
            t.CustomerID,
            t.Total,
            t.SalesTax,
            t.Comment,
            t.CashierID,
            t.StoreID,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.PhoneNumber,
            c.Address,
            c.City,
            c.State,
            c.Zip
        FROM [dbo].[Transaction] t
        LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
        WHERE t.TransactionNumber = %s
        """
        
        transaction_result = quick_query(transaction_query, (transaction_number,))
        
        if transaction_result.empty:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        transaction_info = transaction_result.iloc[0].to_dict()
        
        # Get transaction line items
        line_items_query = """
        SELECT 
            te.ID as LineID,
            te.ItemID,
            i.ItemLookupCode,
            i.Description,
            te.Quantity,
            te.Price,
            (te.Quantity * te.Price) as LineTotal,
            i.Cost,
            ((te.Quantity * te.Price) - (te.Quantity * ISNULL(i.Cost, 0))) as LineProfit,
            d.Name as Department,
            cat.Name as Category
        FROM dbo.TransactionEntry te
        INNER JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Department d ON i.DepartmentID = d.ID
        LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
        WHERE te.TransactionNumber = %s
        ORDER BY te.ID
        """
        
        line_items_result = quick_query(line_items_query, (transaction_number,))
        
        # Get tender/payment information (simplified to avoid schema issues)
        tender_query = """
        SELECT 
            te.TenderID,
            te.Amount,
            te.Description
        FROM dbo.TenderEntry te
        WHERE te.TransactionNumber = %s
        """
        
        tender_result = quick_query(tender_query, (transaction_number,))
        
        # Skip tax details for now to avoid schema issues
        tax_result = None
        
        # Format response
        response = {
            'success': True,
            'data': {
                'transaction_info': {
                    'transaction_number': int(transaction_info['TransactionNumber']),
                    'date_time': transaction_info['Time'].isoformat() if pd.notna(transaction_info['Time']) else None,
                    'batch_number': int(transaction_info['BatchNumber']) if pd.notna(transaction_info['BatchNumber']) else None,
                    'customer_id': int(transaction_info['CustomerID']) if pd.notna(transaction_info['CustomerID']) else None,
                    'customer_name': transaction_info['CustomerName'] or 'Walk-in',
                    'customer_phone': transaction_info['PhoneNumber'] or '',
                    'customer_address': transaction_info['Address'] or '',
                    'customer_city': transaction_info['City'] or '',
                    'customer_state': transaction_info['State'] or '',
                    'customer_zip': transaction_info['Zip'] or '',
                    'subtotal': float(transaction_info['Total']) - float(transaction_info['SalesTax']) if pd.notna(transaction_info['Total']) and pd.notna(transaction_info['SalesTax']) else float(transaction_info['Total']) if pd.notna(transaction_info['Total']) else 0.0,
                    'tax': float(transaction_info['SalesTax']) if pd.notna(transaction_info['SalesTax']) else 0.0,
                    'total': float(transaction_info['Total']) if pd.notna(transaction_info['Total']) else 0.0,
                    'comment': transaction_info['Comment'] or '',
                    'cashier_id': int(transaction_info['CashierID']) if pd.notna(transaction_info['CashierID']) else None,
                    'store_id': int(transaction_info['StoreID']) if pd.notna(transaction_info['StoreID']) else None
                },
                'line_items': [],
                'tax_details': [],
                'tender_details': [],
                'summary': {
                    'item_count': len(line_items_result),
                    'total_quantity': 0,
                    'total_profit': 0
                }
            }
        }
        
        # Add line items
        total_quantity = 0
        total_profit = 0
        
        for _, row in line_items_result.iterrows():
            line_item = {
                'line_id': int(row['LineID']),
                'item_id': int(row['ItemID']),
                'lookup_code': row['ItemLookupCode'] or '',
                'description': row['Description'] or '',
                'quantity': float(row['Quantity']),
                'price': float(row['Price']),
                'line_total': float(row['LineTotal']),
                'cost': float(row['Cost']) if pd.notna(row['Cost']) else 0.0,
                'line_profit': float(row['LineProfit']) if pd.notna(row['LineProfit']) else 0.0,
                'department': row['Department'] or '',
                'category': row['Category'] or ''
            }
            
            response['data']['line_items'].append(line_item)
            total_quantity += line_item['quantity']
            total_profit += line_item['line_profit']
        
        # Add tender details (simplified)
        if tender_result is not None and not tender_result.empty:
            for _, row in tender_result.iterrows():
                tender_detail = {
                    'tender_id': int(row['TenderID']) if pd.notna(row['TenderID']) else None,
                    'amount': float(row['Amount']) if pd.notna(row['Amount']) else 0.0,
                    'description': row['Description'] or ''
                }
                response['data']['tender_details'].append(tender_detail)
        
        # Update summary
        response['data']['summary']['total_quantity'] = total_quantity
        response['data']['summary']['total_profit'] = total_profit
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting transaction details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@transaction_detail_api.route('/api/ar/<int:ar_id>/details', methods=['GET'])
def get_ar_details(ar_id):
    """Get detailed AR/invoice information"""
    try:
        # Get AR header information
        ar_query = """
        SELECT 
            ar.ID,
            ar.Date,
            ar.CustomerID,
            ar.TransactionNumber,
            ar.Type,
            ar.OriginalAmount,
            ar.Balance,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.PhoneNumber,
            c.Address,
            c.City,
            c.State,
            c.Zip,
            DATEDIFF(day, ar.Date, GETDATE()) as DaysOld
        FROM dbo.AccountReceivable ar
        LEFT JOIN dbo.Customer c ON ar.CustomerID = c.ID
        WHERE ar.ID = %s
        """
        
        ar_result = quick_query(ar_query, (ar_id,))
        
        if ar_result.empty:
            return jsonify({
                'success': False,
                'error': 'AR record not found'
            }), 404
        
        ar_info = ar_result.iloc[0].to_dict()
        
        # Get AR history for this specific AR
        history_query = """
        SELECT 
            arh.Date,
            arh.Amount,
            arh.HistoryType,
            arh.Comment
        FROM dbo.AccountReceivableHistory arh
        WHERE arh.AccountReceivableID = %s
        ORDER BY arh.Date ASC
        """
        
        history_result = quick_query(history_query, (ar_id,))
        
        # Get related transaction details if available
        transaction_details = None
        if pd.notna(ar_info['TransactionNumber']) and ar_info['TransactionNumber'] > 0:
            try:
                # Get the transaction details by calling the other endpoint internally
                from flask import current_app
                with current_app.test_request_context():
                    transaction_response = get_transaction_details(ar_info['TransactionNumber'])
                    if hasattr(transaction_response, 'get_json'):
                        response_data = transaction_response.get_json()
                        if response_data and response_data.get('success'):
                            transaction_details = response_data['data']
            except Exception as e:
                logger.warning(f"Could not load related transaction details: {e}")
        
        # Format response
        response = {
            'success': True,
            'data': {
                'ar_info': {
                    'ar_id': int(ar_info['ID']),
                    'date': ar_info['Date'].isoformat() if pd.notna(ar_info['Date']) else None,
                    'customer_id': int(ar_info['CustomerID']) if pd.notna(ar_info['CustomerID']) else None,
                    'customer_name': ar_info['CustomerName'] or 'Unknown',
                    'customer_phone': ar_info['PhoneNumber'] or '',
                    'customer_address': ar_info['Address'] or '',
                    'customer_city': ar_info['City'] or '',
                    'customer_state': ar_info['State'] or '',
                    'customer_zip': ar_info['Zip'] or '',
                    'transaction_number': int(ar_info['TransactionNumber']) if pd.notna(ar_info['TransactionNumber']) and ar_info['TransactionNumber'] > 0 else None,
                    'type': ar_info['Type'] or '',
                    'original_amount': float(ar_info['OriginalAmount']) if pd.notna(ar_info['OriginalAmount']) else 0.0,
                    'current_balance': float(ar_info['Balance']) if pd.notna(ar_info['Balance']) else 0.0,
                    'days_old': int(ar_info['DaysOld']) if pd.notna(ar_info['DaysOld']) else 0
                },
                'history': [],
                'transaction_details': transaction_details
            }
        }
        
        # Add history entries
        for _, row in history_result.iterrows():
            history_entry = {
                'date': row['Date'].isoformat() if pd.notna(row['Date']) else None,
                'amount': float(row['Amount']) if pd.notna(row['Amount']) else 0.0,
                'history_type': int(row['HistoryType']) if pd.notna(row['HistoryType']) else 0,
                'comment': row['Comment'] or ''
            }
            response['data']['history'].append(history_entry)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting AR details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
