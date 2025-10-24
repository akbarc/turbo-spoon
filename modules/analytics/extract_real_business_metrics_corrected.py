#!/usr/bin/env python3
"""
Extract Real Business Metrics from Georgia Dashboard Database - CORRECTED SCHEMA
This script connects directly to the database and extracts comprehensive business metrics using the correct table and column names
"""

import os
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from database_pymssql import SQLServerConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def decimal_default(obj):
    """JSON encoder for Decimal and other non-serializable objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)

def extract_business_metrics():
    """Extract comprehensive business metrics using correct schema"""
    metrics = {
        'extraction_timestamp': datetime.now().isoformat(),
        'executive_summary': {},
        'sales_performance': {},
        'inventory_health': {},
        'customer_intelligence': {},
        'ar_summary': {},
        'database_metrics': {}
    }
    
    try:
        # Initialize database connection
        db = SQLServerConnection()
        logger.info("Database connection established")
        
        # Executive Summary Metrics
        logger.info("Extracting executive summary metrics...")
        
        # Today's sales - using correct Transaction table schema
        today_sales_query = """
        SELECT 
            COUNT(DISTINCT t.CustomerID) as customer_count,
            SUM(t.Total) as total_sales,
            COUNT(DISTINCT t.TransactionNumber) as transaction_count,
            AVG(t.Total) as avg_transaction
        FROM 
            [dbo].[Transaction] t
        WHERE 
            CAST(t.Time AS DATE) = CAST(GETDATE() AS DATE)
        """
        today_data = db.execute_query(today_sales_query, description="Today's sales metrics")
        if not today_data.empty:
            metrics['executive_summary']['today'] = {
                'customers': int(today_data.iloc[0]['customer_count'] or 0),
                'sales': float(today_data.iloc[0]['total_sales'] or 0),
                'transactions': int(today_data.iloc[0]['transaction_count'] or 0),
                'avg_transaction': float(today_data.iloc[0]['avg_transaction'] or 0)
            }
        
        # Week to date
        week_sales_query = """
        SELECT 
            COUNT(DISTINCT t.CustomerID) as customer_count,
            SUM(t.Total) as total_sales,
            COUNT(DISTINCT t.TransactionNumber) as transaction_count
        FROM 
            [dbo].[Transaction] t
        WHERE 
            t.Time >= DATEADD(day, -DATEPART(weekday, GETDATE()) + 1, CAST(GETDATE() AS DATE))
        """
        week_data = db.execute_query(week_sales_query, description="Week sales metrics")
        if not week_data.empty:
            metrics['executive_summary']['week'] = {
                'customers': int(week_data.iloc[0]['customer_count'] or 0),
                'sales': float(week_data.iloc[0]['total_sales'] or 0),
                'transactions': int(week_data.iloc[0]['transaction_count'] or 0)
            }
        
        # Month to date
        month_sales_query = """
        SELECT 
            COUNT(DISTINCT t.CustomerID) as customer_count,
            SUM(t.Total) as total_sales,
            COUNT(DISTINCT t.TransactionNumber) as transaction_count
        FROM 
            [dbo].[Transaction] t
        WHERE 
            YEAR(t.Time) = YEAR(GETDATE()) 
            AND MONTH(t.Time) = MONTH(GETDATE())
        """
        month_data = db.execute_query(month_sales_query, description="Month sales metrics")
        if not month_data.empty:
            metrics['executive_summary']['month'] = {
                'customers': int(month_data.iloc[0]['customer_count'] or 0),
                'sales': float(month_data.iloc[0]['total_sales'] or 0),
                'transactions': int(month_data.iloc[0]['transaction_count'] or 0)
            }
        
        # Sales Performance Metrics
        logger.info("Extracting sales performance metrics...")
        
        # Top products by revenue (last 30 days) - using TransactionEntry
        top_products_query = """
        SELECT TOP 10
            i.Name as product_name,
            i.ID as item_id,
            SUM(te.Quantity) as total_qty,
            SUM(te.Price * te.Quantity) as total_revenue,
            AVG(te.Price) as avg_price,
            COUNT(DISTINCT t.CustomerID) as unique_customers
        FROM 
            [dbo].[Transaction] t 
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            LEFT JOIN dbo.Item i ON te.ItemID = i.ID
        WHERE 
            t.Time >= DATEADD(day, -30, GETDATE())
        GROUP BY 
            i.Name, i.ID
        ORDER BY 
            total_revenue DESC
        """
        top_products = db.execute_query(top_products_query, description="Top products by revenue")
        metrics['sales_performance']['top_products'] = top_products.to_dict('records') if not top_products.empty else []
        
        # Top categories by revenue
        top_categories_query = """
        SELECT TOP 10
            ISNULL(c.Name, 'Uncategorized') as category,
            SUM(te.Quantity) as total_qty,
            SUM(te.Price * te.Quantity) as total_revenue,
            COUNT(DISTINCT i.ID) as product_count,
            COUNT(DISTINCT t.CustomerID) as unique_customers
        FROM 
            [dbo].[Transaction] t 
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            LEFT JOIN dbo.Item i ON te.ItemID = i.ID
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE 
            t.Time >= DATEADD(day, -30, GETDATE())
        GROUP BY 
            c.Name
        ORDER BY 
            total_revenue DESC
        """
        top_categories = db.execute_query(top_categories_query, description="Top categories by revenue")
        metrics['sales_performance']['top_categories'] = top_categories.to_dict('records') if not top_categories.empty else []
        
        # Inventory Health Metrics
        logger.info("Extracting inventory health metrics...")
        
        # Low stock items - using correct Item table schema
        low_stock_query = """
        SELECT TOP 20
            i.ID as item_id,
            i.Name as product_name,
            i.Quantity as current_stock,
            ISNULL(c.Name, 'Uncategorized') as category,
            i.Cost,
            i.Price
        FROM 
            dbo.Item i
            LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE 
            i.Quantity <= 5 
            AND i.Quantity >= 0
            AND i.Active = 1
        ORDER BY 
            i.Quantity ASC
        """
        low_stock = db.execute_query(low_stock_query, description="Low stock items")
        metrics['inventory_health']['low_stock'] = low_stock.to_dict('records') if not low_stock.empty else []
        
        # Overall inventory summary
        inventory_summary_query = """
        SELECT 
            COUNT(*) as total_products,
            SUM(CASE WHEN Quantity <= 5 THEN 1 ELSE 0 END) as low_stock_count,
            SUM(CASE WHEN Quantity = 0 THEN 1 ELSE 0 END) as out_of_stock_count,
            SUM(Quantity * Cost) as total_inventory_value,
            AVG(Quantity) as avg_stock_level,
            COUNT(CASE WHEN Active = 1 THEN 1 END) as active_products
        FROM 
            dbo.Item
        WHERE 
            Quantity >= 0
        """
        inventory_summary = db.execute_query(inventory_summary_query, description="Inventory summary")
        if not inventory_summary.empty:
            metrics['inventory_health']['summary'] = inventory_summary.iloc[0].to_dict()
        
        # Customer Intelligence Metrics
        logger.info("Extracting customer intelligence metrics...")
        
        # Customer summary stats using Customer table
        customer_stats_query = """
        SELECT 
            COUNT(*) as total_customers,
            COUNT(CASE WHEN AccountBalance > 0 THEN 1 END) as customers_with_balance,
            SUM(AccountBalance) as total_ar_balance,
            AVG(AccountBalance) as avg_customer_balance
        FROM 
            dbo.Customer
        """
        customer_stats = db.execute_query(customer_stats_query, description="Customer statistics")
        if not customer_stats.empty:
            metrics['customer_intelligence']['summary'] = customer_stats.iloc[0].to_dict()
        
        # Top customers by sales (last 30 days)
        top_customers_query = """
        SELECT TOP 10
            c.ID as customer_id,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Walk-in Customer') as customer_name,
            c.AccountBalance as current_balance,
            SUM(t.Total) as total_purchases_30d,
            COUNT(DISTINCT t.TransactionNumber) as transaction_count_30d,
            MAX(t.Time) as last_transaction,
            CASE 
                WHEN c.AccountBalance > 1000 THEN 'High Risk'
                WHEN c.AccountBalance > 500 THEN 'Medium Risk'
                ELSE 'Low Risk'
            END as risk_level
        FROM 
            dbo.Customer c
            LEFT JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID AND t.Time >= DATEADD(day, -30, GETDATE())
        GROUP BY 
            c.ID, c.Company, c.FirstName, c.LastName, c.AccountBalance
        ORDER BY 
            total_purchases_30d DESC
        """
        top_customers = db.execute_query(top_customers_query, description="Top customers analysis")
        metrics['customer_intelligence']['top_customers'] = top_customers.to_dict('records') if not top_customers.empty else []
        
        # AR Summary Metrics
        logger.info("Extracting AR summary metrics...")
        
        # AR aging analysis using AccountReceivable table
        ar_aging_query = """
        SELECT 
            COUNT(*) as total_customers_with_balance,
            SUM(Balance) as total_balance,
            SUM(CASE WHEN Balance > 0 AND Balance <= 100 THEN Balance ELSE 0 END) as balance_0_100,
            SUM(CASE WHEN Balance > 100 AND Balance <= 500 THEN Balance ELSE 0 END) as balance_100_500,
            SUM(CASE WHEN Balance > 500 AND Balance <= 1000 THEN Balance ELSE 0 END) as balance_500_1000,
            SUM(CASE WHEN Balance > 1000 THEN Balance ELSE 0 END) as balance_over_1000,
            COUNT(CASE WHEN Balance > 0 AND Balance <= 100 THEN 1 END) as count_0_100,
            COUNT(CASE WHEN Balance > 100 AND Balance <= 500 THEN 1 END) as count_100_500,
            COUNT(CASE WHEN Balance > 500 AND Balance <= 1000 THEN 1 END) as count_500_1000,
            COUNT(CASE WHEN Balance > 1000 THEN 1 END) as count_over_1000
        FROM 
            dbo.AccountReceivable
        WHERE 
            Balance > 0
        """
        ar_aging = db.execute_query(ar_aging_query, description="AR aging analysis")
        if not ar_aging.empty:
            metrics['ar_summary']['aging'] = ar_aging.iloc[0].to_dict()
        
        # High risk customers from AR
        high_risk_query = """
        SELECT TOP 20
            ar.CustomerID,
            c.Company,
            c.FirstName,
            c.LastName,
            ar.Balance,
            ar.LastTransactionDate,
            DATEDIFF(day, ar.LastTransactionDate, GETDATE()) as days_since_transaction
        FROM 
            dbo.AccountReceivable ar
            LEFT JOIN dbo.Customer c ON ar.CustomerID = c.ID
        WHERE 
            ar.Balance > 500
        ORDER BY 
            ar.Balance DESC
        """
        high_risk = db.execute_query(high_risk_query, description="High risk customers")
        metrics['ar_summary']['high_risk_customers'] = high_risk.to_dict('records') if not high_risk.empty else []
        
        # Database Statistics
        logger.info("Extracting database statistics...")
        
        # Table row counts - using correct table names
        table_stats_query = """
        SELECT 
            'Customer' as table_name, COUNT(*) as row_count FROM dbo.Customer
        UNION ALL SELECT 'Item', COUNT(*) FROM dbo.Item
        UNION ALL SELECT 'Transaction', COUNT(*) FROM [dbo].[Transaction]
        UNION ALL SELECT 'TransactionEntry', COUNT(*) FROM dbo.TransactionEntry
        UNION ALL SELECT 'AccountReceivable', COUNT(*) FROM dbo.AccountReceivable
        UNION ALL SELECT 'Category', COUNT(*) FROM dbo.Category
        """
        table_stats = db.execute_query(table_stats_query, description="Table statistics")
        metrics['database_metrics']['table_counts'] = table_stats.to_dict('records') if not table_stats.empty else []
        
        # Date range of transaction data
        date_range_query = """
        SELECT 
            MIN(Time) as earliest_transaction,
            MAX(Time) as latest_transaction,
            COUNT(DISTINCT CAST(Time AS DATE)) as unique_transaction_days
        FROM 
            [dbo].[Transaction]
        """
        date_range = db.execute_query(date_range_query, description="Data range analysis")
        if not date_range.empty:
            metrics['database_metrics']['data_range'] = date_range.iloc[0].to_dict()
        
        logger.info("✅ Successfully extracted all business metrics")
        
    except Exception as e:
        logger.error(f"❌ Error extracting metrics: {str(e)}")
        metrics['error'] = str(e)
    
    finally:
        if 'db' in locals():
            db.close()
    
    return metrics

def main():
    """Main function to extract and save metrics"""
    logger.info("🚀 Starting business metrics extraction with corrected schema...")
    
    # Extract metrics
    metrics = extract_business_metrics()
    
    # Save to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'real_business_metrics_corrected_{timestamp}.json'
    
    try:
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=2, default=decimal_default)
        
        logger.info(f"✅ Metrics saved to {filename}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("REAL BUSINESS METRICS SUMMARY")
        print(f"{'='*60}")
        
        if 'executive_summary' in metrics and 'today' in metrics['executive_summary']:
            today = metrics['executive_summary']['today']
            print(f"Today's Performance:")
            print(f"  • Customers: {today.get('customers', 'N/A')}")
            print(f"  • Sales: ${today.get('sales', 0):,.2f}")
            print(f"  • Transactions: {today.get('transactions', 'N/A')}")
            print(f"  • Avg Transaction: ${today.get('avg_transaction', 0):,.2f}")
        
        if 'executive_summary' in metrics and 'month' in metrics['executive_summary']:
            month = metrics['executive_summary']['month']
            print(f"\nMonth to Date:")
            print(f"  • Customers: {month.get('customers', 'N/A')}")
            print(f"  • Sales: ${month.get('sales', 0):,.2f}")
            print(f"  • Transactions: {month.get('transactions', 'N/A')}")
        
        if 'customer_intelligence' in metrics and 'summary' in metrics['customer_intelligence']:
            customer_summary = metrics['customer_intelligence']['summary']
            print(f"\nCustomer Intelligence:")
            print(f"  • Total Customers: {customer_summary.get('total_customers', 'N/A')}")
            print(f"  • Customers with Balance: {customer_summary.get('customers_with_balance', 'N/A')}")
            print(f"  • Total AR Balance: ${customer_summary.get('total_ar_balance', 0):,.2f}")
        
        if 'inventory_health' in metrics and 'summary' in metrics['inventory_health']:
            inventory_summary = metrics['inventory_health']['summary']
            print(f"\nInventory Health:")
            print(f"  • Total Products: {inventory_summary.get('total_products', 'N/A')}")
            print(f"  • Low Stock Items: {inventory_summary.get('low_stock_count', 'N/A')}")
            print(f"  • Total Inventory Value: ${inventory_summary.get('total_inventory_value', 0):,.2f}")
        
        if 'ar_summary' in metrics and 'aging' in metrics['ar_summary']:
            ar_aging = metrics['ar_summary']['aging']
            print(f"\nAR Summary:")
            print(f"  • Total AR Balance: ${ar_aging.get('total_balance', 0):,.2f}")
            print(f"  • Customers with Balance: {ar_aging.get('total_customers_with_balance', 'N/A')}")
            print(f"  • High Balance Customers (>$1000): {ar_aging.get('count_over_1000', 'N/A')}")
        
        if 'database_metrics' in metrics and 'table_counts' in metrics['database_metrics']:
            print(f"\nDatabase Statistics:")
            for table in metrics['database_metrics']['table_counts']:
                print(f"  • {table['table_name']}: {table['row_count']:,} records")
        
        print(f"\n📄 Full details saved to: {filename}")
        
    except Exception as e:
        logger.error(f"❌ Error saving metrics: {str(e)}")

if __name__ == "__main__":
    main()