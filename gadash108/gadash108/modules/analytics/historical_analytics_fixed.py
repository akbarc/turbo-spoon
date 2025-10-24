"""
Fixed 5-Year Historical Analytics for SQL Server 2008 R2
All queries compatible with SQL Server 2008
"""

import pandas as pd
from datetime import datetime
from database_pymssql import SQLServerConnection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalAnalyticsFixed:
    def __init__(self):
        self.db = SQLServerConnection()
        
    def get_yearly_growth_fixed(self):
        """Get yearly revenue growth without LAG function"""
        query = """
        SELECT 
            y1.Year,
            y1.TotalRevenue,
            y1.UniqueCustomers,
            y1.Transactions,
            y1.AvgTransaction,
            y2.TotalRevenue as PrevYearRevenue,
            CASE 
                WHEN y2.TotalRevenue > 0 
                THEN ((y1.TotalRevenue - y2.TotalRevenue) / y2.TotalRevenue * 100)
                ELSE NULL
            END as RevenueGrowthPercent,
            CASE 
                WHEN y2.UniqueCustomers > 0 
                THEN ((y1.UniqueCustomers - y2.UniqueCustomers) * 100.0 / y2.UniqueCustomers)
                ELSE NULL
            END as CustomerGrowthPercent
        FROM (
            SELECT 
                YEAR(t.Time) as Year,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(t.Total) as TotalRevenue,
                AVG(t.Total) as AvgTransaction
            FROM [dbo].[Transaction] t
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time)
        ) y1
        LEFT JOIN (
            SELECT 
                YEAR(t.Time) as Year,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                SUM(t.Total) as TotalRevenue
            FROM [dbo].[Transaction] t
            WHERE t.Time >= '2018-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time)
        ) y2 ON y1.Year = y2.Year + 1
        ORDER BY y1.Year
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_category_growth_fixed(self):
        """Get category growth without LAG function"""
        query = """
        WITH TopCategories AS (
            SELECT TOP 10 
                ISNULL(cat.Name, 'Uncategorized') as Category,
                SUM(te.Price * te.Quantity) as TotalRevenue
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY cat.Name
            ORDER BY TotalRevenue DESC
        )
        SELECT 
            cy1.Year,
            cy1.Category,
            cy1.Revenue,
            cy2.Revenue as PrevYearRevenue,
            CASE 
                WHEN cy2.Revenue > 0
                THEN ((cy1.Revenue - cy2.Revenue) / cy2.Revenue * 100)
                ELSE NULL
            END as GrowthPercent,
            cy1.Transactions,
            cy1.UnitsSold
        FROM (
            SELECT 
                YEAR(t.Time) as Year,
                ISNULL(cat.Name, 'Uncategorized') as Category,
                SUM(te.Price * te.Quantity) as Revenue,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(te.Quantity) as UnitsSold
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
                AND ISNULL(cat.Name, 'Uncategorized') IN (SELECT Category FROM TopCategories)
            GROUP BY YEAR(t.Time), cat.Name
        ) cy1
        LEFT JOIN (
            SELECT 
                YEAR(t.Time) as Year,
                ISNULL(cat.Name, 'Uncategorized') as Category,
                SUM(te.Price * te.Quantity) as Revenue
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2018-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time), cat.Name
        ) cy2 ON cy1.Year = cy2.Year + 1 AND cy1.Category = cy2.Category
        ORDER BY cy1.Category, cy1.Year
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_customer_segments_over_time(self):
        """Track customer segments without window functions"""
        query = """
        SELECT 
            Year,
            COUNT(CASE WHEN YearlyRevenue >= 50000 THEN 1 END) as PlatinumCustomers,
            COUNT(CASE WHEN YearlyRevenue >= 25000 AND YearlyRevenue < 50000 THEN 1 END) as GoldCustomers,
            COUNT(CASE WHEN YearlyRevenue >= 10000 AND YearlyRevenue < 25000 THEN 1 END) as SilverCustomers,
            COUNT(CASE WHEN YearlyRevenue >= 5000 AND YearlyRevenue < 10000 THEN 1 END) as BronzeCustomers,
            COUNT(CASE WHEN YearlyRevenue < 5000 THEN 1 END) as StandardCustomers,
            SUM(CASE WHEN YearlyRevenue >= 50000 THEN YearlyRevenue END) as PlatinumRevenue,
            SUM(CASE WHEN YearlyRevenue >= 25000 AND YearlyRevenue < 50000 THEN YearlyRevenue END) as GoldRevenue,
            SUM(CASE WHEN YearlyRevenue >= 10000 AND YearlyRevenue < 25000 THEN YearlyRevenue END) as SilverRevenue,
            SUM(CASE WHEN YearlyRevenue >= 5000 AND YearlyRevenue < 10000 THEN YearlyRevenue END) as BronzeRevenue,
            SUM(CASE WHEN YearlyRevenue < 5000 THEN YearlyRevenue END) as StandardRevenue
        FROM (
            SELECT 
                YEAR(t.Time) as Year,
                t.CustomerID,
                SUM(t.Total) as YearlyRevenue
            FROM [dbo].[Transaction] t
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time), t.CustomerID
        ) CustomerYearly
        GROUP BY Year
        ORDER BY Year
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_monthly_seasonality(self):
        """Get monthly patterns with fixed decimal precision"""
        query = """
        WITH MonthlyData AS (
            SELECT 
                MONTH(t.Time) as Month,
                DATENAME(MONTH, MIN(t.Time)) as MonthName,
                AVG(CAST(DailyRevenue as FLOAT)) as AvgDailyRevenue,
                AVG(CAST(DailyTransactions as FLOAT)) as AvgDailyTransactions
            FROM (
                SELECT 
                    CAST(t.Time as DATE) as Date,
                    SUM(t.Total) as DailyRevenue,
                    COUNT(*) as DailyTransactions
                FROM [dbo].[Transaction] t
                WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
                GROUP BY CAST(t.Time as DATE)
            ) Daily
            GROUP BY MONTH(Date)
        ),
        YearlyAvg AS (
            SELECT AVG(AvgDailyRevenue) as OverallAvgRevenue
            FROM MonthlyData
        )
        SELECT 
            m.Month,
            m.MonthName,
            m.AvgDailyRevenue,
            m.AvgDailyTransactions,
            CAST((m.AvgDailyRevenue / y.OverallAvgRevenue * 100) as DECIMAL(10,2)) as SeasonalIndex
        FROM MonthlyData m
        CROSS JOIN YearlyAvg y
        ORDER BY m.Month
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_top_customers_evolution(self):
        """Track top customers over time"""
        query = """
        SELECT 
            Year,
            CustomerRank,
            CustomerName,
            Revenue,
            Transactions,
            AvgTransaction
        FROM (
            SELECT 
                YEAR(t.Time) as Year,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(t.Total) as Revenue,
                COUNT(*) as Transactions,
                AVG(t.Total) as AvgTransaction,
                ROW_NUMBER() OVER (PARTITION BY YEAR(t.Time) ORDER BY SUM(t.Total) DESC) as CustomerRank
            FROM [dbo].[Transaction] t
            JOIN dbo.Customer c ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
            GROUP BY YEAR(t.Time), c.Company, c.FirstName, c.LastName
        ) RankedCustomers
        WHERE CustomerRank <= 20
        ORDER BY Year, CustomerRank
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_comprehensive_summary(self):
        """Get a comprehensive 5-year summary"""
        query = """
        -- Overall 5-year metrics
        SELECT 
            MIN(YEAR(t.Time)) as StartYear,
            MAX(YEAR(t.Time)) as EndYear,
            COUNT(DISTINCT t.CustomerID) as TotalUniqueCustomers,
            COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
            SUM(t.Total) as TotalRevenue,
            AVG(t.Total) as OverallAvgTransaction,
            COUNT(DISTINCT CAST(t.Time as DATE)) as TotalBusinessDays,
            SUM(t.Total) / COUNT(DISTINCT CAST(t.Time as DATE)) as AvgDailyRevenue,
            -- Best periods
            (SELECT TOP 1 YEAR(Time) 
             FROM [dbo].[Transaction] 
             WHERE Time >= '2019-01-01' AND Time <= '2023-12-31'
             GROUP BY YEAR(Time) 
             ORDER BY SUM(Total) DESC) as BestYear,
            (SELECT TOP 1 DATENAME(MONTH, Time) 
             FROM [dbo].[Transaction] 
             WHERE Time >= '2019-01-01' AND Time <= '2023-12-31'
             GROUP BY MONTH(Time), DATENAME(MONTH, Time) 
             ORDER BY SUM(Total) DESC) as BestMonth
        FROM [dbo].[Transaction] t
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        """
        
        summary = self.db.execute_query(query).iloc[0].to_dict() if not self.db.execute_query(query).empty else {}
        
        # Category breakdown
        category_query = """
        SELECT TOP 5
            ISNULL(cat.Name, 'Uncategorized') as Category,
            SUM(te.Price * te.Quantity) as Revenue,
            CAST(SUM(te.Price * te.Quantity) * 100.0 / 
                (SELECT SUM(te2.Price * te2.Quantity) 
                 FROM [dbo].[Transaction] t2
                 JOIN TransactionEntry te2 ON te2.TransactionNumber = t2.TransactionNumber
                 WHERE t2.Time >= '2019-01-01' AND t2.Time <= '2023-12-31') 
                as DECIMAL(5,2)) as PercentOfTotal
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= '2019-01-01' AND t.Time <= '2023-12-31'
        GROUP BY cat.Name
        ORDER BY Revenue DESC
        """
        
        categories = self.db.execute_query(category_query).to_dict('records')
        
        return {
            "summary": summary,
            "top_categories": categories
        }
    
    def generate_complete_report(self):
        """Generate complete fixed report"""
        report = {
            "report_date": datetime.now().isoformat(),
            "period": "2019-01-01 to 2023-12-31",
            "yearly_growth": None,
            "category_growth": None,
            "customer_segments": None,
            "seasonality": None,
            "top_customers": None,
            "overall_summary": None
        }
        
        try:
            self.db.connect()
            
            logger.info("Generating fixed historical analysis...")
            report["yearly_growth"] = self.get_yearly_growth_fixed()
            report["category_growth"] = self.get_category_growth_fixed()
            report["customer_segments"] = self.get_customer_segments_over_time()
            report["seasonality"] = self.get_monthly_seasonality()
            report["top_customers"] = self.get_top_customers_evolution()
            report["overall_summary"] = self.get_comprehensive_summary()
            
            return report
            
        finally:
            self.db.close()
    
    def save_report(self, report):
        """Save report with visualizable summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_file = f"historical_fixed_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        txt_file = f"historical_fixed_summary_{timestamp}.txt"
        with open(txt_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("5-YEAR BUSINESS PERFORMANCE REPORT (2019-2023)\n")
            f.write("="*80 + "\n\n")
            
            # Overall Summary
            if report.get("overall_summary"):
                summary = report["overall_summary"]["summary"]
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-"*40 + "\n")
                f.write(f"Total Revenue (5 years): ${summary.get('TotalRevenue', 0):,.0f}\n")
                f.write(f"Total Customers: {summary.get('TotalUniqueCustomers', 0):,}\n")
                f.write(f"Total Transactions: {summary.get('TotalTransactions', 0):,}\n")
                f.write(f"Average Daily Revenue: ${summary.get('AvgDailyRevenue', 0):,.0f}\n")
                f.write(f"Best Year: {summary.get('BestYear')}\n")
                f.write(f"Best Month: {summary.get('BestMonth')}\n\n")
            
            # Yearly Performance
            if report.get("yearly_growth"):
                f.write("YEARLY PERFORMANCE\n")
                f.write("-"*40 + "\n")
                f.write("Year  | Revenue      | Customers | Growth\n")
                f.write("------|-------------|-----------|-------\n")
                for year in report["yearly_growth"]:
                    growth = year.get('RevenueGrowthPercent', 0)
                    growth_str = f"{growth:+.1f}%" if growth else "  N/A"
                    f.write(f"{year['Year']} | ${year['TotalRevenue']:>11,.0f} | "
                           f"{year['UniqueCustomers']:>9} | {growth_str:>6}\n")
            
            # Customer Segments
            if report.get("customer_segments"):
                f.write("\n\nCUSTOMER SEGMENT EVOLUTION\n")
                f.write("-"*40 + "\n")
                f.write("Year | Platinum | Gold | Silver | Bronze | Standard\n")
                f.write("-----|----------|------|--------|--------|---------\n")
                for year in report["customer_segments"]:
                    f.write(f"{year['Year']} | {year['PlatinumCustomers']:>8} | "
                           f"{year['GoldCustomers']:>4} | {year['SilverCustomers']:>6} | "
                           f"{year['BronzeCustomers']:>6} | {year['StandardCustomers']:>8}\n")
            
            # Top Categories
            if report.get("overall_summary") and "top_categories" in report["overall_summary"]:
                f.write("\n\nTOP CATEGORIES (5-Year Total)\n")
                f.write("-"*40 + "\n")
                for cat in report["overall_summary"]["top_categories"]:
                    f.write(f"{cat['Category']:.<30} ${cat['Revenue']:>12,.0f} ({cat['PercentOfTotal']:.1f}%)\n")
            
            # Seasonality
            if report.get("seasonality"):
                f.write("\n\nSEASONAL PATTERNS\n")
                f.write("-"*40 + "\n")
                f.write("Month     | Seasonal Index | Avg Daily Revenue\n")
                f.write("----------|---------------|------------------\n")
                for month in report["seasonality"]:
                    f.write(f"{month['MonthName']:.<9} | {month['SeasonalIndex']:>13.1f} | "
                           f"${month['AvgDailyRevenue']:>16,.0f}\n")
            
            # Calculate key metrics
            if report.get("yearly_growth") and len(report["yearly_growth"]) > 1:
                first_year = report["yearly_growth"][0]
                last_year = report["yearly_growth"][-1]
                total_growth = ((last_year['TotalRevenue'] - first_year['TotalRevenue']) / 
                               first_year['TotalRevenue'] * 100) if first_year['TotalRevenue'] > 0 else 0
                years = last_year['Year'] - first_year['Year']
                cagr = ((float(last_year['TotalRevenue']) / float(first_year['TotalRevenue'])) ** (1/years) - 1) * 100 if years > 0 and first_year['TotalRevenue'] > 0 else 0
                
                f.write("\n\nKEY GROWTH METRICS\n")
                f.write("-"*40 + "\n")
                f.write(f"Total Revenue Growth: {total_growth:+.1f}%\n")
                f.write(f"5-Year CAGR: {cagr:.2f}%\n")
                f.write(f"Customer Base Growth: {last_year['UniqueCustomers'] - first_year['UniqueCustomers']:+,}\n")
            
            f.write("\n" + "="*80 + "\n")
        
        return json_file, txt_file

def main():
    analyzer = HistoricalAnalyticsFixed()
    report = analyzer.generate_complete_report()
    json_file, txt_file = analyzer.save_report(report)
    
    print(f"\n✅ Analysis complete!")
    print(f"   JSON: {json_file}")
    print(f"   Summary: {txt_file}")
    
    # Print quick insights
    if report.get("overall_summary"):
        summary = report["overall_summary"]["summary"]
        print(f"\n📊 5-Year Total: ${summary.get('TotalRevenue', 0):,.0f}")
        print(f"👥 Total Customers: {summary.get('TotalUniqueCustomers', 0):,}")
        
    if report.get("yearly_growth") and len(report["yearly_growth"]) > 1:
        first = report["yearly_growth"][0]
        last = report["yearly_growth"][-1]
        growth = ((last['TotalRevenue'] - first['TotalRevenue']) / first['TotalRevenue'] * 100) if first['TotalRevenue'] > 0 else 0
        print(f"📈 Total Growth: {growth:+.1f}%")

if __name__ == "__main__":
    main()