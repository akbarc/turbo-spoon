"""
Core AR Management Module
Handles basic AR operations: balances, aging, statements, exports
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

class ARManager:
    """Core AR Management functionality"""
    
    def __init__(self):
        self.db = None
        
    def get_ar_summary(self) -> Dict:
        """Get high-level AR summary metrics"""
        try:
            with SQLServerConnection() as db:
                # Total AR
                total_ar_query = """
                SELECT 
                    COUNT(DISTINCT ID) as customer_count,
                    SUM(AccountBalance) as total_ar,
                    AVG(AccountBalance) as avg_ar,
                    MAX(AccountBalance) as max_ar
                FROM dbo.Customer
                WHERE AccountBalance > 0
                """
                total_ar_df = db.execute_query(total_ar_query)
                total_ar = total_ar_df.to_dict('records') if not total_ar_df.empty else []
                
                # Aging buckets
                aging_query = """
                SELECT 
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN Balance ELSE 0 END) as current_0_30,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) BETWEEN 31 AND 60 THEN Balance ELSE 0 END) as days_31_60,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) BETWEEN 61 AND 90 THEN Balance ELSE 0 END) as days_61_90,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 THEN Balance ELSE 0 END) as over_90,
                    COUNT(CASE WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN 1 END) as count_0_30,
                    COUNT(CASE WHEN DATEDIFF(day, Date, GETDATE()) BETWEEN 31 AND 60 THEN 1 END) as count_31_60,
                    COUNT(CASE WHEN DATEDIFF(day, Date, GETDATE()) BETWEEN 61 AND 90 THEN 1 END) as count_61_90,
                    COUNT(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 THEN 1 END) as count_over_90
                FROM dbo.AccountReceivable
                WHERE Balance > 0
                """
                aging_df = db.execute_query(aging_query)
                aging = aging_df.to_dict('records') if not aging_df.empty else []
                
                # Recent activity
                activity_query = """
                SELECT TOP 10
                    'Payment' as type,
                    p.Time as date,
                    c.Company,
                    p.Amount as amount,
                    p.Comment as description
                FROM dbo.Payment p
                INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
                WHERE p.Time >= DATEADD(day, -7, GETDATE())
                
                UNION ALL
                
                SELECT TOP 10
                    'Adjustment' as type,
                    ar.Date,
                    c.Company,
                    ar.OriginalAmount,
                    CASE 
                        WHEN ar.OriginalAmount = 65 THEN 'NSF Fee'
                        WHEN ar.OriginalAmount < 0 THEN 'Credit'
                        ELSE 'Adjustment'
                    END
                FROM dbo.AccountReceivable ar
                INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
                WHERE ar.TransactionNumber = 0
                    AND ar.Date >= DATEADD(day, -7, GETDATE())
                ORDER BY date DESC
                """
                activity = db.execute_query(activity_query)
                
                return {
                    'summary': total_ar[0] if total_ar and len(total_ar) > 0 else {'total_ar': 0, 'customer_count': 0},
                    'aging': aging[0] if aging and len(aging) > 0 else {'current_0_30': 0, 'days_31_60': 0, 'days_61_90': 0, 'over_90': 0},
                    'recent_activity': activity.to_dict('records') if not activity.empty else []
                }
                
        except Exception as e:
            logger.error(f"Error getting AR summary: {e}")
            return {'error': str(e)}
    
    def get_customer_ar_list(self, 
                             min_balance: float = 0,
                             days_overdue: Optional[int] = None,
                             sort_by: str = 'balance_desc') -> pd.DataFrame:
        """
        Get list of customers with AR details
        
        Args:
            min_balance: Minimum AR balance to include
            days_overdue: Filter by minimum days overdue
            sort_by: Sort order (balance_desc, balance_asc, days_desc, days_asc, name)
        """
        try:
            with SQLServerConnection() as db:
                query = """
                WITH CustomerAR AS (
                    SELECT 
                        c.ID,
                        c.Company,
                        c.FirstName,
                        c.LastName,
                        c.PhoneNumber,
                        c.AccountBalance,
                        c.CreditLimit,
                        c.LastVisit,
                        -- Calculate oldest unpaid invoice
                        (SELECT MIN(Date) FROM dbo.AccountReceivable 
                         WHERE CustomerID = c.ID AND Balance > 0) as OldestInvoiceDate,
                        -- Calculate weighted average days outstanding
                        (SELECT SUM(DATEDIFF(day, Date, GETDATE()) * Balance) / NULLIF(SUM(Balance), 0)
                         FROM dbo.AccountReceivable 
                         WHERE CustomerID = c.ID AND Balance > 0) as WeightedDaysOutstanding,
                        -- Get last payment date
                        (SELECT MAX(Time) FROM dbo.Payment WHERE CustomerID = c.ID) as LastPaymentDate,
                        -- Count open invoices
                        (SELECT COUNT(*) FROM dbo.AccountReceivable 
                         WHERE CustomerID = c.ID AND Balance > 0) as OpenInvoiceCount
                    FROM dbo.Customer c
                    WHERE c.AccountBalance > %s
                )
                SELECT 
                    ID,
                    COALESCE(Company, FirstName + ' ' + LastName, 'Unknown') as CustomerName,
                    PhoneNumber,
                    AccountBalance,
                    CreditLimit,
                    CASE 
                        WHEN CreditLimit > 0 THEN AccountBalance / CreditLimit * 100
                        ELSE NULL 
                    END as CreditUtilization,
                    OldestInvoiceDate,
                    DATEDIFF(day, OldestInvoiceDate, GETDATE()) as DaysOverdue,
                    WeightedDaysOutstanding,
                    LastPaymentDate,
                    DATEDIFF(day, LastPaymentDate, GETDATE()) as DaysSinceLastPayment,
                    OpenInvoiceCount,
                    LastVisit
                FROM CustomerAR
                WHERE 1=1
                """
                
                params = [min_balance]
                
                if days_overdue is not None:
                    query += " AND DATEDIFF(day, OldestInvoiceDate, GETDATE()) >= %s"
                    params.append(days_overdue)
                
                # Add sorting
                sort_mapping = {
                    'balance_desc': 'AccountBalance DESC',
                    'balance_asc': 'AccountBalance ASC',
                    'days_desc': 'DaysOverdue DESC',
                    'days_asc': 'DaysOverdue ASC',
                    'name': 'CustomerName ASC'
                }
                query += f" ORDER BY {sort_mapping.get(sort_by, 'AccountBalance DESC')}"
                
                return db.execute_query(query, params)
                
        except Exception as e:
            logger.error(f"Error getting customer AR list: {e}")
            return pd.DataFrame()
    
    def get_customer_ar_detail(self, customer_id: int) -> Dict:
        """Get detailed AR information for a specific customer"""
        try:
            with SQLServerConnection() as db:
                # Customer info - ALL FIELDS
                customer_query = """
                SELECT 
                    -- Primary identifiers
                    ID, AccountNumber, AccountTypeID, StoreID, HQID, GlobalCustomer,
                    
                    -- Name fields
                    FirstName, LastName, Company, Title,
                    COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
                    
                    -- Contact information
                    PhoneNumber, FaxNumber, EmailAddress,
                    
                    -- Address fields
                    Address, Address2, City, State, Zip, Country,
                    
                    -- Financial fields
                    AccountBalance, CreditLimit, TotalSales, TotalSavings, 
                    Vouchers, CurrentDiscount, PriceLevel, LastClosingBalance,
                    
                    -- Status flags
                    TaxExempt, TaxNumber, AssessFinanceCharges, LimitPurchase,
                    LayawayCustomer, Employee,
                    
                    -- Activity tracking
                    AccountOpened, LastVisit, TotalVisits, 
                    LastStartingDate, LastClosingDate, LastUpdated,
                    
                    -- References
                    CashierID, SalesRepID, PrimaryShipToID, DefaultShippingServiceID,
                    
                    -- Custom fields
                    CustomText1, CustomText2, CustomText3, CustomText4, CustomText5,
                    CustomNumber1, CustomNumber2, CustomNumber3, CustomNumber4, CustomNumber5,
                    CustomDate1, CustomDate2, CustomDate3, CustomDate4, CustomDate5,
                    
                    -- Other fields
                    Notes, PictureName
                FROM dbo.Customer
                WHERE ID = %s
                """
                customer_df = db.execute_query(customer_query, [customer_id])
                customer = customer_df.to_dict('records') if not customer_df.empty else []
                
                # Open invoices
                invoices_query = """
                SELECT 
                    ar.ID,
                    ar.Date,
                    ar.DueDate,
                    ar.OriginalAmount,
                    ar.Balance,
                    DATEDIFF(day, ar.Date, GETDATE()) as DaysOld,
                    CASE 
                        WHEN ar.TransactionNumber = 0 THEN 'Adjustment'
                        ELSE 'Invoice #' + CAST(ar.TransactionNumber as VARCHAR(20))
                    END as Reference,
                    CASE 
                        WHEN ar.OriginalAmount = 65 THEN 'NSF Fee'
                        WHEN ar.OriginalAmount < 0 THEN 'Credit'
                        WHEN ar.TransactionNumber = 0 THEN 'Manual Adjustment'
                        ELSE 'Sale'
                    END as Type,
                    arh.Comment as Notes
                FROM dbo.AccountReceivable ar
                LEFT JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
                WHERE ar.CustomerID = %s AND ar.Balance != 0
                ORDER BY ar.Date DESC
                """
                invoices = db.execute_query(invoices_query, [customer_id])
                
                # Recent payments
                payments_query = """
                SELECT TOP 20
                    ID,
                    Time as PaymentDate,
                    Amount,
                    Comment
                FROM dbo.Payment
                WHERE CustomerID = %s
                ORDER BY Time DESC
                """
                payments = db.execute_query(payments_query, [customer_id])
                
                # Recent transactions
                transactions_query = """
                SELECT TOP 20
                    TransactionNumber,
                    Time as TransactionDate,
                    Total,
                    SalesTax,
                    ReferenceNumber,
                    Comment
                FROM [dbo].[Transaction]
                WHERE CustomerID = %s
                ORDER BY Time DESC
                """
                transactions = db.execute_query(transactions_query, [customer_id])
                
                # Payment statistics
                stats_query = """
                WITH PaymentStats AS (
                    SELECT 
                        AVG(DATEDIFF(day, t.Time, p.Time)) as AvgDaysToPay,
                        MIN(DATEDIFF(day, t.Time, p.Time)) as MinDaysToPay,
                        MAX(DATEDIFF(day, t.Time, p.Time)) as MaxDaysToPay,
                        COUNT(*) as PaymentCount
                    FROM [dbo].[Transaction] t
                    INNER JOIN dbo.Payment p ON p.CustomerID = t.CustomerID
                        AND p.Time > t.Time
                        AND p.Time < DATEADD(day, 90, t.Time)
                    WHERE t.CustomerID = %s
                        AND t.Time > DATEADD(month, -12, GETDATE())
                )
                SELECT * FROM PaymentStats
                """
                stats_df = db.execute_query(stats_query, [customer_id])
                stats = stats_df.to_dict('records') if not stats_df.empty else []
                
                return {
                    'customer': customer[0] if customer else {},
                    'open_invoices': invoices.to_dict('records') if not invoices.empty else [],
                    'recent_payments': payments.to_dict('records') if not payments.empty else [],
                    'recent_transactions': transactions.to_dict('records') if not transactions.empty else [],
                    'payment_stats': stats[0] if stats else {}
                }
                
        except Exception as e:
            logger.error(f"Error getting customer AR detail: {e}")
            return {'error': str(e)}
    
    def get_aging_report(self, as_of_date: Optional[datetime] = None) -> pd.DataFrame:
        """Generate standard AR aging report"""
        try:
            with SQLServerConnection() as db:
                if as_of_date is None:
                    as_of_date = datetime.now()
                
                query = """
                SELECT 
                    c.ID as CustomerID,
                    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                    c.PhoneNumber,
                    c.CreditLimit,
                    SUM(ar.Balance) as TotalAR,
                    SUM(CASE WHEN DATEDIFF(day, ar.Date, %s) <= 30 THEN ar.Balance ELSE 0 END) as Current_0_30,
                    SUM(CASE WHEN DATEDIFF(day, ar.Date, %s) BETWEEN 31 AND 60 THEN ar.Balance ELSE 0 END) as Days_31_60,
                    SUM(CASE WHEN DATEDIFF(day, ar.Date, %s) BETWEEN 61 AND 90 THEN ar.Balance ELSE 0 END) as Days_61_90,
                    SUM(CASE WHEN DATEDIFF(day, ar.Date, %s) > 90 THEN ar.Balance ELSE 0 END) as Over_90,
                    MAX(ar.Date) as NewestInvoice,
                    MIN(ar.Date) as OldestInvoice,
                    COUNT(ar.ID) as InvoiceCount
                FROM dbo.Customer c
                INNER JOIN dbo.AccountReceivable ar ON c.ID = ar.CustomerID
                WHERE ar.Balance > 0
                GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.PhoneNumber, c.CreditLimit
                HAVING SUM(ar.Balance) > 0
                ORDER BY SUM(ar.Balance) DESC
                """
                
                params = [as_of_date, as_of_date, as_of_date, as_of_date]
                return db.execute_query(query, params)
                
        except Exception as e:
            logger.error(f"Error generating aging report: {e}")
            return pd.DataFrame()
    
    def export_ar_data(self, 
                       data_type: str = 'aging',
                       format: str = 'csv',
                       customer_id: Optional[int] = None) -> Tuple[bytes, str]:
        """
        Export AR data in CSV format
        
        Args:
            data_type: Type of data to export ('aging', 'detail', 'statement')
            format: Export format (only 'csv' for now)
            customer_id: Customer ID for customer-specific exports
            
        Returns:
            Tuple of (file_content, filename)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if data_type == 'aging':
                df = self.get_aging_report()
                filename = f'ar_aging_report_{timestamp}.csv'
                
            elif data_type == 'detail' and customer_id:
                data = self.get_customer_ar_detail(customer_id)
                # Convert invoices to DataFrame for CSV export
                df = pd.DataFrame(data['open_invoices'])
                customer_name = data['customer'].get('CustomerName', 'Unknown')
                # Clean customer name for filename
                customer_name = ''.join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f'ar_detail_{customer_name}_{timestamp}.csv'
                
            elif data_type == 'customers':
                df = self.get_customer_ar_list()
                filename = f'ar_customer_list_{timestamp}.csv'
                
            else:
                df = pd.DataFrame()
                filename = f'ar_export_{timestamp}.csv'
            
            if not df.empty:
                csv_content = df.to_csv(index=False).encode('utf-8')
                return csv_content, filename
            else:
                return b'', filename
                
        except Exception as e:
            logger.error(f"Error exporting AR data: {e}")
            return b'', 'error.csv'
    
    def calculate_dso(self, days: int = 30) -> float:
        """
        Calculate Days Sales Outstanding (DSO)
        
        DSO = (Average AR / Sales) * Days in Period
        """
        try:
            with SQLServerConnection() as db:
                query = """
                WITH Metrics AS (
                    SELECT 
                        SUM(c.AccountBalance) as total_ar,
                        (SELECT SUM(Total) FROM [dbo].[Transaction] 
                         WHERE Time >= DATEADD(day, -%s, GETDATE())
                         AND Total > 0) as total_sales
                    FROM dbo.Customer c
                    WHERE c.AccountBalance > 0
                )
                SELECT 
                    CASE 
                        WHEN total_sales > 0 THEN (total_ar / (total_sales / %s))
                        ELSE 0
                    END as dso
                FROM Metrics
                """
                
                result_df = db.execute_query(query, [days, days])
                if not result_df.empty:
                    return float(result_df.iloc[0]['dso'] or 0)
                return 0
                
        except Exception as e:
            logger.error(f"Error calculating DSO: {e}")
            return 0
    
    def get_collection_metrics(self, period_days: int = 30) -> Dict:
        """Get collection performance metrics for the period"""
        try:
            with SQLServerConnection() as db:
                query = """
                WITH PeriodMetrics AS (
                    SELECT 
                        -- New charges
                        (SELECT SUM(Total) FROM [dbo].[Transaction] 
                         WHERE Time >= DATEADD(day, -%s, GETDATE())) as new_charges,
                        
                        -- Payments received
                        (SELECT SUM(Amount) FROM dbo.Payment 
                         WHERE Time >= DATEADD(day, -%s, GETDATE())) as payments_received,
                        
                        -- Adjustments
                        (SELECT SUM(OriginalAmount) FROM dbo.AccountReceivable 
                         WHERE Date >= DATEADD(day, -%s, GETDATE()) 
                         AND TransactionNumber = 0) as adjustments,
                        
                        -- NSF fees
                        (SELECT COUNT(*) * 65 FROM dbo.AccountReceivable 
                         WHERE Date >= DATEADD(day, -%s, GETDATE()) 
                         AND OriginalAmount = 65 
                         AND TransactionNumber = 0) as nsf_fees,
                        
                        -- Unique customers who paid
                        (SELECT COUNT(DISTINCT CustomerID) FROM dbo.Payment 
                         WHERE Time >= DATEADD(day, -%s, GETDATE())) as customers_paid,
                        
                        -- Total customers with AR
                        (SELECT COUNT(*) FROM dbo.Customer WHERE AccountBalance > 0) as customers_with_ar
                )
                SELECT 
                    new_charges,
                    payments_received,
                    adjustments,
                    nsf_fees,
                    customers_paid,
                    customers_with_ar,
                    CASE 
                        WHEN new_charges > 0 THEN (payments_received / new_charges) * 100
                        ELSE 0 
                    END as collection_rate
                FROM PeriodMetrics
                """
                
                params = [period_days] * 5
                result_df = db.execute_query(query, params)
                if not result_df.empty:
                    return result_df.iloc[0].to_dict()
                return {}
                
        except Exception as e:
            logger.error(f"Error getting collection metrics: {e}")
            return {}