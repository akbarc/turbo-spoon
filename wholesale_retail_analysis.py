"""
Wholesale vs Retail Analysis
Identifies wholesale patterns based on transaction size and SKU concentration
"""

import pandas as pd
from datetime import datetime
from database_pymssql import SQLServerConnection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WholesaleRetailAnalysis:
    def __init__(self):
        self.db = SQLServerConnection()
        # Wholesale indicators: transactions over $10K or high volume of limited SKUs
        self.wholesale_threshold = 10000
        self.bulk_quantity_threshold = 100  # Units of same item
        
    def analyze_wholesale_patterns(self):
        """Complete wholesale vs retail analysis"""
        report = {
            "report_date": datetime.now().isoformat(),
            "analysis_period": "2019-2024",
            "yearly_breakdown": {},
            "wholesale_customers": {},
            "product_patterns": {},
            "revenue_split": {}
        }
        
        try:
            self.db.connect()
            
            # Yearly wholesale vs retail breakdown
            logger.info("Analyzing yearly wholesale vs retail patterns...")
            report["yearly_breakdown"] = self.get_yearly_wholesale_retail()
            
            # Identify wholesale customers
            logger.info("Identifying wholesale customers...")
            report["wholesale_customers"] = self.get_wholesale_customers()
            
            # SKU concentration analysis
            logger.info("Analyzing SKU concentration in large orders...")
            report["product_patterns"] = self.get_sku_concentration_patterns()
            
            # Revenue split analysis
            logger.info("Calculating revenue splits...")
            report["revenue_split"] = self.get_revenue_splits()
            
            # Bulk order patterns
            logger.info("Analyzing bulk order patterns...")
            report["bulk_patterns"] = self.get_bulk_order_patterns()
            
            # Category analysis for wholesale
            logger.info("Analyzing wholesale by category...")
            report["wholesale_categories"] = self.get_wholesale_category_analysis()
            
            # Customer type evolution
            logger.info("Tracking customer type evolution...")
            report["customer_evolution"] = self.get_customer_type_evolution()
            
            return report
            
        finally:
            self.db.close()
    
    def get_yearly_wholesale_retail(self):
        """Analyze wholesale vs retail by year based on transaction size"""
        query = """
        WITH TransactionClassification AS (
            SELECT 
                YEAR(t.Time) as Year,
                t.TransactionNumber,
                t.CustomerID,
                t.Total,
                CASE 
                    WHEN t.Total >= 10000 THEN 'Wholesale'
                    WHEN t.Total >= 5000 THEN 'Large Retail'
                    WHEN t.Total >= 1000 THEN 'Medium Retail'
                    ELSE 'Small Retail'
                END as TransactionType,
                -- Get item count and unique SKU count
                (SELECT COUNT(*) FROM TransactionEntry WHERE TransactionNumber = t.TransactionNumber) as ItemCount,
                (SELECT COUNT(DISTINCT ItemID) FROM TransactionEntry WHERE TransactionNumber = t.TransactionNumber) as UniqueSKUs
            FROM [dbo].[Transaction] t
            WHERE t.Time >= '2019-01-01'
        )
        SELECT 
            Year,
            TransactionType,
            COUNT(*) as TransactionCount,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            SUM(Total) as TotalRevenue,
            AVG(Total) as AvgTransaction,
            MIN(Total) as MinTransaction,
            MAX(Total) as MaxTransaction,
            AVG(ItemCount) as AvgItemsPerTransaction,
            AVG(UniqueSKUs) as AvgSKUsPerTransaction,
            -- Calculate SKU concentration (items per unique SKU)
            AVG(CAST(ItemCount as FLOAT) / NULLIF(UniqueSKUs, 0)) as AvgItemsPerSKU
        FROM TransactionClassification
        GROUP BY Year, TransactionType
        ORDER BY Year, 
            CASE 
                WHEN TransactionType = 'Wholesale' THEN 1
                WHEN TransactionType = 'Large Retail' THEN 2
                WHEN TransactionType = 'Medium Retail' THEN 3
                ELSE 4
            END
        """
        
        result = self.db.execute_query(query)
        
        # Calculate percentage breakdown by year
        yearly_summary = []
        for year in result['Year'].unique():
            year_data = result[result['Year'] == year]
            total_revenue = year_data['TotalRevenue'].sum()
            
            summary = {
                'year': int(year),
                'total_revenue': float(total_revenue),
                'wholesale_revenue': float(year_data[year_data['TransactionType'] == 'Wholesale']['TotalRevenue'].sum()),
                'wholesale_pct': float(year_data[year_data['TransactionType'] == 'Wholesale']['TotalRevenue'].sum() / total_revenue * 100) if total_revenue > 0 else 0,
                'wholesale_transactions': int(year_data[year_data['TransactionType'] == 'Wholesale']['TransactionCount'].sum()),
                'wholesale_customers': int(year_data[year_data['TransactionType'] == 'Wholesale']['UniqueCustomers'].sum()),
                'breakdown': year_data.to_dict('records')
            }
            yearly_summary.append(summary)
        
        return yearly_summary
    
    def get_wholesale_customers(self):
        """Identify customers with wholesale buying patterns"""
        query = """
        WITH CustomerMetrics AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                COUNT(t.TransactionNumber) as TotalTransactions,
                COUNT(CASE WHEN t.Total >= 10000 THEN 1 END) as WholesaleTransactions,
                COUNT(CASE WHEN t.Total >= 5000 AND t.Total < 10000 THEN 1 END) as LargeTransactions,
                SUM(t.Total) as TotalRevenue,
                SUM(CASE WHEN t.Total >= 10000 THEN t.Total ELSE 0 END) as WholesaleRevenue,
                AVG(t.Total) as AvgTransaction,
                MAX(t.Total) as LargestTransaction,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName
            HAVING COUNT(CASE WHEN t.Total >= 10000 THEN 1 END) > 0
                OR AVG(t.Total) > 5000
        )
        SELECT 
            CustomerName,
            TotalTransactions,
            WholesaleTransactions,
            LargeTransactions,
            TotalRevenue,
            WholesaleRevenue,
            CAST(WholesaleRevenue * 100.0 / NULLIF(TotalRevenue, 0) as DECIMAL(5,2)) as WholesalePct,
            AvgTransaction,
            LargestTransaction,
            CASE 
                WHEN WholesaleTransactions >= TotalTransactions * 0.5 THEN 'Primarily Wholesale'
                WHEN WholesaleTransactions >= TotalTransactions * 0.25 THEN 'Mixed Wholesale/Retail'
                WHEN AvgTransaction >= 5000 THEN 'Large Volume Buyer'
                ELSE 'Occasional Wholesale'
            END as CustomerType,
            FirstPurchase,
            LastPurchase,
            DATEDIFF(DAY, LastPurchase, GETDATE()) as DaysSinceLastPurchase
        FROM CustomerMetrics
        ORDER BY WholesaleRevenue DESC
        """
        
        customers = self.db.execute_query(query)
        
        # Top wholesale customers by year
        yearly_top_query = """
        SELECT 
            YEAR(t.Time) as Year,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            COUNT(CASE WHEN t.Total >= 10000 THEN 1 END) as WholesaleOrders,
            SUM(CASE WHEN t.Total >= 10000 THEN t.Total ELSE 0 END) as WholesaleRevenue,
            MAX(t.Total) as LargestOrder
        FROM dbo.Customer c
        JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
        WHERE t.Time >= '2019-01-01'
            AND t.Total >= 10000
        GROUP BY YEAR(t.Time), c.Company, c.FirstName, c.LastName
        ORDER BY Year, WholesaleRevenue DESC
        """
        
        yearly_top = self.db.execute_query(yearly_top_query)
        
        return {
            "all_wholesale_customers": customers.to_dict('records'),
            "top_by_year": yearly_top.to_dict('records')
        }
    
    def get_sku_concentration_patterns(self):
        """Analyze SKU concentration in large orders (bulk buying indicator)"""
        query = """
        WITH OrderDetails AS (
            SELECT 
                t.TransactionNumber,
                YEAR(t.Time) as Year,
                t.CustomerID,
                t.Total as OrderTotal,
                te.ItemID,
                i.Description as ItemDescription,
                i.ItemLookupCode,
                cat.Name as Category,
                te.Quantity,
                te.Price * te.Quantity as LineTotal,
                COUNT(*) OVER (PARTITION BY t.TransactionNumber) as TotalLines,
                COUNT(DISTINCT te.ItemID) OVER (PARTITION BY t.TransactionNumber) as UniqueSKUs,
                SUM(te.Quantity) OVER (PARTITION BY t.TransactionNumber) as TotalUnits
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2019-01-01'
                AND t.Total >= 5000  -- Focus on larger orders
        )
        SELECT 
            Year,
            TransactionNumber,
            OrderTotal,
            ItemDescription,
            Category,
            Quantity,
            LineTotal,
            UniqueSKUs,
            TotalUnits,
            CAST(TotalUnits as FLOAT) / UniqueSKUs as UnitsPerSKU,
            CAST(LineTotal * 100.0 / OrderTotal as DECIMAL(5,2)) as PctOfOrder,
            CASE 
                WHEN Quantity >= 100 THEN 'Bulk Item'
                WHEN LineTotal >= OrderTotal * 0.5 THEN 'Dominant Item'
                WHEN UniqueSKUs <= 3 AND OrderTotal >= 10000 THEN 'Focused Wholesale'
                WHEN UniqueSKUs <= 5 AND TotalUnits >= 200 THEN 'Limited SKU Bulk'
                ELSE 'Mixed Order'
            END as OrderPattern
        FROM OrderDetails
        WHERE LineTotal >= 1000  -- Focus on significant line items
        ORDER BY Year, OrderTotal DESC, LineTotal DESC
        """
        
        patterns = self.db.execute_query(query)
        
        # Summary of bulk buying patterns
        summary_query = """
        WITH BulkOrders AS (
            SELECT 
                YEAR(t.Time) as Year,
                t.TransactionNumber,
                t.Total,
                COUNT(DISTINCT te.ItemID) as UniqueSKUs,
                SUM(te.Quantity) as TotalUnits,
                MAX(te.Quantity) as MaxSingleItemQty
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '2019-01-01'
                AND t.Total >= 10000
            GROUP BY YEAR(t.Time), t.TransactionNumber, t.Total
        )
        SELECT 
            Year,
            COUNT(*) as WholesaleOrderCount,
            AVG(UniqueSKUs) as AvgSKUsPerOrder,
            AVG(TotalUnits) as AvgUnitsPerOrder,
            AVG(CAST(TotalUnits as FLOAT) / UniqueSKUs) as AvgUnitsPerSKU,
            -- Categorize order patterns
            COUNT(CASE WHEN UniqueSKUs <= 3 THEN 1 END) as FocusedOrders,
            COUNT(CASE WHEN UniqueSKUs <= 10 AND TotalUnits >= 500 THEN 1 END) as BulkOrders,
            COUNT(CASE WHEN MaxSingleItemQty >= 100 THEN 1 END) as SingleItemBulkOrders
        FROM BulkOrders
        GROUP BY Year
        ORDER BY Year
        """
        
        summary = self.db.execute_query(summary_query)
        
        return {
            "detailed_patterns": patterns.head(100).to_dict('records'),
            "yearly_summary": summary.to_dict('records')
        }
    
    def get_revenue_splits(self):
        """Calculate detailed revenue splits between wholesale and retail"""
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            DATENAME(MONTH, t.Time) as MonthName,
            -- Transaction size categories
            COUNT(CASE WHEN t.Total >= 10000 THEN 1 END) as WholesaleCount,
            COUNT(CASE WHEN t.Total >= 5000 AND t.Total < 10000 THEN 1 END) as LargeRetailCount,
            COUNT(CASE WHEN t.Total >= 1000 AND t.Total < 5000 THEN 1 END) as MediumRetailCount,
            COUNT(CASE WHEN t.Total < 1000 THEN 1 END) as SmallRetailCount,
            -- Revenue by category
            SUM(CASE WHEN t.Total >= 10000 THEN t.Total ELSE 0 END) as WholesaleRevenue,
            SUM(CASE WHEN t.Total >= 5000 AND t.Total < 10000 THEN t.Total ELSE 0 END) as LargeRetailRevenue,
            SUM(CASE WHEN t.Total >= 1000 AND t.Total < 5000 THEN t.Total ELSE 0 END) as MediumRetailRevenue,
            SUM(CASE WHEN t.Total < 1000 THEN t.Total ELSE 0 END) as SmallRetailRevenue,
            SUM(t.Total) as TotalRevenue
        FROM [dbo].[Transaction] t
        WHERE t.Time >= '2019-01-01'
        GROUP BY YEAR(t.Time), MONTH(t.Time), DATENAME(MONTH, t.Time)
        ORDER BY Year, Month
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_bulk_order_patterns(self):
        """Identify specific bulk order patterns and products"""
        query = """
        WITH BulkItems AS (
            SELECT 
                YEAR(t.Time) as Year,
                i.ItemLookupCode,
                i.Description,
                cat.Name as Category,
                COUNT(DISTINCT t.TransactionNumber) as OrderCount,
                SUM(te.Quantity) as TotalQuantity,
                AVG(te.Quantity) as AvgQuantityPerOrder,
                MAX(te.Quantity) as MaxSingleOrder,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2019-01-01'
                AND te.Quantity >= 50  -- Focus on bulk quantities
            GROUP BY YEAR(t.Time), i.ItemLookupCode, i.Description, cat.Name
        )
        SELECT TOP 100
            Year,
            ItemLookupCode,
            Description,
            Category,
            OrderCount,
            TotalQuantity,
            AvgQuantityPerOrder,
            MaxSingleOrder,
            TotalRevenue,
            UniqueCustomers,
            CASE 
                WHEN Category LIKE '%CIGARETTE%' THEN 'Tobacco Wholesale'
                WHEN Category LIKE '%CIGAR%' THEN 'Cigar Wholesale'
                WHEN AvgQuantityPerOrder >= 100 THEN 'High Volume Item'
                WHEN MaxSingleOrder >= 200 THEN 'Bulk Purchase Item'
                ELSE 'Regular Wholesale'
            END as ItemType
        FROM BulkItems
        ORDER BY TotalRevenue DESC
        """
        
        bulk_items = self.db.execute_query(query)
        
        # Carton/case analysis for cigarettes
        carton_query = """
        SELECT 
            YEAR(t.Time) as Year,
            i.Description,
            COUNT(CASE WHEN te.Quantity % 10 = 0 AND te.Quantity >= 10 THEN 1 END) as CartonOrders,
            COUNT(CASE WHEN te.Quantity < 10 THEN 1 END) as PackOrders,
            SUM(CASE WHEN te.Quantity % 10 = 0 AND te.Quantity >= 10 THEN te.Quantity ELSE 0 END) as CartonUnits,
            SUM(CASE WHEN te.Quantity < 10 THEN te.Quantity ELSE 0 END) as PackUnits
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= '2019-01-01'
            AND cat.Name LIKE '%CIGARETTE%'
        GROUP BY YEAR(t.Time), i.Description
        HAVING COUNT(CASE WHEN te.Quantity % 10 = 0 AND te.Quantity >= 10 THEN 1 END) > 0
        ORDER BY Year, CartonOrders DESC
        """
        
        carton_analysis = self.db.execute_query(carton_query)
        
        return {
            "bulk_items": bulk_items.to_dict('records'),
            "carton_analysis": carton_analysis.head(50).to_dict('records')
        }
    
    def get_wholesale_category_analysis(self):
        """Analyze which categories are primarily wholesale vs retail"""
        query = """
        WITH CategorySales AS (
            SELECT 
                YEAR(t.Time) as Year,
                cat.Name as Category,
                COUNT(DISTINCT t.TransactionNumber) as TotalOrders,
                COUNT(DISTINCT CASE WHEN t.Total >= 10000 THEN t.TransactionNumber END) as WholesaleOrders,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                SUM(CASE WHEN t.Total >= 10000 THEN te.Price * te.Quantity ELSE 0 END) as WholesaleRevenue,
                AVG(t.Total) as AvgOrderSize,
                AVG(te.Quantity) as AvgQuantity
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= '2019-01-01'
            GROUP BY YEAR(t.Time), cat.Name
        )
        SELECT 
            Year,
            Category,
            TotalOrders,
            WholesaleOrders,
            TotalRevenue,
            WholesaleRevenue,
            CAST(WholesaleRevenue * 100.0 / NULLIF(TotalRevenue, 0) as DECIMAL(5,2)) as WholesalePct,
            AvgOrderSize,
            AvgQuantity,
            CASE 
                WHEN WholesaleRevenue > TotalRevenue * 0.5 THEN 'Wholesale Dominant'
                WHEN WholesaleRevenue > TotalRevenue * 0.25 THEN 'Mixed Channel'
                ELSE 'Retail Dominant'
            END as ChannelType
        FROM CategorySales
        WHERE TotalRevenue > 10000  -- Focus on significant categories
        ORDER BY Year, WholesaleRevenue DESC
        """
        
        return self.db.execute_query(query).to_dict('records')
    
    def get_customer_type_evolution(self):
        """Track how customers evolve between wholesale and retail"""
        query = """
        WITH CustomerYearlyPattern AS (
            SELECT 
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                YEAR(t.Time) as Year,
                COUNT(*) as Transactions,
                SUM(t.Total) as Revenue,
                AVG(t.Total) as AvgTransaction,
                MAX(t.Total) as MaxTransaction,
                COUNT(CASE WHEN t.Total >= 10000 THEN 1 END) as WholesaleTransactions,
                CASE 
                    WHEN AVG(t.Total) >= 5000 OR MAX(t.Total) >= 10000 THEN 'Wholesale'
                    WHEN AVG(t.Total) >= 1000 THEN 'Large Retail'
                    ELSE 'Small Retail'
                END as CustomerType
            FROM dbo.Customer c
            JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            WHERE t.Time >= '2019-01-01'
            GROUP BY c.ID, c.Company, c.FirstName, c.LastName, YEAR(t.Time)
        )
        SELECT 
            p1.CustomerName,
            p1.Year as FromYear,
            p1.CustomerType as FromType,
            p2.Year as ToYear,
            p2.CustomerType as ToType,
            p1.Revenue as FromRevenue,
            p2.Revenue as ToRevenue,
            CASE 
                WHEN p1.CustomerType = 'Small Retail' AND p2.CustomerType = 'Wholesale' THEN 'Upgraded to Wholesale'
                WHEN p1.CustomerType = 'Wholesale' AND p2.CustomerType IN ('Large Retail', 'Small Retail') THEN 'Downgraded from Wholesale'
                WHEN p1.CustomerType = p2.CustomerType THEN 'Stable'
                ELSE 'Changed'
            END as Evolution
        FROM CustomerYearlyPattern p1
        JOIN CustomerYearlyPattern p2 
            ON p1.ID = p2.ID 
            AND p2.Year = p1.Year + 1
        WHERE p1.Year >= 2019 AND p1.Year <= 2022
        ORDER BY p1.Year, Evolution, p2.Revenue DESC
        """
        
        evolution = self.db.execute_query(query)
        
        # Summary of customer movements
        summary_query = """
        WITH Movements AS (
            SELECT 
                p1.Year as Year,
                COUNT(CASE WHEN p1.CustomerType != 'Wholesale' AND p2.CustomerType = 'Wholesale' THEN 1 END) as UpgradedToWholesale,
                COUNT(CASE WHEN p1.CustomerType = 'Wholesale' AND p2.CustomerType != 'Wholesale' THEN 1 END) as DowngradedFromWholesale,
                COUNT(CASE WHEN p1.CustomerType = 'Wholesale' AND p2.CustomerType = 'Wholesale' THEN 1 END) as StayedWholesale,
                COUNT(CASE WHEN p1.CustomerType != 'Wholesale' AND p2.CustomerType != 'Wholesale' THEN 1 END) as StayedRetail
            FROM (
                SELECT 
                    c.ID,
                    YEAR(t.Time) as Year,
                    CASE 
                        WHEN AVG(t.Total) >= 5000 OR MAX(t.Total) >= 10000 THEN 'Wholesale'
                        ELSE 'Retail'
                    END as CustomerType
                FROM dbo.Customer c
                JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
                WHERE t.Time >= '2019-01-01'
                GROUP BY c.ID, YEAR(t.Time)
            ) p1
            JOIN (
                SELECT 
                    c.ID,
                    YEAR(t.Time) as Year,
                    CASE 
                        WHEN AVG(t.Total) >= 5000 OR MAX(t.Total) >= 10000 THEN 'Wholesale'
                        ELSE 'Retail'
                    END as CustomerType
                FROM dbo.Customer c
                JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
                WHERE t.Time >= '2019-01-01'
                GROUP BY c.ID, YEAR(t.Time)
            ) p2 ON p1.ID = p2.ID AND p2.Year = p1.Year + 1
            GROUP BY p1.Year
        )
        SELECT * FROM Movements
        ORDER BY Year
        """
        
        movement_summary = self.db.execute_query(summary_query)
        
        return {
            "detailed_evolution": evolution.head(100).to_dict('records'),
            "yearly_summary": movement_summary.to_dict('records')
        }
    
    def save_report(self, report):
        """Save wholesale vs retail analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_file = f"wholesale_retail_analysis_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Create summary
        txt_file = f"wholesale_retail_summary_{timestamp}.txt"
        with open(txt_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("WHOLESALE VS RETAIL ANALYSIS REPORT\n")
            f.write(f"Generated: {report['report_date']}\n")
            f.write("="*80 + "\n\n")
            
            # Yearly breakdown
            if 'yearly_breakdown' in report:
                f.write("YEARLY WHOLESALE VS RETAIL BREAKDOWN\n")
                f.write("-"*40 + "\n")
                f.write("Year  | Wholesale Rev  | % of Total | # Orders | # Customers\n")
                f.write("------|---------------|------------|----------|------------\n")
                
                for year_data in report['yearly_breakdown']:
                    f.write(f"{year_data['year']} | ${year_data['wholesale_revenue']:>13,.0f} | "
                           f"{year_data['wholesale_pct']:>9.1f}% | "
                           f"{year_data['wholesale_transactions']:>8} | "
                           f"{year_data['wholesale_customers']:>11}\n")
            
            # Top wholesale customers
            if 'wholesale_customers' in report and 'all_wholesale_customers' in report['wholesale_customers']:
                f.write("\n\nTOP WHOLESALE CUSTOMERS\n")
                f.write("-"*40 + "\n")
                
                top_customers = report['wholesale_customers']['all_wholesale_customers'][:10]
                for customer in top_customers:
                    f.write(f"{customer['CustomerName'][:30]:.<30} ${customer['WholesaleRevenue']:>12,.0f} "
                           f"({customer['WholesalePct']:.1f}% wholesale)\n")
            
            # SKU patterns
            if 'product_patterns' in report and 'yearly_summary' in report['product_patterns']:
                f.write("\n\nWHOLESALE ORDER PATTERNS\n")
                f.write("-"*40 + "\n")
                f.write("Year | Avg SKUs | Avg Units | Units/SKU | Focused Orders | Bulk Orders\n")
                f.write("-----|----------|-----------|-----------|----------------|------------\n")
                
                for year in report['product_patterns']['yearly_summary']:
                    f.write(f"{year['Year']} | {year['AvgSKUsPerOrder']:>8.1f} | "
                           f"{year['AvgUnitsPerOrder']:>9.0f} | "
                           f"{year['AvgUnitsPerSKU']:>9.1f} | "
                           f"{year['FocusedOrders']:>14} | "
                           f"{year['BulkOrders']:>11}\n")
            
            # Category analysis
            if 'wholesale_categories' in report:
                f.write("\n\nCATEGORY WHOLESALE ANALYSIS (2023)\n")
                f.write("-"*40 + "\n")
                
                categories_2023 = [c for c in report['wholesale_categories'] if c['Year'] == 2023][:10]
                for cat in categories_2023:
                    if cat['Category']:
                        f.write(f"{cat['Category'][:25]:.<25} {cat['WholesalePct']:>5.1f}% wholesale "
                               f"(${cat['WholesaleRevenue']:>10,.0f})\n")
            
            # Key insights
            f.write("\n\nKEY INSIGHTS\n")
            f.write("-"*40 + "\n")
            
            if 'yearly_breakdown' in report:
                # Calculate trends
                years = report['yearly_breakdown']
                if len(years) >= 2:
                    recent_wholesale_pct = years[-1]['wholesale_pct']
                    older_wholesale_pct = years[0]['wholesale_pct']
                    trend = "increasing" if recent_wholesale_pct > older_wholesale_pct else "decreasing"
                    
                    f.write(f"• Wholesale share is {trend}: {older_wholesale_pct:.1f}% (2019) → "
                           f"{recent_wholesale_pct:.1f}% (most recent)\n")
                    
                    total_wholesale_rev = sum(y['wholesale_revenue'] for y in years)
                    total_rev = sum(y['total_revenue'] for y in years)
                    f.write(f"• Overall wholesale represents {total_wholesale_rev/total_rev*100:.1f}% of total revenue\n")
            
            if 'wholesale_customers' in report and 'all_wholesale_customers' in report['wholesale_customers']:
                wholesale_customer_count = len(report['wholesale_customers']['all_wholesale_customers'])
                f.write(f"• {wholesale_customer_count} customers have wholesale buying patterns\n")
                
                primarily_wholesale = [c for c in report['wholesale_customers']['all_wholesale_customers'] 
                                     if c['CustomerType'] == 'Primarily Wholesale']
                f.write(f"• {len(primarily_wholesale)} customers are primarily wholesale buyers\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write(f"Full report saved to: {json_file}\n")
        
        return json_file, txt_file

def main():
    """Run wholesale vs retail analysis"""
    logger.info("Starting Wholesale vs Retail Analysis...")
    
    try:
        analyzer = WholesaleRetailAnalysis()
        report = analyzer.analyze_wholesale_patterns()
        
        json_file, txt_file = analyzer.save_report(report)
        
        logger.info(f"✅ Analysis complete!")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   Summary: {txt_file}")
        
        # Print key findings
        print("\n" + "="*60)
        print("WHOLESALE VS RETAIL - KEY FINDINGS")
        print("="*60)
        
        if 'yearly_breakdown' in report and report['yearly_breakdown']:
            recent_year = report['yearly_breakdown'][-1]
            print(f"\nMost Recent Year ({recent_year['year']}):")
            print(f"  Wholesale Revenue: ${recent_year['wholesale_revenue']:,.0f}")
            print(f"  Wholesale % of Total: {recent_year['wholesale_pct']:.1f}%")
            print(f"  Wholesale Orders: {recent_year['wholesale_transactions']}")
            print(f"  Wholesale Customers: {recent_year['wholesale_customers']}")
        
        if 'wholesale_customers' in report and 'all_wholesale_customers' in report['wholesale_customers']:
            top_3 = report['wholesale_customers']['all_wholesale_customers'][:3]
            print("\nTop Wholesale Customers:")
            for customer in top_3:
                print(f"  {customer['CustomerName']}: ${customer['WholesaleRevenue']:,.0f}")
        
        if 'product_patterns' in report and 'yearly_summary' in report['product_patterns']:
            recent_pattern = report['product_patterns']['yearly_summary'][-1]
            print(f"\nWholesale Order Characteristics:")
            print(f"  Avg SKUs per Order: {recent_pattern['AvgSKUsPerOrder']:.1f}")
            print(f"  Avg Units per SKU: {recent_pattern['AvgUnitsPerSKU']:.1f}")
            print(f"  Focused Orders (≤3 SKUs): {recent_pattern['FocusedOrders']}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()