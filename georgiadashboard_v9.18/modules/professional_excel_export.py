"""
Professional Excel Export Module
Creates two types of Excel exports:
1. Professional - Business-ready, formatted for sharing
2. Detailed - Complete data dump with all information
"""

from flask import Blueprint, jsonify, send_file, request
import pandas as pd
import logging
from datetime import datetime
import io
import xlsxwriter
from modules.customer_balance_engine import customer_balance_engine
from modules.customer_detail_api import CustomerDetailAPI
from app.customer_ledger import AccurateCustomerLedger as CustomerLedger

logger = logging.getLogger(__name__)

# Create Blueprint
professional_excel_api = Blueprint('professional_excel_api', __name__)

@professional_excel_api.route('/api/customer/<int:customer_id>/export/professional', methods=['GET'])
def export_professional_excel(customer_id):
    """Export professional, business-ready Excel report"""
    try:
        # Get comprehensive data using validated balance and overview
        overview_data = customer_balance_engine.get_comprehensive_customer_overview(customer_id)
        balance_data = overview_data['balance_data']
        customer_details = overview_data['customer_details']
        overview_metrics = overview_data['overview_metrics']
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define professional styles
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#2E5090',
            'font_color': 'white',
            'border': 1
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#4A90B8',
            'font_color': 'white',
            'border': 1
        })
        
        subheader_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'bg_color': '#E7F3FF',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'border': 1
        })
        
        currency_bold_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'bold': True,
            'bg_color': '#F0F8FF',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'mm/dd/yyyy',
            'align': 'center',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'text_wrap': True
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right',
            'border': 1
        })
        
        # Create main worksheet
        worksheet = workbook.add_worksheet('Customer Ledger Report')
        worksheet.set_column('A:A', 15)  # Date
        worksheet.set_column('B:B', 12)  # Type
        worksheet.set_column('C:C', 15)  # Reference
        worksheet.set_column('D:D', 30)  # Description
        worksheet.set_column('E:E', 25)  # Comment
        worksheet.set_column('F:F', 15)  # Payment Method
        worksheet.set_column('G:G', 12)  # Debit
        worksheet.set_column('H:H', 12)  # Credit
        worksheet.set_column('I:I', 15)  # Balance
        
        row = 0
        
        # Title
        worksheet.merge_range('A1:I1', 'CUSTOMER ACCOUNT LEDGER', title_format)
        row += 2
        
        # Company header (if you want to add company info)
        worksheet.merge_range(f'A{row+1}:I{row+1}', f'Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}', header_format)
        row += 2
        
        # Customer Information Section - Professional Layout
        
        # Create a white background format for spacing
        white_bg = workbook.add_format({'bg_color': 'white', 'border': 0})
        
        # Professional info formats
        info_header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_color': '#2E5090',
            'align': 'left',
            'valign': 'vcenter',
            'bottom': 2,
            'bottom_color': '#2E5090'
        })
        
        info_label_format = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#555555',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        info_value_format = workbook.add_format({
            'font_size': 10,
            'font_color': '#000000',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        info_value_bold = workbook.add_format({
            'font_size': 11,
            'font_color': '#000000',
            'align': 'left',
            'valign': 'vcenter',
            'bold': True
        })
        
        currency_info_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'font_size': 10,
            'font_color': '#000000',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        currency_info_bold = workbook.add_format({
            'num_format': '$#,##0.00',
            'font_size': 11,
            'font_color': '#059669',
            'align': 'left',
            'valign': 'vcenter',
            'bold': True
        })
        
        # CUSTOMER DETAILS HEADER
        worksheet.merge_range(f'A{row+1}:I{row+1}', 'CUSTOMER DETAILS', info_header_format)
        row += 2  # Add spacing
        
        # Get company or customer name for primary display
        company = customer_details.get('company', '')
        customer_name = f"{customer_details.get('first_name', '')} {customer_details.get('last_name', '')}".strip()
        primary_name = company if company else customer_name
        
        # PRIMARY CUSTOMER NAME (Large, Bold)
        if primary_name:
            worksheet.write(row, 0, primary_name, info_value_bold)
            worksheet.merge_range(f'B{row+1}:D{row+1}', '', white_bg)
            
            # Account info on the right
            worksheet.write(row, 5, 'Account #:', info_label_format)
            worksheet.write(row, 6, customer_details.get('account_number', 'N/A'), info_value_format)
            row += 1
            
            # If company exists and we have a contact name, show it
            if company and customer_name:
                worksheet.write(row, 0, 'Contact:', info_label_format)
                worksheet.write(row, 1, customer_name, info_value_format)
                worksheet.write(row, 5, 'Customer ID:', info_label_format)
                worksheet.write(row, 6, str(customer_id), info_value_format)
                row += 1
        
        row += 1  # Spacing
        
        # CONTACT INFORMATION
        worksheet.write(row, 0, 'CONTACT', info_label_format)
        worksheet.merge_range(f'B{row+1}:C{row+1}', '', white_bg)
        worksheet.write(row, 4, 'FINANCIAL', info_label_format)
        worksheet.merge_range(f'E{row+1}:H{row+1}', '', white_bg)
        row += 1
        
        # Address
        address = customer_details.get('address', '')
        if address:
            worksheet.write(row, 0, 'Address:', info_label_format)
            worksheet.merge_range(f'B{row+1}:C{row+1}', address, info_value_format)
        
        # Current Balance
        current_balance = balance_data.get('current_balance', {}).get('authoritative_balance', 0)
        worksheet.write(row, 4, 'Current Balance:', info_label_format)
        worksheet.merge_range(f'F{row+1}:G{row+1}', current_balance, currency_info_bold)
        row += 1
        
        # City, State, ZIP
        city = customer_details.get('city', '')
        state = customer_details.get('state', '')
        zip_code = customer_details.get('zip', '')
        city_state_zip = ', '.join(filter(None, [city, state, zip_code]))
        
        if city_state_zip:
            worksheet.write(row, 0, 'City/State/ZIP:', info_label_format)
            worksheet.merge_range(f'B{row+1}:C{row+1}', city_state_zip, info_value_format)
        
        # Credit Limit
        worksheet.write(row, 4, 'Credit Limit:', info_label_format)
        worksheet.merge_range(f'F{row+1}:G{row+1}', customer_details.get('credit_limit', 0), currency_info_format)
        row += 1
        
        # Phone
        phone = customer_details.get('phone', '')
        if phone:
            worksheet.write(row, 0, 'Phone:', info_label_format)
            worksheet.merge_range(f'B{row+1}:C{row+1}', phone, info_value_format)
        
        # Total Lifetime Sales
        worksheet.write(row, 4, 'Lifetime Sales:', info_label_format)
        worksheet.merge_range(f'F{row+1}:G{row+1}', customer_details.get('total_sales_lifetime', 0), currency_info_format)
        row += 1
        
        # Email
        email = customer_details.get('email', '')
        if email:
            worksheet.write(row, 0, 'Email:', info_label_format)
            worksheet.merge_range(f'B{row+1}:C{row+1}', email, info_value_format)
        
        # Customer Since
        customer_since = overview_metrics['tenure'].get('customer_since')
        if customer_since:
            try:
                since_date = datetime.fromisoformat(customer_since).strftime('%B %Y')
                worksheet.write(row, 4, 'Customer Since:', info_label_format)
                worksheet.merge_range(f'F{row+1}:G{row+1}', since_date, info_value_format)
            except:
                pass
        row += 1
        
        row += 1  # Spacing
        
        # TAX & LICENSING
        worksheet.write(row, 0, 'TAX & LICENSING', info_label_format)
        worksheet.merge_range(f'B{row+1}:C{row+1}', '', white_bg)
        worksheet.write(row, 4, 'ACCOUNT ACTIVITY', info_label_format)
        worksheet.merge_range(f'E{row+1}:H{row+1}', '', white_bg)
        row += 1
        
        # Tax Number
        tax_number = customer_details.get('tax_number', '')
        worksheet.write(row, 0, 'Tax ID/EIN:', info_label_format)
        worksheet.merge_range(f'B{row+1}:C{row+1}', tax_number if tax_number else 'Not on file', info_value_format)
        
        # Last Payment
        last_payment = overview_metrics.get('payments', {}).get('last_payment_date')
        if last_payment:
            try:
                last_payment_str = datetime.fromisoformat(last_payment).strftime('%m/%d/%Y')
                worksheet.write(row, 4, 'Last Payment:', info_label_format)
                worksheet.merge_range(f'F{row+1}:G{row+1}', last_payment_str, info_value_format)
            except:
                pass
        row += 1
        
        # Tax Exempt Status
        tax_exempt = 'Yes' if customer_details.get('tax_exempt') else 'No'
        worksheet.write(row, 0, 'Tax Exempt:', info_label_format)
        worksheet.merge_range(f'B{row+1}:C{row+1}', tax_exempt, info_value_format)
        
        # Last Visit
        last_visit = customer_details.get('last_visit')
        if last_visit:
            try:
                last_visit_str = datetime.fromisoformat(last_visit).strftime('%m/%d/%Y')
                worksheet.write(row, 4, 'Last Visit:', info_label_format)
                worksheet.merge_range(f'F{row+1}:G{row+1}', last_visit_str, info_value_format)
            except:
                pass
        row += 1
        
        # Tobacco License
        tobacco_license = customer_details.get('custom_text1', '')
        if tobacco_license:
            worksheet.write(row, 0, 'Tobacco License:', info_label_format)
            worksheet.merge_range(f'B{row+1}:C{row+1}', tobacco_license, info_value_format)
        
        # Total Visits
        total_visits = customer_details.get('total_visits', 0)
        if total_visits:
            worksheet.write(row, 4, 'Total Visits:', info_label_format)
            worksheet.merge_range(f'F{row+1}:G{row+1}', f'{total_visits:,}', info_value_format)
            row += 1
        
        # Sales Tax License
        sales_tax_license = customer_details.get('custom_text2', '')
        if sales_tax_license:
            worksheet.write(row, 0, 'Sales Tax License:', info_label_format)
            worksheet.merge_range(f'B{row+1}:C{row+1}', sales_tax_license, info_value_format)
            row += 1
        
        # Notes (if any)
        notes = customer_details.get('notes', '').strip()
        if notes:
            row += 1
            worksheet.write(row, 0, 'NOTES', info_label_format)
            worksheet.merge_range(f'B{row+1}:I{row+1}', '', white_bg)
            row += 1
            # Wrap long notes
            notes_format = workbook.add_format({
                'font_size': 9,
                'font_color': '#333333',
                'align': 'left',
                'valign': 'top',
                'text_wrap': True
            })
            worksheet.merge_range(f'A{row+1}:I{row+1}', notes, notes_format)
            # Set row height based on note length
            note_lines = len(notes) // 100 + 1  # Rough estimate
            worksheet.set_row(row, min(15 * note_lines, 60))  # Max 60 pixels height
            row += 1
        
        row += 1  # Extra spacing
        
        # Account Summary Section
        worksheet.write(row, 0, 'ACCOUNT SUMMARY', subheader_format)
        worksheet.merge_range(f'B{row+1}:I{row+1}', '', subheader_format)
        row += 1
        
        current_balance = balance_data['current_balance']['authoritative_balance']
        events = balance_data['business_events']['summary']['event_types']
        
        worksheet.write(row, 0, 'Current Balance:', text_format)
        worksheet.write(row, 1, current_balance, currency_bold_format)
        worksheet.write(row, 3, 'Balance Status:', text_format)
        worksheet.write(row, 4, 'VALIDATED ✓', text_format)
        row += 1
        
        total_sales = abs(events.get('SALE_INVOICE', {}).get('total_amount', 0))
        total_payments = abs(events.get('PAYMENT_RECEIVED', {}).get('total_amount', 0))
        
        worksheet.write(row, 0, 'Total Sales:', text_format)
        worksheet.write(row, 1, total_sales, currency_format)
        worksheet.write(row, 3, 'Total Payments:', text_format)
        worksheet.write(row, 4, total_payments, currency_format)
        row += 2
        
        # Transaction History Section
        worksheet.write(row, 0, 'TRANSACTION HISTORY', subheader_format)
        worksheet.merge_range(f'B{row+1}:I{row+1}', '', subheader_format)
        row += 1
        
        # Headers
        headers = ['Date', 'Type', 'Reference', 'Description', 'Comment', 'Payment Method', 'Debit', 'Credit', 'Running Balance']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        # Get ledger data with tender types
        ledger = CustomerLedger()
        ledger_data = ledger.get_ledger(customer_id)
        
        # Transaction data (already in most recent first order)
        if ledger_data and 'ledger' in ledger_data:
            for transaction in ledger_data['ledger']:
                transaction_date = pd.to_datetime(transaction['TransactionDate']).date()
                
                # Get transaction type
                trans_type = transaction.get('TransactionType', '')
                if trans_type == 'PMT':
                    display_type = 'Payment'
                elif trans_type == 'SALE':
                    display_type = 'Sale'
                elif trans_type == 'RETURN':
                    display_type = 'Return'
                elif trans_type == 'NSF-FEE':
                    display_type = 'NSF Fee'
                elif trans_type == 'NSF-REV':
                    display_type = 'NSF Reversal'
                else:
                    display_type = transaction.get('Category', trans_type)
                
                worksheet.write(row, 0, transaction_date, date_format)
                worksheet.write(row, 1, display_type, text_format)
                worksheet.write(row, 2, transaction.get('ReferenceNumber', transaction.get('RefNumber', '')), text_format)
                worksheet.write(row, 3, transaction.get('StandardDescription', transaction.get('Description', '')), text_format)
                
                # Comment
                comment = transaction.get('Comments', transaction.get('Comment', ''))
                worksheet.write(row, 4, comment, text_format)
                
                # Tender type (payment method) - use TenderType field (singular)
                tender = transaction.get('TenderType', '')
                if tender == 'UNSPECIFIED' or tender == '':
                    tender = ''
                worksheet.write(row, 5, tender, text_format)
                
                # Debit/Credit
                debit = transaction.get('Debit', 0)
                credit = transaction.get('Credit', 0)
                
                if debit > 0:
                    worksheet.write(row, 6, debit, currency_format)
                else:
                    worksheet.write(row, 6, '', text_format)
                    
                if credit > 0:
                    worksheet.write(row, 7, credit, currency_format)
                else:
                    worksheet.write(row, 7, '', text_format)
                    
                worksheet.write(row, 8, transaction.get('RunningBalance', 0), currency_bold_format)
                row += 1
        
        # Add totals row
        row += 1
        worksheet.write(row, 3, 'FINAL BALANCE:', subheader_format)
        worksheet.write(row, 8, current_balance, currency_bold_format)
        
        workbook.close()
        output.seek(0)
        
        filename = f'customer_ledger_professional_{customer_id}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error creating professional Excel export: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@professional_excel_api.route('/api/customer/<int:customer_id>/export/detailed', methods=['GET'])
def export_detailed_excel(customer_id):
    """Export detailed Excel report with everything"""
    try:
        # Get comprehensive data
        balance_data = customer_balance_engine.get_customer_balance_comprehensive(customer_id)
        customer_api = CustomerDetailAPI()
        customer_360 = customer_api.get_customer_360(customer_id)
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'bg_color': '#1f4e79',
            'font_color': 'white',
            'border': 1
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#4a90b8',
            'font_color': 'white',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'mm/dd/yyyy',
            'align': 'center',
            'border': 1
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1,
            'text_wrap': True
        })
        
        # Get ledger data with tender types for detailed export
        ledger = CustomerLedger()
        ledger_result = ledger.get_ledger(customer_id)
        
        # Sheet 1: Complete Transaction Timeline with Tender Types
        ws_timeline = workbook.add_worksheet('Complete Timeline')
        ws_timeline.set_column('A:A', 12)  # Date
        ws_timeline.set_column('B:B', 15)  # Event Type
        ws_timeline.set_column('C:C', 15)  # Reference
        ws_timeline.set_column('D:D', 40)  # Description
        ws_timeline.set_column('E:E', 15)  # Payment Method
        ws_timeline.set_column('F:F', 12)  # Debit
        ws_timeline.set_column('G:G', 12)  # Credit
        ws_timeline.set_column('H:H', 15)  # Running Balance
        ws_timeline.set_column('I:I', 30)  # Comment
        
        # Timeline headers
        timeline_headers = ['Date', 'Type', 'Reference', 'Description', 'Payment Method', 'Debit', 'Credit', 'Running Balance', 'Comment']
        for col, header in enumerate(timeline_headers):
            ws_timeline.write(0, col, header, header_format)
        
        # Timeline data from ledger with tender types
        if ledger_result and 'ledger' in ledger_result:
            for row, transaction in enumerate(ledger_result['ledger'], 1):
                ws_timeline.write(row, 0, pd.to_datetime(transaction['TransactionDate']).date(), date_format)
                ws_timeline.write(row, 1, transaction.get('TransactionType', ''), text_format)
                ws_timeline.write(row, 2, transaction.get('ReferenceNumber', transaction.get('RefNumber', '')), text_format)
                ws_timeline.write(row, 3, transaction.get('StandardDescription', transaction.get('Description', '')), text_format)
                
                # Use TenderType field (singular)
                tender = transaction.get('TenderType', '')
                if tender == 'UNSPECIFIED' or tender == '':
                    tender = ''
                ws_timeline.write(row, 4, tender, text_format)
                
                debit = transaction.get('Debit', 0)
                credit = transaction.get('Credit', 0)
                
                if debit > 0:
                    ws_timeline.write(row, 5, debit, currency_format)
                else:
                    ws_timeline.write(row, 5, '', text_format)
                    
                if credit > 0:
                    ws_timeline.write(row, 6, credit, currency_format)
                else:
                    ws_timeline.write(row, 6, '', text_format)
                
                ws_timeline.write(row, 7, transaction.get('RunningBalance', 0), currency_format)
                ws_timeline.write(row, 8, transaction.get('Comments', transaction.get('OriginalComment', '')), text_format)
        
        # Sheet 2: Business Events Summary
        ws_events = workbook.add_worksheet('Business Events')
        ws_events.set_column('A:A', 20)
        ws_events.set_column('B:B', 15)
        ws_events.set_column('C:C', 15)
        ws_events.set_column('D:D', 15)
        
        event_headers = ['Event Type', 'Count', 'Total Amount', 'Average Amount']
        for col, header in enumerate(event_headers):
            ws_events.write(0, col, header, header_format)
        
        events = balance_data['business_events']['summary']['event_types']
        row = 1
        for event_type, data in events.items():
            ws_events.write(row, 0, event_type, text_format)
            ws_events.write(row, 1, data.get('count', 0), number_format)
            ws_events.write(row, 2, data.get('total_amount', 0), currency_format)
            ws_events.write(row, 3, data.get('average_amount', 0), currency_format)
            row += 1
        
        # Sheet 3: Outstanding AR
        ws_ar = workbook.add_worksheet('Outstanding AR')
        ws_ar.set_column('A:A', 12)
        ws_ar.set_column('B:B', 15)
        ws_ar.set_column('C:C', 15)
        ws_ar.set_column('D:D', 15)
        ws_ar.set_column('E:E', 10)
        
        ar_headers = ['Date', 'Invoice', 'Original Amount', 'Current Balance', 'Days Old']
        for col, header in enumerate(ar_headers):
            ws_ar.write(0, col, header, header_format)
        
        ar_breakdown = balance_data.get('ar_breakdown', {})
        invoices = ar_breakdown.get('invoices', [])
        for row, invoice in enumerate(invoices, 1):
            ws_ar.write(row, 0, pd.to_datetime(invoice['Date']).date(), date_format)
            ws_ar.write(row, 1, invoice.get('TransactionNumber', invoice.get('ID', '')), text_format)
            ws_ar.write(row, 2, float(invoice['OriginalAmount']), currency_format)
            ws_ar.write(row, 3, float(invoice['Balance']), currency_format)
            ws_ar.write(row, 4, invoice.get('DaysOld', 0), number_format)
        
        # Sheet 4: Verification Details
        ws_verify = workbook.add_worksheet('Verification')
        ws_verify.set_column('A:A', 25)
        ws_verify.set_column('B:B', 20)
        
        verification = balance_data.get('balance_verification', {})
        ws_verify.write(0, 0, 'Verification Item', header_format)
        ws_verify.write(0, 1, 'Status/Value', header_format)
        
        verify_row = 1
        ws_verify.write(verify_row, 0, 'Verification Status', text_format)
        ws_verify.write(verify_row, 1, verification.get('status', 'Unknown'), text_format)
        verify_row += 1
        
        ws_verify.write(verify_row, 0, 'Confidence Level', text_format)
        ws_verify.write(verify_row, 1, verification.get('confidence_level', 'Unknown'), text_format)
        verify_row += 1
        
        ws_verify.write(verify_row, 0, 'All Methods Agree', text_format)
        ws_verify.write(verify_row, 1, str(verification.get('all_methods_agree', False)), text_format)
        verify_row += 1
        
        ws_verify.write(verify_row, 0, 'Current Balance', text_format)
        ws_verify.write(verify_row, 1, balance_data['current_balance']['authoritative_balance'], currency_format)
        
        workbook.close()
        output.seek(0)
        
        filename = f'customer_ledger_detailed_{customer_id}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error creating detailed Excel export: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
