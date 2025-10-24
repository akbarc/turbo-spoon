#!/usr/bin/env python3
"""
GP Analysis Module - Deep profitability insights for business operations
"""

from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class GPAnalysis:
    """Comprehensive Gross Profit Analysis"""
    
    def __init__(self, db_connection):
        """Initialize with database connection"""
        self.db = db_connection
    
    def _get_date_filter(self, timeframe='YTD'):
        """Build date filter based on timeframe"""
        current_date = datetime.now()
        current_year = current_date.year
        
        if timeframe == 'MTD':
            start_date = current_date.replace(day=1).strftime('%Y-%m-%d')
            end_date = current_date.strftime('%Y-%m-%d')
        elif timeframe == 'QTD':
            quarter = (current_date.month - 1) // 3
            start_month = quarter * 3 + 1
            start_date = current_date.replace(month=start_month, day=1).strftime('%Y-%m-%d')
            end_date = current_date.strftime('%Y-%m-%d')
        elif timeframe == 'YTD':
            start_date = f"{current_year}-01-01"
            end_date = current_date.strftime('%Y-%m-%d')
        elif timeframe == '12M':
            start_date = (current_date - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = current_date.strftime('%Y-%m-%d')
        else:  # Default to YTD
            start_date = f"{current_year}-01-01"
            end_date = current_date.strftime('%Y-%m-%d')
        
        return f"t.Time >= '{start_date}' AND t.Time <= '{end_date}'"
    
    def get_executive_summary(self, timeframe='YTD'):
        """Get high-level GP metrics for executives"""
        date_filter = self._get_date_filter(timeframe)
        
        query = f"""
        WITH GPMetrics AS (
            SELECT 
                -- Overall metrics
                SUM(te.Price * te.Quantity) as TotalRevenue,
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
                ) as TotalGP,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT te.ItemID) as UniqueSKUs,
                SUM(te.Quantity) as TotalUnits
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
        ),
        BestCategory AS (
            SELECT TOP 1
                ISNULL(cat.Name, 'Uncategorized') as CategoryName,
                SUM(
                    te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as CategoryGP
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
            GROUP BY cat.Name
            ORDER BY CategoryGP DESC
        )
        SELECT 
            m.TotalRevenue as total_revenue,
            m.TotalCost as total_cost,
            m.TotalGP as total_gp,
            CAST(m.TotalGP * 100.0 / NULLIF(m.TotalRevenue, 0) as DECIMAL(5,2)) as gp_margin,
            m.TransactionCount as transaction_count,
            m.UniqueCustomers as active_customers,
            m.UniqueSKUs as active_skus,
            m.TotalUnits as units_sold,
            m.TotalGP / NULLIF(m.UniqueCustomers, 0) as gp_per_customer,
            m.TotalRevenue / NULLIF(m.TransactionCount, 0) as avg_ticket,
            bc.CategoryName as best_category_name,
            bc.CategoryGP as best_category_gp
        FROM GPMetrics m
        CROSS JOIN BestCategory bc
        """
        
        result = self.db.execute_query(query, description="Executive GP Summary")
        
        if not result.empty:
            row = result.iloc[0]
            return {
                'total_revenue': float(row.get('total_revenue', 0)),
                'total_cost': float(row.get('total_cost', 0)),
                'total_gp': float(row.get('total_gp', 0)),
                'gp_margin': float(row.get('gp_margin', 0)),
                'transaction_count': int(row.get('transaction_count', 0)),
                'active_customers': int(row.get('active_customers', 0)),
                'active_skus': int(row.get('active_skus', 0)),
                'units_sold': int(row.get('units_sold', 0)),
                'gp_per_customer': float(row.get('gp_per_customer', 0)),
                'avg_ticket': float(row.get('avg_ticket', 0)),
                'best_category': {
                    'name': row.get('best_category_name', 'Unknown'),
                    'gp': float(row.get('best_category_gp', 0))
                }
            }
        return {}
    
    def get_category_gp_analysis(self, timeframe='YTD'):
        """Deep dive into category-level profitability"""
        date_filter = self._get_date_filter(timeframe)
        
        query = f"""
        WITH CategoryGP AS (
            SELECT 
                ISNULL(cat.Name, 'Uncategorized') as Category,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT i.ID) as UniqueSKUs,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as Cost,
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
            WHERE {date_filter}
            GROUP BY cat.Name
        )
        SELECT 
            Category as category,
            Transactions as transactions,
            UniqueCustomers as customers,
            UniqueSKUs as skus,
            UnitsSold as units,
            Revenue as revenue,
            Cost as cost,
            GrossProfit as gp,
            CAST(GrossProfit * 100.0 / NULLIF(Revenue, 0) as DECIMAL(5,2)) as margin,
            Revenue / NULLIF(Transactions, 0) as avg_transaction,
            GrossProfit / NULLIF(Transactions, 0) as gp_per_transaction,
            0 as trend  -- Placeholder for trend calculation
        FROM CategoryGP
        ORDER BY GrossProfit DESC
        """
        
        result = self.db.execute_query(query, description="Category GP Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_customer_gp_analysis(self, timeframe='YTD', limit=100):
        """Analyze profitability by customer"""
        date_filter = self._get_date_filter(timeframe)
        
        query = f"""
        WITH CustomerGP AS (
            SELECT 
                c.ID,
                c.FirstName + ' ' + c.LastName as CustomerName,
                c.Company,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                COUNT(DISTINCT te.ItemID) as UniqueSKUs,
                SUM(te.Quantity) as TotalUnits,
                SUM(te.Price * te.Quantity) as TotalRevenue,
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
                ) as TotalGP,
                MIN(t.Time) as FirstTransaction,
                MAX(t.Time) as LastTransaction,
                DATEDIFF(day, MIN(t.Time), MAX(t.Time)) as CustomerLifeDays
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Customer c ON t.CustomerID = c.ID
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
            GROUP BY c.ID, c.FirstName, c.LastName, c.Company
        ),
        TopCategory AS (
            SELECT 
                t.CustomerID,
                ISNULL(cat.Name, 'Uncategorized') as TopCategoryName,
                ROW_NUMBER() OVER (PARTITION BY t.CustomerID ORDER BY SUM(te.Price * te.Quantity) DESC) as rn
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
            GROUP BY t.CustomerID, cat.Name
        )
        SELECT TOP {limit}
            CASE 
                WHEN cg.Company IS NOT NULL AND cg.Company != '' THEN cg.Company
                ELSE cg.CustomerName
            END as customer,
            cg.TransactionCount as transaction_count,
            cg.UniqueSKUs as unique_skus,
            cg.TotalUnits as units,
            cg.TotalRevenue as revenue,
            cg.TotalCost as cost,
            cg.TotalGP as gp,
            CAST(cg.TotalGP * 100.0 / NULLIF(cg.TotalRevenue, 0) as DECIMAL(5,2)) as margin,
            cg.TotalRevenue / NULLIF(cg.TransactionCount, 0) as avg_ticket,
            cg.TotalGP / NULLIF(cg.TransactionCount, 0) as gp_per_transaction,
            tc.TopCategoryName as top_category
        FROM CustomerGP cg
        LEFT JOIN TopCategory tc ON cg.ID = tc.CustomerID AND tc.rn = 1
        ORDER BY cg.TotalGP DESC
        """
        
        result = self.db.execute_query(query, description="Customer GP Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_product_gp_analysis(self, timeframe='YTD', top_n=50):
        """Analyze profitability by product"""
        date_filter = self._get_date_filter(timeframe)
        
        query = f"""
        WITH ProductGP AS (
            SELECT 
                i.Description as Product,
                i.ItemLookupCode as SKU,
                ISNULL(cat.Name, 'Uncategorized') as Category,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as Cost,
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
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
            GROUP BY i.ID, i.Description, i.ItemLookupCode, cat.Name
        )
        SELECT TOP {top_n}
            Product as product,
            SKU as sku,
            Category as category,
            UnitsSold as units,
            Revenue as revenue,
            Cost as cost,
            GrossProfit as gp,
            CAST(GrossProfit * 100.0 / NULLIF(Revenue, 0) as DECIMAL(5,2)) as margin,
            Revenue / NULLIF(UnitsSold, 0) as avg_price,
            Cost / NULLIF(UnitsSold, 0) as avg_cost
        FROM ProductGP
        ORDER BY GrossProfit DESC
        """
        
        result = self.db.execute_query(query, description="Product GP Analysis")
        return result.to_dict('records') if not result.empty else []
    
    def get_low_margin_products(self, timeframe='YTD', limit=20):
        """Identify products with low or negative margins"""
        date_filter = self._get_date_filter(timeframe)
        
        query = f"""
        WITH ProductGP AS (
            SELECT 
                i.Description as Product,
                i.ItemLookupCode as SKU,
                ISNULL(cat.Name, 'Uncategorized') as Category,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as Cost,
                SUM(
                    te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as GrossProfit,
                CAST(SUM(te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END) * 100.0 / NULLIF(SUM(te.Price * te.Quantity), 0) as DECIMAL(10,2)) as Margin
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
                AND te.Price > 0  -- Exclude zero price items
            GROUP BY i.ID, i.Description, i.ItemLookupCode, cat.Name
            HAVING SUM(te.Quantity) > 0  -- Must have sales
        )
        SELECT TOP {limit}
            Product as product,
            SKU as sku,
            Category as category,
            UnitsSold as units,
            Revenue as revenue,
            Cost as cost,
            GrossProfit as gp,
            Margin as margin
        FROM ProductGP
        WHERE Margin < 15  -- Less than 15% margin
        ORDER BY Margin ASC, Revenue DESC
        """
        
        result = self.db.execute_query(query, description="Low Margin Products")
        return result.to_dict('records') if not result.empty else []
    
    def get_gp_trending(self, timeframe='YTD'):
        """Get GP trends over time"""
        date_filter = self._get_date_filter(timeframe)
        
        # Determine grouping based on timeframe
        if timeframe == 'MTD':
            date_group = "CONVERT(VARCHAR(10), t.Time, 120)"  # Daily
            date_format = "CONVERT(VARCHAR(10), t.Time, 120)"
        else:
            date_group = "YEAR(t.Time), MONTH(t.Time)"  # Monthly
            date_format = "CAST(YEAR(t.Time) as VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(t.Time) as VARCHAR), 2)"
        
        query = f"""
        WITH TrendingGP AS (
            SELECT 
                {date_format} as Period,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as Cost,
                SUM(
                    te.Price * te.Quantity - 
                    CASE 
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                        ELSE te.Cost * te.Quantity
                    END
                ) as GrossProfit,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as Customers
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE {date_filter}
            GROUP BY {date_group}
        )
        SELECT 
            Period as period,
            Revenue as revenue,
            Cost as cost,
            GrossProfit as gp,
            CAST(GrossProfit * 100.0 / NULLIF(Revenue, 0) as DECIMAL(5,2)) as margin,
            Transactions as transactions,
            Customers as customers,
            GrossProfit / NULLIF(Transactions, 0) as gp_per_transaction
        FROM TrendingGP
        ORDER BY Period
        """
        
        result = self.db.execute_query(query, description="GP Trending")
        return result.to_dict('records') if not result.empty else []
    
    def get_gp_opportunities(self, timeframe='YTD'):
        """Identify GP improvement opportunities"""
        opportunities = []
        
        # Get low margin products
        low_margin = self.get_low_margin_products(timeframe, limit=10)
        if low_margin:
            total_impact = sum(p['revenue'] * 0.05 for p in low_margin)  # 5% improvement potential
            opportunities.append({
                'opportunity': 'Improve Low Margin Products',
                'description': f'Found {len(low_margin)} products with margins below 15%. Consider price adjustments or cost negotiations.',
                'impact': total_impact,
                'priority': 'High'
            })
        
        # Get category analysis
        categories = self.get_category_gp_analysis(timeframe)
        if categories:
            low_margin_cats = [c for c in categories if c['margin'] < 20]
            if low_margin_cats:
                impact = sum(c['revenue'] * 0.03 for c in low_margin_cats)  # 3% improvement
                opportunities.append({
                    'opportunity': 'Optimize Category Mix',
                    'description': f'{len(low_margin_cats)} categories have margins below 20%. Focus on higher margin categories.',
                    'impact': impact,
                    'priority': 'Medium'
                })
        
        # Get customer analysis
        customers = self.get_customer_gp_analysis(timeframe, limit=20)
        if customers:
            low_margin_customers = [c for c in customers if c['margin'] < 15]
            if low_margin_customers:
                impact = sum(c['revenue'] * 0.02 for c in low_margin_customers)
                opportunities.append({
                    'opportunity': 'Customer Profitability Review',
                    'description': f'{len(low_margin_customers)} top customers have low margins. Consider pricing or terms adjustments.',
                    'impact': impact,
                    'priority': 'High'
                })
        
        # Sort by impact
        opportunities.sort(key=lambda x: x['impact'], reverse=True)
        
        return opportunities