"""
Customer Groups Excel Export Module
Generates professional Excel exports for customer groups with payment/invoice details
"""

import logging
import xlsxwriter
from datetime import datetime
from typing import List, Dict
import os
import tempfile

logger = logging.getLogger(__name__)

class CustomerGroupsExcelExporter:
    """Handles Excel export for customer groups with professional formatting"""
    
    def __init__(self):
        self.workbook = None
        self.formats = {}
    
    def _create_formats(self):
        """Create Excel formats for professional styling"""
        self.formats = {
            'title': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 16,
                'bold': True,
                'font_color': '#1f4e79',
                'bottom': 2,
                'bottom_color': '#1f4e79'
            }),
            'header': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 11,
                'bold': True,
                'bg_color': '#d9e1f2',
                'font_color': '#1f4e79',
                'border': 1,
                'border_color': '#8ea9db',
                'text_wrap': True,
                'valign': 'vcenter'
            }),
            'data': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 10,
                'border': 1,
                'border_color': '#d0d0d0',
                'valign': 'top'
            }),
            'money': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 10,
                'num_format': '$#,##0.00',
                'border': 1,
                'border_color': '#d0d0d0',
                'valign': 'top'
            }),
            'date': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 10,
                'num_format': 'mm/dd/yyyy',
                'border': 1,
                'border_color': '#d0d0d0',
                'valign': 'top'
            }),
            'integer': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 10,
                'num_format': '#,##0',
                'border': 1,
                'border_color': '#d0d0d0',
                'valign': 'top'
            }),
            'group_header': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 12,
                'bold': True,
                'bg_color': '#e2efda',
                'font_color': '#375623',
                'border': 1,
                'border_color': '#70ad47'
            }),
            'summary_label': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 11,
                'bold': True,
                'font_color': '#1f4e79'
            }),
            'summary_value': self.workbook.add_format({
                'font_name': 'Calibri',
                'font_size': 11,
                'num_format': '$#,##0.00',
                'font_color': '#1f4e79'
            })
        }
    
    def export_groups_to_excel(self, groups_data: List[Dict], filename: str = None) -> str:
        """
        Export customer groups data to Excel with professional formatting
        
        Args:
            groups_data: List of group dictionaries with customer details
            filename: Optional filename, will generate if not provided
            
        Returns:
            str: Path to the generated Excel file
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"customer_groups_export_{timestamp}.xlsx"
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)
            
            self.workbook = xlsxwriter.Workbook(file_path, {'nan_inf_to_errors': True})
            self._create_formats()
            
            # Create summary worksheet
            self._create_summary_sheet(groups_data)
            
            # Create detailed groups worksheet
            self._create_detailed_sheet(groups_data)
            
            # Create customer details worksheet
            self._create_customer_details_sheet(groups_data)
            
            self.workbook.close()
            
            logger.info(f"Customer groups Excel export created: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error creating Excel export: {e}")
            if self.workbook:
                self.workbook.close()
            raise
    
    def _create_summary_sheet(self, groups_data: List[Dict]):
        """Create summary overview sheet"""
        worksheet = self.workbook.add_worksheet('Summary')
        
        # Title
        worksheet.write(0, 0, 'Customer Groups Summary Report', self.formats['title'])
        worksheet.write(1, 0, f'Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}', self.formats['data'])
        
        # Overall statistics
        total_groups = len(groups_data)
        total_customers = sum(g['customer_count'] for g in groups_data)
        total_ar = sum(g['total_ar_balance'] for g in groups_data)
        total_sales = sum(g.get('total_lifetime_sales', 0) for g in groups_data)
        
        row = 3
        worksheet.write(row, 0, 'Overall Statistics:', self.formats['summary_label'])
        row += 1
        worksheet.write(row, 0, 'Total Customer Groups:', self.formats['data'])
        worksheet.write(row, 1, total_groups, self.formats['integer'])
        row += 1
        worksheet.write(row, 0, 'Total Customers:', self.formats['data'])
        worksheet.write(row, 1, total_customers, self.formats['integer'])
        row += 1
        worksheet.write(row, 0, 'Total AR Balance:', self.formats['data'])
        worksheet.write(row, 1, total_ar, self.formats['summary_value'])
        row += 1
        worksheet.write(row, 0, 'Total Lifetime Sales:', self.formats['data'])
        worksheet.write(row, 1, total_sales, self.formats['summary_value'])
        
        # Top 10 groups by AR balance
        row += 3
        worksheet.write(row, 0, 'Top 10 Groups by AR Balance:', self.formats['summary_label'])
        row += 1
        
        headers = ['Group Name', 'Customers', 'AR Balance', 'Lifetime Sales', 'Last Payment', 'Last Sale']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, self.formats['header'])
        row += 1
        
        # Sort and show top 10
        sorted_groups = sorted(groups_data, key=lambda x: x['total_ar_balance'], reverse=True)[:10]
        
        for group in sorted_groups:
            worksheet.write(row, 0, group['group_name'], self.formats['data'])
            worksheet.write(row, 1, group['customer_count'], self.formats['integer'])
            worksheet.write(row, 2, group['total_ar_balance'], self.formats['money'])
            worksheet.write(row, 3, group.get('total_lifetime_sales', 0), self.formats['money'])
            
            # Last payment date
            last_payment = group.get('most_recent_payment_date')
            if last_payment and str(last_payment) != '1900-01-01':
                worksheet.write(row, 4, str(last_payment)[:10], self.formats['date'])
            else:
                worksheet.write(row, 4, 'None', self.formats['data'])
            
            # Last sale date
            last_sale = group.get('most_recent_sale_date')
            if last_sale and str(last_sale) != '1900-01-01':
                worksheet.write(row, 5, str(last_sale)[:10], self.formats['date'])
            else:
                worksheet.write(row, 5, 'None', self.formats['data'])
            
            row += 1
        
        # Auto-fit columns
        worksheet.set_column(0, 0, 25)  # Group Name
        worksheet.set_column(1, 1, 12)  # Customers
        worksheet.set_column(2, 3, 15)  # AR Balance, Sales
        worksheet.set_column(4, 5, 12)  # Dates
    
    def _create_detailed_sheet(self, groups_data: List[Dict]):
        """Create detailed groups sheet"""
        worksheet = self.workbook.add_worksheet('Group Details')
        
        # Title
        worksheet.write(0, 0, 'Detailed Customer Groups', self.formats['title'])
        
        # Headers
        headers = [
            'Group Name', 'Customer Count', 'Total AR Balance', 'Total Credit Limit',
            'Total Lifetime Sales', 'Most Recent Payment Date', 'Most Recent Sale Date',
            'Days Since Payment', 'Days Since Sale'
        ]
        
        row = 2
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, self.formats['header'])
        row += 1
        
        # Sort groups by AR balance
        sorted_groups = sorted(groups_data, key=lambda x: x['total_ar_balance'], reverse=True)
        
        for group in sorted_groups:
            worksheet.write(row, 0, group['group_name'], self.formats['data'])
            worksheet.write(row, 1, self._safe_number(group['customer_count']), self.formats['integer'])
            worksheet.write(row, 2, self._safe_number(group['total_ar_balance']), self.formats['money'])
            worksheet.write(row, 3, self._safe_number(group.get('total_credit_limit', 0)), self.formats['money'])
            worksheet.write(row, 4, self._safe_number(group.get('total_lifetime_sales', 0)), self.formats['money'])
            
            # Payment date
            payment_date = group.get('most_recent_payment_date')
            if payment_date and str(payment_date) != '1900-01-01':
                worksheet.write(row, 5, str(payment_date)[:10], self.formats['date'])
            else:
                worksheet.write(row, 5, 'None', self.formats['data'])
            
            # Sale date
            sale_date = group.get('most_recent_sale_date')
            if sale_date and str(sale_date) != '1900-01-01':
                worksheet.write(row, 6, str(sale_date)[:10], self.formats['date'])
            else:
                worksheet.write(row, 6, 'None', self.formats['data'])
            
            # Days since calculations
            worksheet.write(row, 7, self._calculate_days_since_payment(group), self.formats['integer'])
            worksheet.write(row, 8, self._calculate_days_since_sale(group), self.formats['integer'])
            
            row += 1
        
        # Auto-fit columns
        worksheet.set_column(0, 0, 25)  # Group Name
        worksheet.set_column(1, 1, 12)  # Count
        worksheet.set_column(2, 4, 15)  # Money columns
        worksheet.set_column(5, 6, 15)  # Dates
        worksheet.set_column(7, 8, 12)  # Days
    
    def _create_customer_details_sheet(self, groups_data: List[Dict]):
        """Create detailed customer information sheet"""
        worksheet = self.workbook.add_worksheet('Customer Details')
        
        # Title
        worksheet.write(0, 0, 'Individual Customer Details', self.formats['title'])
        
        # Headers
        headers = [
            'Group Name', 'Customer Name', 'Phone', 'Email', 'AR Balance', 'Credit Limit',
            'Last Payment Date', 'Last Payment Amount', 'Last Payment Comment',
            'Last Sale Date', 'Last Sale Amount', 'Last Sale Comment',
            'Days Since Payment', 'Days Since Sale'
        ]
        
        row = 2
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, self.formats['header'])
        row += 1
        
        # Sort groups by AR balance and iterate through customers
        sorted_groups = sorted(groups_data, key=lambda x: x['total_ar_balance'], reverse=True)
        
        for group in sorted_groups:
            customers = group.get('customers', [])
            customers.sort(key=lambda x: x.get('AccountBalance', 0), reverse=True)
            
            for customer in customers:
                worksheet.write(row, 0, group['group_name'], self.formats['data'])
                
                # Customer name
                if customer.get('Company'):
                    customer_name = customer['Company']
                else:
                    first = customer.get('FirstName', '') or ''
                    last = customer.get('LastName', '') or ''
                    customer_name = f"{first} {last}".strip()
                
                worksheet.write(row, 1, customer_name, self.formats['data'])
                worksheet.write(row, 2, customer.get('PhoneNumber', ''), self.formats['data'])
                worksheet.write(row, 3, customer.get('EmailAddress', ''), self.formats['data'])
                worksheet.write(row, 4, self._safe_number(customer.get('AccountBalance', 0)), self.formats['money'])
                worksheet.write(row, 5, self._safe_number(customer.get('CreditLimit', 0)), self.formats['money'])
                
                # Payment details
                last_payment_date = customer.get('LastPaymentDate')
                if last_payment_date and str(last_payment_date) != '1900-01-01':
                    worksheet.write(row, 6, str(last_payment_date)[:10], self.formats['date'])
                    worksheet.write(row, 7, self._safe_number(customer.get('LastPaymentAmount', 0)), self.formats['money'])
                    worksheet.write(row, 8, customer.get('LastPaymentComment', ''), self.formats['data'])
                else:
                    worksheet.write(row, 6, 'None', self.formats['data'])
                    worksheet.write(row, 7, 0, self.formats['money'])
                    worksheet.write(row, 8, '', self.formats['data'])
                
                # Sale details
                last_sale_date = customer.get('LastInvoiceDate')
                if last_sale_date and str(last_sale_date) != '1900-01-01':
                    worksheet.write(row, 9, str(last_sale_date)[:10], self.formats['date'])
                    worksheet.write(row, 10, self._safe_number(customer.get('LastInvoiceAmount', 0)), self.formats['money'])
                    worksheet.write(row, 11, customer.get('LastInvoiceComment', ''), self.formats['data'])
                else:
                    worksheet.write(row, 9, 'None', self.formats['data'])
                    worksheet.write(row, 10, 0, self.formats['money'])
                    worksheet.write(row, 11, '', self.formats['data'])
                
                # Days calculations
                worksheet.write(row, 12, self._safe_number(customer.get('DaysSinceLastPayment', 9999), 9999), self.formats['integer'])
                worksheet.write(row, 13, self._safe_number(customer.get('DaysSinceLastSale', 9999), 9999), self.formats['integer'])
                
                row += 1
        
        # Auto-fit columns
        worksheet.set_column(0, 1, 20)  # Group, Customer
        worksheet.set_column(2, 3, 15)  # Phone, Email
        worksheet.set_column(4, 5, 12)  # Money
        worksheet.set_column(6, 9, 12)  # Dates
        worksheet.set_column(7, 10, 12)  # Amounts
        worksheet.set_column(8, 11, 25)  # Comments
        worksheet.set_column(12, 13, 10)  # Days
    
    def _safe_number(self, value, default=0):
        """Safely convert value to number, handling NaN/None/inf"""
        try:
            if value is None or str(value).lower() in ['nan', 'inf', '-inf', 'none']:
                return default
            num = float(value)
            if not (-1e15 < num < 1e15):  # Check for reasonable range
                return default
            return num
        except (ValueError, TypeError, OverflowError):
            return default
    
    def _calculate_days_since_payment(self, group: Dict) -> int:
        """Calculate days since most recent payment for group"""
        payment_date = group.get('most_recent_payment_date')
        if payment_date and str(payment_date) != '1900-01-01':
            try:
                if isinstance(payment_date, str):
                    payment_dt = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
                else:
                    payment_dt = payment_date
                days = (datetime.now() - payment_dt).days
                return max(0, min(days, 9999))  # Reasonable bounds
            except:
                return 9999
        return 9999
    
    def _calculate_days_since_sale(self, group: Dict) -> int:
        """Calculate days since most recent sale for group"""
        sale_date = group.get('most_recent_sale_date')
        if sale_date and str(sale_date) != '1900-01-01':
            try:
                if isinstance(sale_date, str):
                    sale_dt = datetime.fromisoformat(sale_date.replace('Z', '+00:00'))
                else:
                    sale_dt = sale_date
                days = (datetime.now() - sale_dt).days
                return max(0, min(days, 9999))  # Reasonable bounds
            except:
                return 9999
        return 9999
