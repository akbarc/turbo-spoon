"""
Comprehensive Customer Analytics Report
Generates all requested customer metrics from POS database
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerAnalyticsReport:
    def __init__(self):
        self.db = SQLServerConnection()
        self.current_year = datetime.now().year
        self.last_year = self.current_year - 1
        
    def generate_full_report(self):
        """Generate complete customer analytics report with all priorities"""
        report = {
            "report_date": datetime.now().isoformat(),
            "priority_1": {},
            "priority_2": {},
            "priority_3": {}
        }
        
        try:
            self.db.connect()
            
            # Priority 1 - Must Have
            logger.info("Generating Priority 1 metrics...")
            report["priority_1"]["customer_revenue_brackets"] = self.get_customer_revenue_brackets()
            report["priority_1"]["revenue_concentration"] = self.get_revenue_concentration()
            report["priority_1"]["customer_retention"] = self.get_customer_retention_yoy()
            
            # Priority 2 - Very Helpful
            logger.info("Generating Priority 2 metrics...")
            report["priority_2"]["geographic_distribution"] = self.get_geographic_distribution()
            report["priority_2"]["new_customer_trends"] = self.get_new_customer_trends()
            report["priority_2"]["category_revenue_breakdown"] = self.get_category_revenue_breakdown()
            
            # Priority 3 - Nice to Have
            logger.info("Generating Priority 3 metrics...")
            report["priority_3"]["order_metrics"] = self.get_order_value_frequency()
            report["priority_3"]["seasonal_patterns"] = self.get_seasonal_patterns()
            
            return report
            
        finally:
            self.db.close()
    
    def get_customer_revenue_brackets(self):
        """Priority 1: Customer count by revenue brackets"""
        query = """
        WITH CustomerAnnualRevenue AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(CASE WHEN YEAR(t.Time) = YEAR(GETDATE()) THEN t.Total ELSE 0 END) as CurrentYearRevenue,
                SUM(CASE WHEN t.Time >= DATEADD(YEAR, -1, GETDATE()) THEN t.Total ELSE 0 END) as LastYearRevenue
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            CASE 
                WHEN LastYearRevenue >= 100000 THEN '$100K+'
                WHEN LastYearRevenue >= 50000 THEN '$50K-$100K'
                WHEN LastYearRevenue >= 25000 THEN '$25K-$50K'
                WHEN LastYearRevenue >= 10000 THEN '$10K-$25K'
                WHEN LastYearRevenue > 0 THEN 'Under $10K'
                ELSE 'No Purchases'
            END as RevenueBracket,
            COUNT(*) as CustomerCount,
            SUM(LastYearRevenue) as TotalRevenue,
            AVG(LastYearRevenue) as AvgRevenue,
            MIN(LastYearRevenue) as MinRevenue,
            MAX(LastYearRevenue) as MaxRevenue
        FROM CustomerAnnualRevenue
        GROUP BY 
            CASE 
                WHEN LastYearRevenue >= 100000 THEN '$100K+'
                WHEN LastYearRevenue >= 50000 THEN '$50K-$100K'
                WHEN LastYearRevenue >= 25000 THEN '$25K-$50K'
                WHEN LastYearRevenue >= 10000 THEN '$10K-$25K'
                WHEN LastYearRevenue > 0 THEN 'Under $10K'
                ELSE 'No Purchases'
            END
        ORDER BY 
            CASE 
                WHEN LastYearRevenue >= 100000 THEN 1
                WHEN LastYearRevenue >= 50000 THEN 2
                WHEN LastYearRevenue >= 25000 THEN 3
                WHEN LastYearRevenue >= 10000 THEN 4
                WHEN LastYearRevenue > 0 THEN 5
                ELSE 6
            END
        """
        
        result = self.db.execute_query(query)
        
        # Also get detailed top customers in each bracket
        detail_query = """
        WITH CustomerAnnualRevenue AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(CASE WHEN t.Time >= DATEADD(YEAR, -1, GETDATE()) THEN t.Total ELSE 0 END) as AnnualRevenue,
                COUNT(CASE WHEN t.Time >= DATEADD(YEAR, -1, GETDATE()) THEN 1 ELSE NULL END) as AnnualTransactions
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
            HAVING SUM(CASE WHEN t.Time >= DATEADD(YEAR, -1, GETDATE()) THEN t.Total ELSE 0 END) > 0
        )
        SELECT TOP 100
            CustomerName,
            AnnualRevenue,
            AnnualTransactions,
            AnnualRevenue / NULLIF(AnnualTransactions, 0) as AvgTransaction,
            CASE 
                WHEN AnnualRevenue >= 100000 THEN '$100K+'
                WHEN AnnualRevenue >= 50000 THEN '$50K-$100K'
                WHEN AnnualRevenue >= 25000 THEN '$25K-$50K'
                WHEN AnnualRevenue >= 10000 THEN '$10K-$25K'
                ELSE 'Under $10K'
            END as Bracket
        FROM CustomerAnnualRevenue
        ORDER BY AnnualRevenue DESC
        """
        
        top_customers = self.db.execute_query(detail_query)
        
        return {
            "summary": result.to_dict('records'),
            "top_customers_by_bracket": top_customers.to_dict('records')
        }
    
    def get_revenue_concentration(self):
        """Priority 1: Revenue concentration from top 50 customers"""
        query = """
        WITH TotalRevenue AS (
            SELECT SUM(t.Total) as GrandTotal
            FROM [dbo].[Transaction] t
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
        ),
        CustomerRevenue AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(t.Total) as CustomerTotal,
                COUNT(*) as TransactionCount
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        RankedCustomers AS (
            SELECT 
                CustomerName,
                CustomerTotal,
                TransactionCount,
                ROW_NUMBER() OVER (ORDER BY CustomerTotal DESC) as Rank
            FROM CustomerRevenue
        )
        SELECT 
            'Top 10 Customers' as CustomerGroup,
            COUNT(*) as CustomerCount,
            SUM(CustomerTotal) as GroupRevenue,
            (SELECT GrandTotal FROM TotalRevenue) as TotalRevenue,
            CAST(SUM(CustomerTotal) * 100.0 / (SELECT GrandTotal FROM TotalRevenue) as DECIMAL(5,2)) as PercentOfTotal
        FROM RankedCustomers
        WHERE Rank <= 10
        UNION ALL
        SELECT 
            'Top 25 Customers' as CustomerGroup,
            COUNT(*) as CustomerCount,
            SUM(CustomerTotal) as GroupRevenue,
            (SELECT GrandTotal FROM TotalRevenue) as TotalRevenue,
            CAST(SUM(CustomerTotal) * 100.0 / (SELECT GrandTotal FROM TotalRevenue) as DECIMAL(5,2)) as PercentOfTotal
        FROM RankedCustomers
        WHERE Rank <= 25
        UNION ALL
        SELECT 
            'Top 50 Customers' as CustomerGroup,
            COUNT(*) as CustomerCount,
            SUM(CustomerTotal) as GroupRevenue,
            (SELECT GrandTotal FROM TotalRevenue) as TotalRevenue,
            CAST(SUM(CustomerTotal) * 100.0 / (SELECT GrandTotal FROM TotalRevenue) as DECIMAL(5,2)) as PercentOfTotal
        FROM RankedCustomers
        WHERE Rank <= 50
        UNION ALL
        SELECT 
            'Top 100 Customers' as CustomerGroup,
            COUNT(*) as CustomerCount,
            SUM(CustomerTotal) as GroupRevenue,
            (SELECT GrandTotal FROM TotalRevenue) as TotalRevenue,
            CAST(SUM(CustomerTotal) * 100.0 / (SELECT GrandTotal FROM TotalRevenue) as DECIMAL(5,2)) as PercentOfTotal
        FROM RankedCustomers
        WHERE Rank <= 100
        """
        
        concentration = self.db.execute_query(query)
        
        # Get the actual top 50 customers
        top50_query = """
        WITH CustomerRevenue AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(t.Total) as Revenue,
                COUNT(*) as Transactions,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT TOP 50
            CustomerName,
            Revenue,
            Transactions,
            Revenue / NULLIF(Transactions, 0) as AvgTransaction,
            FirstPurchase,
            LastPurchase,
            DATEDIFF(DAY, LastPurchase, GETDATE()) as DaysSinceLastPurchase
        FROM CustomerRevenue
        ORDER BY Revenue DESC
        """
        
        top50 = self.db.execute_query(top50_query)
        
        return {
            "concentration_summary": concentration.to_dict('records'),
            "top_50_customers": top50.to_dict('records')
        }
    
    def get_customer_retention_yoy(self):
        """Priority 1: Customer retention rate year-over-year"""
        query = """
        WITH CustomerActivity AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(CASE WHEN YEAR(t.Time) = %s THEN 1 ELSE 0 END) as LastYearTransactions,
                SUM(CASE WHEN YEAR(t.Time) = %s THEN 1 ELSE 0 END) as CurrentYearTransactions,
                SUM(CASE WHEN YEAR(t.Time) = %s THEN t.Total ELSE 0 END) as LastYearRevenue,
                SUM(CASE WHEN YEAR(t.Time) = %s THEN t.Total ELSE 0 END) as CurrentYearRevenue
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE YEAR(t.Time) IN (%s, %s)
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            COUNT(CASE WHEN LastYearTransactions > 0 THEN 1 END) as LastYearActiveCustomers,
            COUNT(CASE WHEN CurrentYearTransactions > 0 THEN 1 END) as CurrentYearActiveCustomers,
            COUNT(CASE WHEN LastYearTransactions > 0 AND CurrentYearTransactions > 0 THEN 1 END) as RetainedCustomers,
            COUNT(CASE WHEN LastYearTransactions = 0 AND CurrentYearTransactions > 0 THEN 1 END) as NewCustomers,
            COUNT(CASE WHEN LastYearTransactions > 0 AND CurrentYearTransactions = 0 THEN 1 END) as LostCustomers,
            CAST(COUNT(CASE WHEN LastYearTransactions > 0 AND CurrentYearTransactions > 0 THEN 1 END) * 100.0 / 
                NULLIF(COUNT(CASE WHEN LastYearTransactions > 0 THEN 1 END), 0) as DECIMAL(5,2)) as RetentionRate,
            SUM(LastYearRevenue) as LastYearTotalRevenue,
            SUM(CurrentYearRevenue) as CurrentYearTotalRevenue,
            SUM(CASE WHEN LastYearTransactions > 0 AND CurrentYearTransactions > 0 THEN CurrentYearRevenue ELSE 0 END) as RetainedCustomerRevenue
        FROM CustomerActivity
        """
        
        params = (self.last_year, self.current_year, self.last_year, self.current_year, self.last_year, self.current_year)
        retention = self.db.execute_query(query, params)
        
        # Monthly retention cohorts
        cohort_query = """
        WITH MonthlyCustomers AS (
            SELECT DISTINCT
                YEAR(t.Time) as Year,
                MONTH(t.Time) as Month,
                t.CustomerID
            FROM [dbo].[Transaction] t
            WHERE t.Time >= DATEADD(YEAR, -2, GETDATE())
        ),
        CohortAnalysis AS (
            SELECT 
                m1.Year as CohortYear,
                m1.Month as CohortMonth,
                COUNT(DISTINCT m1.CustomerID) as CohortSize,
                COUNT(DISTINCT m2.CustomerID) as RetainedNextMonth,
                COUNT(DISTINCT m3.CustomerID) as RetainedIn3Months,
                COUNT(DISTINCT m6.CustomerID) as RetainedIn6Months
            FROM MonthlyCustomers m1
            LEFT JOIN MonthlyCustomers m2 ON m1.CustomerID = m2.CustomerID 
                AND ((m2.Year = m1.Year AND m2.Month = m1.Month + 1) 
                    OR (m2.Year = m1.Year + 1 AND m1.Month = 12 AND m2.Month = 1))
            LEFT JOIN MonthlyCustomers m3 ON m1.CustomerID = m3.CustomerID
                AND ((m3.Year = m1.Year AND m3.Month = m1.Month + 3)
                    OR (m3.Year = m1.Year + 1 AND m3.Month = (m1.Month + 3) % 12))
            LEFT JOIN MonthlyCustomers m6 ON m1.CustomerID = m6.CustomerID
                AND ((m6.Year = m1.Year AND m6.Month = m1.Month + 6)
                    OR (m6.Year = m1.Year + 1 AND m6.Month = (m1.Month + 6) % 12))
            GROUP BY m1.Year, m1.Month
        )
        SELECT 
            CohortYear,
            CohortMonth,
            CohortSize,
            RetainedNextMonth,
            CAST(RetainedNextMonth * 100.0 / NULLIF(CohortSize, 0) as DECIMAL(5,2)) as OneMonthRetention,
            RetainedIn3Months,
            CAST(RetainedIn3Months * 100.0 / NULLIF(CohortSize, 0) as DECIMAL(5,2)) as ThreeMonthRetention,
            RetainedIn6Months,
            CAST(RetainedIn6Months * 100.0 / NULLIF(CohortSize, 0) as DECIMAL(5,2)) as SixMonthRetention
        FROM CohortAnalysis
        ORDER BY CohortYear DESC, CohortMonth DESC
        """
        
        cohorts = self.db.execute_query(cohort_query)
        
        return {
            "annual_retention": retention.to_dict('records'),
            "monthly_cohorts": cohorts.head(12).to_dict('records')
        }
    
    def get_geographic_distribution(self):
        """Priority 2: Geographic distribution of customers and revenue"""
        query = """
        WITH CustomerGeo AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                c.State,
                c.City,
                c.Zip,
                SUM(t.Total) as TotalRevenue,
                COUNT(t.TransactionNumber) as TotalTransactions,
                MIN(t.Time) as FirstTransaction,
                MAX(t.Time) as LastTransaction
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.State, c.City, c.Zip
        )
        SELECT 
            ISNULL(State, 'Unknown') as State,
            COUNT(DISTINCT ID) as CustomerCount,
            SUM(TotalRevenue) as StateRevenue,
            AVG(TotalRevenue) as AvgCustomerRevenue,
            SUM(TotalTransactions) as TotalTransactions
        FROM CustomerGeo
        GROUP BY State
        ORDER BY StateRevenue DESC
        """
        
        by_state = self.db.execute_query(query)
        
        # City level breakdown for top states
        city_query = """
        WITH CustomerGeo AS (
            SELECT 
                c.ID,
                c.State,
                c.City,
                SUM(t.Total) as Revenue
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID, c.State, c.City
        )
        SELECT TOP 50
            ISNULL(State, 'Unknown') as State,
            ISNULL(City, 'Unknown') as City,
            COUNT(DISTINCT ID) as CustomerCount,
            SUM(Revenue) as CityRevenue
        FROM CustomerGeo
        GROUP BY State, City
        HAVING SUM(Revenue) > 0
        ORDER BY CityRevenue DESC
        """
        
        by_city = self.db.execute_query(city_query)
        
        return {
            "by_state": by_state.to_dict('records'),
            "top_cities": by_city.to_dict('records')
        }
    
    def get_new_customer_trends(self):
        """Priority 2: New customer acquisition trends over last 24 months"""
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
                COUNT(*) as NewCustomers
            FROM CustomerFirstPurchase
            WHERE FirstPurchaseDate >= DATEADD(MONTH, -24, GETDATE())
            GROUP BY YEAR(FirstPurchaseDate), MONTH(FirstPurchaseDate)
        )
        SELECT 
            Year,
            Month,
            DATENAME(MONTH, DATEFROMPARTS(Year, Month, 1)) as MonthName,
            NewCustomers,
            SUM(NewCustomers) OVER (ORDER BY Year, Month) as CumulativeNewCustomers
        FROM MonthlyNewCustomers
        ORDER BY Year DESC, Month DESC
        """
        
        monthly_trends = self.db.execute_query(query)
        
        # New customer quality analysis
        quality_query = """
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
        )
        SELECT 
            CASE 
                WHEN FirstPurchase >= DATEADD(MONTH, -3, GETDATE()) THEN '0-3 Months'
                WHEN FirstPurchase >= DATEADD(MONTH, -6, GETDATE()) THEN '3-6 Months'
                WHEN FirstPurchase >= DATEADD(MONTH, -12, GETDATE()) THEN '6-12 Months'
                WHEN FirstPurchase >= DATEADD(MONTH, -24, GETDATE()) THEN '12-24 Months'
                ELSE 'Over 24 Months'
            END as CustomerAge,
            COUNT(*) as CustomerCount,
            AVG(LifetimeRevenue) as AvgLifetimeValue,
            AVG(TotalTransactions) as AvgTransactions,
            AVG(CustomerLifeMonths) as AvgLifeMonths
        FROM CustomerMetrics
        GROUP BY 
            CASE 
                WHEN FirstPurchase >= DATEADD(MONTH, -3, GETDATE()) THEN '0-3 Months'
                WHEN FirstPurchase >= DATEADD(MONTH, -6, GETDATE()) THEN '3-6 Months'
                WHEN FirstPurchase >= DATEADD(MONTH, -12, GETDATE()) THEN '6-12 Months'
                WHEN FirstPurchase >= DATEADD(MONTH, -24, GETDATE()) THEN '12-24 Months'
                ELSE 'Over 24 Months'
            END
        ORDER BY 
            CASE 
                WHEN FirstPurchase >= DATEADD(MONTH, -3, GETDATE()) THEN 1
                WHEN FirstPurchase >= DATEADD(MONTH, -6, GETDATE()) THEN 2
                WHEN FirstPurchase >= DATEADD(MONTH, -12, GETDATE()) THEN 3
                WHEN FirstPurchase >= DATEADD(MONTH, -24, GETDATE()) THEN 4
                ELSE 5
            END
        """
        
        customer_quality = self.db.execute_query(quality_query)
        
        return {
            "monthly_acquisition": monthly_trends.to_dict('records'),
            "customer_quality_by_cohort": customer_quality.to_dict('records')
        }
    
    def get_category_revenue_breakdown(self):
        """Priority 2: Product category revenue breakdown"""
        query = """
        SELECT 
            ISNULL(cat.Name, 'Uncategorized') as Category,
            COUNT(DISTINCT te.TransactionNumber) as Transactions,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                    ELSE te.Cost
                END * te.Quantity) as GrossProfit,
            AVG(te.Price) as AvgPrice,
            CAST(SUM(te.Price * te.Quantity) * 100.0 / 
                (SELECT SUM(te2.Price * te2.Quantity) 
                 FROM [dbo].[Transaction] t2 
                 JOIN TransactionEntry te2 ON te2.TransactionNumber = t2.TransactionNumber 
                 WHERE t2.Time >= DATEADD(YEAR, -1, GETDATE())) as DECIMAL(5,2)) as PercentOfTotal
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
        GROUP BY cat.Name
        ORDER BY Revenue DESC
        """
        
        category_breakdown = self.db.execute_query(query)
        
        # Top items by category
        top_items_query = """
        WITH ItemSales AS (
            SELECT 
                ISNULL(cat.Name, 'Uncategorized') as Category,
                i.Description as ItemDescription,
                i.ItemLookupCode,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                AVG(te.Price) as AvgSellingPrice,
                COUNT(DISTINCT te.TransactionNumber) as TransactionCount
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY cat.Name, i.Description, i.ItemLookupCode
        ),
        RankedItems AS (
            SELECT 
                Category,
                ItemDescription,
                ItemLookupCode,
                UnitsSold,
                Revenue,
                AvgSellingPrice,
                TransactionCount,
                ROW_NUMBER() OVER (PARTITION BY Category ORDER BY Revenue DESC) as ItemRank
            FROM ItemSales
        )
        SELECT * FROM RankedItems WHERE ItemRank <= 5
        """
        
        top_items = self.db.execute_query(top_items_query)
        
        return {
            "category_summary": category_breakdown.to_dict('records'),
            "top_items_by_category": top_items.to_dict('records')
        }
    
    def get_order_value_frequency(self):
        """Priority 3: Average order value and frequency"""
        query = """
        WITH CustomerMetrics AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                COUNT(t.TransactionNumber) as TotalOrders,
                SUM(t.Total) as TotalRevenue,
                AVG(t.Total) as AvgOrderValue,
                MIN(t.Time) as FirstOrder,
                MAX(t.Time) as LastOrder,
                DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) + 1 as CustomerLifeDays
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            COUNT(*) as TotalCustomers,
            AVG(TotalOrders) as AvgOrdersPerCustomer,
            AVG(AvgOrderValue) as OverallAvgOrderValue,
            AVG(CAST(TotalOrders as FLOAT) / NULLIF(CustomerLifeDays, 0) * 30) as AvgOrdersPerMonth,
            MIN(AvgOrderValue) as MinAvgOrderValue,
            MAX(AvgOrderValue) as MaxAvgOrderValue,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY AvgOrderValue) OVER () as Q1_OrderValue,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY AvgOrderValue) OVER () as MedianOrderValue,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY AvgOrderValue) OVER () as Q3_OrderValue
        FROM CustomerMetrics
        """
        
        # SQL Server 2008 doesn't support PERCENTILE_CONT, so let's use a different approach
        query = """
        WITH CustomerMetrics AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                COUNT(t.TransactionNumber) as TotalOrders,
                SUM(t.Total) as TotalRevenue,
                AVG(t.Total) as AvgOrderValue,
                MIN(t.Time) as FirstOrder,
                MAX(t.Time) as LastOrder,
                DATEDIFF(DAY, MIN(t.Time), MAX(t.Time)) + 1 as CustomerLifeDays
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            COUNT(*) as TotalCustomers,
            AVG(TotalOrders) as AvgOrdersPerCustomer,
            AVG(AvgOrderValue) as OverallAvgOrderValue,
            AVG(CAST(TotalOrders as FLOAT) / NULLIF(CustomerLifeDays, 0) * 30) as AvgOrdersPerMonth,
            MIN(AvgOrderValue) as MinAvgOrderValue,
            MAX(AvgOrderValue) as MaxAvgOrderValue,
            STDEV(AvgOrderValue) as StdDevOrderValue
        FROM CustomerMetrics
        """
        
        order_metrics = self.db.execute_query(query)
        
        # Distribution of order values
        distribution_query = """
        SELECT 
            CASE 
                WHEN Total < 25 THEN '$0-$25'
                WHEN Total < 50 THEN '$25-$50'
                WHEN Total < 100 THEN '$50-$100'
                WHEN Total < 250 THEN '$100-$250'
                WHEN Total < 500 THEN '$250-$500'
                ELSE '$500+'
            END as OrderValueBracket,
            COUNT(*) as OrderCount,
            SUM(Total) as TotalRevenue,
            AVG(Total) as AvgInBracket
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(YEAR, -1, GETDATE())
        GROUP BY 
            CASE 
                WHEN Total < 25 THEN '$0-$25'
                WHEN Total < 50 THEN '$25-$50'
                WHEN Total < 100 THEN '$50-$100'
                WHEN Total < 250 THEN '$100-$250'
                WHEN Total < 500 THEN '$250-$500'
                ELSE '$500+'
            END
        ORDER BY 
            CASE 
                WHEN Total < 25 THEN 1
                WHEN Total < 50 THEN 2
                WHEN Total < 100 THEN 3
                WHEN Total < 250 THEN 4
                WHEN Total < 500 THEN 5
                ELSE 6
            END
        """
        
        value_distribution = self.db.execute_query(distribution_query)
        
        return {
            "order_metrics_summary": order_metrics.to_dict('records'),
            "order_value_distribution": value_distribution.to_dict('records')
        }
    
    def get_seasonal_patterns(self):
        """Priority 3: Seasonal revenue patterns"""
        query = """
        WITH MonthlyRevenue AS (
            SELECT 
                YEAR(t.Time) as Year,
                MONTH(t.Time) as Month,
                DATENAME(MONTH, t.Time) as MonthName,
                SUM(t.Total) as Revenue,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                AVG(t.Total) as AvgTransaction
            FROM [dbo].[Transaction] t
            WHERE t.Time >= DATEADD(YEAR, -3, GETDATE())
            GROUP BY YEAR(t.Time), MONTH(t.Time), DATENAME(MONTH, t.Time)
        ),
        SeasonalAverages AS (
            SELECT 
                Month,
                MonthName,
                AVG(Revenue) as AvgMonthlyRevenue,
                AVG(Transactions) as AvgTransactions,
                AVG(UniqueCustomers) as AvgCustomers,
                MIN(Revenue) as MinRevenue,
                MAX(Revenue) as MaxRevenue
            FROM MonthlyRevenue
            GROUP BY Month, MonthName
        )
        SELECT 
            Month,
            MonthName,
            AvgMonthlyRevenue,
            AvgTransactions,
            AvgCustomers,
            MinRevenue,
            MaxRevenue,
            CAST((AvgMonthlyRevenue - (SELECT AVG(AvgMonthlyRevenue) FROM SeasonalAverages)) * 100.0 / 
                (SELECT AVG(AvgMonthlyRevenue) FROM SeasonalAverages) as DECIMAL(5,2)) as SeasonalIndex
        FROM SeasonalAverages
        ORDER BY Month
        """
        
        seasonal = self.db.execute_query(query)
        
        # Weekly patterns
        weekly_query = """
        SELECT 
            DATENAME(WEEKDAY, t.Time) as DayOfWeek,
            DATEPART(WEEKDAY, t.Time) as DayNumber,
            COUNT(*) as Transactions,
            SUM(t.Total) as Revenue,
            AVG(t.Total) as AvgTransaction,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers
        FROM [dbo].[Transaction] t
        WHERE t.Time >= DATEADD(MONTH, -3, GETDATE())
        GROUP BY DATENAME(WEEKDAY, t.Time), DATEPART(WEEKDAY, t.Time)
        ORDER BY DATEPART(WEEKDAY, t.Time)
        """
        
        weekly = self.db.execute_query(weekly_query)
        
        # Quarterly trends
        quarterly_query = """
        SELECT 
            YEAR(t.Time) as Year,
            DATEPART(QUARTER, t.Time) as Quarter,
            'Q' + CAST(DATEPART(QUARTER, t.Time) as VARCHAR) + ' ' + CAST(YEAR(t.Time) as VARCHAR) as Period,
            SUM(t.Total) as Revenue,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers
        FROM [dbo].[Transaction] t
        WHERE t.Time >= DATEADD(YEAR, -3, GETDATE())
        GROUP BY YEAR(t.Time), DATEPART(QUARTER, t.Time)
        ORDER BY Year DESC, Quarter DESC
        """
        
        quarterly = self.db.execute_query(quarterly_query)
        
        return {
            "monthly_seasonality": seasonal.to_dict('records'),
            "weekly_patterns": weekly.to_dict('records'),
            "quarterly_trends": quarterly.head(12).to_dict('records')
        }
    
    def save_report(self, report_data):
        """Save report to JSON and create summary text file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON
        json_filename = f"customer_analytics_report_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Create readable text summary
        txt_filename = f"customer_analytics_summary_{timestamp}.txt"
        with open(txt_filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE CUSTOMER ANALYTICS REPORT\n")
            f.write(f"Generated: {report_data['report_date']}\n")
            f.write("="*80 + "\n\n")
            
            # Priority 1 Summary
            f.write("PRIORITY 1: MUST HAVE METRICS\n")
            f.write("-"*40 + "\n\n")
            
            f.write("1. Customer Revenue Brackets (Annual):\n")
            if 'customer_revenue_brackets' in report_data['priority_1']:
                for bracket in report_data['priority_1']['customer_revenue_brackets']['summary']:
                    f.write(f"   {bracket['RevenueBracket']}: {bracket['CustomerCount']} customers, ${bracket['TotalRevenue']:,.2f} revenue\n")
            
            f.write("\n2. Revenue Concentration:\n")
            if 'revenue_concentration' in report_data['priority_1']:
                for conc in report_data['priority_1']['revenue_concentration']['concentration_summary']:
                    f.write(f"   {conc['CustomerGroup']}: {conc['PercentOfTotal']:.2f}% of total revenue\n")
            
            f.write("\n3. Customer Retention:\n")
            if 'customer_retention' in report_data['priority_1']:
                retention = report_data['priority_1']['customer_retention']['annual_retention'][0]
                f.write(f"   Retention Rate: {retention.get('RetentionRate', 0):.2f}%\n")
                f.write(f"   Retained Customers: {retention.get('RetainedCustomers', 0)}\n")
                f.write(f"   Lost Customers: {retention.get('LostCustomers', 0)}\n")
                f.write(f"   New Customers: {retention.get('NewCustomers', 0)}\n")
            
            # Priority 2 Summary
            f.write("\n\nPRIORITY 2: VERY HELPFUL METRICS\n")
            f.write("-"*40 + "\n\n")
            
            f.write("1. Geographic Distribution (Top 5 States):\n")
            if 'geographic_distribution' in report_data['priority_2']:
                for i, state in enumerate(report_data['priority_2']['geographic_distribution']['by_state'][:5]):
                    f.write(f"   {state['State']}: {state['CustomerCount']} customers, ${state['StateRevenue']:,.2f}\n")
            
            f.write("\n2. Category Revenue Breakdown (Top 10):\n")
            if 'category_revenue_breakdown' in report_data['priority_2']:
                for i, cat in enumerate(report_data['priority_2']['category_revenue_breakdown']['category_summary'][:10]):
                    f.write(f"   {cat['Category']}: ${cat['Revenue']:,.2f} ({cat['PercentOfTotal']:.1f}%)\n")
            
            # Priority 3 Summary
            f.write("\n\nPRIORITY 3: NICE TO HAVE METRICS\n")
            f.write("-"*40 + "\n\n")
            
            if 'order_metrics' in report_data['priority_3']:
                metrics = report_data['priority_3']['order_metrics']['order_metrics_summary'][0]
                f.write(f"Average Order Value: ${metrics.get('OverallAvgOrderValue', 0):,.2f}\n")
                f.write(f"Avg Orders Per Customer: {metrics.get('AvgOrdersPerCustomer', 0):.1f}\n")
                f.write(f"Avg Orders Per Month: {metrics.get('AvgOrdersPerMonth', 0):.1f}\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write(f"Full detailed report saved to: {json_filename}\n")
        
        return json_filename, txt_filename

def main():
    """Generate and save the comprehensive customer analytics report"""
    logger.info("Starting Customer Analytics Report Generation...")
    
    try:
        reporter = CustomerAnalyticsReport()
        report = reporter.generate_full_report()
        
        json_file, txt_file = reporter.save_report(report)
        
        logger.info(f"✅ Report generated successfully!")
        logger.info(f"   JSON Report: {json_file}")
        logger.info(f"   Text Summary: {txt_file}")
        
        # Print summary to console
        print("\n" + "="*60)
        print("CUSTOMER ANALYTICS REPORT - QUICK SUMMARY")
        print("="*60)
        
        if 'customer_revenue_brackets' in report['priority_1']:
            print("\nRevenue Brackets:")
            for bracket in report['priority_1']['customer_revenue_brackets']['summary']:
                print(f"  {bracket['RevenueBracket']}: {bracket['CustomerCount']} customers")
        
        if 'revenue_concentration' in report['priority_1']:
            print("\nRevenue Concentration:")
            conc = report['priority_1']['revenue_concentration']['concentration_summary']
            if len(conc) > 2:
                print(f"  Top 50 customers: {conc[2]['PercentOfTotal']:.1f}% of revenue")
        
        if 'customer_retention' in report['priority_1']:
            retention = report['priority_1']['customer_retention']['annual_retention']
            if retention:
                print(f"\nRetention Rate: {retention[0].get('RetentionRate', 0):.1f}%")
        
        print("\n" + "="*60)
        print(f"Full reports saved to:")
        print(f"  - {json_file}")
        print(f"  - {txt_file}")
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise

if __name__ == "__main__":
    main()