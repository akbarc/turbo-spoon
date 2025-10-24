#!/usr/bin/env python3
"""
Extract Real Business Metrics from Georgia Dashboard Database
This script connects directly to the database and extracts comprehensive business metrics
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
    """Extract comprehensive business metrics"""
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
        
        # Today's sales
        today_sales_query = """
        SELECT 
            COUNT(DISTINCT h.customer) as customer_count,
            SUM(d.qty * d.price) as total_sales,
            COUNT(DISTINCT h.id) as transaction_count,
            AVG(d.qty * d.price) as avg_transaction
        FROM 
            sale_h h 
            JOIN sale_d d ON h.id = d.sale_id 
        WHERE 
            CAST(h.date AS DATE) = CAST(GETDATE() AS DATE)
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
            COUNT(DISTINCT h.customer) as customer_count,
            SUM(d.qty * d.price) as total_sales,
            COUNT(DISTINCT h.id) as transaction_count
        FROM 
            sale_h h 
            JOIN sale_d d ON h.id = d.sale_id 
        WHERE 
            h.date >= DATEADD(day, -DATEPART(weekday, GETDATE()) + 1, CAST(GETDATE() AS DATE))
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
            COUNT(DISTINCT h.customer) as customer_count,
            SUM(d.qty * d.price) as total_sales,
            COUNT(DISTINCT h.id) as transaction_count
        FROM 
            sale_h h 
            JOIN sale_d d ON h.id = d.sale_id 
        WHERE 
            YEAR(h.date) = YEAR(GETDATE()) 
            AND MONTH(h.date) = MONTH(GETDATE())
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
        
        # Top products by revenue (last 30 days)
        top_products_query = """
        SELECT TOP 10
            i.name as product_name,
            i.item_code,
            SUM(d.qty) as total_qty,
            SUM(d.qty * d.price) as total_revenue,
            AVG(d.price) as avg_price,
            COUNT(DISTINCT h.customer) as unique_customers
        FROM 
            sale_h h 
            JOIN sale_d d ON h.id = d.sale_id 
            LEFT JOIN item i ON d.item_code = i.item_code
        WHERE 
            h.date >= DATEADD(day, -30, GETDATE())
        GROUP BY 
            i.name, i.item_code
        ORDER BY 
            total_revenue DESC
        """
        top_products = db.execute_query(top_products_query, description="Top products by revenue")
        metrics['sales_performance']['top_products'] = top_products.to_dict('records') if not top_products.empty else []
        
        # Top categories by revenue
        top_categories_query = """
        SELECT TOP 10
            ISNULL(i.category, 'Uncategorized') as category,
            SUM(d.qty) as total_qty,
            SUM(d.qty * d.price) as total_revenue,
            COUNT(DISTINCT d.item_code) as product_count,
            COUNT(DISTINCT h.customer) as unique_customers
        FROM 
            sale_h h 
            JOIN sale_d d ON h.id = d.sale_id 
            LEFT JOIN item i ON d.item_code = i.item_code
        WHERE 
            h.date >= DATEADD(day, -30, GETDATE())
        GROUP BY 
            i.category
        ORDER BY 
            total_revenue DESC
        """
        top_categories = db.execute_query(top_categories_query, description="Top categories by revenue")
        metrics['sales_performance']['top_categories'] = top_categories.to_dict('records') if not top_categories.empty else []
        
        # Inventory Health Metrics
        logger.info("Extracting inventory health metrics...")
        
        # Low stock items (quantity <= 5)
        low_stock_query = """
        SELECT TOP 20
            i.item_code,
            i.name as product_name,
            i.onhand as current_stock,
            ISNULL(i.category, 'Uncategorized') as category,
            i.cost,
            i.price,
            DATEDIFF(day, i.last_sale_date, GETDATE()) as days_since_last_sale
        FROM 
            item i
        WHERE 
            i.onhand <= 5 
            AND i.onhand >= 0
            AND i.active = 1
        ORDER BY 
            i.onhand ASC, days_since_last_sale ASC
        """
        low_stock = db.execute_query(low_stock_query, description="Low stock items")
        metrics['inventory_health']['low_stock'] = low_stock.to_dict('records') if not low_stock.empty else []
        
        # Dead stock (no sales in 90+ days and stock > 0)
        dead_stock_query = """
        SELECT TOP 20
            i.item_code,
            i.name as product_name,
            i.onhand as current_stock,
            i.cost,
            i.price,
            (i.onhand * i.cost) as tied_up_capital,
            DATEDIFF(day, ISNULL(i.last_sale_date, i.date_created), GETDATE()) as days_without_sale
        FROM 
            item i
        WHERE 
            i.onhand > 0
            AND i.active = 1
            AND (
                i.last_sale_date IS NULL 
                OR DATEDIFF(day, i.last_sale_date, GETDATE()) > 90
            )
        ORDER BY 
            tied_up_capital DESC
        """
        dead_stock = db.execute_query(dead_stock_query, description="Dead stock analysis")
        metrics['inventory_health']['dead_stock'] = dead_stock.to_dict('records') if not dead_stock.empty else []
        
        # Overall inventory summary
        inventory_summary_query = """
        SELECT 
            COUNT(*) as total_products,
            SUM(CASE WHEN onhand <= 5 THEN 1 ELSE 0 END) as low_stock_count,
            SUM(CASE WHEN onhand = 0 THEN 1 ELSE 0 END) as out_of_stock_count,
            SUM(onhand * cost) as total_inventory_value,
            AVG(onhand) as avg_stock_level,
            COUNT(CASE WHEN active = 1 THEN 1 END) as active_products
        FROM 
            item
        WHERE 
            onhand >= 0
        """
        inventory_summary = db.execute_query(inventory_summary_query, description="Inventory summary")
        if not inventory_summary.empty:
            metrics['inventory_health']['summary'] = inventory_summary.iloc[0].to_dict()
        
        # Customer Intelligence Metrics
        logger.info("Extracting customer intelligence metrics...")
        
        # Customer summary stats
        customer_stats_query = """
        SELECT 
            COUNT(DISTINCT customer_id) as total_customers,
            COUNT(DISTINCT CASE WHEN last_sale_date >= DATEADD(day, -30, GETDATE()) THEN customer_id END) as active_30_days,
            COUNT(DISTINCT CASE WHEN last_sale_date >= DATEADD(day, -90, GETDATE()) THEN customer_id END) as active_90_days,
            COUNT(DISTINCT CASE WHEN balance > 0 THEN customer_id END) as customers_with_balance,
            SUM(balance) as total_ar_balance,
            AVG(balance) as avg_customer_balance
        FROM 
            customer
        WHERE 
            active = 1
        """
        customer_stats = db.execute_query(customer_stats_query, description="Customer statistics")
        if not customer_stats.empty:
            metrics['customer_intelligence']['summary'] = customer_stats.iloc[0].to_dict()
        
        # Top customers by sales (last 30 days)
        top_customers_query = """
        SELECT TOP 10
            c.customer_id,
            c.name as customer_name,
            c.balance as current_balance,
            SUM(d.qty * d.price) as total_purchases_30d,
            COUNT(DISTINCT h.id) as transaction_count_30d,
            c.last_sale_date,
            CASE 
                WHEN c.balance > 0 AND DATEDIFF(day, c.last_payment_date, GETDATE()) > 30 THEN 'High Risk'
                WHEN c.balance > 0 AND DATEDIFF(day, c.last_payment_date, GETDATE()) > 15 THEN 'Medium Risk'
                ELSE 'Low Risk'
            END as risk_level
        FROM 
            customer c
            LEFT JOIN sale_h h ON c.customer_id = h.customer AND h.date >= DATEADD(day, -30, GETDATE())
            LEFT JOIN sale_d d ON h.id = d.sale_id
        WHERE 
            c.active = 1
        GROUP BY 
            c.customer_id, c.name, c.balance, c.last_sale_date, c.last_payment_date
        ORDER BY 
            total_purchases_30d DESC
        """
        top_customers = db.execute_query(top_customers_query, description="Top customers analysis")
        metrics['customer_intelligence']['top_customers'] = top_customers.to_dict('records') if not top_customers.empty else []
        
        # AR Summary Metrics
        logger.info("Extracting AR summary metrics...")
        
        # AR aging analysis
        ar_aging_query = """
        SELECT 
            COUNT(*) as total_customers_with_balance,
            SUM(balance) as total_balance,
            SUM(CASE WHEN balance > 0 AND balance <= 100 THEN balance ELSE 0 END) as balance_0_100,
            SUM(CASE WHEN balance > 100 AND balance <= 500 THEN balance ELSE 0 END) as balance_100_500,
            SUM(CASE WHEN balance > 500 AND balance <= 1000 THEN balance ELSE 0 END) as balance_500_1000,
            SUM(CASE WHEN balance > 1000 THEN balance ELSE 0 END) as balance_over_1000,
            COUNT(CASE WHEN balance > 0 AND balance <= 100 THEN 1 END) as count_0_100,
            COUNT(CASE WHEN balance > 100 AND balance <= 500 THEN 1 END) as count_100_500,
            COUNT(CASE WHEN balance > 500 AND balance <= 1000 THEN 1 END) as count_500_1000,
            COUNT(CASE WHEN balance > 1000 THEN 1 END) as count_over_1000
        FROM 
            customer 
        WHERE 
            balance > 0 
            AND active = 1
        """
        ar_aging = db.execute_query(ar_aging_query, description="AR aging analysis")
        if not ar_aging.empty:
            metrics['ar_summary']['aging'] = ar_aging.iloc[0].to_dict()
        
        # High risk customers (balance > 0 and no payment in 30+ days)
        high_risk_query = """
        SELECT TOP 20
            customer_id,
            name,
            balance,
            last_sale_date,
            last_payment_date,
            DATEDIFF(day, ISNULL(last_payment_date, '1900-01-01'), GETDATE()) as days_since_payment,
            DATEDIFF(day, ISNULL(last_sale_date, '1900-01-01'), GETDATE()) as days_since_sale
        FROM 
            customer
        WHERE 
            balance > 0 
            AND active = 1
            AND (
                last_payment_date IS NULL 
                OR DATEDIFF(day, last_payment_date, GETDATE()) > 30
            )
        ORDER BY 
            balance DESC
        """
        high_risk = db.execute_query(high_risk_query, description="High risk customers")
        metrics['ar_summary']['high_risk_customers'] = high_risk.to_dict('records') if not high_risk.empty else []
        
        # Database Statistics
        logger.info("Extracting database statistics...")
        
        # Table row counts
        table_stats_query = """
        SELECT 
            'customer' as table_name, COUNT(*) as row_count FROM customer
        UNION ALL SELECT 'item', COUNT(*) FROM item
        UNION ALL SELECT 'sale_h', COUNT(*) FROM sale_h
        UNION ALL SELECT 'sale_d', COUNT(*) FROM sale_d
        UNION ALL SELECT 'purchase_h', COUNT(*) FROM purchase_h
        UNION ALL SELECT 'purchase_d', COUNT(*) FROM purchase_d
        """
        table_stats = db.execute_query(table_stats_query, description="Table statistics")
        metrics['database_metrics']['table_counts'] = table_stats.to_dict('records') if not table_stats.empty else []
        
        # Date range of data
        date_range_query = """
        SELECT 
            MIN(date) as earliest_sale,
            MAX(date) as latest_sale,
            COUNT(DISTINCT CAST(date AS DATE)) as unique_sale_days
        FROM 
            sale_h
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
    logger.info("🚀 Starting business metrics extraction...")
    
    # Extract metrics
    metrics = extract_business_metrics()
    
    # Save to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'real_business_metrics_{timestamp}.json'
    
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
        
        if 'customer_intelligence' in metrics and 'summary' in metrics['customer_intelligence']:
            customer_summary = metrics['customer_intelligence']['summary']
            print(f"\nCustomer Intelligence:")
            print(f"  • Total Customers: {customer_summary.get('total_customers', 'N/A')}")
            print(f"  • Active (30 days): {customer_summary.get('active_30_days', 'N/A')}")
            print(f"  • Total AR Balance: ${customer_summary.get('total_ar_balance', 0):,.2f}")
        
        if 'inventory_health' in metrics and 'summary' in metrics['inventory_health']:
            inventory_summary = metrics['inventory_health']['summary']
            print(f"\nInventory Health:")
            print(f"  • Total Products: {inventory_summary.get('total_products', 'N/A')}")
            print(f"  • Low Stock Items: {inventory_summary.get('low_stock_count', 'N/A')}")
            print(f"  • Total Inventory Value: ${inventory_summary.get('total_inventory_value', 0):,.2f}")
        
        print(f"\n📄 Full details saved to: {filename}")
        
    except Exception as e:
        logger.error(f"❌ Error saving metrics: {str(e)}")

if __name__ == "__main__":
    main()