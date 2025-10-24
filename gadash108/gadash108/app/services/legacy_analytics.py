"""
Legacy Analytics Compatibility Layer for Georgia Dashboard v9.18
Preserves all original business logic while using new architecture
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

from database_pymssql import SQLServerConnection
from config.logging_config import analytics_logger


class LegacyAnalyticsService:
    """Compatibility layer that preserves all original business logic"""
    
    def __init__(self):
        self.db = SQLServerConnection()
        
    def get_executive_summary(self, period='today', custom_start=None, custom_end=None):
        """Get executive summary using original business logic"""
        try:
            if not self.db.connect():
                return {'error': 'Database not initialized'}
            
            # Calculate date range (original logic)
            if custom_start and custom_end:
                try:
                    start_date = datetime.strptime(custom_start, '%Y-%m-%d')
                    end_date = datetime.strptime(custom_end, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                except ValueError as e:
                    return {'error': 'Invalid date format. Use YYYY-MM-DD'}
            else:
                end_date = datetime.now()
                if period == 'today':
                    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                elif period == '7d':
                    start_date = end_date - timedelta(days=7)
                elif period == '30d':
                    start_date = end_date - timedelta(days=30)
                elif period == 'MTD':
                    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                elif period == 'YTD':
                    start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate comparison period
            period_duration = end_date - start_date
            comp_start = start_date - period_duration
            comp_end = start_date
            
            # Current period metrics (original query)
            current_query = """
            SELECT 
                COALESCE(SUM(t.Total), 0) as revenue,
                COUNT(DISTINCT t.TransactionNumber) as transactions,
                COUNT(DISTINCT t.CustomerID) as unique_customers,
                COALESCE(AVG(t.Total), 0) as avg_ticket
            FROM [dbo].[Transaction] t
            WHERE t.Time >= %s AND t.Time <= %s
            """
            
            current_result = self.db.execute_query(current_query, (start_date, end_date), "Current Period Metrics")
            comp_result = self.db.execute_query(current_query, (comp_start, comp_end), "Comparison Period Metrics")
            
            # Gross profit calculation (original logic with tobacco uplifts)
            profit_query = """
            SELECT 
                COALESCE(SUM(te.Price * te.Quantity - 
                    CASE 
                        WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                        WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                        ELSE te.Cost * te.Quantity
                    END), 0) as gross_profit,
                COALESCE(SUM(te.Price * te.Quantity), 0) as total_revenue
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE t.Time >= %s AND t.Time <= %s
            """
            
            current_profit = self.db.execute_query(profit_query, (start_date, end_date), "Current Period Profit")
            comp_profit = self.db.execute_query(profit_query, (comp_start, comp_end), "Comparison Period Profit")
            
            # AR metrics (original logic)
            ar_query = """
            SELECT 
                COALESCE(SUM(c.AccountBalance), 0) as ar_balance,
                COUNT(CASE WHEN c.AccountBalance > 0 THEN 1 END) as customers_with_balance
            FROM dbo.Customer c
            WHERE c.AccountBalance > 0
            """
            
            ar_result = self.db.execute_query(ar_query, description="AR Balance")
            
            # Inventory summary (original logic)
            inventory_query = """
            SELECT 
                COUNT(*) as total_items,
                SUM(CASE WHEN i.Quantity > 0 THEN 1 ELSE 0 END) as in_stock,
                SUM(CASE WHEN i.Quantity <= 0 THEN 1 ELSE 0 END) as out_of_stock,
                COALESCE(SUM(i.Quantity * i.Cost), 0) as inventory_value
            FROM dbo.Item i
            WHERE i.Inactive = 0
            """
            
            inventory_result = self.db.execute_query(inventory_query, description="Inventory Summary")
            
            # Format response (original format)
            response = {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
            
            # Current period data
            if not current_result.empty:
                current_row = current_result.iloc[0]
                response['sales'] = {
                    'total_revenue': float(current_row.get('revenue', 0) or 0),
                    'total_transactions': int(current_row.get('transactions', 0) or 0),
                    'unique_customers': int(current_row.get('unique_customers', 0) or 0),
                    'avg_transaction_value': float(current_row.get('avg_ticket', 0) or 0)
                }
            
            # Profit data
            if not current_profit.empty:
                profit_row = current_profit.iloc[0]
                response['profit'] = {
                    'gross_profit': float(profit_row.get('gross_profit', 0) or 0),
                    'total_revenue': float(profit_row.get('total_revenue', 0) or 0)
                }
                
                # Calculate GP percentage
                revenue = profit_row.get('total_revenue', 0) or 0
                if revenue > 0:
                    gp_percent = (profit_row.get('gross_profit', 0) or 0) / revenue * 100
                    response['profit']['gp_percentage'] = round(gp_percent, 2)
            
            # AR data
            if not ar_result.empty:
                ar_row = ar_result.iloc[0]
                response['accounts_receivable'] = {
                    'total_ar': float(ar_row.get('ar_balance', 0) or 0),
                    'customers_with_balance': int(ar_row.get('customers_with_balance', 0) or 0)
                }
            
            # Inventory data
            if not inventory_result.empty:
                inv_row = inventory_result.iloc[0]
                response['inventory'] = {
                    'total_items': int(inv_row.get('total_items', 0) or 0),
                    'in_stock_items': int(inv_row.get('in_stock', 0) or 0),
                    'out_of_stock_items': int(inv_row.get('out_of_stock', 0) or 0),
                    'total_value': float(inv_row.get('inventory_value', 0) or 0)
                }
            
            # Comparison data for trends
            if not comp_result.empty:
                comp_row = comp_result.iloc[0]
                current_revenue = response.get('sales', {}).get('total_revenue', 0)
                comp_revenue = float(comp_row.get('revenue', 0) or 0)
                
                if comp_revenue > 0:
                    revenue_change = ((current_revenue - comp_revenue) / comp_revenue) * 100
                    response['trends'] = {
                        'revenue_change_percent': round(revenue_change, 2),
                        'comparison_period': {
                            'start_date': comp_start.isoformat(),
                            'end_date': comp_end.isoformat(),
                            'revenue': comp_revenue
                        }
                    }
            
            analytics_logger.info(f"✅ Executive summary generated for period: {period}")
            return response
            
        except Exception as e:
            analytics_logger.error(f"❌ Error generating executive summary: {e}")
            return {'error': str(e)}
        finally:
            if self.db:
                self.db.close()
