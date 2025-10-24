#!/usr/bin/env python3
"""
Comprehensive Cigarette Business Intelligence System
Deep dive into suppliers, ordering patterns, historical trends, and optimization opportunities
"""

from database_pymssql import SQLServerConnection
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class ComprehensiveCigaretteAnalytics:
    def __init__(self):
        self.db = SQLServerConnection()
        self.analysis_results = {}
        
    def run_full_analysis(self):
        """Execute comprehensive multi-dimensional analysis"""
        
        print("🔍 Starting Comprehensive Cigarette Business Analysis...")
        print("="*80)
        
        # 1. Supplier Performance Analysis
        self.analyze_supplier_performance()
        
        # 2. Purchase Order History & Patterns
        self.analyze_purchase_patterns()
        
        # 3. Product-Supplier Relationships
        self.analyze_product_supplier_matrix()
        
        # 4. Sales Velocity & Inventory Turnover
        self.analyze_inventory_metrics()
        
        # 5. Customer Segmentation Analysis
        self.analyze_customer_segments()
        
        # 6. Seasonal & Temporal Patterns
        self.analyze_seasonal_patterns()
        
        # 7. Profitability Analysis
        self.analyze_profitability()
        
        # 8. Competitive & Market Analysis
        self.analyze_market_dynamics()
        
        return self.analysis_results
    
    def analyze_supplier_performance(self):
        """Deep dive into supplier metrics and performance"""
        
        print("\n📦 ANALYZING SUPPLIER PERFORMANCE...")
        
        query = """
        WITH SupplierMetrics AS (
            SELECT 
                s.SupplierName,
                s.ID as SupplierID,
                COUNT(DISTINCT po.ID) as Total_POs,
                COUNT(DISTINCT poe.ItemID) as Unique_SKUs,
                SUM(poe.QuantityOrdered) as Total_Units_Ordered,
                SUM(poe.QuantityReceived) as Total_Units_Received,
                AVG(poe.Price) as Avg_Unit_Cost,
                SUM(poe.QuantityOrdered * poe.Price) as Total_Purchase_Value,
                MIN(po.DateCreated) as First_Order_Date,
                MAX(po.DateCreated) as Last_Order_Date,
                DATEDIFF(day, MIN(po.DateCreated), MAX(po.DateCreated)) as Relationship_Days,
                -- Fulfillment rate
                CASE 
                    WHEN SUM(poe.QuantityOrdered) > 0 
                    THEN (SUM(poe.QuantityReceived) * 100.0 / SUM(poe.QuantityOrdered))
                    ELSE 0
                END as Fulfillment_Rate,
                -- Order frequency
                CASE 
                    WHEN DATEDIFF(day, MIN(po.DateCreated), MAX(po.DateCreated)) > 0
                    THEN COUNT(DISTINCT po.ID) * 30.0 / DATEDIFF(day, MIN(po.DateCreated), MAX(po.DateCreated))
                    ELSE 0
                END as Orders_Per_Month
            FROM dbo.Supplier s
            JOIN dbo.PurchaseOrder po ON s.ID = po.SupplierID
            JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
            JOIN dbo.Item i ON poe.ItemID = i.ID
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name IN ('CIGARETTE', 'CIGARS', 'CIGAR GA')
            GROUP BY s.SupplierName, s.ID
        ),
        RecentActivity AS (
            SELECT 
                s.SupplierName,
                -- Last 3 months metrics
                COUNT(DISTINCT CASE WHEN po.DateCreated >= DATEADD(month, -3, GETDATE()) THEN po.ID END) as Orders_3mo,
                SUM(CASE WHEN po.DateCreated >= DATEADD(month, -3, GETDATE()) THEN poe.QuantityOrdered ELSE 0 END) as Units_3mo,
                SUM(CASE WHEN po.DateCreated >= DATEADD(month, -3, GETDATE()) THEN poe.QuantityOrdered * poe.Price ELSE 0 END) as Value_3mo,
                -- Last month metrics
                COUNT(DISTINCT CASE WHEN po.DateCreated >= DATEADD(month, -1, GETDATE()) THEN po.ID END) as Orders_1mo,
                SUM(CASE WHEN po.DateCreated >= DATEADD(month, -1, GETDATE()) THEN poe.QuantityOrdered ELSE 0 END) as Units_1mo,
                -- Top products
                STUFF((
                    SELECT TOP 5 ', ' + i2.Description
                    FROM dbo.PurchaseOrderEntry poe2
                    JOIN dbo.PurchaseOrder po2 ON poe2.PurchaseOrderID = po2.ID
                    JOIN dbo.Item i2 ON poe2.ItemID = i2.ID
                    WHERE po2.SupplierID = s.ID
                    GROUP BY i2.Description
                    ORDER BY SUM(poe2.QuantityOrdered) DESC
                    FOR XML PATH('')
                ), 1, 2, '') as Top_Products
            FROM dbo.Supplier s
            LEFT JOIN dbo.PurchaseOrder po ON s.ID = po.SupplierID
            LEFT JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
            GROUP BY s.SupplierName, s.ID
        )
        SELECT 
            sm.*,
            ra.Orders_3mo,
            ra.Units_3mo,
            ra.Value_3mo,
            ra.Orders_1mo,
            ra.Units_1mo,
            ra.Top_Products,
            -- Trend indicator
            CASE 
                WHEN ra.Orders_1mo > sm.Orders_Per_Month THEN 'INCREASING'
                WHEN ra.Orders_1mo < sm.Orders_Per_Month * 0.5 THEN 'DECREASING'
                ELSE 'STABLE'
            END as Order_Trend
        FROM SupplierMetrics sm
        JOIN RecentActivity ra ON sm.SupplierName = ra.SupplierName
        ORDER BY sm.Total_Purchase_Value DESC
        """
        
        supplier_data = self.db.execute_query(query, [], 'Supplier Performance Analysis')
        self.analysis_results['supplier_performance'] = supplier_data
        
        # Print summary
        if not supplier_data.empty:
            print(f"✓ Analyzed {len(supplier_data)} suppliers")
            print(f"  Top Supplier: {supplier_data.iloc[0]['SupplierName']}")
            print(f"  Total Value: ${supplier_data['Total_Purchase_Value'].sum():,.2f}")
    
    def analyze_purchase_patterns(self):
        """Analyze historical purchase order patterns"""
        
        print("\n📊 ANALYZING PURCHASE ORDER PATTERNS...")
        
        query = """
        WITH MonthlyOrders AS (
            SELECT 
                YEAR(po.DateCreated) as Year,
                MONTH(po.DateCreated) as Month,
                DATENAME(month, po.DateCreated) as MonthName,
                COUNT(DISTINCT po.ID) as PO_Count,
                COUNT(DISTINCT po.SupplierID) as Supplier_Count,
                SUM(poe.QuantityOrdered) as Total_Units,
                SUM(poe.QuantityOrdered * poe.Price) as Total_Value,
                AVG(poe.Price) as Avg_Unit_Price,
                -- Day of week distribution
                COUNT(DISTINCT CASE WHEN DATEPART(weekday, po.DateCreated) = 2 THEN po.ID END) as Monday_Orders,
                COUNT(DISTINCT CASE WHEN DATEPART(weekday, po.DateCreated) = 3 THEN po.ID END) as Tuesday_Orders,
                COUNT(DISTINCT CASE WHEN DATEPART(weekday, po.DateCreated) = 4 THEN po.ID END) as Wednesday_Orders,
                COUNT(DISTINCT CASE WHEN DATEPART(weekday, po.DateCreated) = 5 THEN po.ID END) as Thursday_Orders,
                COUNT(DISTINCT CASE WHEN DATEPART(weekday, po.DateCreated) = 6 THEN po.ID END) as Friday_Orders,
                COUNT(DISTINCT CASE WHEN DATEPART(weekday, po.DateCreated) = 7 THEN po.ID END) as Saturday_Orders
            FROM dbo.PurchaseOrder po
            JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
            JOIN dbo.Item i ON poe.ItemID = i.ID
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name IN ('CIGARETTE', 'CIGARS', 'CIGAR GA')
              AND po.DateCreated >= DATEADD(year, -2, GETDATE())
            GROUP BY YEAR(po.DateCreated), MONTH(po.DateCreated), DATENAME(month, po.DateCreated)
        )
        SELECT 
            *,
            -- Calculate month-over-month change
            LAG(Total_Units, 1) OVER (ORDER BY Year, Month) as Prev_Month_Units,
            CASE 
                WHEN LAG(Total_Units, 1) OVER (ORDER BY Year, Month) > 0
                THEN ((Total_Units - LAG(Total_Units, 1) OVER (ORDER BY Year, Month)) * 100.0 / 
                      LAG(Total_Units, 1) OVER (ORDER BY Year, Month))
                ELSE 0
            END as MoM_Change_Pct,
            -- Identify peak ordering day
            CASE GREATEST(Monday_Orders, Tuesday_Orders, Wednesday_Orders, Thursday_Orders, Friday_Orders, Saturday_Orders)
                WHEN Monday_Orders THEN 'Monday'
                WHEN Tuesday_Orders THEN 'Tuesday'
                WHEN Wednesday_Orders THEN 'Wednesday'
                WHEN Thursday_Orders THEN 'Thursday'
                WHEN Friday_Orders THEN 'Friday'
                WHEN Saturday_Orders THEN 'Saturday'
            END as Peak_Order_Day
        FROM MonthlyOrders
        ORDER BY Year DESC, Month DESC
        """
        
        # For SQL Server 2008, simplify the GREATEST function
        query = query.replace(
            "CASE GREATEST(Monday_Orders, Tuesday_Orders, Wednesday_Orders, Thursday_Orders, Friday_Orders, Saturday_Orders)",
            "CASE (SELECT MAX(v) FROM (VALUES (Monday_Orders), (Tuesday_Orders), (Wednesday_Orders), (Thursday_Orders), (Friday_Orders), (Saturday_Orders)) AS value(v))"
        )
        
        purchase_patterns = self.db.execute_query(query, [], 'Purchase Pattern Analysis')
        self.analysis_results['purchase_patterns'] = purchase_patterns
        
        if not purchase_patterns.empty:
            print(f"✓ Analyzed {len(purchase_patterns)} months of ordering data")
            avg_monthly = purchase_patterns['Total_Units'].mean()
            print(f"  Average Monthly Units: {avg_monthly:,.0f}")
    
    def analyze_product_supplier_matrix(self):
        """Analyze product-supplier relationships and pricing"""
        
        print("\n🔗 ANALYZING PRODUCT-SUPPLIER RELATIONSHIPS...")
        
        query = """
        WITH ProductSupplier AS (
            SELECT 
                i.Description as Product,
                i.ItemLookupCode as SKU,
                s.SupplierName,
                COUNT(DISTINCT po.ID) as Order_Count,
                SUM(poe.QuantityOrdered) as Total_Ordered,
                AVG(poe.Price) as Avg_Cost,
                MIN(poe.Price) as Min_Cost,
                MAX(poe.Price) as Max_Cost,
                STDEV(poe.Price) as Price_StdDev,
                MAX(po.DateCreated) as Last_Order_Date,
                -- Calculate average margin
                (SELECT AVG(te.Price - te.Cost)
                 FROM dbo.TransactionEntry te
                 WHERE te.ItemID = i.ID) as Avg_Margin,
                -- Current stock
                i.Quantity as Current_Stock,
                -- Sales velocity
                (SELECT SUM(te2.Quantity) / 8.0
                 FROM dbo.TransactionEntry te2
                 JOIN [dbo].[Transaction] t2 ON te2.TransactionNumber = t2.TransactionNumber
                 WHERE te2.ItemID = i.ID 
                   AND t2.Time >= DATEADD(week, -8, GETDATE())) as Weekly_Sales
            FROM dbo.Item i
            JOIN dbo.PurchaseOrderEntry poe ON i.ID = poe.ItemID
            JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
            JOIN dbo.Supplier s ON po.SupplierID = s.ID
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND po.DateCreated >= DATEADD(year, -1, GETDATE())
            GROUP BY i.Description, i.ItemLookupCode, s.SupplierName, i.ID, i.Quantity
        ),
        SupplierRanking AS (
            SELECT 
                Product,
                SKU,
                SupplierName,
                Order_Count,
                Total_Ordered,
                Avg_Cost,
                Avg_Margin,
                Current_Stock,
                Weekly_Sales,
                ROW_NUMBER() OVER (PARTITION BY Product ORDER BY Total_Ordered DESC) as Supplier_Rank,
                COUNT(*) OVER (PARTITION BY Product) as Supplier_Count
            FROM ProductSupplier
        )
        SELECT 
            *,
            CASE 
                WHEN Supplier_Rank = 1 THEN 'PRIMARY'
                WHEN Supplier_Rank = 2 THEN 'SECONDARY'
                ELSE 'BACKUP'
            END as Supplier_Type,
            CASE 
                WHEN Weekly_Sales > 0 THEN Current_Stock / Weekly_Sales
                ELSE 999
            END as Weeks_Coverage
        FROM SupplierRanking
        WHERE Supplier_Rank <= 3  -- Top 3 suppliers per product
        ORDER BY Weekly_Sales DESC, Product, Supplier_Rank
        """
        
        product_supplier = self.db.execute_query(query, [], 'Product-Supplier Matrix Analysis')
        self.analysis_results['product_supplier_matrix'] = product_supplier
        
        if not product_supplier.empty:
            multi_source = product_supplier[product_supplier['Supplier_Count'] > 1]['Product'].nunique()
            print(f"✓ Analyzed {product_supplier['Product'].nunique()} products")
            print(f"  Multi-sourced Products: {multi_source}")
    
    def analyze_inventory_metrics(self):
        """Analyze inventory turnover and velocity metrics"""
        
        print("\n📈 ANALYZING INVENTORY METRICS...")
        
        query = """
        WITH InventoryMetrics AS (
            SELECT 
                i.Description,
                i.ItemLookupCode as SKU,
                i.Quantity as Current_Stock,
                i.Cost as Current_Cost,
                i.Price as Retail_Price,
                i.Quantity * i.Cost as Inventory_Value,
                -- Sales metrics (last 12 weeks)
                (SELECT SUM(te.Quantity) 
                 FROM dbo.TransactionEntry te
                 JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                 WHERE te.ItemID = i.ID 
                   AND t.Time >= DATEADD(week, -12, GETDATE())) as Units_Sold_12wk,
                -- Weekly average
                (SELECT SUM(te.Quantity) / 12.0
                 FROM dbo.TransactionEntry te
                 JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                 WHERE te.ItemID = i.ID 
                   AND t.Time >= DATEADD(week, -12, GETDATE())) as Avg_Weekly_Sales,
                -- Purchase metrics
                (SELECT SUM(poe.QuantityOrdered)
                 FROM dbo.PurchaseOrderEntry poe
                 JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
                 WHERE poe.ItemID = i.ID
                   AND po.DateCreated >= DATEADD(week, -12, GETDATE())) as Units_Ordered_12wk,
                -- Last purchase date
                (SELECT MAX(po.DateCreated)
                 FROM dbo.PurchaseOrderEntry poe
                 JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
                 WHERE poe.ItemID = i.ID) as Last_Purchase_Date
            FROM dbo.Item i
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND i.Inactive = 0
        )
        SELECT 
            Description,
            SKU,
            Current_Stock,
            Inventory_Value,
            Units_Sold_12wk,
            Avg_Weekly_Sales,
            Units_Ordered_12wk,
            -- Turnover rate (annualized)
            CASE 
                WHEN Current_Stock > 0 AND Units_Sold_12wk > 0
                THEN (Units_Sold_12wk * 52.0 / 12.0) / Current_Stock
                ELSE 0
            END as Annual_Turnover_Rate,
            -- Days of inventory
            CASE 
                WHEN Avg_Weekly_Sales > 0
                THEN Current_Stock / (Avg_Weekly_Sales / 7.0)
                ELSE 999
            END as Days_Of_Inventory,
            -- Stock status
            CASE 
                WHEN Current_Stock <= 0 THEN 'OUT_OF_STOCK'
                WHEN Avg_Weekly_Sales > 0 AND Current_Stock / Avg_Weekly_Sales < 1 THEN 'CRITICAL'
                WHEN Avg_Weekly_Sales > 0 AND Current_Stock / Avg_Weekly_Sales < 2 THEN 'LOW'
                WHEN Avg_Weekly_Sales > 0 AND Current_Stock / Avg_Weekly_Sales > 8 THEN 'OVERSTOCK'
                ELSE 'NORMAL'
            END as Stock_Status,
            Last_Purchase_Date,
            DATEDIFF(day, Last_Purchase_Date, GETDATE()) as Days_Since_Purchase
        FROM InventoryMetrics
        WHERE Units_Sold_12wk > 0 OR Current_Stock > 0
        ORDER BY Inventory_Value DESC
        """
        
        inventory_metrics = self.db.execute_query(query, [], 'Inventory Metrics Analysis')
        self.analysis_results['inventory_metrics'] = inventory_metrics
        
        if not inventory_metrics.empty:
            total_value = inventory_metrics['Inventory_Value'].sum()
            avg_turnover = inventory_metrics[inventory_metrics['Annual_Turnover_Rate'] > 0]['Annual_Turnover_Rate'].mean()
            print(f"✓ Analyzed {len(inventory_metrics)} SKUs")
            print(f"  Total Inventory Value: ${total_value:,.2f}")
            print(f"  Average Turnover Rate: {avg_turnover:.1f}x per year")
    
    def analyze_customer_segments(self):
        """Analyze customer purchasing patterns for cigarettes"""
        
        print("\n👥 ANALYZING CUSTOMER SEGMENTS...")
        
        query = """
        WITH CustomerMetrics AS (
            SELECT 
                CASE 
                    WHEN c.Company IS NOT NULL AND LEN(c.Company) > 2 THEN 'WHOLESALE'
                    ELSE 'RETAIL'
                END as Customer_Type,
                COUNT(DISTINCT t.CustomerID) as Customer_Count,
                COUNT(DISTINCT t.TransactionNumber) as Transaction_Count,
                SUM(te.Quantity) as Total_Units,
                SUM(te.Quantity * (te.Price - te.Cost)) as Total_Profit,
                AVG(te.Quantity) as Avg_Units_Per_Transaction,
                -- Time distribution
                COUNT(DISTINCT CASE WHEN DATEPART(hour, t.Time) BETWEEN 6 AND 12 THEN t.TransactionNumber END) as Morning_Sales,
                COUNT(DISTINCT CASE WHEN DATEPART(hour, t.Time) BETWEEN 12 AND 17 THEN t.TransactionNumber END) as Afternoon_Sales,
                COUNT(DISTINCT CASE WHEN DATEPART(hour, t.Time) BETWEEN 17 AND 22 THEN t.TransactionNumber END) as Evening_Sales,
                -- Brand preferences
                SUM(CASE WHEN i.Description LIKE 'NEWPORT%' THEN te.Quantity ELSE 0 END) as Newport_Units,
                SUM(CASE WHEN i.Description LIKE 'MARL%' THEN te.Quantity ELSE 0 END) as Marlboro_Units,
                SUM(CASE WHEN i.Description LIKE '24/7%' THEN te.Quantity ELSE 0 END) as Budget_Units
            FROM dbo.[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            JOIN dbo.Category cat ON i.CategoryID = cat.ID
            LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
            WHERE cat.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(month, -3, GETDATE())
            GROUP BY CASE WHEN c.Company IS NOT NULL AND LEN(c.Company) > 2 THEN 'WHOLESALE' ELSE 'RETAIL' END
        )
        SELECT 
            *,
            Total_Profit / NULLIF(Total_Units, 0) as Profit_Per_Unit,
            Newport_Units * 100.0 / NULLIF(Total_Units, 0) as Newport_Pct,
            Marlboro_Units * 100.0 / NULLIF(Total_Units, 0) as Marlboro_Pct,
            Budget_Units * 100.0 / NULLIF(Total_Units, 0) as Budget_Pct
        FROM CustomerMetrics
        """
        
        customer_segments = self.db.execute_query(query, [], 'Customer Segmentation Analysis')
        self.analysis_results['customer_segments'] = customer_segments
        
        if not customer_segments.empty:
            print(f"✓ Analyzed {customer_segments['Customer_Count'].sum()} customers")
    
    def analyze_seasonal_patterns(self):
        """Analyze seasonal and temporal patterns"""
        
        print("\n📅 ANALYZING SEASONAL PATTERNS...")
        
        query = """
        WITH SeasonalData AS (
            SELECT 
                YEAR(t.Time) as Year,
                DATEPART(quarter, t.Time) as Quarter,
                MONTH(t.Time) as Month,
                DATENAME(month, t.Time) as MonthName,
                DATEPART(week, t.Time) as Week,
                SUM(te.Quantity) as Units_Sold,
                SUM(te.Quantity * (te.Price - te.Cost)) as Profit,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(DISTINCT t.CustomerID) as Unique_Customers,
                AVG(te.Price) as Avg_Price
            FROM dbo.[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN dbo.Item i ON te.ItemID = i.ID
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(year, -2, GETDATE())
            GROUP BY YEAR(t.Time), DATEPART(quarter, t.Time), MONTH(t.Time), 
                     DATENAME(month, t.Time), DATEPART(week, t.Time)
        )
        SELECT 
            Year,
            Quarter,
            Month,
            MonthName,
            AVG(Units_Sold) as Avg_Weekly_Units,
            SUM(Units_Sold) as Total_Monthly_Units,
            SUM(Profit) as Total_Monthly_Profit,
            AVG(Avg_Price) as Avg_Monthly_Price,
            -- Identify peak weeks
            MAX(Units_Sold) as Peak_Week_Units,
            MIN(Units_Sold) as Low_Week_Units
        FROM SeasonalData
        GROUP BY Year, Quarter, Month, MonthName
        ORDER BY Year DESC, Month DESC
        """
        
        seasonal_patterns = self.db.execute_query(query, [], 'Seasonal Pattern Analysis')
        self.analysis_results['seasonal_patterns'] = seasonal_patterns
        
        if not seasonal_patterns.empty:
            print(f"✓ Analyzed {len(seasonal_patterns)} months of seasonal data")
    
    def analyze_profitability(self):
        """Deep profitability analysis by product, supplier, and time"""
        
        print("\n💰 ANALYZING PROFITABILITY...")
        
        query = """
        WITH ProfitAnalysis AS (
            SELECT 
                i.Description as Product,
                i.ItemLookupCode as SKU,
                -- Sales metrics
                SUM(te.Quantity) as Units_Sold,
                SUM(te.Quantity * te.Price) as Revenue,
                SUM(te.Quantity * te.Cost) as COGS,
                SUM(te.Quantity * (te.Price - te.Cost)) as Gross_Profit,
                AVG(te.Price - te.Cost) as Avg_Margin,
                -- Calculate margin percentage
                CASE 
                    WHEN SUM(te.Quantity * te.Price) > 0
                    THEN (SUM(te.Quantity * (te.Price - te.Cost)) * 100.0 / SUM(te.Quantity * te.Price))
                    ELSE 0
                END as Margin_Pct,
                -- Velocity
                COUNT(DISTINCT t.TransactionNumber) as Transaction_Count,
                COUNT(DISTINCT t.CustomerID) as Customer_Count
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(month, -6, GETDATE())
            GROUP BY i.Description, i.ItemLookupCode
        )
        SELECT 
            *,
            -- Rank by different metrics
            RANK() OVER (ORDER BY Gross_Profit DESC) as Profit_Rank,
            RANK() OVER (ORDER BY Units_Sold DESC) as Volume_Rank,
            RANK() OVER (ORDER BY Margin_Pct DESC) as Margin_Rank,
            -- ABC classification
            CASE 
                WHEN SUM(Gross_Profit) OVER (ORDER BY Gross_Profit DESC) <= SUM(Gross_Profit) OVER () * 0.8 THEN 'A'
                WHEN SUM(Gross_Profit) OVER (ORDER BY Gross_Profit DESC) <= SUM(Gross_Profit) OVER () * 0.95 THEN 'B'
                ELSE 'C'
            END as ABC_Class
        FROM ProfitAnalysis
        WHERE Units_Sold > 0
        ORDER BY Gross_Profit DESC
        """
        
        profitability = self.db.execute_query(query, [], 'Profitability Analysis')
        self.analysis_results['profitability'] = profitability
        
        if not profitability.empty:
            total_profit = profitability['Gross_Profit'].sum()
            avg_margin = profitability['Margin_Pct'].mean()
            print(f"✓ Analyzed profitability for {len(profitability)} products")
            print(f"  Total Gross Profit (6mo): ${total_profit:,.2f}")
            print(f"  Average Margin: {avg_margin:.1f}%")
    
    def analyze_market_dynamics(self):
        """Analyze market trends and competitive dynamics"""
        
        print("\n🎯 ANALYZING MARKET DYNAMICS...")
        
        query = """
        WITH MarketTrends AS (
            SELECT 
                -- Extract brand
                CASE 
                    WHEN i.Description LIKE 'NEWPORT%' THEN 'NEWPORT'
                    WHEN i.Description LIKE 'MARL%' THEN 'MARLBORO'
                    WHEN i.Description LIKE '24/7%' THEN '24/7'
                    WHEN i.Description LIKE 'CAMEL%' THEN 'CAMEL'
                    WHEN i.Description LIKE 'AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                    ELSE 'OTHER'
                END as Brand,
                DATEPART(year, t.Time) as Year,
                DATEPART(month, t.Time) as Month,
                SUM(te.Quantity) as Units,
                AVG(te.Price) as Avg_Price,
                COUNT(DISTINCT t.CustomerID) as Customers
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'
              AND t.Time >= DATEADD(year, -1, GETDATE())
            GROUP BY 
                CASE 
                    WHEN i.Description LIKE 'NEWPORT%' THEN 'NEWPORT'
                    WHEN i.Description LIKE 'MARL%' THEN 'MARLBORO'
                    WHEN i.Description LIKE '24/7%' THEN '24/7'
                    WHEN i.Description LIKE 'CAMEL%' THEN 'CAMEL'
                    WHEN i.Description LIKE 'AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                    ELSE 'OTHER'
                END,
                DATEPART(year, t.Time),
                DATEPART(month, t.Time)
        )
        SELECT 
            Brand,
            Year,
            Month,
            Units,
            Avg_Price,
            Customers,
            SUM(Units) OVER (PARTITION BY Brand ORDER BY Year, Month) as Cumulative_Units,
            Units * 100.0 / SUM(Units) OVER (PARTITION BY Year, Month) as Market_Share
        FROM MarketTrends
        ORDER BY Year DESC, Month DESC, Units DESC
        """
        
        market_dynamics = self.db.execute_query(query, [], 'Market Dynamics Analysis')
        self.analysis_results['market_dynamics'] = market_dynamics
        
        if not market_dynamics.empty:
            brands = market_dynamics['Brand'].nunique()
            print(f"✓ Analyzed {brands} brand categories")
    
    def generate_comprehensive_report(self):
        """Generate detailed HTML report with all analyses"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Comprehensive Cigarette Business Intelligence Report - {datetime.now().strftime('%B %d, %Y')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f0f2f5; }}
        .header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .section {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ margin: 0; font-size: 2.5em; }}
        h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
        tr:hover {{ background: #f8f9fa; }}
        .metric-box {{ display: inline-block; background: #ecf0f1; padding: 15px; margin: 10px; border-radius: 8px; min-width: 200px; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
        .alert {{ background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .chart {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Comprehensive Cigarette Business Intelligence Report</h1>
        <p style="opacity: 0.9; font-size: 1.2em;">Complete Analysis of Suppliers, Ordering Patterns, and Market Dynamics</p>
        <p>Generated: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}</p>
    </div>
"""
        
        # Executive Summary
        if 'supplier_performance' in self.analysis_results:
            suppliers = self.analysis_results['supplier_performance']
            total_value = suppliers['Total_Purchase_Value'].sum()
            active_suppliers = len(suppliers[suppliers['Orders_1mo'] > 0])
            
            html_content += f"""
    <div class="section">
        <h2>Executive Summary</h2>
        <div style="display: flex; flex-wrap: wrap;">
            <div class="metric-box">
                <div class="metric-value">{len(suppliers)}</div>
                <div class="metric-label">Total Suppliers</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{active_suppliers}</div>
                <div class="metric-label">Active This Month</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">${total_value/1000000:.1f}M</div>
                <div class="metric-label">Total Purchase Value</div>
            </div>
        </div>
    </div>
"""
        
        # Supplier Performance Details
        if 'supplier_performance' in self.analysis_results:
            suppliers = self.analysis_results['supplier_performance']
            html_content += """
    <div class="section">
        <h2>Supplier Performance Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Supplier</th>
                    <th>Total Orders</th>
                    <th>SKUs</th>
                    <th>Total Value</th>
                    <th>Last 3 Months</th>
                    <th>Last Month</th>
                    <th>Trend</th>
                    <th>Top Products</th>
                </tr>
            </thead>
            <tbody>
"""
            for _, row in suppliers.head(15).iterrows():
                trend_color = {'INCREASING': 'green', 'DECREASING': 'red', 'STABLE': 'blue'}.get(row.get('Order_Trend', 'STABLE'), 'gray')
                html_content += f"""
                <tr>
                    <td><strong>{row['SupplierName']}</strong></td>
                    <td>{row['Total_POs']:.0f}</td>
                    <td>{row['Unique_SKUs']:.0f}</td>
                    <td>${row['Total_Purchase_Value']:,.0f}</td>
                    <td>${row.get('Value_3mo', 0):,.0f}</td>
                    <td>{row.get('Orders_1mo', 0):.0f} orders</td>
                    <td style="color: {trend_color}; font-weight: bold;">{row.get('Order_Trend', 'N/A')}</td>
                    <td style="font-size: 0.9em;">{str(row.get('Top_Products', ''))[:100]}...</td>
                </tr>
"""
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # Inventory Metrics
        if 'inventory_metrics' in self.analysis_results:
            inventory = self.analysis_results['inventory_metrics']
            critical = len(inventory[inventory['Stock_Status'] == 'CRITICAL'])
            out_of_stock = len(inventory[inventory['Stock_Status'] == 'OUT_OF_STOCK'])
            overstock = len(inventory[inventory['Stock_Status'] == 'OVERSTOCK'])
            
            html_content += f"""
    <div class="section">
        <h2>Inventory Status Overview</h2>
        <div class="alert">
            <strong>ALERTS:</strong> {out_of_stock} items OUT OF STOCK | {critical} items CRITICAL (&lt;1 week supply)
        </div>
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Current Stock</th>
                    <th>Weekly Sales</th>
                    <th>Days of Inventory</th>
                    <th>Turnover Rate</th>
                    <th>Status</th>
                    <th>Days Since Order</th>
                </tr>
            </thead>
            <tbody>
"""
            # Show critical items first
            critical_items = inventory[inventory['Stock_Status'].isin(['OUT_OF_STOCK', 'CRITICAL'])].head(20)
            for _, row in critical_items.iterrows():
                status_color = {'OUT_OF_STOCK': '#e74c3c', 'CRITICAL': '#f39c12', 'LOW': '#f1c40f'}.get(row['Stock_Status'], '#27ae60')
                html_content += f"""
                <tr>
                    <td><strong>{row['Description']}</strong></td>
                    <td>{row['Current_Stock']:.0f}</td>
                    <td>{row.get('Avg_Weekly_Sales', 0):.1f}</td>
                    <td>{row.get('Days_Of_Inventory', 0):.1f}</td>
                    <td>{row.get('Annual_Turnover_Rate', 0):.1f}x</td>
                    <td style="background: {status_color}; color: white; font-weight: bold;">{row['Stock_Status']}</td>
                    <td>{row.get('Days_Since_Purchase', 'Never')}</td>
                </tr>
"""
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # Purchase Patterns
        if 'purchase_patterns' in self.analysis_results:
            patterns = self.analysis_results['purchase_patterns']
            html_content += """
    <div class="section">
        <h2>Historical Purchase Order Patterns</h2>
        <table>
            <thead>
                <tr>
                    <th>Month</th>
                    <th>POs</th>
                    <th>Units</th>
                    <th>Value</th>
                    <th>MoM Change</th>
                    <th>Peak Day</th>
                </tr>
            </thead>
            <tbody>
"""
            for _, row in patterns.head(12).iterrows():
                change_color = 'green' if row.get('MoM_Change_Pct', 0) > 0 else 'red'
                html_content += f"""
                <tr>
                    <td>{row['MonthName']} {row['Year']}</td>
                    <td>{row['PO_Count']:.0f}</td>
                    <td>{row['Total_Units']:,.0f}</td>
                    <td>${row['Total_Value']:,.0f}</td>
                    <td style="color: {change_color};">{row.get('MoM_Change_Pct', 0):.1f}%</td>
                    <td>{row.get('Peak_Order_Day', 'N/A')}</td>
                </tr>
"""
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # Profitability Analysis
        if 'profitability' in self.analysis_results:
            profit = self.analysis_results['profitability']
            top_profit = profit.head(15)
            
            html_content += """
    <div class="section">
        <h2>Top 15 Products by Profitability</h2>
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Units Sold</th>
                    <th>Revenue</th>
                    <th>Gross Profit</th>
                    <th>Margin %</th>
                    <th>Profit Rank</th>
                    <th>Volume Rank</th>
                </tr>
            </thead>
            <tbody>
"""
            for _, row in top_profit.iterrows():
                html_content += f"""
                <tr>
                    <td><strong>{row['Product']}</strong></td>
                    <td>{row['Units_Sold']:,.0f}</td>
                    <td>${row['Revenue']:,.2f}</td>
                    <td>${row['Gross_Profit']:,.2f}</td>
                    <td>{row['Margin_Pct']:.1f}%</td>
                    <td>#{row['Profit_Rank']:.0f}</td>
                    <td>#{row['Volume_Rank']:.0f}</td>
                </tr>
"""
            html_content += """
            </tbody>
        </table>
    </div>
"""
        
        # Close HTML
        html_content += """
    <div class="section" style="text-align: center; background: #34495e; color: white;">
        <p>End of Report - Generated by Comprehensive Cigarette Analytics System</p>
        <p>Data Period: Last 2 Years with Focus on Recent 6 Months</p>
    </div>
</body>
</html>
"""
        
        # Save report
        filename = f"cigarette_comprehensive_report_{timestamp}.html"
        with open(filename, 'w') as f:
            f.write(html_content)
        
        return filename

def main():
    analytics = ComprehensiveCigaretteAnalytics()
    
    # Run all analyses
    results = analytics.run_full_analysis()
    
    # Generate report
    report_file = analytics.generate_comprehensive_report()
    
    print("\n" + "="*80)
    print("✅ COMPREHENSIVE ANALYSIS COMPLETE")
    print(f"📊 Report saved: {report_file}")
    
    # Print summary statistics
    if 'supplier_performance' in results and not results['supplier_performance'].empty:
        print(f"\n📦 SUPPLIER SUMMARY:")
        print(f"  Total Suppliers: {len(results['supplier_performance'])}")
        print(f"  Total Purchase Value: ${results['supplier_performance']['Total_Purchase_Value'].sum():,.2f}")
    
    if 'inventory_metrics' in results and not results['inventory_metrics'].empty:
        inventory = results['inventory_metrics']
        print(f"\n📈 INVENTORY SUMMARY:")
        print(f"  Total SKUs: {len(inventory)}")
        print(f"  Out of Stock: {len(inventory[inventory['Stock_Status'] == 'OUT_OF_STOCK'])}")
        print(f"  Critical: {len(inventory[inventory['Stock_Status'] == 'CRITICAL'])}")
    
    return report_file

if __name__ == '__main__':
    main()