"""
5-Year Historical Business Analytics (2019-2023)
Comprehensive growth and trend analysis excluding 2024
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalAnalytics:
    def __init__(self):
        self.db = SQLServerConnection()
        self.start_date = '2019-01-01'
        self.end_date = '2023-12-31'  # Excluding 2024
        
    def generate_historical_report(self):
        """Generate comprehensive 5-year historical analysis"""
        report = {
            "report_date": datetime.now().isoformat(),
            "analysis_period": f"{self.start_date} to {self.end_date}",
            "yearly_growth": {},
            "customer_evolution": {},
            "category_trends": {},
            "seasonal_analysis": {},
            "profitability_trends": {},
            "customer_retention": {}
        }
        
        try:
            self.db.connect()
            
            logger.info("Generating 5-year historical analysis...")
            
            # Core growth metrics
            report["yearly_growth"]["revenue_growth"] = self.get_yearly_revenue_growth()
            report["yearly_growth"]["customer_growth"] = self.get_customer_growth()
            report["yearly_growth"]["transaction_metrics"] = self.get_transaction_growth()
            
            # Customer evolution
            report["customer_evolution"]["acquisition"] = self.get_customer_acquisition_trends()
            report["customer_evolution"]["lifetime_value"] = self.get_ltv_evolution()
            report["customer_evolution"]["segment_migration"] = self.get_segment_migration()
            
            # Category and product trends
            report["category_trends"]["category_growth"] = self.get_category_growth()
            report["category_trends"]["product_lifecycle"] = self.get_product_lifecycle()
            
            # Seasonal patterns
            report["seasonal_analysis"]["monthly_patterns"] = self.get_monthly_patterns()
            report["seasonal_analysis"]["quarterly_performance"] = self.get_quarterly_performance()
            
            # Profitability trends
            report["profitability_trends"]["margin_evolution"] = self.get_margin_evolution()
            report["profitability_trends"]["customer_profitability"] = self.get_customer_profitability_trends()
            
            # Retention and churn
            report["customer_retention"]["cohort_analysis"] = self.get_cohort_retention()
            report["customer_retention"]["churn_trends"] = self.get_churn_trends()
            
            return report
            
        finally:
            self.db.close()
    
    def get_yearly_revenue_growth(self):
        """Analyze year-over-year revenue growth"""
        query = """
        WITH YearlyMetrics AS (
            SELECT 
                YEAR(t.Time) as Year,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(t.Total) as TotalRevenue,
                SUM(t.Total - t.SalesTax) as NetRevenue,
                AVG(t.Total) as AvgTransaction,
                SUM(te.Quantity) as TotalUnits
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time)
        ),
        GrowthCalc AS (
            SELECT 
                Year,
                UniqueCustomers,
                Transactions,
                TotalRevenue,
                NetRevenue,
                AvgTransaction,
                TotalUnits,
                LAG(TotalRevenue) OVER (ORDER BY Year) as PrevYearRevenue,
                LAG(UniqueCustomers) OVER (ORDER BY Year) as PrevYearCustomers,
                LAG(Transactions) OVER (ORDER BY Year) as PrevYearTransactions
            FROM YearlyMetrics
        )
        SELECT 
            Year,
            UniqueCustomers,
            Transactions,
            TotalRevenue,
            NetRevenue,
            AvgTransaction,
            TotalUnits,
            CASE 
                WHEN PrevYearRevenue IS NOT NULL 
                THEN ((TotalRevenue - PrevYearRevenue) / PrevYearRevenue * 100)
                ELSE NULL
            END as RevenueGrowthPercent,
            CASE 
                WHEN PrevYearCustomers IS NOT NULL 
                THEN ((UniqueCustomers - PrevYearCustomers) / CAST(PrevYearCustomers as FLOAT) * 100)
                ELSE NULL
            END as CustomerGrowthPercent,
            TotalRevenue / NULLIF(UniqueCustomers, 0) as RevenuePerCustomer,
            TotalRevenue / NULLIF(Transactions, 0) as RevenuePerTransaction
        FROM GrowthCalc
        ORDER BY Year
        """
        
        result = self.db.execute_query(query)
        
        # Calculate compound annual growth rate (CAGR)
        if not result.empty:
            first_year = result.iloc[0]['TotalRevenue']
            last_year = result.iloc[-1]['TotalRevenue']
            years = len(result) - 1
            if years > 0 and first_year > 0:
                cagr = ((last_year / first_year) ** (1/years) - 1) * 100
            else:
                cagr = 0
                
            return {
                "yearly_data": result.to_dict('records'),
                "cagr_revenue": round(cagr, 2),
                "total_growth": round((last_year - first_year) / first_year * 100, 2) if first_year > 0 else 0
            }
        return {"yearly_data": [], "cagr_revenue": 0, "total_growth": 0}
    
    def get_customer_growth(self):
        """Track customer base growth and composition"""
        query = """
        WITH CustomerCohorts AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                YEAR(MIN(t.Time)) as AcquisitionYear,
                COUNT(DISTINCT YEAR(t.Time)) as ActiveYears,
                SUM(t.Total) as TotalLifetimeValue,
                COUNT(DISTINCT t.TransactionNumber) as TotalTransactions
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        YearlyCustomerMetrics AS (
            SELECT 
                AcquisitionYear,
                COUNT(*) as NewCustomers,
                AVG(TotalLifetimeValue) as AvgLTV,
                AVG(ActiveYears) as AvgActiveYears,
                SUM(TotalLifetimeValue) as CohortTotalValue
            FROM CustomerCohorts
            GROUP BY AcquisitionYear
        )
        SELECT 
            AcquisitionYear as Year,
            NewCustomers,
            SUM(NewCustomers) OVER (ORDER BY AcquisitionYear) as CumulativeCustomers,
            AvgLTV,
            AvgActiveYears,
            CohortTotalValue,
            NewCustomers * 100.0 / SUM(NewCustomers) OVER () as PercentOfTotal
        FROM YearlyCustomerMetrics
        ORDER BY AcquisitionYear
        """
        
        cohorts = self.db.execute_query(query)
        
        # Customer activity by year
        activity_query = """
        SELECT 
            YEAR(t.Time) as Year,
            COUNT(DISTINCT t.CustomerID) as ActiveCustomers,
            COUNT(DISTINCT CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM [dbo].[Transaction] t2 
                    WHERE t2.CustomerID = t.CustomerID 
                    AND YEAR(t2.Time) = YEAR(t.Time) - 1
                ) THEN t.CustomerID 
            END) as NewCustomers,
            COUNT(DISTINCT CASE 
                WHEN EXISTS (
                    SELECT 1 FROM [dbo].[Transaction] t2 
                    WHERE t2.CustomerID = t.CustomerID 
                    AND YEAR(t2.Time) = YEAR(t.Time) - 1
                ) THEN t.CustomerID 
            END) as ReturningCustomers
        FROM [dbo].[Transaction] t
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY YEAR(t.Time)
        ORDER BY Year
        """
        
        activity = self.db.execute_query(activity_query)
        
        return {
            "cohort_analysis": cohorts.to_dict('records'),
            "yearly_activity": activity.to_dict('records')
        }
    
    def get_transaction_growth(self):
        """Analyze transaction patterns and basket size evolution"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            COUNT(*) as TotalTransactions,
            AVG(t.Total) as AvgTransactionValue,
            MIN(t.Total) as MinTransaction,
            MAX(t.Total) as MaxTransaction,
            STDEV(t.Total) as StdDevTransaction,
            -- Basket size metrics
            AVG(ItemCount) as AvgItemsPerTransaction,
            AVG(UniqueItems) as AvgUniqueItemsPerTransaction
        FROM [dbo].[Transaction] t
        JOIN (
            SELECT 
                TransactionNumber,
                COUNT(*) as ItemCount,
                COUNT(DISTINCT ItemID) as UniqueItems
            FROM TransactionEntry
            GROUP BY TransactionNumber
        ) te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY YEAR(t.Time)
        ORDER BY Year
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_customer_acquisition_trends(self):
        """Analyze new customer acquisition patterns"""
        query = """
        WITH FirstPurchases AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MIN(t.Time) as FirstPurchaseDate,
                YEAR(MIN(t.Time)) as AcquisitionYear,
                MONTH(MIN(t.Time)) as AcquisitionMonth
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        ),
        MonthlyAcquisition AS (
            SELECT 
                AcquisitionYear,
                AcquisitionMonth,
                COUNT(*) as NewCustomers,
                -- Calculate first year value
                (SELECT SUM(t2.Total) 
                 FROM [dbo].[Transaction] t2 
                 WHERE t2.CustomerID = fp.ID 
                 AND t2.Time >= fp.FirstPurchaseDate 
                 AND t2.Time < DATEADD(YEAR, 1, fp.FirstPurchaseDate)) as FirstYearValue
            FROM FirstPurchases fp
            GROUP BY AcquisitionYear, AcquisitionMonth, fp.ID, fp.FirstPurchaseDate
        )
        SELECT 
            AcquisitionYear as Year,
            AcquisitionMonth as Month,
            SUM(NewCustomers) as NewCustomers,
            AVG(FirstYearValue) as AvgFirstYearValue,
            SUM(FirstYearValue) as TotalFirstYearValue
        FROM MonthlyAcquisition
        GROUP BY AcquisitionYear, AcquisitionMonth
        ORDER BY AcquisitionYear, AcquisitionMonth
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_ltv_evolution(self):
        """Track how customer lifetime value has evolved"""
        query = """
        WITH CustomerLTV AS (
            SELECT 
                YEAR(MIN(t.Time)) as CohortYear,
                c.ID,
                SUM(t.Total) as LifetimeValue,
                COUNT(DISTINCT t.TransactionNumber) as LifetimeTransactions,
                DATEDIFF(MONTH, MIN(t.Time), MAX(t.Time)) + 1 as LifetimeMonths
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            CohortYear,
            COUNT(*) as Customers,
            AVG(LifetimeValue) as AvgLTV,
            MIN(LifetimeValue) as MinLTV,
            MAX(LifetimeValue) as MaxLTV,
            SUM(LifetimeValue) as TotalCohortValue,
            AVG(LifetimeTransactions) as AvgTransactions,
            AVG(LifetimeMonths) as AvgLifetimeMonths,
            AVG(LifetimeValue / NULLIF(LifetimeMonths, 0)) as AvgMonthlyValue
        FROM CustomerLTV
        GROUP BY CohortYear
        ORDER BY CohortYear
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_segment_migration(self):
        """Track how customers move between value segments over time"""
        query = """
        WITH YearlyCustomerValue AS (
            SELECT 
                t.CustomerID,
                YEAR(t.Time) as Year,
                SUM(t.Total) as YearlyRevenue,
                COUNT(*) as YearlyTransactions,
                CASE 
                    WHEN SUM(t.Total) >= 50000 THEN 'Platinum'
                    WHEN SUM(t.Total) >= 25000 THEN 'Gold'
                    WHEN SUM(t.Total) >= 10000 THEN 'Silver'
                    WHEN SUM(t.Total) >= 5000 THEN 'Bronze'
                    ELSE 'Standard'
                END as Segment
            FROM [dbo].[Transaction] t
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY t.CustomerID, YEAR(t.Time)
        )
        SELECT 
            Year,
            Segment,
            COUNT(*) as CustomerCount,
            SUM(YearlyRevenue) as SegmentRevenue,
            AVG(YearlyRevenue) as AvgCustomerRevenue,
            AVG(YearlyTransactions) as AvgTransactions
        FROM YearlyCustomerValue
        GROUP BY Year, Segment
        ORDER BY Year, 
            CASE 
                WHEN Segment = 'Platinum' THEN 1
                WHEN Segment = 'Gold' THEN 2
                WHEN Segment = 'Silver' THEN 3
                WHEN Segment = 'Bronze' THEN 4
                ELSE 5
            END
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_category_growth(self):
        """Analyze category performance over 5 years"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            ISNULL(cat.Name, 'Uncategorized') as Category,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                    ELSE te.Cost
                END * te.Quantity) as GrossProfit,
            AVG(te.Price) as AvgPrice
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY YEAR(t.Time), cat.Name
        ORDER BY Year, Revenue DESC
        """
        
        category_data = self.db.execute_query(query)
        
        # Calculate growth rates for top categories
        growth_query = """
        WITH CategoryYearly AS (
            SELECT 
                YEAR(t.Time) as Year,
                ISNULL(cat.Name, 'Uncategorized') as Category,
                SUM(te.Price * te.Quantity) as Revenue
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time), cat.Name
        ),
        TopCategories AS (
            SELECT TOP 10 Category, SUM(Revenue) as TotalRevenue
            FROM CategoryYearly
            GROUP BY Category
            ORDER BY TotalRevenue DESC
        )
        SELECT 
            cy.Year,
            cy.Category,
            cy.Revenue,
            LAG(cy.Revenue) OVER (PARTITION BY cy.Category ORDER BY cy.Year) as PrevYearRevenue,
            CASE 
                WHEN LAG(cy.Revenue) OVER (PARTITION BY cy.Category ORDER BY cy.Year) > 0
                THEN ((cy.Revenue - LAG(cy.Revenue) OVER (PARTITION BY cy.Category ORDER BY cy.Year)) / 
                      LAG(cy.Revenue) OVER (PARTITION BY cy.Category ORDER BY cy.Year) * 100)
                ELSE NULL
            END as GrowthPercent
        FROM CategoryYearly cy
        WHERE cy.Category IN (SELECT Category FROM TopCategories)
        ORDER BY cy.Category, cy.Year
        """
        
        growth_data = self.db.execute_query(growth_query)
        
        return {
            "category_performance": category_data.to_dict('records'),
            "top_category_growth": growth_data.to_dict('records')
        }
    
    def get_product_lifecycle(self):
        """Analyze product introduction and performance"""
        query = """
        WITH ProductIntroduction AS (
            SELECT 
                i.ItemLookupCode,
                i.Description,
                cat.Name as Category,
                MIN(te.TransactionTime) as FirstSoldDate,
                YEAR(MIN(te.TransactionTime)) as IntroductionYear,
                MAX(te.TransactionTime) as LastSoldDate,
                COUNT(DISTINCT te.TransactionNumber) as TotalTransactions,
                SUM(te.Quantity) as TotalUnitsSold,
                SUM(te.Price * te.Quantity) as TotalRevenue
            FROM Item i
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            JOIN TransactionEntry te ON te.ItemID = i.ID
            JOIN [dbo].[Transaction] t ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY i.ItemLookupCode, i.Description, cat.Name
        )
        SELECT 
            IntroductionYear,
            COUNT(*) as NewProductsIntroduced,
            AVG(TotalRevenue) as AvgProductRevenue,
            SUM(TotalRevenue) as TotalNewProductRevenue,
            AVG(DATEDIFF(DAY, FirstSoldDate, LastSoldDate)) as AvgProductLifeDays
        FROM ProductIntroduction
        GROUP BY IntroductionYear
        ORDER BY IntroductionYear
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_monthly_patterns(self):
        """Analyze monthly patterns across the 5 years"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            DATENAME(MONTH, t.Time) as MonthName,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(t.Total) as Revenue,
            AVG(t.Total) as AvgTransaction,
            -- Day of month analysis
            COUNT(DISTINCT CAST(t.Time as DATE)) as ActiveDays,
            SUM(t.Total) / COUNT(DISTINCT CAST(t.Time as DATE)) as RevenuePerDay
        FROM [dbo].[Transaction] t
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY YEAR(t.Time), MONTH(t.Time), DATENAME(MONTH, t.Time)
        ORDER BY Year, Month
        """
        
        monthly = self.db.execute_query(query)
        
        # Calculate seasonal indices
        seasonal_query = """
        WITH MonthlyAvg AS (
            SELECT 
                MONTH(t.Time) as Month,
                AVG(CAST(COUNT(*) as FLOAT)) as AvgTransactions,
                AVG(SUM(t.Total)) as AvgRevenue
            FROM [dbo].[Transaction] t
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time), MONTH(t.Time)
        ),
        OverallAvg AS (
            SELECT 
                AVG(AvgRevenue) as TotalAvgRevenue
            FROM MonthlyAvg
        )
        SELECT 
            m.Month,
            DATENAME(MONTH, DATEADD(MONTH, m.Month - 1, '2000-01-01')) as MonthName,
            m.AvgRevenue,
            o.TotalAvgRevenue as YearlyAverage,
            (m.AvgRevenue / o.TotalAvgRevenue * 100) as SeasonalIndex
        FROM MonthlyAvg m
        CROSS JOIN OverallAvg o
        ORDER BY m.Month
        """
        
        seasonal = self.db.execute_query(seasonal_query)
        
        return {
            "monthly_data": monthly.to_dict('records'),
            "seasonal_indices": seasonal.to_dict('records')
        }
    
    def get_quarterly_performance(self):
        """Analyze quarterly business performance"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            DATEPART(QUARTER, t.Time) as Quarter,
            'Q' + CAST(DATEPART(QUARTER, t.Time) as VARCHAR) as QuarterName,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(t.Total) as Revenue,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
            AVG(t.Total) as AvgTransaction
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY YEAR(t.Time), DATEPART(QUARTER, t.Time)
        ORDER BY Year, Quarter
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_margin_evolution(self):
        """Track profit margin evolution over time"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
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
            CAST(SUM(te.Price * te.Quantity - 
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                    ELSE te.Cost
                END * te.Quantity) * 100.0 / 
                NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as GrossProfitMargin,
            -- Category breakdown
            SUM(CASE WHEN cat.Name = 'CIGARETTE' THEN te.Price * te.Quantity ELSE 0 END) as CigaretteRevenue,
            SUM(CASE WHEN cat.Name = 'CIGARS' THEN te.Price * te.Quantity ELSE 0 END) as CigarRevenue,
            SUM(CASE WHEN cat.Name LIKE '%ECIG%' OR cat.Name LIKE '%ELECTRONIC%' 
                THEN te.Price * te.Quantity ELSE 0 END) as VapeRevenue
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY YEAR(t.Time)
        ORDER BY Year
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_customer_profitability_trends(self):
        """Analyze customer profitability trends over time"""
        query = """
        WITH CustomerProfitYearly AS (
            SELECT 
                YEAR(t.Time) as Year,
                t.CustomerID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
                COUNT(DISTINCT t.TransactionNumber) as Transactions
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Customer c ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time), t.CustomerID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            Year,
            COUNT(DISTINCT CustomerID) as TotalCustomers,
            AVG(Revenue) as AvgCustomerRevenue,
            AVG(GrossProfit) as AvgCustomerProfit,
            AVG(Transactions) as AvgTransactionsPerCustomer,
            -- Profit distribution
            COUNT(CASE WHEN GrossProfit >= 10000 THEN 1 END) as HighProfitCustomers,
            COUNT(CASE WHEN GrossProfit >= 5000 AND GrossProfit < 10000 THEN 1 END) as MediumProfitCustomers,
            COUNT(CASE WHEN GrossProfit >= 1000 AND GrossProfit < 5000 THEN 1 END) as LowProfitCustomers,
            COUNT(CASE WHEN GrossProfit < 1000 THEN 1 END) as MinimalProfitCustomers,
            -- Concentration
            (SELECT SUM(Revenue) FROM (
                SELECT TOP 50 Revenue 
                FROM CustomerProfitYearly cp2 
                WHERE cp2.Year = cpy.Year 
                ORDER BY Revenue DESC
            ) top50) / SUM(Revenue) * 100 as Top50ConcentrationPercent
        FROM CustomerProfitYearly cpy
        GROUP BY Year
        ORDER BY Year
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_cohort_retention(self):
        """Analyze customer retention by cohort"""
        query = """
        WITH CustomerCohorts AS (
            SELECT 
                c.ID as CustomerID,
                YEAR(MIN(t.Time)) as CohortYear,
                MONTH(MIN(t.Time)) as CohortMonth
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY c.ID
        ),
        CohortActivity AS (
            SELECT 
                cc.CohortYear,
                cc.CustomerID,
                YEAR(t.Time) as ActivityYear,
                SUM(t.Total) as YearlyRevenue
            FROM CustomerCohorts cc
            JOIN [dbo].[Transaction] t ON t.CustomerID = cc.CustomerID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY cc.CohortYear, cc.CustomerID, YEAR(t.Time)
        )
        SELECT 
            CohortYear,
            ActivityYear,
            ActivityYear - CohortYear as YearsSinceCohort,
            COUNT(DISTINCT CustomerID) as ActiveCustomers,
            SUM(YearlyRevenue) as CohortRevenue,
            AVG(YearlyRevenue) as AvgRevenuePerCustomer
        FROM CohortActivity
        GROUP BY CohortYear, ActivityYear
        ORDER BY CohortYear, ActivityYear
        """
        
        cohort_data = self.db.execute_query(query)
        
        # Calculate retention rates
        retention_query = """
        WITH CohortSizes AS (
            SELECT 
                YEAR(MIN(t.Time)) as CohortYear,
                COUNT(DISTINCT c.ID) as CohortSize
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY c.ID
        ),
        RetentionCalc AS (
            SELECT 
                cs.CohortYear,
                cs.CohortSize,
                -- Year 1 retention
                (SELECT COUNT(DISTINCT CustomerID) 
                 FROM [dbo].[Transaction] t2 
                 JOIN dbo.Customer c2 ON t2.CustomerID = c2.ID
                 WHERE YEAR(t2.Time) = cs.CohortYear + 1
                 AND c2.ID IN (
                     SELECT CustomerID FROM [dbo].[Transaction] 
                     WHERE YEAR(Time) = cs.CohortYear
                 )) as Year1Retained,
                -- Year 2 retention
                (SELECT COUNT(DISTINCT CustomerID) 
                 FROM [dbo].[Transaction] t2 
                 JOIN dbo.Customer c2 ON t2.CustomerID = c2.ID
                 WHERE YEAR(t2.Time) = cs.CohortYear + 2
                 AND c2.ID IN (
                     SELECT CustomerID FROM [dbo].[Transaction] 
                     WHERE YEAR(Time) = cs.CohortYear
                 )) as Year2Retained
            FROM CohortSizes cs
        )
        SELECT 
            CohortYear,
            CohortSize,
            Year1Retained,
            CAST(Year1Retained * 100.0 / NULLIF(CohortSize, 0) as DECIMAL(5,2)) as Year1RetentionRate,
            Year2Retained,
            CAST(Year2Retained * 100.0 / NULLIF(CohortSize, 0) as DECIMAL(5,2)) as Year2RetentionRate
        FROM RetentionCalc
        ORDER BY CohortYear
        """
        
        retention_rates = self.db.execute_query(retention_query)
        
        return {
            "cohort_activity": cohort_data.to_dict('records'),
            "retention_rates": retention_rates.to_dict('records')
        }
    
    def get_churn_trends(self):
        """Analyze customer churn patterns over time"""
        query = """
        WITH CustomerLastPurchase AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                MAX(t.Time) as LastPurchaseDate,
                YEAR(MAX(t.Time)) as LastActiveYear,
                COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
                SUM(t.Total) as TotalRevenue
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            LastActiveYear,
            COUNT(*) as ChurnedCustomers,
            AVG(TotalRevenue) as AvgLostRevenue,
            SUM(TotalRevenue) as TotalLostRevenue,
            AVG(TotalTransactions) as AvgTransactionsBeforeChurn,
            -- Churn by value segment
            COUNT(CASE WHEN TotalRevenue >= 10000 THEN 1 END) as HighValueChurn,
            COUNT(CASE WHEN TotalRevenue >= 5000 AND TotalRevenue < 10000 THEN 1 END) as MediumValueChurn,
            COUNT(CASE WHEN TotalRevenue < 5000 THEN 1 END) as LowValueChurn
        FROM CustomerLastPurchase
        WHERE LastActiveYear < 2023  -- Customers who haven't purchased in 2023
        GROUP BY LastActiveYear
        ORDER BY LastActiveYear
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def save_historical_report(self, report_data):
        """Save the 5-year historical analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_filename = f"historical_analysis_2019_2023_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Create executive summary
        txt_filename = f"historical_analysis_summary_{timestamp}.txt"
        with open(txt_filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("5-YEAR HISTORICAL BUSINESS ANALYSIS (2019-2023)\n")
            f.write(f"Generated: {report_data['report_date']}\n")
            f.write("="*80 + "\n\n")
            
            # Yearly Growth Summary
            f.write("YEARLY REVENUE GROWTH\n")
            f.write("-"*40 + "\n")
            if 'revenue_growth' in report_data.get('yearly_growth', {}):
                revenue_data = report_data['yearly_growth']['revenue_growth']
                f.write(f"5-Year Revenue CAGR: {revenue_data.get('cagr_revenue', 0):.2f}%\n")
                f.write(f"Total Growth: {revenue_data.get('total_growth', 0):.2f}%\n\n")
                
                f.write("Year-by-Year Performance:\n")
                for year in revenue_data.get('yearly_data', []):
                    f.write(f"  {year['Year']}: ${year['TotalRevenue']:,.0f} revenue, "
                           f"{year['UniqueCustomers']} customers\n")
                    if year.get('RevenueGrowthPercent'):
                        f.write(f"         Growth: {year['RevenueGrowthPercent']:.1f}%\n")
            
            # Customer Evolution
            f.write("\n\nCUSTOMER EVOLUTION\n")
            f.write("-"*40 + "\n")
            if 'customer_growth' in report_data.get('yearly_growth', {}):
                customer_data = report_data['yearly_growth']['customer_growth']
                if 'yearly_activity' in customer_data:
                    f.write("Active Customers by Year:\n")
                    for year in customer_data['yearly_activity']:
                        f.write(f"  {year['Year']}: {year['ActiveCustomers']} active, "
                               f"{year['NewCustomers']} new, {year['ReturningCustomers']} returning\n")
            
            # Category Trends
            f.write("\n\nTOP CATEGORY PERFORMANCE\n")
            f.write("-"*40 + "\n")
            if 'category_growth' in report_data.get('category_trends', {}):
                cat_data = report_data['category_trends']['category_growth']
                if 'category_performance' in cat_data:
                    # Group by year and show top 3 categories
                    years = set(item['Year'] for item in cat_data['category_performance'])
                    for year in sorted(years)[-2:]:  # Last 2 years
                        f.write(f"\n{year} Top Categories:\n")
                        year_cats = [c for c in cat_data['category_performance'] if c['Year'] == year]
                        for cat in sorted(year_cats, key=lambda x: x['Revenue'], reverse=True)[:3]:
                            f.write(f"  {cat['Category']}: ${cat['Revenue']:,.0f}\n")
            
            # Profitability Trends
            f.write("\n\nPROFITABILITY TRENDS\n")
            f.write("-"*40 + "\n")
            if 'margin_evolution' in report_data.get('profitability_trends', {}):
                margins = report_data['profitability_trends']['margin_evolution']
                f.write("Gross Profit Margins by Year:\n")
                for year_margin in margins:
                    f.write(f"  {year_margin['Year']}: {year_margin.get('GrossProfitMargin', 0):.2f}% margin, "
                           f"${year_margin['GrossProfit']:,.0f} profit\n")
            
            # Retention Summary
            f.write("\n\nCUSTOMER RETENTION\n")
            f.write("-"*40 + "\n")
            if 'cohort_analysis' in report_data.get('customer_retention', {}):
                retention = report_data['customer_retention']['cohort_analysis']
                if 'retention_rates' in retention:
                    f.write("Cohort Retention Rates:\n")
                    for cohort in retention['retention_rates']:
                        f.write(f"  {cohort['CohortYear']} Cohort: "
                               f"Year 1: {cohort.get('Year1RetentionRate', 0):.1f}%, "
                               f"Year 2: {cohort.get('Year2RetentionRate', 0):.1f}%\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write(f"Full detailed report saved to: {json_filename}\n")
        
        return json_filename, txt_filename

def main():
    """Generate 5-year historical analysis"""
    logger.info("Starting 5-Year Historical Analysis (2019-2023)...")
    
    try:
        analyzer = HistoricalAnalytics()
        report = analyzer.generate_historical_report()
        
        json_file, txt_file = analyzer.save_historical_report(report)
        
        logger.info(f"✅ Historical analysis completed!")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   Summary: {txt_file}")
        
        # Print key insights
        print("\n" + "="*60)
        print("5-YEAR BUSINESS ANALYSIS - KEY INSIGHTS (2019-2023)")
        print("="*60)
        
        if 'revenue_growth' in report.get('yearly_growth', {}):
            revenue = report['yearly_growth']['revenue_growth']
            print(f"\n📈 Revenue Growth:")
            print(f"   5-Year CAGR: {revenue.get('cagr_revenue', 0):.2f}%")
            print(f"   Total Growth: {revenue.get('total_growth', 0):.2f}%")
            
            yearly = revenue.get('yearly_data', [])
            if len(yearly) >= 2:
                print(f"\n   2019: ${yearly[0]['TotalRevenue']:,.0f}")
                print(f"   2023: ${yearly[-1]['TotalRevenue']:,.0f}")
        
        if 'customer_growth' in report.get('yearly_growth', {}):
            customers = report['yearly_growth']['customer_growth']
            if 'yearly_activity' in customers and customers['yearly_activity']:
                first_year = customers['yearly_activity'][0]
                last_year = customers['yearly_activity'][-1]
                print(f"\n👥 Customer Base:")
                print(f"   2019: {first_year['ActiveCustomers']} active customers")
                print(f"   2023: {last_year['ActiveCustomers']} active customers")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()