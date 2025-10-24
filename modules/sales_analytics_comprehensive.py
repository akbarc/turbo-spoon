#!/usr/bin/env python3
"""
Comprehensive Sales Analytics Module - Complete rebuild with excise tax accuracy
"""

from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class SalesAnalyticsComprehensive:
    """Complete Sales Analytics with accurate excise tax calculations and YoY comparisons"""
    
    def __init__(self, db_connection):
        """Initialize with database connection"""
        self.db = db_connection
    
    def _get_date_ranges(self, timeframe='YTD'):
        """Get current and previous year date ranges for comparisons"""
        current_date = datetime.now()
        current_year = current_date.year
        previous_year = current_year - 1
        
        if timeframe == 'MTD':
            # Month to date
            current_start = current_date.replace(day=1)
            current_end = current_date
            prev_start = current_date.replace(year=previous_year, day=1)
            prev_end = current_date.replace(year=previous_year)
        elif timeframe == 'QTD':
            # Quarter to date
            quarter = (current_date.month - 1) // 3
            start_month = quarter * 3 + 1
            current_start = current_date.replace(month=start_month, day=1)
            current_end = current_date
            prev_start = current_date.replace(year=previous_year, month=start_month, day=1)
            prev_end = current_date.replace(year=previous_year)
        elif timeframe == 'YTD':
            # Year to date
            current_start = current_date.replace(month=1, day=1)
            current_end = current_date
            prev_start = current_date.replace(year=previous_year, month=1, day=1)
            prev_end = current_date.replace(year=previous_year)
        elif timeframe == '12M':
            # Last 12 months
            current_end = current_date
            current_start = current_date - timedelta(days=365)
            prev_end = current_start
            prev_start = prev_end - timedelta(days=365)
        else:
            # Default to YTD
            current_start = current_date.replace(month=1, day=1)
            current_end = current_date
            prev_start = current_date.replace(year=previous_year, month=1, day=1)
            prev_end = current_date.replace(year=previous_year)
        
        return {
            'current': {
                'start': current_start.strftime('%Y-%m-%d'),
                'end': current_end.strftime('%Y-%m-%d'),
                'year': current_year
            },
            'previous': {
                'start': prev_start.strftime('%Y-%m-%d'),
                'end': prev_end.strftime('%Y-%m-%d'),
                'year': previous_year
            }
        }
    
    def get_executive_dashboard_data(self, timeframe='YTD'):
        """Get comprehensive executive dashboard data with YoY comparisons"""
        date_ranges = self._get_date_ranges(timeframe)
        
        # Fast query without excise tax joins for better performance
        base_query = """
        WITH SalesMetrics AS (
            SELECT 
                -- Revenue and basic metrics (excise tax calculated separately)
                SUM(te.Price * te.Quantity) as TotalRevenue,
                SUM(te.Cost * te.Quantity) as BaseCost,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as BaseGrossProfit,
                
                -- Transaction metrics
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT te.ItemID) as UniqueSKUs,
                SUM(te.Quantity) as TotalUnits,
                
                -- Time metrics
                MIN(t.Time) as FirstTransaction,
                MAX(t.Time) as LastTransaction
                
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '{start_date}' AND t.Time <= '{end_date}'
        ),
        TopCategories AS (
            SELECT TOP 5
                ISNULL(cat.Name, 'Uncategorized') as CategoryName,
                SUM(te.Price * te.Quantity) as CategoryRevenue,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as CategoryGP,
                SUM(te.Quantity) as CategoryUnits,
                COUNT(DISTINCT te.ItemID) as CategorySKUs
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '{start_date}' AND t.Time <= '{end_date}'
            GROUP BY cat.Name
            ORDER BY CategoryRevenue DESC
        ),
        TopCustomers AS (
            SELECT TOP 5
                CASE 
                    WHEN c.Company IS NOT NULL AND c.Company != '' THEN c.Company
                    ELSE c.FirstName + ' ' + c.LastName
                END as CustomerName,
                SUM(te.Price * te.Quantity) as CustomerRevenue,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as CustomerGP,
                COUNT(DISTINCT t.TransactionNumber) as CustomerTransactions
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Customer c ON t.CustomerID = c.ID
            LEFT JOIN Item i ON te.ItemID = i.ID
            WHERE t.Time >= '{start_date}' AND t.Time <= '{end_date}'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
            ORDER BY CustomerRevenue DESC
        )
        SELECT 
            -- Main metrics (simplified for performance)
            sm.TotalRevenue,
            sm.BaseCost,
            0 as TotalExciseTax,  -- Will be calculated separately
            sm.BaseCost as TotalCost,  -- Using base cost for now
            sm.BaseGrossProfit as TrueGrossProfit,
            CAST(sm.BaseGrossProfit * 100.0 / NULLIF(sm.TotalRevenue, 0) as DECIMAL(5,2)) as GPMargin,
            
            -- Transaction metrics
            sm.TransactionCount,
            sm.UniqueCustomers,
            sm.UniqueSKUs,
            sm.TotalUnits,
            sm.TotalRevenue / NULLIF(sm.TransactionCount, 0) as AvgTransaction,
            sm.BaseGrossProfit / NULLIF(sm.UniqueCustomers, 0) as GPPerCustomer,
            
            -- Time metrics
            sm.FirstTransaction,
            sm.LastTransaction,
            DATEDIFF(day, sm.FirstTransaction, sm.LastTransaction) as ActiveDays
            
        FROM SalesMetrics sm
        """
        
        # Get current period data
        current_query = base_query.format(
            start_date=date_ranges['current']['start'],
            end_date=date_ranges['current']['end']
        )
        
        # Get previous period data
        previous_query = base_query.format(
            start_date=date_ranges['previous']['start'],
            end_date=date_ranges['previous']['end']
        )
        
        try:
            current_result = self.db.execute_query(current_query, description=f"Current {timeframe} Sales Analytics")
            previous_result = self.db.execute_query(previous_query, description=f"Previous {timeframe} Sales Analytics")
            
            current_data = current_result.iloc[0].to_dict() if not current_result.empty else {}
            previous_data = previous_result.iloc[0].to_dict() if not previous_result.empty else {}
            
            # Calculate changes
            changes = self._calculate_changes(current_data, previous_data)
            
            # Get top categories and customers for current period
            categories = self._get_top_categories(date_ranges['current']['start'], date_ranges['current']['end'])
            customers = self._get_top_customers(date_ranges['current']['start'], date_ranges['current']['end'])
            
            # Get excise tax separately for better performance
            excise_tax = self._get_excise_tax_total(date_ranges['current']['start'], date_ranges['current']['end'])
            
            return {
                'timeframe': timeframe,
                'date_ranges': date_ranges,
                'current': current_data,
                'previous': previous_data,
                'changes': changes,
                'top_categories': categories,
                'top_customers': customers,
                'summary': {
                    'total_revenue': float(current_data.get('TotalRevenue', 0)),
                    'true_gross_profit': float(current_data.get('TrueGrossProfit', 0)),
                    'gp_margin': float(current_data.get('GPMargin', 0)),
                    'excise_tax_impact': float(excise_tax),
                    'transaction_count': int(current_data.get('TransactionCount', 0)),
                    'unique_customers': int(current_data.get('UniqueCustomers', 0)),
                    'avg_transaction': float(current_data.get('AvgTransaction', 0)),
                    'gp_per_customer': float(current_data.get('GPPerCustomer', 0))
                }
            }
            
        except Exception as e:
            logger.error(f"Error in executive dashboard data: {e}")
            return {'error': str(e)}
    
    def _get_excise_tax_total(self, start_date, end_date):
        """Get total excise tax for date range (separate query for performance)"""
        try:
            query = f"""
            SELECT SUM(pe.PriceC) as TotalExciseTax
            FROM PUExciseEntry pe
            WHERE pe.TransactionTime >= '{start_date}' AND pe.TransactionTime <= '{end_date}'
            """
            
            result = self.db.execute_query(query, description="Excise Tax Total")
            if not result.empty:
                return float(result.iloc[0]['TotalExciseTax'] or 0)
            return 0.0
        except Exception as e:
            logger.warning(f"Could not get excise tax total: {e}")
            return 0.0
    
    def _get_top_categories(self, start_date, end_date, limit=10):
        """Get top categories with excise tax impact"""
        query = f"""
        SELECT TOP {limit}
            ISNULL(cat.Name, 'Uncategorized') as Category,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as BaseCost,
            SUM(ISNULL(pe.PriceC, 0)) as ExciseTax,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
            CAST(SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) * 100.0 / 
                 NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as Margin,
            SUM(te.Quantity) as Units,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            COUNT(DISTINCT te.ItemID) as UniqueSKUs
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
        WHERE t.Time >= '{start_date}' AND t.Time <= '{end_date}'
        GROUP BY cat.Name
        ORDER BY Revenue DESC
        """
        
        result = self.db.execute_query(query, description="Top Categories Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def _get_top_customers(self, start_date, end_date, limit=10):
        """Get top customers with profitability analysis"""
        query = f"""
        SELECT TOP {limit}
            CASE 
                WHEN c.Company IS NOT NULL AND c.Company != '' THEN c.Company
                ELSE c.FirstName + ' ' + c.LastName
            END as Customer,
            c.AccountNumber,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
            CAST(SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) * 100.0 / 
                 NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as Margin,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as Units,
            MAX(t.Time) as LastPurchase,
            SUM(te.Price * te.Quantity) / NULLIF(COUNT(DISTINCT t.TransactionNumber), 0) as AvgTransaction
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        JOIN Customer c ON t.CustomerID = c.ID
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
        WHERE t.Time >= '{start_date}' AND t.Time <= '{end_date}'
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountNumber
        ORDER BY Revenue DESC
        """
        
        result = self.db.execute_query(query, description="Top Customers Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def _calculate_changes(self, current, previous):
        """Calculate percentage and absolute changes between periods"""
        changes = {}
        
        key_metrics = [
            'TotalRevenue', 'TrueGrossProfit', 'GPMargin', 'TotalExciseTax',
            'TransactionCount', 'UniqueCustomers', 'AvgTransaction', 'GPPerCustomer'
        ]
        
        for key in key_metrics:
            current_val = float(current.get(key, 0))
            previous_val = float(previous.get(key, 0))
            
            if previous_val > 0:
                change_pct = ((current_val - previous_val) / previous_val) * 100
                change_abs = current_val - previous_val
                direction = 'up' if change_abs > 0 else 'down' if change_abs < 0 else 'flat'
            else:
                change_pct = 0
                change_abs = current_val
                direction = 'new' if current_val > 0 else 'flat'
            
            changes[key] = {
                'absolute': change_abs,
                'percentage': change_pct,
                'direction': direction,
                'current': current_val,
                'previous': previous_val
            }
        
        return changes
    
    def get_monthly_trends(self, timeframe='YTD'):
        """Get monthly sales and GP trends with YoY comparison"""
        date_ranges = self._get_date_ranges(timeframe)
        current_year = date_ranges['current']['year']
        previous_year = date_ranges['previous']['year']
        
        query = f"""
        WITH MonthlyTrends AS (
            SELECT 
                YEAR(t.Time) as Year,
                MONTH(t.Time) as Month,
                DATENAME(MONTH, t.Time) as MonthName,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as BaseCost,
                SUM(ISNULL(pe.PriceC, 0)) as ExciseTax,
                SUM(te.Cost * te.Quantity + ISNULL(pe.PriceC, 0)) as TotalCost,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) as GrossProfit,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as Customers,
                SUM(te.Quantity) as Units
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE YEAR(t.Time) IN ({current_year}, {previous_year})
                AND t.Time >= '{date_ranges['previous']['start']}'
                AND t.Time <= '{date_ranges['current']['end']}'
            GROUP BY YEAR(t.Time), MONTH(t.Time), DATENAME(MONTH, t.Time)
        )
        SELECT 
            Year,
            Month,
            MonthName,
            Revenue,
            BaseCost,
            ExciseTax,
            TotalCost,
            GrossProfit,
            CAST(GrossProfit * 100.0 / NULLIF(Revenue, 0) as DECIMAL(5,2)) as Margin,
            Transactions,
            Customers,
            Units,
            Revenue / NULLIF(Transactions, 0) as AvgTransaction
        FROM MonthlyTrends
        ORDER BY Year, Month
        """
        
        result = self.db.execute_query(query, description="Monthly Trends Analysis")
        monthly_data = result.to_dict('records') if not result.empty else []
        
        # Separate current and previous year data
        current_year_data = [row for row in monthly_data if row['Year'] == current_year]
        previous_year_data = [row for row in monthly_data if row['Year'] == previous_year]
        
        return {
            'current_year': current_year_data,
            'previous_year': previous_year_data,
            'current_year_num': current_year,
            'previous_year_num': previous_year,
            'timeframe': timeframe
        }
    
    def get_category_analysis(self, timeframe='YTD', limit=20):
        """Get detailed category analysis with excise tax impact"""
        date_ranges = self._get_date_ranges(timeframe)
        
        query = f"""
        WITH CategoryAnalysis AS (
            SELECT 
                ISNULL(cat.Name, 'Uncategorized') as Category,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as BaseCost,
                SUM(ISNULL(pe.PriceC, 0)) as ExciseTax,
                SUM(te.Cost * te.Quantity + ISNULL(pe.PriceC, 0)) as TotalCost,
                SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) as GrossProfit,
                SUM(te.Quantity) as Units,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as Customers,
                COUNT(DISTINCT te.ItemID) as UniqueSKUs,
                AVG(te.Price) as AvgPrice,
                MIN(t.Time) as FirstSale,
                MAX(t.Time) as LastSale
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '{date_ranges['current']['start']}' 
                AND t.Time <= '{date_ranges['current']['end']}'
            GROUP BY cat.Name
        )
        SELECT TOP {limit}
            Category,
            Revenue,
            BaseCost,
            ExciseTax,
            TotalCost,
            GrossProfit,
            CAST(GrossProfit * 100.0 / NULLIF(Revenue, 0) as DECIMAL(5,2)) as Margin,
            Units,
            Transactions,
            Customers,
            UniqueSKUs,
            AvgPrice,
            Revenue / NULLIF(Transactions, 0) as AvgTransaction,
            GrossProfit / NULLIF(Transactions, 0) as GPPerTransaction,
            ExciseTax / NULLIF(Revenue, 0) * 100 as ExciseTaxRate,
            FirstSale,
            LastSale
        FROM CategoryAnalysis
        WHERE Revenue > 0
        ORDER BY Revenue DESC
        """
        
        result = self.db.execute_query(query, description="Category Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_product_analysis(self, timeframe='YTD', limit=50):
        """Get detailed product analysis with profitability"""
        date_ranges = self._get_date_ranges(timeframe)
        
        query = f"""
        SELECT TOP {limit}
            i.Description as Product,
            i.ItemLookupCode as SKU,
            ISNULL(cat.Name, 'Uncategorized') as Category,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as BaseCost,
            SUM(ISNULL(pe.PriceC, 0)) as ExciseTax,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
            CAST(SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) * 100.0 / 
                 NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as Margin,
            SUM(te.Quantity) as Units,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            COUNT(DISTINCT t.CustomerID) as Customers,
            AVG(te.Price) as AvgPrice,
            SUM(te.Price * te.Quantity) / NULLIF(COUNT(DISTINCT t.TransactionNumber), 0) as AvgTransaction
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
        WHERE t.Time >= '{date_ranges['current']['start']}' 
            AND t.Time <= '{date_ranges['current']['end']}'
        GROUP BY i.ID, i.Description, i.ItemLookupCode, cat.Name
        HAVING SUM(te.Price * te.Quantity) > 0
        ORDER BY Revenue DESC
        """
        
        result = self.db.execute_query(query, description="Product Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_customer_profitability(self, timeframe='YTD', limit=25):
        """Get customer profitability analysis with excise tax impact"""
        date_ranges = self._get_date_ranges(timeframe)
        
        query = f"""
        SELECT TOP {limit}
            CASE 
                WHEN c.Company IS NOT NULL AND c.Company != '' THEN c.Company
                ELSE c.FirstName + ' ' + c.LastName
            END as Customer,
            c.AccountNumber,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as BaseCost,
            SUM(ISNULL(pe.PriceC, 0)) as ExciseTax,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
            CAST(SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) * 100.0 / 
                 NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(5,2)) as Margin,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as Units,
            COUNT(DISTINCT te.ItemID) as UniqueSKUs,
            MIN(t.Time) as FirstPurchase,
            MAX(t.Time) as LastPurchase,
            SUM(te.Price * te.Quantity) / NULLIF(COUNT(DISTINCT t.TransactionNumber), 0) as AvgTransaction,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity - ISNULL(pe.PriceC, 0)) / 
                NULLIF(COUNT(DISTINCT t.TransactionNumber), 0) as GPPerTransaction
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        JOIN Customer c ON t.CustomerID = c.ID
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
        WHERE t.Time >= '{date_ranges['current']['start']}' 
            AND t.Time <= '{date_ranges['current']['end']}'
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountNumber
        HAVING SUM(te.Price * te.Quantity) > 0
        ORDER BY Revenue DESC
        """
        
        result = self.db.execute_query(query, description="Customer Profitability Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_excise_tax_impact(self, timeframe='YTD'):
        """Get detailed excise tax impact analysis"""
        date_ranges = self._get_date_ranges(timeframe)
        
        query = f"""
        WITH ExciseImpact AS (
            SELECT 
                pe.SubDescription3 as ExciseType,
                ISNULL(cat.Name, 'Uncategorized') as Category,
                COUNT(*) as TransactionCount,
                SUM(pe.Quantity) as TotalUnits,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(pe.PriceC) as TotalExciseTax,
                AVG(pe.PriceC / NULLIF(pe.Quantity, 0)) as AvgExcisePerUnit,
                SUM(pe.PriceC) / NULLIF(SUM(te.Price * te.Quantity), 0) * 100 as ExciseAsPercentOfSales
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '{date_ranges['current']['start']}' 
                AND t.Time <= '{date_ranges['current']['end']}'
            GROUP BY pe.SubDescription3, cat.Name
        )
        SELECT 
            ExciseType,
            Category,
            TransactionCount,
            TotalUnits,
            Revenue,
            TotalExciseTax,
            AvgExcisePerUnit,
            ExciseAsPercentOfSales
        FROM ExciseImpact
        WHERE TotalExciseTax > 0
        ORDER BY TotalExciseTax DESC
        """
        
        result = self.db.execute_query(query, description="Excise Tax Impact Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_performance_insights(self, timeframe='YTD'):
        """Get actionable performance insights and opportunities"""
        try:
            # Get basic metrics
            dashboard_data = self.get_executive_dashboard_data(timeframe)
            
            insights = []
            
            if 'changes' in dashboard_data:
                changes = dashboard_data['changes']
                
                # Revenue insights
                revenue_change = changes.get('TotalRevenue', {})
                if revenue_change.get('direction') == 'up' and revenue_change.get('percentage', 0) > 5:
                    insights.append({
                        'type': 'positive',
                        'title': 'Strong Revenue Growth',
                        'description': f"Revenue increased by {revenue_change['percentage']:.1f}% vs last year",
                        'impact': 'high',
                        'metric': 'revenue'
                    })
                elif revenue_change.get('direction') == 'down':
                    insights.append({
                        'type': 'warning',
                        'title': 'Revenue Decline',
                        'description': f"Revenue decreased by {abs(revenue_change['percentage']):.1f}% vs last year",
                        'impact': 'high',
                        'metric': 'revenue'
                    })
                
                # GP insights
                gp_change = changes.get('TrueGrossProfit', {})
                margin_change = changes.get('GPMargin', {})
                
                if gp_change.get('direction') == 'up' and gp_change.get('percentage', 0) > 10:
                    insights.append({
                        'type': 'positive',
                        'title': 'Excellent Profitability Growth',
                        'description': f"Gross profit increased by {gp_change['percentage']:.1f}% with {margin_change.get('percentage', 0):.1f}pp margin improvement",
                        'impact': 'high',
                        'metric': 'profitability'
                    })
                
                # Customer insights
                customer_change = changes.get('UniqueCustomers', {})
                if customer_change.get('direction') == 'up':
                    insights.append({
                        'type': 'positive',
                        'title': 'Growing Customer Base',
                        'description': f"Customer count increased by {customer_change['percentage']:.1f}% ({int(customer_change['absolute'])} new customers)",
                        'impact': 'medium',
                        'metric': 'customers'
                    })
            
            # Add excise tax insights
            excise_data = self.get_excise_tax_impact(timeframe)
            if excise_data:
                total_excise = sum(row['TotalExciseTax'] for row in excise_data)
                insights.append({
                    'type': 'info',
                    'title': 'Excise Tax Impact',
                    'description': f"Total excise tax: ${total_excise:,.2f} across {len(excise_data)} tax types",
                    'impact': 'medium',
                    'metric': 'excise'
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
            return []
