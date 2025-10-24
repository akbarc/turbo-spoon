"""
Enhanced Customer Detail API
Provides comprehensive customer analytics including sales, products, patterns, and AR
Updated with validated balance calculation methodology
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_pymssql import SQLServerConnection
from datetime import datetime, timedelta
import pandas as pd
import logging
from modules.customer_balance_engine import customer_balance_engine

logger = logging.getLogger(__name__)

class CustomerDetailAPI:
    """Comprehensive customer detail analytics with validated balance calculation"""
    
    def get_current_balance(self, customer_id: int):
        """Get current customer balance using validated methodology"""
        return customer_balance_engine.get_current_balance(customer_id)
    
    def get_customer_360(self, customer_id: int):
        """Get complete 360-degree view of customer"""
        try:
            with SQLServerConnection() as db:
                # Get validated balance information
                balance_data = customer_balance_engine.get_customer_balance_comprehensive(customer_id)
                
                result = {
                    'customer': self._get_customer_info(db, customer_id),
                    'account_details': self._get_account_details(db, customer_id),
                    'balance_comprehensive': balance_data,  # NEW: Validated balance data
                    'sales_summary': self._get_sales_summary(db, customer_id),
                    'purchase_patterns': self._get_purchase_patterns(db, customer_id),
                    'top_products': self._get_top_products(db, customer_id),
                    'payment_history': self._get_payment_history(db, customer_id),
                    'visit_frequency': self._get_visit_frequency(db, customer_id),
                    'category_preferences': self._get_category_preferences(db, customer_id),
                    'profit_analysis': self._get_profit_analysis(db, customer_id),
                    'open_invoices': self._get_open_invoices(db, customer_id),
                    'nsf_history': self._get_nsf_history(db, customer_id),
                    'trends': self._get_customer_trends(db, customer_id),
                    'loyalty_metrics': self._get_loyalty_metrics(db, customer_id),
                    'recent_transactions': self._get_recent_transactions(db, customer_id),
                    'notes_alerts': self._get_notes_alerts(db, customer_id)
                }
                return result
        except Exception as e:
            logger.error(f"Error getting customer 360: {e}")
            raise
    
    def _get_customer_info(self, db, customer_id):
        """Get basic customer information"""
        query = """
        SELECT 
            c.ID,
            c.Company,
            c.FirstName,
            c.LastName,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as DisplayName,
            c.PhoneNumber,
            c.Address,
            c.City,
            c.State,
            c.Zip,
            c.AccountBalance as LegacyAccountBalance,  -- UPDATED: Mark as legacy
            c.CreditLimit,
            c.AccountOpened,
            c.LastUpdated,
            c.TaxExempt,
            -- Calculate customer lifetime
            DATEDIFF(month, c.AccountOpened, GETDATE()) as MonthsAsCustomer,
            -- Get last visit
            (SELECT TOP 1 Time FROM [dbo].[Transaction] WHERE CustomerID = c.ID ORDER BY Time DESC) as LastVisit,
            -- Get total transactions
            (SELECT COUNT(*) FROM [dbo].[Transaction] WHERE CustomerID = c.ID) as TotalTransactions
        FROM dbo.Customer c
        WHERE c.ID = %s
        """
        result = db.execute_query(query, (customer_id,))
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
    
    def _get_sales_summary(self, db, customer_id):
        """Get sales summary statistics"""
        query = """
        SELECT 
            COUNT(DISTINCT t.TransactionNumber) as total_transactions,
            COUNT(DISTINCT CAST(t.Time AS DATE)) as days_with_purchases,
            SUM(t.Total) as lifetime_sales,
            AVG(t.Total) as avg_transaction,
            MAX(t.Total) as largest_transaction,
            MIN(t.Total) as smallest_transaction,
            -- Last 30 days
            SUM(CASE WHEN t.Time >= DATEADD(day, -30, GETDATE()) THEN t.Total ELSE 0 END) as sales_30d,
            COUNT(CASE WHEN t.Time >= DATEADD(day, -30, GETDATE()) THEN 1 ELSE NULL END) as transactions_30d,
            -- Last 90 days
            SUM(CASE WHEN t.Time >= DATEADD(day, -90, GETDATE()) THEN t.Total ELSE 0 END) as sales_90d,
            COUNT(CASE WHEN t.Time >= DATEADD(day, -90, GETDATE()) THEN 1 ELSE NULL END) as transactions_90d,
            -- YTD
            SUM(CASE WHEN YEAR(t.Time) = YEAR(GETDATE()) THEN t.Total ELSE 0 END) as sales_ytd,
            COUNT(CASE WHEN YEAR(t.Time) = YEAR(GETDATE()) THEN 1 ELSE NULL END) as transactions_ytd
        FROM [dbo].[Transaction] t
        WHERE t.CustomerID = %s
        """
        result = db.execute_query(query, (customer_id,))
        if not result.empty:
            return result.iloc[0].to_dict()
        return {}
    
    def _get_purchase_patterns(self, db, customer_id):
        """Analyze purchase patterns"""
        query = """
        SELECT 
            -- Day of week analysis
            DATENAME(weekday, t.Time) as DayOfWeek,
            COUNT(*) as Transactions,
            AVG(t.Total) as AvgSpend,
            SUM(t.Total) as TotalSpend
        FROM [dbo].[Transaction] t
        WHERE t.CustomerID = %s
            AND t.Time >= DATEADD(month, -6, GETDATE())
        GROUP BY DATENAME(weekday, t.Time), DATEPART(weekday, t.Time)
        ORDER BY DATEPART(weekday, t.Time)
        """
        day_patterns = db.execute_query(query, (customer_id,))
        
        # Time of day analysis
        query2 = """
        SELECT 
            CASE 
                WHEN DATEPART(hour, t.Time) < 6 THEN 'Early Morning'
                WHEN DATEPART(hour, t.Time) < 12 THEN 'Morning'
                WHEN DATEPART(hour, t.Time) < 17 THEN 'Afternoon'
                WHEN DATEPART(hour, t.Time) < 21 THEN 'Evening'
                ELSE 'Night'
            END as TimeOfDay,
            COUNT(*) as Transactions,
            AVG(t.Total) as AvgSpend
        FROM [dbo].[Transaction] t
        WHERE t.CustomerID = %s
            AND t.Time >= DATEADD(month, -6, GETDATE())
        GROUP BY CASE 
                WHEN DATEPART(hour, t.Time) < 6 THEN 'Early Morning'
                WHEN DATEPART(hour, t.Time) < 12 THEN 'Morning'
                WHEN DATEPART(hour, t.Time) < 17 THEN 'Afternoon'
                WHEN DATEPART(hour, t.Time) < 21 THEN 'Evening'
                ELSE 'Night'
            END
        """
        time_patterns = db.execute_query(query2, (customer_id,))
        
        return {
            'by_day': day_patterns.to_dict('records') if not day_patterns.empty else [],
            'by_time': time_patterns.to_dict('records') if not time_patterns.empty else []
        }
    
    def _get_top_products(self, db, customer_id):
        """Get customer's top purchased products"""
        query = """
        SELECT TOP 20
            i.ItemLookupCode,
            i.Description,
            i.DepartmentID,
            d.Name as Department,
            COUNT(te.ID) as PurchaseCount,
            SUM(te.Quantity) as TotalQuantity,
            SUM(te.Price * te.Quantity) as TotalSpent,
            AVG(te.Price) as AvgPrice,
            MAX(t.Time) as LastPurchased
        FROM [dbo].[Transaction] t
        INNER JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Department d ON i.DepartmentID = d.ID
        WHERE t.CustomerID = %s
        GROUP BY i.ItemLookupCode, i.Description, i.DepartmentID, d.Name
        ORDER BY TotalSpent DESC
        """
        result = db.execute_query(query, (customer_id,))
        return result.to_dict('records') if not result.empty else []
    
    def _get_payment_history(self, db, customer_id):
        """Get payment history"""
        query = """
        SELECT TOP 50
            p.Time as PaymentDate,
            p.Amount,
            p.Comment,
            CASE 
                WHEN UPPER(p.Comment) LIKE '%%NSF%%' THEN 'NSF'
                WHEN UPPER(p.Comment) LIKE '%%RETURN%%' THEN 'Returned'
                WHEN p.Amount > 0 THEN 'Payment'
                ELSE 'Credit'
            END as Type
        FROM dbo.Payment p
        WHERE p.CustomerID = %s
        ORDER BY p.Time DESC
        """
        result = db.execute_query(query, (customer_id,))
        return result.to_dict('records') if not result.empty else []
    
    def _get_visit_frequency(self, db, customer_id):
        """Analyze visit frequency"""
        query = """
        WITH VisitDates AS (
            SELECT DISTINCT CAST(Time AS DATE) as VisitDate
            FROM [dbo].[Transaction]
            WHERE CustomerID = %s
                AND Time >= DATEADD(month, -6, GETDATE())
        ),
        VisitGaps AS (
            SELECT 
                VisitDate,
                LAG(VisitDate) OVER (ORDER BY VisitDate) as PrevVisit,
                DATEDIFF(day, LAG(VisitDate) OVER (ORDER BY VisitDate), VisitDate) as DaysSinceLastVisit
            FROM VisitDates
        )
        SELECT 
            COUNT(*) as TotalVisits,
            AVG(DaysSinceLastVisit) as AvgDaysBetweenVisits,
            MIN(DaysSinceLastVisit) as MinDaysBetween,
            MAX(DaysSinceLastVisit) as MaxDaysBetween,
            CASE 
                WHEN AVG(DaysSinceLastVisit) <= 7 THEN 'Weekly'
                WHEN AVG(DaysSinceLastVisit) <= 14 THEN 'Bi-Weekly'
                WHEN AVG(DaysSinceLastVisit) <= 30 THEN 'Monthly'
                ELSE 'Occasional'
            END as VisitPattern
        FROM VisitGaps
        WHERE DaysSinceLastVisit IS NOT NULL
        """
        result = db.execute_query(query, (customer_id,))
        if not result.empty:
            return result.iloc[0].to_dict()
        return {}
    
    def _get_category_preferences(self, db, customer_id):
        """Get category purchase preferences"""
        query = """
        SELECT TOP 10
            ISNULL(d.Name, 'Uncategorized') as Category,
            COUNT(DISTINCT i.ID) as UniqueProducts,
            SUM(te.Quantity) as TotalUnits,
            SUM(te.Price * te.Quantity) as TotalSpent,
            COUNT(te.ID) as PurchaseCount,
            CAST(100.0 * SUM(te.Price * te.Quantity) / 
                (SELECT SUM(Total) FROM [dbo].[Transaction] WHERE CustomerID = %s) 
                AS DECIMAL(5,2)) as PercentOfSpend
        FROM [dbo].[Transaction] t
        INNER JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Department d ON i.DepartmentID = d.ID
        WHERE t.CustomerID = %s
        GROUP BY d.Name
        ORDER BY TotalSpent DESC
        """
        result = db.execute_query(query, (customer_id, customer_id))
        return result.to_dict('records') if not result.empty else []
    
    def _get_profit_analysis(self, db, customer_id):
        """Get profit analysis for customer"""
        query = """
        SELECT 
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(te.Quantity * ISNULL(i.Cost, 0)) as TotalCost,
            SUM(te.Price * te.Quantity - te.Quantity * ISNULL(i.Cost, 0)) as GrossProfit,
            CASE 
                WHEN SUM(te.Price * te.Quantity) > 0 
                THEN CAST(100.0 * SUM(te.Price * te.Quantity - te.Quantity * ISNULL(i.Cost, 0)) / 
                    SUM(te.Price * te.Quantity) AS DECIMAL(5,2))
                ELSE 0 
            END as GrossProfitMargin,
            -- Last 30 days
            SUM(CASE WHEN t.Time >= DATEADD(day, -30, GETDATE()) 
                THEN te.Price * te.Quantity - te.Quantity * ISNULL(i.Cost, 0) 
                ELSE 0 END) as Profit30Days,
            -- Last 90 days
            SUM(CASE WHEN t.Time >= DATEADD(day, -90, GETDATE()) 
                THEN te.Price * te.Quantity - te.Quantity * ISNULL(i.Cost, 0) 
                ELSE 0 END) as Profit90Days
        FROM [dbo].[Transaction] t
        INNER JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN dbo.Item i ON te.ItemID = i.ID
        WHERE t.CustomerID = %s
        """
        result = db.execute_query(query, (customer_id,))
        if not result.empty:
            return result.iloc[0].to_dict()
        return {}
    
    def _get_open_invoices(self, db, customer_id):
        """Get open AR invoices"""
        query = """
        SELECT 
            ar.Date,
            ar.Reference,
            ar.Type,
            ar.OriginalAmount,
            ar.Balance,
            DATEDIFF(day, ar.Date, GETDATE()) as DaysOld,
            CASE 
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN 'Current'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 Days'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 Days'
                ELSE 'Over 90 Days'
            END as AgingBucket
        FROM dbo.AccountReceivable ar
        WHERE ar.CustomerID = %s
            AND ar.Balance > 0
        ORDER BY ar.Date DESC
        """
        result = db.execute_query(query, (customer_id,))
        return result.to_dict('records') if not result.empty else []
    
    def _get_nsf_history(self, db, customer_id):
        """Get NSF/returned check history"""
        query = """
        SELECT 
            p.Time as Date,
            p.Amount,
            p.Comment,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM dbo.Payment p2 
                    WHERE p2.CustomerID = p.CustomerID 
                    AND p2.Time > p.Time 
                    AND p2.Amount >= p.Amount * 0.9
                    AND UPPER(p2.Comment) NOT LIKE '%%NSF%%'
                ) THEN 'Recovered'
                ELSE 'Outstanding'
            END as Status
        FROM dbo.Payment p
        WHERE p.CustomerID = %s
            AND (UPPER(p.Comment) LIKE '%%NSF%%' 
                OR UPPER(p.Comment) LIKE '%%RETURN%%'
                OR UPPER(p.Comment) LIKE '%%BOUNCE%%')
        ORDER BY p.Time DESC
        """
        result = db.execute_query(query, (customer_id,))
        return result.to_dict('records') if not result.empty else []
    
    def _get_customer_trends(self, db, customer_id):
        """Get customer trends over time"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            COUNT(*) as Transactions,
            SUM(t.Total) as Sales,
            AVG(t.Total) as AvgTransaction
        FROM [dbo].[Transaction] t
        WHERE t.CustomerID = %s
            AND t.Time >= DATEADD(month, -12, GETDATE())
        GROUP BY YEAR(t.Time), MONTH(t.Time)
        ORDER BY Year, Month
        """
        result = db.execute_query(query, (customer_id,))
        return result.to_dict('records') if not result.empty else []
    
    def _get_account_details(self, db, customer_id):
        """Get detailed account information"""
        query = """
        SELECT 
            c.*,
            -- Account status
            CASE 
                WHEN c.AccountBalance = 0 THEN 'Clear'
                WHEN c.AccountBalance > c.CreditLimit THEN 'Over Limit'
                WHEN c.AccountBalance > c.CreditLimit * 0.8 THEN 'Near Limit'
                ELSE 'Good Standing'
            END as AccountStatus,
            -- Credit utilization
            CASE 
                WHEN c.CreditLimit > 0 
                THEN CAST(100.0 * c.AccountBalance / c.CreditLimit AS DECIMAL(5,2))
                ELSE NULL
            END as CreditUtilization,
            -- Payment status
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM dbo.Payment 
                    WHERE CustomerID = c.ID 
                    AND Time >= DATEADD(day, -30, GETDATE())
                ) THEN 'Active'
                WHEN EXISTS (
                    SELECT 1 FROM dbo.Payment 
                    WHERE CustomerID = c.ID 
                    AND Time >= DATEADD(day, -90, GETDATE())
                ) THEN 'Slow'
                ELSE 'Inactive'
            END as PaymentStatus,
            -- Additional flags
            c.TaxExempt,
            c.EmailAddress,
            c.PriceLevel,
            c.GlobalDiscount,
            c.StoreCredit,
            -- Custom fields that might exist
            c.CustomText1,
            c.CustomText2,
            c.CustomText3,
            c.CustomNumber1,
            c.CustomNumber2,
            c.CustomDate1,
            c.CustomDate2
        FROM dbo.Customer c
        WHERE c.ID = %s
        """
        result = db.execute_query(query, (customer_id,))
        if not result.empty:
            return result.iloc[0].to_dict()
        return {}
    
    def _get_loyalty_metrics(self, db, customer_id):
        """Calculate customer loyalty metrics"""
        query = """
        WITH CustomerMetrics AS (
            SELECT 
                c.ID,
                c.AccountOpened,
                -- Calculate customer lifetime value
                (SELECT SUM(Total) FROM [dbo].[Transaction] WHERE CustomerID = c.ID) as LifetimeValue,
                -- Calculate average monthly spend
                (SELECT SUM(Total) / NULLIF(COUNT(DISTINCT YEAR(Time) * 12 + MONTH(Time)), 0)
                 FROM [dbo].[Transaction] 
                 WHERE CustomerID = c.ID) as AvgMonthlySpend,
                -- Calculate retention score (based on consistency of purchases)
                (SELECT COUNT(DISTINCT YEAR(Time) * 12 + MONTH(Time))
                 FROM [dbo].[Transaction] 
                 WHERE CustomerID = c.ID 
                 AND Time >= DATEADD(year, -1, GETDATE())) as ActiveMonths,
                -- Last purchase recency
                DATEDIFF(day, 
                    (SELECT MAX(Time) FROM [dbo].[Transaction] WHERE CustomerID = c.ID),
                    GETDATE()) as DaysSinceLastPurchase
            FROM dbo.Customer c
            WHERE c.ID = %s
        )
        SELECT 
            LifetimeValue,
            AvgMonthlySpend,
            ActiveMonths,
            DaysSinceLastPurchase,
            CASE 
                WHEN ActiveMonths >= 10 AND DaysSinceLastPurchase <= 30 THEN 'Loyal'
                WHEN ActiveMonths >= 6 AND DaysSinceLastPurchase <= 60 THEN 'Regular'
                WHEN DaysSinceLastPurchase <= 90 THEN 'Occasional'
                WHEN DaysSinceLastPurchase <= 180 THEN 'At Risk'
                ELSE 'Churned'
            END as LoyaltyStatus,
            CAST(ActiveMonths * 100.0 / 12 AS DECIMAL(5,2)) as RetentionScore
        FROM CustomerMetrics
        """
        result = db.execute_query(query, (customer_id,))
        if not result.empty:
            return result.iloc[0].to_dict()
        return {}
    
    def _get_recent_transactions(self, db, customer_id):
        """Get recent transaction details"""
        query = """
        SELECT TOP 10
            t.TransactionNumber,
            t.Time,
            t.Total,
            t.SubTotal,
            t.Tax,
            t.Comment,
            CASE 
                WHEN t.Comment LIKE '%delivery%' THEN 'Delivery'
                WHEN t.Comment LIKE '%pick%' THEN 'Pickup'
                ELSE 'In-Store'
            END as TransactionType,
            -- Get item count
            (SELECT COUNT(*) FROM dbo.TransactionEntry WHERE TransactionNumber = t.TransactionNumber) as ItemCount,
            -- Get top items in transaction
            STUFF((
                SELECT TOP 3 ', ' + i.Description
                FROM dbo.TransactionEntry te
                INNER JOIN dbo.Item i ON te.ItemID = i.ID
                WHERE te.TransactionNumber = t.TransactionNumber
                ORDER BY te.Price * te.Quantity DESC
                FOR XML PATH('')
            ), 1, 2, '') as TopItems
        FROM [dbo].[Transaction] t
        WHERE t.CustomerID = %s
        ORDER BY t.Time DESC
        """
        result = db.execute_query(query, (customer_id,))
        return result.to_dict('records') if not result.empty else []
    
    def _get_notes_alerts(self, db, customer_id):
        """Get customer notes and alerts"""
        notes = []
        
        # Check for NSF history
        nsf_check = """
        SELECT COUNT(*) as NSFCount
        FROM dbo.Payment
        WHERE CustomerID = %s
            AND (UPPER(Comment) LIKE '%%NSF%%' OR UPPER(Comment) LIKE '%%RETURN%%')
        """
        nsf_result = db.execute_query(nsf_check, (customer_id,))
        if not nsf_result.empty and nsf_result.iloc[0]['NSFCount'] > 0:
            notes.append({
                'type': 'alert',
                'severity': 'high',
                'message': f"Customer has {nsf_result.iloc[0]['NSFCount']} NSF/returned checks on record"
            })
        
        # Check for overdue balance
        overdue_check = """
        SELECT 
            SUM(Balance) as OverdueAmount,
            MIN(Date) as OldestInvoice,
            DATEDIFF(day, MIN(Date), GETDATE()) as MaxDaysOverdue
        FROM dbo.AccountReceivable
        WHERE CustomerID = %s
            AND Balance > 0
            AND DATEDIFF(day, Date, GETDATE()) > 30
        """
        overdue_result = db.execute_query(overdue_check, (customer_id,))
        if not overdue_result.empty and overdue_result.iloc[0]['OverdueAmount']:
            notes.append({
                'type': 'alert',
                'severity': 'medium',
                'message': f"${overdue_result.iloc[0]['OverdueAmount']:.2f} overdue for {overdue_result.iloc[0]['MaxDaysOverdue']} days"
            })
        
        # Check for high-value customer
        value_check = """
        SELECT SUM(Total) as YearlySpend
        FROM [dbo].[Transaction]
        WHERE CustomerID = %s
            AND Time >= DATEADD(year, -1, GETDATE())
        """
        value_result = db.execute_query(value_check, (customer_id,))
        if not value_result.empty and value_result.iloc[0]['YearlySpend'] > 10000:
            notes.append({
                'type': 'info',
                'severity': 'positive',
                'message': f"VIP Customer - ${value_result.iloc[0]['YearlySpend']:.2f} spent in last year"
            })
        
        return notes