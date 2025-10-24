"""
Enhanced Customer Ledger Excel Export
Consolidates payment entries and provides cleaner customer information
"""

from flask import Blueprint, send_file
import pandas as pd
import logging
from datetime import datetime
import io
import xlsxwriter
from modules.customer_balance_engine import customer_balance_engine
from customer_ledger import AccurateCustomerLedger as CustomerLedger

logger = logging.getLogger(__name__)

# Create Blueprint
enhanced_ledger_api = Blueprint('enhanced_ledger_api', __name__)

@enhanced_ledger_api.route('/api/customer/<int:customer_id>/export/enhanced', methods=['GET'])
def export_enhanced_ledger(customer_id):
    """Export enhanced ledger with consolidated payments and clean customer info"""
    try:
        # Get comprehensive data
        overview_data = customer_balance_engine.get_comprehensive_customer_overview(customer_id)
        customer_details = overview_data['customer_details']
        
        # Get ledger data
        ledger_engine = CustomerLedger()
        ledger_data = ledger_engine.get_complete_ledger(customer_id)
        
        # Get inventory movements to identify returns
        from database_pymssql import SQLServerConnection
        db = SQLServerConnection()
        
        # Query to find dates with inventory returns for this customer
        return_dates_query = f"""
        SELECT DISTINCT
            CAST(t.Time as DATE) as ReturnDate,
            SUM(ABS(te.Quantity * te.Price)) as ReturnAmount
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.CustomerID = {customer_id}
            AND te.Quantity < 0
            AND t.Time >= DATEADD(YEAR, -2, GETDATE())
        GROUP BY CAST(t.Time as DATE)
        """
        
        return_dates_df = db.execute_query(return_dates_query)
        return_dates = {}
        if not return_dates_df.empty:
            for _, return_row in return_dates_df.iterrows():
                return_dates[return_row['ReturnDate'].date() if hasattr(return_row['ReturnDate'], 'date') else return_row['ReturnDate']] = return_row['ReturnAmount']
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define formats - professional with subtle colors
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#2B579A',  # Professional dark blue
            'font_color': 'white',
            'border': 0
        })
        
        section_header = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#E7E6E6',  # Light gray
            'top': 1,
            'bottom': 1
        })
        
        info_label = workbook.add_format({
            'bold': True,
            'align': 'left',
            'bg_color': '#F2F2F2'  # Very light gray
        })
        
        info_value = workbook.add_format({
            'align': 'left'
        })
        
        table_header = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E2F3',  # Light blue
            'border': 1,
            'align': 'center',
            'text_wrap': True
        })
        
        currency_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'border': 1
        })
        
        currency_bold = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'bold': True,
            'bg_color': '#F2F2F2',  # Light gray for emphasis
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'mm/dd/yyyy',
            'align': 'left',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1
        })
        
        type_format = workbook.add_format({
            'align': 'left',
            'border': 1
        })
        
        # Add alternating row color for ledger
        alt_row_format = workbook.add_format({
            'bg_color': '#F7F7F7',  # Very light gray for alternating rows
            'border': 1
        })
        
        currency_alt = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'bg_color': '#F7F7F7',
            'border': 1
        })
        
        # Create worksheet
        ws = workbook.add_worksheet('Customer Statement')
        
        # Set column widths
        ws.set_column('A:A', 18)  # Date with timestamp
        ws.set_column('B:B', 10)  # Type
        ws.set_column('C:C', 15)  # Reference
        ws.set_column('D:D', 40)  # Description
        ws.set_column('E:E', 35)  # Comments/Details
        ws.set_column('F:F', 15)  # Debit
        ws.set_column('G:G', 15)  # Credit
        ws.set_column('H:H', 18)  # Running Balance
        
        row = 0
        
        # Title with company name
        company_name = customer_details.get('name', 'Customer')
        title_text = f'GEORGIA WHOLESALE CUSTOMER ACCOUNT STATEMENT - {company_name.upper()}'
        ws.merge_range(row, 0, row, 7, title_text, title_format)
        row += 2
        
        # Customer Information Section - no background color
        ws.merge_range(row, 0, row, 7, 'Customer Information', section_header)
        row += 1
        
        # Get the actual current balance from AR table first
        balance_query = f"""
        SELECT SUM(Balance) as CurrentBalance
        FROM AccountReceivable
        WHERE CustomerID = {customer_id}
        """
        balance_result = db.execute_query(balance_query)
        actual_current_balance = 0.0
        if not balance_result.empty and balance_result.iloc[0]['CurrentBalance']:
            actual_current_balance = float(balance_result.iloc[0]['CurrentBalance'])
        
        # Get additional tax/license info from database
        # Correct field mappings:
        # CustomText1 = State Tax ID
        # CustomText2 = Tobacco License  
        # TaxNumber = Resale Certificate
        # CustomText3 = Federal EIN
        # CustomText4 = Additional License/Info
        # CustomText5 = Additional License/Info
        tax_info_query = f"""
        SELECT 
            CustomText1 as StateTaxID,
            TaxNumber as ResaleCertificate, 
            CustomText2 as TobaccoLicense,
            CustomText3 as FederalEIN,
            CustomText4 as AdditionalInfo1,
            CustomText5 as AdditionalInfo2
        FROM Customer
        WHERE ID = {customer_id}
        """
        tax_result = db.execute_query(tax_info_query)
        tax_data = {}
        if not tax_result.empty:
            tax_data = tax_result.iloc[0].to_dict()
        
        # Get contact name and additional notes
        contact_query = f"""
        SELECT 
            FirstName,
            LastName,
            Notes
        FROM Customer
        WHERE ID = {customer_id}
        """
        contact_result = db.execute_query(contact_query)
        contact_name = ''
        customer_notes = ''
        if not contact_result.empty:
            contact_row = contact_result.iloc[0]
            if contact_row.get('FirstName') or contact_row.get('LastName'):
                first = contact_row.get('FirstName', '')
                last = contact_row.get('LastName', '')
                contact_name = f"{first} {last}".strip()
            customer_notes = contact_row.get('Notes', '')
        
        # Build customer info pairs for professional layout
        customer_info = []
        
        # First row: Company Name and Account Number
        customer_info.append(('Company Name:', customer_details.get('name', '')))
        customer_info.append(('Account Number:', customer_details.get('account_number', '')))
        
        # Second row: Phone and Tobacco License
        # Phone field already has -SHAHID or similar in the database, don't add contact name again
        phone_display = customer_details.get('phone', '')
        customer_info.append(('Phone:', phone_display))
        customer_info.append(('Tobacco License:', tax_data.get('TobaccoLicense', '')))
        
        # Third row: Contact and Resale Certificate
        customer_info.append(('Contact:', contact_name if contact_name else ''))
        customer_info.append(('Resale Certificate:', tax_data.get('ResaleCertificate', '')))
        
        # Fourth row: Address and Additional Information
        address_parts = []
        if customer_details.get('address'):
            address_parts.append(customer_details['address'])
        if customer_details.get('city'):
            city_state = customer_details['city']
            if customer_details.get('state'):
                city_state += f", {customer_details['state']}"
            if customer_details.get('zip'):
                city_state += f" {customer_details['zip']}"
            address_parts.append(city_state)
        
        address_display = ' '.join(address_parts) if address_parts else ''
        customer_info.append(('Address:', address_display))
        
        # Additional Information - combine multiple fields
        additional_info_parts = []
        if tax_data.get('AdditionalInfo1'):
            additional_info_parts.append(tax_data['AdditionalInfo1'])
        if tax_data.get('AdditionalInfo2'):
            additional_info_parts.append(tax_data['AdditionalInfo2'])
        additional_info = '-'.join(additional_info_parts) if additional_info_parts else ''
        customer_info.append(('Additional Information:', additional_info))
        
        # Add blank row with Current Balance
        customer_info.append(('', ''))  # Empty left side
        customer_info.append(('Current Balance:', f"${actual_current_balance:,.2f}"))
        
        # Add other relevant fields if they exist
        if tax_data.get('StateTaxID'):
            customer_info.append(('State Tax ID:', tax_data['StateTaxID']))
        if tax_data.get('FederalEIN'):
            customer_info.append(('Federal EIN:', tax_data['FederalEIN']))
        if customer_details.get('email'):
            customer_info.append(('Email:', customer_details['email']))
        
        # Add customer notes if available
        if customer_notes and customer_notes.strip():
            customer_info.append(('Notes:', customer_notes[:100]))  # Limit to 100 chars
        
        # Write customer info in two columns with clean formatting
        for i in range(0, len(customer_info), 2):
            left_label, left_value = customer_info[i] if i < len(customer_info) else ('', '')
            right_label, right_value = customer_info[i + 1] if i + 1 < len(customer_info) else ('', '')
            
            # Left column
            if left_label:  # Only write if there's a label
                ws.write(row, 0, left_label, info_label)
                ws.merge_range(row, 1, row, 3, f"    {left_value}", info_value)  # Add indent for values
            
            # Right column
            if right_label:  # Only write if there's a label
                ws.write(row, 4, right_label, info_label)
                ws.merge_range(row, 5, row, 7, f"    {right_value}", info_value)  # Add indent for values
            
            row += 1
        
        row += 1
        
        # Transaction History Section
        ws.merge_range(row, 0, row, 7, 'Transaction History', section_header)
        row += 1
        
        # Table headers
        headers = ['Date', 'Type', 'Reference', 'Description', 'Details/Applied To', 'Debit', 'Credit', 'Balance']
        for col, header in enumerate(headers):
            ws.write(row, col, header, table_header)
        row += 1
        
        # Get payment tender breakdowns for this customer
        payment_tender_query = f"""
        SELECT 
            p.ID as PaymentID,
            p.Time,
            p.Amount as TotalAmount,
            te.TenderID,
            t.Description as TenderType,
            te.Amount as TenderAmount,
            te.Description as TenderDescription
        FROM Payment p
        LEFT JOIN TenderEntry te ON p.ID = te.PaymentID
        LEFT JOIN Tender t ON te.TenderID = t.ID
        WHERE p.CustomerID = {customer_id}
            AND p.Time >= DATEADD(YEAR, -2, GETDATE())
        ORDER BY p.Time DESC
        """
        payment_tenders_df = db.execute_query(payment_tender_query)
        
        # Group tender entries by payment ID
        payment_tender_details = {}
        if not payment_tenders_df.empty:
            for _, tender_row in payment_tenders_df.iterrows():
                payment_id = tender_row['PaymentID']
                if payment_id not in payment_tender_details:
                    payment_tender_details[payment_id] = {
                        'total': tender_row['TotalAmount'],
                        'time': tender_row['Time'],
                        'tenders': []
                    }
                if tender_row['TenderAmount'] and tender_row['TenderAmount'] != 0:
                    payment_tender_details[payment_id]['tenders'].append({
                        'type': tender_row['TenderType'],
                        'amount': tender_row['TenderAmount']
                    })
        
        # Process and consolidate ledger entries
        consolidated_entries = []
        payment_buffer = {}
        
        for entry in ledger_data['ledger']:
            transaction_type = entry.get('TransactionType', '')
            
            if transaction_type == 'PAYMENT':
                # Group payments by transaction number or date
                ref_num = entry.get('ReferenceNumber', '')
                trans_date = entry.get('TransactionDate', '')
                
                # Create unique key for payment grouping
                payment_key = f"{trans_date}_{ref_num}" if ref_num else f"{trans_date}_payment"
                
                if payment_key not in payment_buffer:
                    payment_buffer[payment_key] = {
                        'date': trans_date,
                        'type': 'PAYMENT',
                        'reference': ref_num,
                        'total_amount': 0,
                        'applied_invoices': [],
                        'tender_type': entry.get('TenderType', ''),
                        'tender_breakdown': [],  # Add tender breakdown
                        'check_number': '',
                        'running_balance': entry.get('RunningBalance', 0),
                        'payment_id': None
                    }
                
                # Add to total payment amount
                credit_amount = float(entry.get('Credit', 0))
                payment_buffer[payment_key]['total_amount'] += credit_amount
                
                # Try to find matching payment ID for tender breakdown
                payment_id = entry.get('PaymentID')
                if payment_id and payment_id in payment_tender_details:
                    payment_buffer[payment_key]['tender_breakdown'] = payment_tender_details[payment_id]['tenders']
                    payment_buffer[payment_key]['payment_id'] = payment_id
                
                # Track which invoice this payment applies to
                description = entry.get('Description', '')
                if 'Applied to' in description or 'Invoice' in description:
                    payment_buffer[payment_key]['applied_invoices'].append(description)
                
                # Extract check number if available
                if 'Check' in entry.get('TenderType', ''):
                    import re
                    check_match = re.search(r'#(\d+)', description)
                    if check_match:
                        payment_buffer[payment_key]['check_number'] = check_match.group(1)
                
                # Update running balance to latest
                payment_buffer[payment_key]['running_balance'] = entry.get('RunningBalance', 0)
                
            else:
                # Flush any pending payments before this transaction
                for payment_data in payment_buffer.values():
                    consolidated_entries.append(payment_data)
                payment_buffer = {}
                
                # Add non-payment transaction as-is
                consolidated_entries.append({
                    'date': entry.get('TransactionDate', ''),
                    'type': transaction_type,
                    'reference': entry.get('ReferenceNumber', ''),
                    'description': entry.get('Description', ''),
                    'debit': float(entry.get('Debit', 0)),
                    'credit': float(entry.get('Credit', 0)),
                    'running_balance': entry.get('RunningBalance', 0),
                    'tender_type': entry.get('TenderType', ''),
                    'comments': entry.get('Comments', '')
                })
        
        # Flush remaining payments
        for payment_data in payment_buffer.values():
            consolidated_entries.append(payment_data)
        
        # Sort consolidated entries by date (oldest first) to calculate running balance correctly
        for entry in consolidated_entries:
            if 'date' in entry:
                try:
                    entry['date_obj'] = pd.to_datetime(entry['date'])
                except:
                    entry['date_obj'] = entry['date']
        
        consolidated_entries.sort(key=lambda x: (x.get('date_obj', pd.Timestamp.min), x.get('type', '')))
        
        # Recalculate running balance after consolidation
        running_balance = 0.0
        for entry in consolidated_entries:
            # Calculate the transaction amount based on transaction type
            trans_type = entry.get('type', '')
            
            if trans_type == 'PAYMENT':
                # Payments reduce the balance (credits)
                amount = -abs(entry.get('total_amount', 0))
            elif trans_type in ['SALE', 'INVOICE']:
                # Sales/Invoices increase the balance (debits)
                amount = abs(entry.get('debit', 0))
            elif 'CREDIT' in trans_type and 'ADJUSTMENT' in trans_type:
                # Credit adjustments reduce the balance
                amount = -abs(entry.get('credit', 0))
            elif 'DEBIT' in trans_type and 'ADJUSTMENT' in trans_type:
                # Debit adjustments increase the balance
                amount = abs(entry.get('debit', 0))
            else:
                # Standard calculation: debit increases, credit decreases
                debit = float(entry.get('debit', 0))
                credit = float(entry.get('credit', 0))
                amount = debit - credit
            
            running_balance += amount
            entry['recalculated_balance'] = running_balance
        
        # Now reverse for display (newest first)
        consolidated_entries.reverse()
        
        # Write consolidated entries with alternating row colors
        for idx, entry in enumerate(consolidated_entries):
            # Use alternating row colors for better readability
            is_alt_row = (idx % 2 == 1)
            row_text_format = alt_row_format if is_alt_row else text_format
            row_currency_format = currency_alt if is_alt_row else currency_format
            
            # Date
            if entry.get('date'):
                try:
                    date_obj = pd.to_datetime(entry['date'])
                    if is_alt_row:
                        ws.write_datetime(row, 0, date_obj, workbook.add_format({
                            'num_format': 'mm/dd/yyyy',
                            'align': 'left',
                            'border': 1,
                            'bg_color': '#F7F7F7'
                        }))
                    else:
                        ws.write_datetime(row, 0, date_obj, date_format)
                except:
                    ws.write(row, 0, entry['date'], row_text_format)
            
            # Type
            trans_type = entry.get('type', '')
            ws.write(row, 1, trans_type, row_text_format)
            
            # Reference
            ws.write(row, 2, entry.get('reference', ''), row_text_format)
            
            # Description
            if entry.get('type') == 'PAYMENT':
                # Create consolidated description for payment with tender breakdown
                tender_breakdown = entry.get('tender_breakdown', [])
                
                if tender_breakdown and len(tender_breakdown) > 1:
                    # Multiple tenders - show breakdown
                    tender_parts = []
                    for tender in tender_breakdown:
                        tender_type = tender['type'] or 'Unknown'
                        amount = tender['amount']
                        if amount > 0:
                            tender_parts.append(f"{tender_type}: ${amount:,.2f}")
                    description = "PAYMENT - " + ", ".join(tender_parts)
                elif tender_breakdown and len(tender_breakdown) == 1:
                    # Single tender
                    tender_type = tender_breakdown[0]['type'] or 'Payment'
                    check_num = entry.get('check_number', '')
                    if check_num:
                        description = f"{tender_type} #{check_num}"
                    else:
                        description = tender_type
                else:
                    # Fallback to original logic if no breakdown available
                    tender = entry.get('tender_type', 'Payment')
                    check_num = entry.get('check_number', '')
                    if check_num:
                        description = f"{tender} #{check_num}"
                    else:
                        description = tender
            elif 'ADJUSTMENT' in entry.get('type', ''):
                # Check if this is actually a return by looking for inventory movement
                is_return = False
                entry_date = entry.get('date')
                if entry_date:
                    try:
                        # Convert to date object for comparison
                        if hasattr(entry_date, 'date'):
                            check_date = entry_date.date()
                        else:
                            check_date = pd.to_datetime(entry_date).date()
                        
                        # Check if there's a return on this date
                        if check_date in return_dates:
                            # Check if amounts are close (within $10 or 10%)
                            adj_amount = abs(entry.get('credit', 0) or entry.get('debit', 0))
                            return_amount = return_dates[check_date]
                            
                            if abs(adj_amount - return_amount) < 10 or abs(adj_amount - return_amount) / max(adj_amount, return_amount) < 0.1:
                                is_return = True
                    except:
                        pass
                
                # For adjustments, show the actual reason from comments if available
                comments = entry.get('comments', '').strip()
                if comments and comments not in ['', 'None', 'N/A']:
                    # Use the comment as the main description for adjustments
                    description = comments
                elif is_return:
                    # This is a return based on inventory movement
                    amount = entry.get('credit', 0) or entry.get('debit', 0)
                    description = f"Product Return ${abs(amount):,.2f}"
                else:
                    # Fall back to the standard description
                    base_desc = entry.get('description', '')
                    # Clean up redundant adjustment text
                    if 'Credit Adjustment - $' in base_desc or 'Debit Adjustment - $' in base_desc:
                        import re
                        # Extract the amount
                        amount_match = re.search(r'\$[\d,]+\.?\d*', base_desc)
                        if amount_match:
                            adj_type = 'Credit' if 'CREDIT' in entry.get('type', '') else 'Debit'
                            description = f"{adj_type} Adjustment {amount_match.group()}"
                        else:
                            description = base_desc
                    else:
                        description = base_desc
            else:
                description = entry.get('description', '')
            ws.write(row, 3, description, row_text_format)
            
            # Details/Applied To column
            details = ""
            if entry.get('type') == 'PAYMENT':
                details_parts = []
                
                # Add applied invoices if available
                if entry.get('applied_invoices'):
                    invoices = entry.get('applied_invoices', [])
                    if invoices:
                        # Clean up invoice descriptions
                        cleaned_invoices = []
                        for inv in invoices:
                            # Extract just the invoice number if possible
                            import re
                            inv_match = re.search(r'Invoice[:\s#]*(\d+)', inv)
                            if inv_match:
                                cleaned_invoices.append(f"Inv #{inv_match.group(1)}")
                            else:
                                cleaned_invoices.append(inv)
                        details_parts.append("Applied to: " + ", ".join(cleaned_invoices))
                
                # Add tender breakdown for multiple tenders
                tender_breakdown = entry.get('tender_breakdown', [])
                if tender_breakdown and len(tender_breakdown) > 1:
                    # Show detailed breakdown for multiple tenders
                    tender_details = []
                    for tender in tender_breakdown:
                        if tender['amount'] > 0:
                            tender_details.append(f"{tender['type']}: ${tender['amount']:,.2f}")
                    if tender_details:
                        details_parts.append("Tenders: " + ", ".join(tender_details))
                
                details = "; ".join(details_parts) if details_parts else ""
            elif entry.get('comments'):
                details = entry.get('comments', '')
            ws.write(row, 4, details, row_text_format)
            
            # Debit
            if entry.get('type') == 'PAYMENT':
                ws.write(row, 5, '', row_currency_format)  # Payments don't have debits
            else:
                debit = entry.get('debit', 0)
                if debit > 0:
                    ws.write(row, 5, debit, row_currency_format)
                else:
                    ws.write(row, 5, '', row_currency_format)
            
            # Credit
            if entry.get('type') == 'PAYMENT':
                ws.write(row, 6, entry.get('total_amount', 0), row_currency_format)
            else:
                credit = entry.get('credit', 0)
                if credit > 0:
                    ws.write(row, 6, credit, row_currency_format)
                else:
                    ws.write(row, 6, '', row_currency_format)
            
            # Running Balance - use recalculated balance with emphasis
            balance = float(entry.get('recalculated_balance', entry.get('running_balance', 0)))
            if is_alt_row:
                balance_format = workbook.add_format({
                    'num_format': '$#,##0.00',
                    'align': 'right',
                    'bold': True if balance != 0 else False,
                    'bg_color': '#F7F7F7',
                    'border': 1
                })
            else:
                balance_format = currency_bold if balance != 0 else currency_format
            ws.write(row, 7, balance, balance_format)
            
            row += 1
        
        # Add summary row - clean and simple
        row += 1
        ws.write(row, 0, '', text_format)
        ws.write(row, 1, '', text_format)
        ws.write(row, 2, '', text_format)
        ws.write(row, 3, '', text_format)
        ws.write(row, 4, '', text_format)
        ws.write(row, 5, '', text_format)
        ws.write(row, 6, 'Current Balance:', workbook.add_format({
            'bold': True,
            'align': 'right',
            'top': 2
        }))
        ws.write(row, 7, actual_current_balance, workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'bold': True,
            'top': 2
        }))
        
        # Add footer
        row += 2
        footer_format = workbook.add_format({
            'font_size': 9,
            'font_color': '#666666',
            'italic': True
        })
        ws.merge_range(row, 0, row, 7, 
                      f"Statement generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                      footer_format)
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Generate filename
        customer_name = customer_details.get('name', 'Customer').replace(' ', '_').replace('/', '_')
        filename = f"{customer_name}_Statement_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Enhanced ledger export error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'error': str(e)}, 500