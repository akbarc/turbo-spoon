"""
Fixed Wholesale vs Retail Analysis Module
Corrects all calculation and aggregation issues
"""

import logging
from datetime import datetime, timedelta
import pandas as pd
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

class WholesaleRetailAnalysis:
    """Fixed wholesale vs retail analysis with proper calculations"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.wholesale_threshold = 5000  # Orders >= $5000 are wholesale
        
    def get_analysis(self, period='ytd', year=None):
        """Get wholesale vs retail analysis with fixed calculations"""
        try:
            if period == 'comparative':
                return self.get_comparative_analysis()
            elif period == 'ytd':
                return self.get_ytd_analysis()
            elif period == 'monthly' and year:
                return self.get_monthly_analysis(year)
            else:
                return self.get_ytd_analysis()
                
        except Exception as e:
            logger.error(f"Wholesale retail analysis error: {e}")
            raise
    
    def get_comparative_analysis(self):
        """Get year-over-year comparative analysis with proper aggregation"""
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day
        
        results = []
        
        # Get data for last 3 years YTD
        for year_offset in range(3):
            year = current_year - year_offset
            period_name = f"{year} YTD"
            
            # Calculate YTD dates for each year
            start_date = f"{year}-01-01"
            if year == current_year:
                end_date = datetime.now().strftime('%Y-%m-%d')
            else:
                # Use same YTD period for comparison
                end_date = f"{year}-{current_month:02d}-{current_day:02d}"
            
            query = """
            WITH OrderDetails AS (
                SELECT 
                    t.TransactionNumber,
                    t.CustomerID,
                    t.Total as OrderTotal,
                    t.Time as OrderDate,
                    CASE 
                        WHEN t.Total >= %s THEN 'Wholesale'
                        ELSE 'Retail'
                    END as OrderType,
                    -- Calculate line-level profit with tobacco uplifts
                    SUM(te.Price * te.Quantity) as Revenue,
                    SUM(
                        CASE 
                            WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                            WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                            ELSE te.Cost * te.Quantity
                        END
                    ) as TotalCost,
                    SUM(
                        te.Price * te.Quantity - 
                        CASE 
                            WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                            WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                            ELSE te.Cost * te.Quantity
                        END
                    ) as GrossProfit
                FROM [dbo].[Transaction] t
                JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
                LEFT JOIN Item i ON te.ItemID = i.ID
                LEFT JOIN Category cat ON i.CategoryID = cat.ID
                WHERE t.Time >= %s AND t.Time <= %s
                GROUP BY t.TransactionNumber, t.CustomerID, t.Total, t.Time
            )
            SELECT 
                OrderType,
                COUNT(DISTINCT TransactionNumber) as OrderCount,
                COUNT(DISTINCT CustomerID) as UniqueCustomers,
                SUM(Revenue) as TotalRevenue,
                SUM(TotalCost) as TotalCost,
                SUM(GrossProfit) as GrossProfit,
                AVG(OrderTotal) as AvgOrderValue,
                MAX(OrderTotal) as MaxOrder,
                MIN(OrderTotal) as MinOrder
            FROM OrderDetails
            GROUP BY OrderType
            """
            
            params = (self.wholesale_threshold, start_date, end_date)
            df = self.db.execute_query(query, params, f"Wholesale/Retail {period_name}")
            
            # Initialize period data
            period_data = {
                'period': period_name,
                'year': year,
                'start_date': start_date,
                'end_date': end_date,
                'wholesale_sales': 0,
                'wholesale_gp': 0,
                'wholesale_orders': 0,
                'wholesale_customers': 0,
                'retail_sales': 0,
                'retail_gp': 0,
                'retail_orders': 0,
                'retail_customers': 0,
                'total_sales': 0,
                'total_gp': 0,
                'total_orders': 0
            }
            
            # Process results
            for _, row in df.iterrows():
                order_type = row['OrderType'].lower()
                if order_type == 'wholesale':
                    period_data['wholesale_sales'] = float(row['TotalRevenue'] or 0)
                    period_data['wholesale_gp'] = float(row['GrossProfit'] or 0)
                    period_data['wholesale_orders'] = int(row['OrderCount'] or 0)
                    period_data['wholesale_customers'] = int(row['UniqueCustomers'] or 0)
                else:  # retail
                    period_data['retail_sales'] = float(row['TotalRevenue'] or 0)
                    period_data['retail_gp'] = float(row['GrossProfit'] or 0)
                    period_data['retail_orders'] = int(row['OrderCount'] or 0)
                    period_data['retail_customers'] = int(row['UniqueCustomers'] or 0)
            
            # Calculate totals
            period_data['total_sales'] = period_data['wholesale_sales'] + period_data['retail_sales']
            period_data['total_gp'] = period_data['wholesale_gp'] + period_data['retail_gp']
            period_data['total_orders'] = period_data['wholesale_orders'] + period_data['retail_orders']
            
            # Calculate percentages
            if period_data['total_sales'] > 0:
                period_data['wholesale_pct'] = (period_data['wholesale_sales'] / period_data['total_sales']) * 100
                period_data['retail_pct'] = (period_data['retail_sales'] / period_data['total_sales']) * 100
                period_data['gp_margin'] = (period_data['total_gp'] / period_data['total_sales']) * 100
            else:
                period_data['wholesale_pct'] = 0
                period_data['retail_pct'] = 0
                period_data['gp_margin'] = 0
            
            results.append(period_data)
        
        return results
    
    def get_ytd_analysis(self):
        """Get current year-to-date analysis"""
        current_year = datetime.now().year
        start_date = f"{current_year}-01-01"
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        query = """
        WITH OrderAnalysis AS (
            SELECT 
                t.TransactionNumber,
                t.CustomerID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                t.Total as OrderTotal,
                t.Time as OrderDate,
                CASE 
                    WHEN t.Total >= %s THEN 'Wholesale'
                    ELSE 'Retail'
                END as OrderType,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as TotalCost,
                SUM(
                    te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as GrossProfit
            FROM [dbo].[Transaction] t
            JOIN dbo.Customer c ON t.CustomerID = c.ID
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= %s AND t.Time <= %s
            GROUP BY t.TransactionNumber, t.CustomerID, c.Company, c.FirstName, c.LastName, t.Total, t.Time
        )
        SELECT 
            OrderType,
            COUNT(DISTINCT TransactionNumber) as OrderCount,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            SUM(Revenue) as TotalRevenue,
            SUM(TotalCost) as TotalCost,
            SUM(GrossProfit) as GrossProfit,
            AVG(OrderTotal) as AvgOrderValue,
            -- Calculate GP margin properly
            CAST(SUM(GrossProfit) * 100.0 / NULLIF(SUM(Revenue), 0) as DECIMAL(5,2)) as GPMargin
        FROM OrderAnalysis
        GROUP BY OrderType
        
        UNION ALL
        
        SELECT 
            'Total' as OrderType,
            COUNT(DISTINCT TransactionNumber) as OrderCount,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            SUM(Revenue) as TotalRevenue,
            SUM(TotalCost) as TotalCost,
            SUM(GrossProfit) as GrossProfit,
            AVG(OrderTotal) as AvgOrderValue,
            CAST(SUM(GrossProfit) * 100.0 / NULLIF(SUM(Revenue), 0) as DECIMAL(5,2)) as GPMargin
        FROM OrderAnalysis
        """
        
        params = (self.wholesale_threshold, start_date, end_date)
        return self.db.execute_query(query, params, "YTD Analysis")
    
    def get_monthly_analysis(self, year):
        """Get monthly breakdown for specified year"""
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        query = """
        WITH MonthlyOrders AS (
            SELECT 
                MONTH(t.Time) as Month,
                DATENAME(MONTH, t.Time) as MonthName,
                t.TransactionNumber,
                t.CustomerID,
                t.Total as OrderTotal,
                CASE 
                    WHEN t.Total >= %s THEN 'Wholesale'
                    ELSE 'Retail'
                END as OrderType,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as TotalCost,
                SUM(
                    te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as GrossProfit
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= %s AND t.Time <= %s
            GROUP BY MONTH(t.Time), DATENAME(MONTH, t.Time), t.TransactionNumber, t.CustomerID, t.Total
        )
        SELECT 
            Month,
            MonthName,
            OrderType,
            COUNT(DISTINCT TransactionNumber) as OrderCount,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            SUM(Revenue) as TotalRevenue,
            SUM(GrossProfit) as GrossProfit,
            AVG(OrderTotal) as AvgOrderValue
        FROM MonthlyOrders
        GROUP BY Month, MonthName, OrderType
        ORDER BY Month, OrderType
        """
        
        params = (self.wholesale_threshold, start_date, end_date)
        df = self.db.execute_query(query, params, f"Monthly Analysis {year}")
        
        # Pivot and calculate totals
        monthly_results = []
        months = df['Month'].unique()
        
        for month in sorted(months):
            month_data = df[df['Month'] == month]
            month_name = month_data.iloc[0]['MonthName'] if not month_data.empty else ''
            
            result = {
                'month': int(month),
                'month_name': month_name,
                'wholesale_sales': 0,
                'wholesale_gp': 0,
                'wholesale_orders': 0,
                'retail_sales': 0,
                'retail_gp': 0,
                'retail_orders': 0,
                'total_sales': 0,
                'total_gp': 0,
                'total_orders': 0
            }
            
            for _, row in month_data.iterrows():
                if row['OrderType'] == 'Wholesale':
                    result['wholesale_sales'] = float(row['TotalRevenue'] or 0)
                    result['wholesale_gp'] = float(row['GrossProfit'] or 0)
                    result['wholesale_orders'] = int(row['OrderCount'] or 0)
                else:
                    result['retail_sales'] = float(row['TotalRevenue'] or 0)
                    result['retail_gp'] = float(row['GrossProfit'] or 0)
                    result['retail_orders'] = int(row['OrderCount'] or 0)
            
            result['total_sales'] = result['wholesale_sales'] + result['retail_sales']
            result['total_gp'] = result['wholesale_gp'] + result['retail_gp']
            result['total_orders'] = result['wholesale_orders'] + result['retail_orders']
            
            # Calculate margins
            if result['total_sales'] > 0:
                result['gp_margin'] = (result['total_gp'] / result['total_sales']) * 100
            else:
                result['gp_margin'] = 0
            
            monthly_results.append(result)
        
        return monthly_results
    
    def get_wholesale_customers(self, limit=50):
        """Get detailed wholesale customer information"""
        query = """
        WITH CustomerAnalysis AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                c.Company,
                c.CreditLimit,
                c.AccountBalance,
                -- Calculate 12-month sales
                SUM(CASE WHEN t.Time >= DATEADD(MONTH, -12, GETDATE()) THEN t.Total ELSE 0 END) as Sales12Months,
                -- Wholesale orders
                COUNT(CASE WHEN t.Total >= %s AND t.Time >= DATEADD(MONTH, -12, GETDATE()) THEN 1 END) as WholesaleOrders,
                -- Total orders
                COUNT(CASE WHEN t.Time >= DATEADD(MONTH, -12, GETDATE()) THEN 1 END) as TotalOrders,
                -- Average order value
                AVG(CASE WHEN t.Time >= DATEADD(MONTH, -12, GETDATE()) THEN t.Total END) as AvgOrderValue,
                -- Last order date
                MAX(t.Time) as LastOrderDate
            FROM dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.CreditLimit, c.AccountBalance
            HAVING COUNT(CASE WHEN t.Total >= %s AND t.Time >= DATEADD(MONTH, -12, GETDATE()) THEN 1 END) > 0
        ),
        NSFData AS (
            SELECT 
                p.CustomerID,
                COUNT(CASE WHEN p.Comment LIKE '%NSF%' OR p.Comment LIKE '%RETURN%' THEN 1 END) as NSFCount
            FROM Payment p
            WHERE p.Time >= DATEADD(YEAR, -1, GETDATE())
            GROUP BY p.CustomerID
        )
        SELECT TOP %s
            ca.CustomerName as name,
            ca.Company as company,
            ca.Sales12Months as sales_12months,
            ca.WholesaleOrders as wholesale_orders,
            ca.TotalOrders as total_orders,
            ca.AvgOrderValue as avg_order_value,
            ca.AccountBalance as account_balance,
            ca.CreditLimit as credit_limit,
            CASE 
                WHEN ca.CreditLimit > 0 THEN 'NET 30'
                ELSE 'CASH'
            END as payment_terms,
            ISNULL(nsf.NSFCount, 0) as nsf_count,
            ca.LastOrderDate as last_order_date,
            DATEDIFF(DAY, ca.LastOrderDate, GETDATE()) as days_since_last_order
        FROM CustomerAnalysis ca
        LEFT JOIN NSFData nsf ON ca.ID = nsf.CustomerID
        ORDER BY ca.Sales12Months DESC
        """
        
        params = (self.wholesale_threshold, self.wholesale_threshold, limit)
        df = self.db.execute_query(query, params, "Wholesale Customers")
        
        return df.to_dict('records')
    
    def get_category_analysis(self):
        """Analyze wholesale vs retail by category"""
        current_year = datetime.now().year
        start_date = f"{current_year}-01-01"
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        query = """
        WITH CategoryOrders AS (
            SELECT 
                ISNULL(cat.Name, 'Uncategorized') as Category,
                CASE 
                    WHEN t.Total >= %s THEN 'Wholesale'
                    ELSE 'Retail'
                END as OrderType,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as GrossProfit,
                COUNT(DISTINCT t.TransactionNumber) as OrderCount
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= %s AND t.Time <= %s
            GROUP BY cat.Name, 
                CASE WHEN t.Total >= %s THEN 'Wholesale' ELSE 'Retail' END
        )
        SELECT 
            Category,
            SUM(CASE WHEN OrderType = 'Wholesale' THEN Revenue ELSE 0 END) as WholesaleRevenue,
            SUM(CASE WHEN OrderType = 'Retail' THEN Revenue ELSE 0 END) as RetailRevenue,
            SUM(Revenue) as TotalRevenue,
            SUM(CASE WHEN OrderType = 'Wholesale' THEN GrossProfit ELSE 0 END) as WholesaleGP,
            SUM(CASE WHEN OrderType = 'Retail' THEN GrossProfit ELSE 0 END) as RetailGP,
            SUM(GrossProfit) as TotalGP,
            CAST(SUM(CASE WHEN OrderType = 'Wholesale' THEN Revenue ELSE 0 END) * 100.0 / 
                NULLIF(SUM(Revenue), 0) as DECIMAL(5,2)) as WholesalePct
        FROM CategoryOrders
        GROUP BY Category
        HAVING SUM(Revenue) > 1000
        ORDER BY TotalRevenue DESC
        """
        
        params = (self.wholesale_threshold, start_date, end_date, self.wholesale_threshold)
        return self.db.execute_query(query, params, "Category Analysis")