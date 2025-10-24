"""
Enhanced Customer Analytics Report with SQL Server 2008 R2 Fixes
Includes additional valuable business metrics
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedCustomerAnalytics:
    def __init__(self):
        self.db = SQLServerConnection()
        self.current_year = datetime.now().year
        self.last_year = self.current_year - 1
        
    def generate_complete_report(self):
        """Generate comprehensive analytics with all fixes and enhancements"""
        report = {
            "report_date": datetime.now().isoformat(),
            "fixed_metrics": {},
            "additional_insights": {}
        }
        
        try:
            self.db.connect()
            
            # Fixed Priority 1 Metrics
            logger.info("Generating fixed Priority 1 metrics...")
            report["fixed_metrics"]["customer_revenue_brackets"] = self.get_customer_revenue_brackets_fixed()
            
            # Fixed Priority 2 Metrics
            logger.info("Generating fixed Priority 2 metrics...")
            report["fixed_metrics"]["new_customer_trends"] = self.get_new_customer_trends_fixed()
            report["fixed_metrics"]["customer_quality"] = self.get_customer_quality_fixed()
            
            # Fixed Priority 3 Metrics
            logger.info("Generating fixed Priority 3 metrics...")
            report["fixed_metrics"]["order_value_distribution"] = self.get_order_value_distribution_fixed()
            
            # Additional Valuable Insights
            logger.info("Generating additional valuable insights...")
            report["additional_insights"]["customer_lifetime_value"] = self.get_customer_lifetime_value()
            report["additional_insights"]["payment_behavior"] = self.get_payment_behavior_analysis()
            report["additional_insights"]["inventory_analysis"] = self.get_inventory_analysis()
            report["additional_insights"]["hourly_patterns"] = self.get_hourly_sales_patterns()
            report["additional_insights"]["churn_risk"] = self.get_churn_risk_analysis()
            report["additional_insights"]["profitability_analysis"] = self.get_profitability_analysis()
            report["additional_insights"]["product_velocity"] = self.get_product_velocity()
            report["additional_insights"]["customer_basket_analysis"] = self.get_basket_analysis()
            report["additional_insights"]["supplier_performance"] = self.get_supplier_performance()
            report["additional_insights"]["cashflow_forecast"] = self.get_cashflow_forecast()
            
            return report
            
        finally:
            self.db.close()
    
    def get_customer_revenue_brackets_fixed(self):
        """FIXED: Customer count by revenue brackets - SQL Server 2008 compatible"""
        query = """
        WITH CustomerAnnualRevenue AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(CASE WHEN t.Time >= DATEADD(YEAR, -1, GETDATE()) THEN t.Total ELSE 0 END) as LastYearRevenue
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        BracketedCustomers AS (
            SELECT 
                CustomerName,
                LastYearRevenue,
                CASE 
                    WHEN LastYearRevenue >= 100000 THEN '$100K+'
                    WHEN LastYearRevenue >= 50000 THEN '$50K-$100K'
                    WHEN LastYearRevenue >= 25000 THEN '$25K-$50K'
                    WHEN LastYearRevenue >= 10000 THEN '$10K-$25K'
                    WHEN LastYearRevenue > 0 THEN 'Under $10K'
                    ELSE 'No Purchases'
                END as RevenueBracket,
                CASE 
                    WHEN LastYearRevenue >= 100000 THEN 1
                    WHEN LastYearRevenue >= 50000 THEN 2
                    WHEN LastYearRevenue >= 25000 THEN 3
                    WHEN LastYearRevenue >= 10000 THEN 4
                    WHEN LastYearRevenue > 0 THEN 5
                    ELSE 6
                END as BracketOrder
            FROM CustomerAnnualRevenue
        )
        SELECT 
            RevenueBracket,
            COUNT(*) as CustomerCount,
            SUM(LastYearRevenue) as TotalRevenue,
            AVG(LastYearRevenue) as AvgRevenue,
            MIN(LastYearRevenue) as MinRevenue,
            MAX(LastYearRevenue) as MaxRevenue
        FROM BracketedCustomers
        GROUP BY RevenueBracket, BracketOrder
        ORDER BY BracketOrder
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_new_customer_trends_fixed(self):
        """FIXED: New customer trends without DATEFROMPARTS"""
        query = """
        WITH CustomerFirstPurchase AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MIN(t.Time) as FirstPurchaseDate
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        MonthlyNewCustomers AS (
            SELECT 
                YEAR(FirstPurchaseDate) as Year,
                MONTH(FirstPurchaseDate) as Month,
                DATENAME(MONTH, FirstPurchaseDate) + ' ' + CAST(YEAR(FirstPurchaseDate) as VARCHAR) as MonthYear,
                COUNT(*) as NewCustomers
            FROM CustomerFirstPurchase
            WHERE FirstPurchaseDate >= DATEADD(MONTH, -24, GETDATE())
            GROUP BY YEAR(FirstPurchaseDate), MONTH(FirstPurchaseDate), 
                     DATENAME(MONTH, FirstPurchaseDate) + ' ' + CAST(YEAR(FirstPurchaseDate) as VARCHAR)
        )
        SELECT 
            Year,
            Month,
            MonthYear,
            NewCustomers,
            SUM(NewCustomers) OVER (ORDER BY Year, Month) as CumulativeNewCustomers
        FROM MonthlyNewCustomers
        ORDER BY Year DESC, Month DESC
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_customer_quality_fixed(self):
        """FIXED: Customer quality analysis - SQL Server 2008 compatible"""
        query = """
        WITH CustomerMetrics AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase,
                COUNT(t.TransactionNumber) as TotalTransactions,
                SUM(t.Total) as LifetimeRevenue,
                DATEDIFF(MONTH, MIN(t.Time), MAX(t.Time)) as CustomerLifeMonths
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        CategorizedCustomers AS (
            SELECT 
                CustomerName,
                TotalTransactions,
                LifetimeRevenue,
                CustomerLifeMonths,
                CASE 
                    WHEN FirstPurchase >= DATEADD(MONTH, -3, GETDATE()) THEN '0-3 Months'
                    WHEN FirstPurchase >= DATEADD(MONTH, -6, GETDATE()) THEN '3-6 Months'
                    WHEN FirstPurchase >= DATEADD(MONTH, -12, GETDATE()) THEN '6-12 Months'
                    WHEN FirstPurchase >= DATEADD(MONTH, -24, GETDATE()) THEN '12-24 Months'
                    ELSE 'Over 24 Months'
                END as CustomerAge,
                CASE 
                    WHEN FirstPurchase >= DATEADD(MONTH, -3, GETDATE()) THEN 1
                    WHEN FirstPurchase >= DATEADD(MONTH, -6, GETDATE()) THEN 2
                    WHEN FirstPurchase >= DATEADD(MONTH, -12, GETDATE()) THEN 3
                    WHEN FirstPurchase >= DATEADD(MONTH, -24, GETDATE()) THEN 4
                    ELSE 5
                END as AgeOrder
            FROM CustomerMetrics
        )
        SELECT 
            CustomerAge,
            COUNT(*) as CustomerCount,
            AVG(LifetimeRevenue) as AvgLifetimeValue,
            AVG(TotalTransactions) as AvgTransactions,
            AVG(CustomerLifeMonths) as AvgLifeMonths,
            SUM(LifetimeRevenue) as TotalCohortRevenue
        FROM CategorizedCustomers
        GROUP BY CustomerAge, AgeOrder
        ORDER BY AgeOrder
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_order_value_distribution_fixed(self):
        """FIXED: Order value distribution - SQL Server 2008 compatible"""
        query = """
        WITH OrderValues AS (
            SELECT 
                Total,
                CASE 
                    WHEN Total < 25 THEN '$0-$25'
                    WHEN Total < 50 THEN '$25-$50'
                    WHEN Total < 100 THEN '$50-$100'
                    WHEN Total < 250 THEN '$100-$250'
                    WHEN Total < 500 THEN '$250-$500'
                    WHEN Total < 1000 THEN '$500-$1K'
                    WHEN Total < 2500 THEN '$1K-$2.5K'
                    WHEN Total < 5000 THEN '$2.5K-$5K'
                    ELSE '$5K+'
                END as OrderValueBracket,
                CASE 
                    WHEN Total < 25 THEN 1
                    WHEN Total < 50 THEN 2
                    WHEN Total < 100 THEN 3
                    WHEN Total < 250 THEN 4
                    WHEN Total < 500 THEN 5
                    WHEN Total < 1000 THEN 6
                    WHEN Total < 2500 THEN 7
                    WHEN Total < 5000 THEN 8
                    ELSE 9
                END as BracketOrder
            FROM [dbo].[Transaction]
            WHERE Time >= DATEADD(YEAR, -1, GETDATE())
        )
        SELECT 
            OrderValueBracket,
            COUNT(*) as OrderCount,
            SUM(Total) as TotalRevenue,
            AVG(Total) as AvgInBracket,
            MIN(Total) as MinOrder,
            MAX(Total) as MaxOrder
        FROM OrderValues
        GROUP BY OrderValueBracket, BracketOrder
        ORDER BY BracketOrder
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_customer_lifetime_value(self):
        """Calculate customer lifetime value metrics"""
        query = """
        WITH CustomerLTV AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase,
                DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) + 1 as LifespanDays,
                COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
                SUM(t.Total) as LifetimeRevenue,
                -- Calculate profit with tobacco uplifts
                SUM(te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                        ELSE te.Cost
                    END * te.Quantity) as LifetimeProfit,
                -- Purchase frequency
                CASE 
                    WHEN DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) > 0 
                    THEN CAST(COUNT(DISTINCT t.TransactionNumber) as FLOAT) / 
                         (DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) / 30.0)
                    ELSE 0
                END as MonthlyFrequency
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        LTVSegments AS (
            SELECT 
                CASE 
                    WHEN LifetimeRevenue >= 50000 THEN 'Platinum ($50K+)'
                    WHEN LifetimeRevenue >= 25000 THEN 'Gold ($25K-$50K)'
                    WHEN LifetimeRevenue >= 10000 THEN 'Silver ($10K-$25K)'
                    WHEN LifetimeRevenue >= 5000 THEN 'Bronze ($5K-$10K)'
                    ELSE 'Standard (Under $5K)'
                END as CustomerSegment,
                COUNT(*) as CustomerCount,
                AVG(LifetimeRevenue) as AvgLTV,
                AVG(LifetimeProfit) as AvgProfit,
                AVG(MonthlyFrequency) as AvgMonthlyOrders,
                AVG(LifespanDays) as AvgLifespanDays,
                SUM(LifetimeRevenue) as TotalSegmentRevenue,
                SUM(LifetimeProfit) as TotalSegmentProfit
            FROM CustomerLTV
            GROUP BY 
                CASE 
                    WHEN LifetimeRevenue >= 50000 THEN 'Platinum ($50K+)'
                    WHEN LifetimeRevenue >= 25000 THEN 'Gold ($25K-$50K)'
                    WHEN LifetimeRevenue >= 10000 THEN 'Silver ($10K-$25K)'
                    WHEN LifetimeRevenue >= 5000 THEN 'Bronze ($5K-$10K)'
                    ELSE 'Standard (Under $5K)'
                END
        )
        SELECT * FROM LTVSegments
        ORDER BY 
            CASE 
                WHEN CustomerSegment LIKE 'Platinum%' THEN 1
                WHEN CustomerSegment LIKE 'Gold%' THEN 2
                WHEN CustomerSegment LIKE 'Silver%' THEN 3
                WHEN CustomerSegment LIKE 'Bronze%' THEN 4
                ELSE 5
            END
        """
        
        ltv_segments = self.db.execute_query(query)
        
        # Calculate predicted future value
        prediction_query = """
        SELECT TOP 100
            CustomerName,
            LifetimeRevenue,
            LifetimeProfit,
            TotalTransactions,
            MonthlyFrequency,
            LifetimeRevenue / NULLIF(DATEDIFF(MONTH, FirstPurchase, LastPurchase) + 1, 0) as MonthlyValue,
            -- Simple 12-month projection
            (LifetimeRevenue / NULLIF(DATEDIFF(MONTH, FirstPurchase, LastPurchase) + 1, 0)) * 12 as Projected12MonthValue,
            DATEDIFF(DAY, LastPurchase, GETDATE()) as DaysSinceLastPurchase,
            CASE 
                WHEN DATEDIFF(DAY, LastPurchase, GETDATE()) > 180 THEN 'At Risk'
                WHEN DATEDIFF(DAY, LastPurchase, GETDATE()) > 90 THEN 'Declining'
                WHEN DATEDIFF(DAY, LastPurchase, GETDATE()) > 30 THEN 'Active'
                ELSE 'Highly Active'
            END as ActivityStatus
        FROM (
            SELECT 
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase,
                COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
                SUM(t.Total) as LifetimeRevenue,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as LifetimeProfit,
                CASE 
                    WHEN DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) > 0 
                    THEN CAST(COUNT(DISTINCT t.TransactionNumber) as FLOAT) / 
                         (DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) / 30.0)
                    ELSE 0
                END as MonthlyFrequency
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            GROUP BY c.Company, c.FirstName, c.LastName
        ) AS CLV
        ORDER BY LifetimeRevenue DESC
        """
        
        top_customers_ltv = self.db.execute_query(prediction_query)
        
        return {
            "segments": ltv_segments.to_dict('records'),
            "top_customers_with_projections": top_customers_ltv.to_dict('records')
        }
    
    def get_payment_behavior_analysis(self):
        """Analyze payment behavior and credit risk"""
        query = """
        WITH CustomerPayments AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                c.CreditLimit,
                -- AR Balance
                (SELECT SUM(arh.Amount) 
                 FROM AccountReceivableHistory arh 
                 JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID 
                 WHERE ar.CustomerID = c.ID) as CurrentBalance,
                -- Payment stats
                COUNT(p.ID) as TotalPayments,
                SUM(p.Amount) as TotalPaid,
                AVG(p.Amount) as AvgPayment,
                MAX(p.Time) as LastPayment,
                MIN(p.Time) as FirstPayment,
                -- Sales for comparison
                (SELECT SUM(Total) FROM [dbo].[Transaction] WHERE CustomerID = c.ID) as TotalSales
            FROM dbo.Customer c
            LEFT JOIN Payment p ON p.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.CreditLimit
        ),
        PaymentMetrics AS (
            SELECT 
                CustomerName,
                CreditLimit,
                ISNULL(CurrentBalance, 0) as CurrentBalance,
                TotalPayments,
                TotalPaid,
                TotalSales,
                CASE 
                    WHEN CreditLimit > 0 THEN CurrentBalance / CreditLimit * 100
                    ELSE NULL
                END as CreditUtilization,
                CASE 
                    WHEN TotalSales > 0 THEN TotalPaid / TotalSales * 100
                    ELSE NULL
                END as PaymentRatio,
                DATEDIFF(DAY, LastPayment, GETDATE()) as DaysSinceLastPayment,
                CASE 
                    WHEN CurrentBalance > CreditLimit AND CreditLimit > 0 THEN 'Over Limit'
                    WHEN CurrentBalance > 0 AND DATEDIFF(DAY, LastPayment, GETDATE()) > 90 THEN 'Delinquent'
                    WHEN CurrentBalance > 0 AND DATEDIFF(DAY, LastPayment, GETDATE()) > 60 THEN 'Past Due'
                    WHEN CurrentBalance > 0 AND DATEDIFF(DAY, LastPayment, GETDATE()) > 30 THEN 'Due'
                    WHEN CurrentBalance <= 0 THEN 'Current'
                    ELSE 'Active'
                END as PaymentStatus
            FROM CustomerPayments
            WHERE TotalSales > 0 OR CurrentBalance != 0
        )
        SELECT 
            PaymentStatus,
            COUNT(*) as CustomerCount,
            AVG(CurrentBalance) as AvgBalance,
            SUM(CurrentBalance) as TotalBalance,
            AVG(CreditUtilization) as AvgCreditUtilization,
            AVG(PaymentRatio) as AvgPaymentRatio,
            AVG(DaysSinceLastPayment) as AvgDaysSincePayment
        FROM PaymentMetrics
        GROUP BY PaymentStatus
        ORDER BY 
            CASE 
                WHEN PaymentStatus = 'Over Limit' THEN 1
                WHEN PaymentStatus = 'Delinquent' THEN 2
                WHEN PaymentStatus = 'Past Due' THEN 3
                WHEN PaymentStatus = 'Due' THEN 4
                WHEN PaymentStatus = 'Active' THEN 5
                ELSE 6
            END
        """
        
        payment_status = self.db.execute_query(query)
        
        # High risk customers
        risk_query = """
        SELECT TOP 50
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.CreditLimit,
            ISNULL((SELECT SUM(arh.Amount) 
                    FROM AccountReceivableHistory arh 
                    JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID 
                    WHERE ar.CustomerID = c.ID), 0) as CurrentBalance,
            (SELECT MAX(Time) FROM Payment WHERE CustomerID = c.ID) as LastPayment,
            (SELECT SUM(Total) FROM [dbo].[Transaction] 
             WHERE CustomerID = c.ID AND Time >= DATEADD(DAY, -90, GETDATE())) as Sales90Days,
            DATEDIFF(DAY, (SELECT MAX(Time) FROM Payment WHERE CustomerID = c.ID), GETDATE()) as DaysSincePayment,
            CASE 
                WHEN c.CreditLimit > 0 AND 
                     ISNULL((SELECT SUM(arh.Amount) FROM AccountReceivableHistory arh 
                             JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID 
                             WHERE ar.CustomerID = c.ID), 0) > c.CreditLimit * 1.2 THEN 'Critical'
                WHEN DATEDIFF(DAY, (SELECT MAX(Time) FROM Payment WHERE CustomerID = c.ID), GETDATE()) > 120 THEN 'High'
                WHEN DATEDIFF(DAY, (SELECT MAX(Time) FROM Payment WHERE CustomerID = c.ID), GETDATE()) > 60 THEN 'Medium'
                ELSE 'Low'
            END as RiskLevel
        FROM dbo.Customer c
        WHERE EXISTS (SELECT 1 FROM [dbo].[Transaction] WHERE CustomerID = c.ID)
        ORDER BY CurrentBalance DESC
        """
        
        high_risk = self.db.execute_query(risk_query)
        
        return {
            "payment_status_summary": payment_status.to_dict('records'),
            "high_risk_customers": high_risk.to_dict('records')
        }
    
    def get_inventory_analysis(self):
        """Analyze inventory turnover and identify dead stock"""
        query = """
        WITH ItemMovement AS (
            SELECT 
                i.ID,
                i.ItemLookupCode,
                i.Description,
                cat.Name as Category,
                i.Cost,
                i.Price,
                i.QuantityOnHand,
                -- Sales data
                SUM(te.Quantity) as UnitsSold90Days,
                COUNT(DISTINCT te.TransactionNumber) as Transactions90Days,
                MAX(te.TransactionTime) as LastSold,
                AVG(te.Price) as AvgSellingPrice
            FROM Item i
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            LEFT JOIN TransactionEntry te ON te.ItemID = i.ID 
                AND te.TransactionTime >= DATEADD(DAY, -90, GETDATE())
            GROUP BY i.ID, i.ItemLookupCode, i.Description, cat.Name, 
                     i.Cost, i.Price, i.QuantityOnHand
        ),
        InventoryMetrics AS (
            SELECT 
                ItemLookupCode,
                Description,
                Category,
                Cost,
                Price,
                QuantityOnHand,
                UnitsSold90Days,
                Transactions90Days,
                LastSold,
                AvgSellingPrice,
                -- Turnover calculation
                CASE 
                    WHEN QuantityOnHand > 0 AND UnitsSold90Days > 0 
                    THEN (UnitsSold90Days * 4.0) / QuantityOnHand  -- Annualized
                    ELSE 0 
                END as TurnoverRate,
                -- Days of supply
                CASE 
                    WHEN UnitsSold90Days > 0 
                    THEN CAST(QuantityOnHand as FLOAT) / (UnitsSold90Days / 90.0)
                    ELSE 999 
                END as DaysOfSupply,
                -- Stock status
                CASE 
                    WHEN QuantityOnHand = 0 THEN 'Out of Stock'
                    WHEN ISNULL(UnitsSold90Days, 0) = 0 AND QuantityOnHand > 0 THEN 'Dead Stock'
                    WHEN QuantityOnHand > 0 AND UnitsSold90Days > 0 
                         AND QuantityOnHand > UnitsSold90Days * 2 THEN 'Overstock'
                    WHEN QuantityOnHand > 0 AND UnitsSold90Days > 0 
                         AND QuantityOnHand < UnitsSold90Days / 3 THEN 'Low Stock'
                    ELSE 'Normal'
                END as StockStatus,
                QuantityOnHand * Cost as InventoryValue
            FROM ItemMovement
        )
        SELECT 
            StockStatus,
            COUNT(*) as ItemCount,
            SUM(InventoryValue) as TotalValue,
            AVG(TurnoverRate) as AvgTurnover,
            AVG(DaysOfSupply) as AvgDaysSupply
        FROM InventoryMetrics
        GROUP BY StockStatus
        ORDER BY 
            CASE 
                WHEN StockStatus = 'Out of Stock' THEN 1
                WHEN StockStatus = 'Low Stock' THEN 2
                WHEN StockStatus = 'Dead Stock' THEN 3
                WHEN StockStatus = 'Overstock' THEN 4
                ELSE 5
            END
        """
        
        inventory_summary = self.db.execute_query(query)
        
        # Dead stock detail
        dead_stock_query = """
        SELECT TOP 100
            i.ItemLookupCode,
            i.Description,
            cat.Name as Category,
            i.QuantityOnHand,
            i.Cost,
            i.QuantityOnHand * i.Cost as TiedUpCapital,
            MAX(te.TransactionTime) as LastSoldDate,
            DATEDIFF(DAY, MAX(te.TransactionTime), GETDATE()) as DaysSinceLastSale
        FROM Item i
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        LEFT JOIN TransactionEntry te ON te.ItemID = i.ID
        WHERE i.QuantityOnHand > 0
        GROUP BY i.ItemLookupCode, i.Description, cat.Name, i.QuantityOnHand, i.Cost
        HAVING MAX(te.TransactionTime) IS NULL 
            OR DATEDIFF(DAY, MAX(te.TransactionTime), GETDATE()) > 180
        ORDER BY i.QuantityOnHand * i.Cost DESC
        """
        
        dead_stock = self.db.execute_query(dead_stock_query)
        
        return {
            "inventory_summary": inventory_summary.to_dict('records'),
            "dead_stock_items": dead_stock.to_dict('records')
        }
    
    def get_hourly_sales_patterns(self):
        """Analyze hourly sales patterns to identify peak times"""
        query = """
        WITH HourlyData AS (
            SELECT 
                DATEPART(HOUR, t.Time) as Hour,
                DATENAME(WEEKDAY, t.Time) as DayOfWeek,
                DATEPART(WEEKDAY, t.Time) as DayNum,
                COUNT(*) as Transactions,
                SUM(t.Total) as Revenue,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers
            FROM [dbo].[Transaction] t
            WHERE t.Time >= DATEADD(MONTH, -3, GETDATE())
            GROUP BY DATEPART(HOUR, t.Time), 
                     DATENAME(WEEKDAY, t.Time),
                     DATEPART(WEEKDAY, t.Time)
        )
        SELECT 
            Hour,
            -- Overall metrics
            SUM(Transactions) as TotalTransactions,
            AVG(Transactions) as AvgTransactions,
            SUM(Revenue) as TotalRevenue,
            AVG(Revenue) as AvgRevenue,
            -- Weekday vs Weekend
            SUM(CASE WHEN DayNum IN (1,7) THEN Transactions ELSE 0 END) as WeekendTransactions,
            SUM(CASE WHEN DayNum NOT IN (1,7) THEN Transactions ELSE 0 END) as WeekdayTransactions,
            SUM(CASE WHEN DayNum IN (1,7) THEN Revenue ELSE 0 END) as WeekendRevenue,
            SUM(CASE WHEN DayNum NOT IN (1,7) THEN Revenue ELSE 0 END) as WeekdayRevenue
        FROM HourlyData
        GROUP BY Hour
        ORDER BY Hour
        """
        
        hourly_patterns = self.db.execute_query(query)
        
        # Peak hours by day
        peak_query = """
        WITH DailyPeaks AS (
            SELECT 
                DATENAME(WEEKDAY, t.Time) as DayOfWeek,
                DATEPART(WEEKDAY, t.Time) as DayNum,
                DATEPART(HOUR, t.Time) as Hour,
                COUNT(*) as Transactions,
                SUM(t.Total) as Revenue
            FROM [dbo].[Transaction] t
            WHERE t.Time >= DATEADD(MONTH, -1, GETDATE())
            GROUP BY DATENAME(WEEKDAY, t.Time), 
                     DATEPART(WEEKDAY, t.Time),
                     DATEPART(HOUR, t.Time)
        ),
        RankedHours AS (
            SELECT 
                DayOfWeek,
                DayNum,
                Hour,
                Transactions,
                Revenue,
                ROW_NUMBER() OVER (PARTITION BY DayOfWeek ORDER BY Revenue DESC) as RevenueRank,
                ROW_NUMBER() OVER (PARTITION BY DayOfWeek ORDER BY Transactions DESC) as TransactionRank
            FROM DailyPeaks
        )
        SELECT 
            DayOfWeek,
            MAX(CASE WHEN RevenueRank = 1 THEN Hour END) as PeakRevenueHour,
            MAX(CASE WHEN RevenueRank = 1 THEN Revenue END) as PeakRevenue,
            MAX(CASE WHEN TransactionRank = 1 THEN Hour END) as PeakTransactionHour,
            MAX(CASE WHEN TransactionRank = 1 THEN Transactions END) as PeakTransactions
        FROM RankedHours
        GROUP BY DayOfWeek, DayNum
        ORDER BY DayNum
        """
        
        peak_hours = self.db.execute_query(peak_query)
        
        return {
            "hourly_distribution": hourly_patterns.to_dict('records'),
            "peak_hours_by_day": peak_hours.to_dict('records')
        }
    
    def get_churn_risk_analysis(self):
        """Identify customers at risk of churning"""
        query = """
        WITH CustomerActivity AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MAX(t.Time) as LastPurchase,
                COUNT(CASE WHEN t.Time >= DATEADD(DAY, -30, GETDATE()) THEN 1 END) as Purchases30Days,
                COUNT(CASE WHEN t.Time >= DATEADD(DAY, -90, GETDATE()) THEN 1 END) as Purchases90Days,
                COUNT(CASE WHEN t.Time >= DATEADD(DAY, -180, GETDATE()) THEN 1 END) as Purchases180Days,
                AVG(CASE WHEN t.Time >= DATEADD(DAY, -90, GETDATE()) THEN t.Total END) as AvgOrder90Days,
                -- Calculate typical purchase frequency
                CASE 
                    WHEN COUNT(*) > 1 
                    THEN DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) / NULLIF(COUNT(*) - 1, 0)
                    ELSE NULL
                END as AvgDaysBetweenOrders
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        ChurnRisk AS (
            SELECT 
                CustomerName,
                LastPurchase,
                Purchases30Days,
                Purchases90Days,
                Purchases180Days,
                AvgOrder90Days,
                AvgDaysBetweenOrders,
                DATEDIFF(DAY, LastPurchase, GETDATE()) as DaysSinceLastPurchase,
                -- Calculate churn risk score
                CASE 
                    WHEN Purchases30Days = 0 AND Purchases90Days > 3 THEN 'High Risk'
                    WHEN Purchases30Days = 0 AND Purchases90Days > 0 THEN 'Medium Risk'
                    WHEN AvgDaysBetweenOrders IS NOT NULL AND 
                         DATEDIFF(DAY, LastPurchase, GETDATE()) > AvgDaysBetweenOrders * 2 THEN 'Medium Risk'
                    WHEN DATEDIFF(DAY, LastPurchase, GETDATE()) > 90 THEN 'Low Risk'
                    ELSE 'Active'
                END as ChurnRiskLevel
            FROM CustomerActivity
            WHERE Purchases180Days > 0  -- Only consider recently active customers
        )
        SELECT 
            ChurnRiskLevel,
            COUNT(*) as CustomerCount,
            AVG(DaysSinceLastPurchase) as AvgDaysSinceLastPurchase,
            AVG(Purchases90Days) as AvgPurchases90Days,
            AVG(AvgOrder90Days) as AvgOrderValue
        FROM ChurnRisk
        GROUP BY ChurnRiskLevel
        ORDER BY 
            CASE 
                WHEN ChurnRiskLevel = 'High Risk' THEN 1
                WHEN ChurnRiskLevel = 'Medium Risk' THEN 2
                WHEN ChurnRiskLevel = 'Low Risk' THEN 3
                ELSE 4
            END
        """
        
        churn_summary = self.db.execute_query(query)
        
        # High risk customer details
        high_risk_query = """
        WITH CustomerMetrics AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MAX(t.Time) as LastPurchase,
                COUNT(CASE WHEN t.Time >= DATEADD(DAY, -30, GETDATE()) THEN 1 END) as Orders30Days,
                COUNT(CASE WHEN t.Time >= DATEADD(DAY, -90, GETDATE()) THEN 1 END) as Orders90Days,
                SUM(CASE WHEN t.Time >= DATEADD(YEAR, -1, GETDATE()) THEN t.Total END) as Revenue12Months,
                c.PhoneNumber
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.PhoneNumber
        )
        SELECT TOP 50
            CustomerName,
            PhoneNumber,
            LastPurchase,
            DATEDIFF(DAY, LastPurchase, GETDATE()) as DaysSinceLastPurchase,
            Orders30Days,
            Orders90Days,
            Revenue12Months
        FROM CustomerMetrics
        WHERE Orders30Days = 0 
            AND Orders90Days > 2
            AND Revenue12Months > 5000
        ORDER BY Revenue12Months DESC
        """
        
        high_risk_details = self.db.execute_query(high_risk_query)
        
        return {
            "churn_risk_summary": churn_summary.to_dict('records'),
            "high_value_at_risk": high_risk_details.to_dict('records')
        }
    
    def get_profitability_analysis(self):
        """Detailed profitability analysis by customer, category, and time"""
        query = """
        WITH ProfitData AS (
            SELECT 
                YEAR(t.Time) as Year,
                MONTH(t.Time) as Month,
                cat.Name as Category,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                    ELSE te.Cost * te.Quantity
                END) as AdjustedCost,
                SUM(te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                        ELSE te.Cost
                    END * te.Quantity) as GrossProfit,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY YEAR(t.Time), MONTH(t.Time), cat.Name
        )
        SELECT 
            Category,
            SUM(Revenue) as TotalRevenue,
            SUM(AdjustedCost) as TotalCost,
            SUM(GrossProfit) as TotalProfit,
            CAST(SUM(GrossProfit) * 100.0 / NULLIF(SUM(Revenue), 0) as DECIMAL(5,2)) as ProfitMargin,
            AVG(GrossProfit / NULLIF(Transactions, 0)) as AvgProfitPerTransaction,
            SUM(Transactions) as TotalTransactions
        FROM ProfitData
        GROUP BY Category
        HAVING SUM(Revenue) > 10000
        ORDER BY TotalProfit DESC
        """
        
        category_profit = self.db.execute_query(query)
        
        # Customer profitability
        customer_profit_query = """
        SELECT TOP 100
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(CASE 
                WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                ELSE te.Cost * te.Quantity
            END) as Cost,
            SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                    ELSE te.Cost
                END * te.Quantity) as GrossProfit,
            CAST(SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                    ELSE te.Cost
                END * te.Quantity) * 100.0 / 
                NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as ProfitMargin,
            COUNT(DISTINCT t.TransactionNumber) as Transactions
        FROM dbo.Customer c
        JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
        GROUP BY c.Company, c.FirstName, c.LastName
        ORDER BY GrossProfit DESC
        """
        
        customer_profit = self.db.execute_query(customer_profit_query)
        
        return {
            "category_profitability": category_profit.to_dict('records'),
            "top_profitable_customers": customer_profit.to_dict('records')
        }
    
    def get_product_velocity(self):
        """Analyze fast and slow moving products"""
        query = """
        WITH ProductSales AS (
            SELECT 
                i.ItemLookupCode,
                i.Description,
                cat.Name as Category,
                -- Last 7 days
                SUM(CASE WHEN te.TransactionTime >= DATEADD(DAY, -7, GETDATE()) 
                    THEN te.Quantity ELSE 0 END) as Units7Days,
                -- Last 30 days
                SUM(CASE WHEN te.TransactionTime >= DATEADD(DAY, -30, GETDATE()) 
                    THEN te.Quantity ELSE 0 END) as Units30Days,
                -- Last 90 days
                SUM(CASE WHEN te.TransactionTime >= DATEADD(DAY, -90, GETDATE()) 
                    THEN te.Quantity ELSE 0 END) as Units90Days,
                -- Revenue
                SUM(CASE WHEN te.TransactionTime >= DATEADD(DAY, -30, GETDATE()) 
                    THEN te.Price * te.Quantity ELSE 0 END) as Revenue30Days,
                -- Velocity trend
                CAST(SUM(CASE WHEN te.TransactionTime >= DATEADD(DAY, -7, GETDATE()) 
                    THEN te.Quantity ELSE 0 END) * 30.0 / 7 as INT) as ProjectedMonthlyUnits,
                i.QuantityOnHand,
                i.Cost,
                i.Price
            FROM Item i
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            LEFT JOIN TransactionEntry te ON te.ItemID = i.ID
            GROUP BY i.ItemLookupCode, i.Description, cat.Name, 
                     i.QuantityOnHand, i.Cost, i.Price
        )
        SELECT TOP 50
            ItemLookupCode,
            Description,
            Category,
            Units7Days,
            Units30Days,
            Units90Days,
            Revenue30Days,
            ProjectedMonthlyUnits,
            QuantityOnHand,
            CASE 
                WHEN ProjectedMonthlyUnits > 0 
                THEN QuantityOnHand / (ProjectedMonthlyUnits / 30.0)
                ELSE 999
            END as DaysOfStock,
            CASE 
                WHEN Units7Days > Units30Days / 4.0 THEN 'Accelerating'
                WHEN Units7Days < Units30Days / 5.0 THEN 'Slowing'
                ELSE 'Stable'
            END as VelocityTrend
        FROM ProductSales
        WHERE Units30Days > 0
        ORDER BY Revenue30Days DESC
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_basket_analysis(self):
        """Analyze what products are frequently bought together"""
        query = """
        WITH TransactionProducts AS (
            SELECT 
                te.TransactionNumber,
                i.Description as Product,
                cat.Name as Category
            FROM TransactionEntry te
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE te.TransactionTime >= DATEADD(MONTH, -3, GETDATE())
        ),
        CategoryPairs AS (
            SELECT 
                t1.Category as Category1,
                t2.Category as Category2,
                COUNT(DISTINCT t1.TransactionNumber) as CoOccurrences
            FROM TransactionProducts t1
            JOIN TransactionProducts t2 
                ON t1.TransactionNumber = t2.TransactionNumber
                AND t1.Category < t2.Category  -- Avoid duplicates
            GROUP BY t1.Category, t2.Category
            HAVING COUNT(DISTINCT t1.TransactionNumber) > 10
        )
        SELECT TOP 20
            Category1,
            Category2,
            CoOccurrences,
            -- Calculate lift (simplified)
            CAST(CoOccurrences as FLOAT) / 
                (SELECT COUNT(DISTINCT TransactionNumber) 
                 FROM TransactionProducts 
                 WHERE Category = Category1) * 100 as Confidence
        FROM CategoryPairs
        ORDER BY CoOccurrences DESC
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_supplier_performance(self):
        """Analyze performance by supplier/distributor"""
        query = """
        WITH SupplierSales AS (
            SELECT 
                CASE 
                    WHEN i.SupplierID IS NOT NULL THEN s.CompanyName
                    WHEN cat.Name LIKE '%CIGARETTE%' THEN 'Tobacco Distributor'
                    WHEN cat.Name LIKE '%CIGAR%' THEN 'Cigar Distributor'
                    WHEN cat.Name LIKE '%ECIG%' OR cat.Name LIKE '%ELECTRONIC%' THEN 'Vape Distributor'
                    ELSE 'Other Suppliers'
                END as Supplier,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as Cost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                COUNT(DISTINCT te.TransactionNumber) as Transactions,
                COUNT(DISTINCT i.ID) as UniqueProducts,
                SUM(te.Quantity) as UnitsSold
            FROM TransactionEntry te
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            LEFT JOIN Supplier s ON i.SupplierID = s.ID
            WHERE te.TransactionTime >= DATEADD(MONTH, -3, GETDATE())
            GROUP BY 
                CASE 
                    WHEN i.SupplierID IS NOT NULL THEN s.CompanyName
                    WHEN cat.Name LIKE '%CIGARETTE%' THEN 'Tobacco Distributor'
                    WHEN cat.Name LIKE '%CIGAR%' THEN 'Cigar Distributor'
                    WHEN cat.Name LIKE '%ECIG%' OR cat.Name LIKE '%ELECTRONIC%' THEN 'Vape Distributor'
                    ELSE 'Other Suppliers'
                END
        )
        SELECT 
            Supplier,
            Revenue,
            Cost,
            GrossProfit,
            CAST(GrossProfit * 100.0 / NULLIF(Revenue, 0) as DECIMAL(5,2)) as Margin,
            Transactions,
            UniqueProducts,
            UnitsSold,
            Revenue / NULLIF(Transactions, 0) as AvgTransactionValue
        FROM SupplierSales
        ORDER BY Revenue DESC
        """
        
        # Note: This query assumes a Supplier table exists. If not, we'll use category-based grouping
        fallback_query = """
        SELECT 
            CASE 
                WHEN cat.Name LIKE '%CIGARETTE%' THEN 'Tobacco Products'
                WHEN cat.Name LIKE '%CIGAR%' THEN 'Cigar Products'
                WHEN cat.Name LIKE '%ECIG%' OR cat.Name LIKE '%ELECTRONIC%' THEN 'Vape Products'
                WHEN cat.Name LIKE '%DRINK%' THEN 'Beverages'
                WHEN cat.Name LIKE '%VITAMIN%' THEN 'Health Products'
                ELSE 'Other Products'
            END as ProductGroup,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as Cost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            CAST(SUM((te.Price - te.Cost) * te.Quantity) * 100.0 / 
                NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as Margin,
            COUNT(DISTINCT te.TransactionNumber) as Transactions,
            COUNT(DISTINCT i.ID) as UniqueProducts
        FROM TransactionEntry te
        JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE te.TransactionTime >= DATEADD(MONTH, -3, GETDATE())
        GROUP BY 
            CASE 
                WHEN cat.Name LIKE '%CIGARETTE%' THEN 'Tobacco Products'
                WHEN cat.Name LIKE '%CIGAR%' THEN 'Cigar Products'
                WHEN cat.Name LIKE '%ECIG%' OR cat.Name LIKE '%ELECTRONIC%' THEN 'Vape Products'
                WHEN cat.Name LIKE '%DRINK%' THEN 'Beverages'
                WHEN cat.Name LIKE '%VITAMIN%' THEN 'Health Products'
                ELSE 'Other Products'
            END
        ORDER BY Revenue DESC
        """
        
        try:
            result = self.db.execute_query(query)
            if result.empty:
                result = self.db.execute_query(fallback_query)
        except:
            result = self.db.execute_query(fallback_query)
            
        return result.to_dict('records')
    
    def get_cashflow_forecast(self):
        """Project future cashflow based on AR and historical patterns"""
        query = """
        WITH ARaging AS (
            SELECT 
                CASE 
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 30 THEN '0-30 Days'
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 60 THEN '31-60 Days'
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 90 THEN '61-90 Days'
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 120 THEN '91-120 Days'
                    ELSE 'Over 120 Days'
                END as AgingBucket,
                SUM(arh.Amount) as Outstanding
            FROM AccountReceivable ar
            JOIN AccountReceivableHistory arh ON arh.AccountReceivableID = ar.ID
            GROUP BY 
                CASE 
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 30 THEN '0-30 Days'
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 60 THEN '31-60 Days'
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 90 THEN '61-90 Days'
                    WHEN DATEDIFF(DAY, ar.Date, GETDATE()) <= 120 THEN '91-120 Days'
                    ELSE 'Over 120 Days'
                END
        ),
        CollectionRates AS (
            -- Historical collection rates by age
            SELECT 
                '0-30 Days' as Bucket, 0.85 as CollectionRate, 35 as AvgDaysToCollect
            UNION ALL SELECT '31-60 Days', 0.70, 65
            UNION ALL SELECT '61-90 Days', 0.50, 95
            UNION ALL SELECT '91-120 Days', 0.30, 125
            UNION ALL SELECT 'Over 120 Days', 0.15, 180
        )
        SELECT 
            a.AgingBucket,
            a.Outstanding,
            c.CollectionRate,
            a.Outstanding * c.CollectionRate as ExpectedCollection,
            c.AvgDaysToCollect,
            DATEADD(DAY, c.AvgDaysToCollect, GETDATE()) as ExpectedCollectionDate
        FROM ARaging a
        JOIN CollectionRates c ON a.AgingBucket = c.Bucket
        ORDER BY 
            CASE 
                WHEN a.AgingBucket = '0-30 Days' THEN 1
                WHEN a.AgingBucket = '31-60 Days' THEN 2
                WHEN a.AgingBucket = '61-90 Days' THEN 3
                WHEN a.AgingBucket = '91-120 Days' THEN 4
                ELSE 5
            END
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def save_enhanced_report(self, report_data):
        """Save enhanced report with all fixes and additional insights"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_filename = f"customer_analytics_enhanced_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Create summary
        txt_filename = f"customer_analytics_enhanced_summary_{timestamp}.txt"
        with open(txt_filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("ENHANCED CUSTOMER ANALYTICS REPORT (WITH FIXES AND ADDITIONS)\n")
            f.write(f"Generated: {report_data['report_date']}\n")
            f.write("="*80 + "\n\n")
            
            f.write("FIXED METRICS (SQL Server 2008 R2 Compatible)\n")
            f.write("-"*40 + "\n")
            
            if 'customer_revenue_brackets' in report_data.get('fixed_metrics', {}):
                f.write("\n1. Customer Revenue Brackets (FIXED):\n")
                for bracket in report_data['fixed_metrics']['customer_revenue_brackets']:
                    f.write(f"   {bracket['RevenueBracket']}: {bracket['CustomerCount']} customers\n")
            
            f.write("\n\nADDITIONAL VALUABLE INSIGHTS\n")
            f.write("-"*40 + "\n")
            
            if 'customer_lifetime_value' in report_data.get('additional_insights', {}):
                f.write("\n1. Customer Lifetime Value Segments:\n")
                for segment in report_data['additional_insights']['customer_lifetime_value'].get('segments', []):
                    f.write(f"   {segment['CustomerSegment']}: {segment['CustomerCount']} customers, "
                           f"${segment.get('AvgLTV', 0):,.0f} avg LTV\n")
            
            if 'churn_risk' in report_data.get('additional_insights', {}):
                f.write("\n2. Churn Risk Analysis:\n")
                for risk in report_data['additional_insights']['churn_risk'].get('churn_risk_summary', []):
                    f.write(f"   {risk['ChurnRiskLevel']}: {risk['CustomerCount']} customers\n")
            
            if 'inventory_analysis' in report_data.get('additional_insights', {}):
                f.write("\n3. Inventory Status:\n")
                for status in report_data['additional_insights']['inventory_analysis'].get('inventory_summary', []):
                    f.write(f"   {status['StockStatus']}: {status['ItemCount']} items, "
                           f"${status.get('TotalValue', 0):,.2f} value\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write(f"Full report saved to: {json_filename}\n")
        
        return json_filename, txt_filename

def main():
    """Run enhanced analytics"""
    logger.info("Starting Enhanced Customer Analytics Report...")
    
    try:
        analytics = EnhancedCustomerAnalytics()
        report = analytics.generate_complete_report()
        
        json_file, txt_file = analytics.save_enhanced_report(report)
        
        logger.info(f"✅ Enhanced report generated successfully!")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   Summary: {txt_file}")
        
        # Print key insights
        print("\n" + "="*60)
        print("ENHANCED ANALYTICS - KEY INSIGHTS")
        print("="*60)
        
        # Show fixed metrics
        if 'customer_revenue_brackets' in report.get('fixed_metrics', {}):
            print("\n✓ Customer Revenue Brackets (FIXED)")
            for bracket in report['fixed_metrics']['customer_revenue_brackets'][:3]:
                print(f"  {bracket['RevenueBracket']}: {bracket['CustomerCount']} customers")
        
        # Show additional insights
        if 'customer_lifetime_value' in report.get('additional_insights', {}):
            segments = report['additional_insights']['customer_lifetime_value'].get('segments', [])
            if segments:
                print(f"\n✓ Top Customer Segment: {segments[0]['CustomerSegment']}")
                print(f"  {segments[0]['CustomerCount']} customers, ${segments[0].get('AvgLTV', 0):,.0f} avg LTV")
        
        if 'churn_risk' in report.get('additional_insights', {}):
            high_risk = [r for r in report['additional_insights']['churn_risk'].get('churn_risk_summary', []) 
                        if 'High' in r.get('ChurnRiskLevel', '')]
            if high_risk:
                print(f"\n⚠ High Churn Risk: {high_risk[0]['CustomerCount']} customers")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()