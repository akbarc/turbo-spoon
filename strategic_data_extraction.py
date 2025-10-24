#!/usr/bin/env python3
"""
Strategic Data Extraction for Georgia Convenience Store
Extracts core business metrics for last 12 months using canonical SQL patterns

Data Extraction Focus:
- Total revenue by month and category
- Gross margin by category with tobacco uplifts (CIGARS 23%, LT-TAX-COLLECTED 10%)
- Top 50 products by revenue and velocity
- Customer count and transaction frequency
- Average basket size and composition

Uses DATABASE_INSTRUCTIONS_CRYSTAL_CLEAR.md canonical SQL patterns
Exports results to JSON for further analysis
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import logging
from database_pymssql import SQLServerConnection
import warnings
warnings.filterwarnings('ignore')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategicDataExtractor:
    def __init__(self):
        """Initialize data extractor with database connection"""
        self.db = None
        self.extraction_data = {}
        self.extraction_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Date ranges for analysis (last 12 months)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=365)
        
        logger.info(f"Strategic Data Extraction initialized")
        logger.info(f"Analysis period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
    
    def connect_database(self):
        """Establish database connection using canonical patterns"""
        try:
            self.db = SQLServerConnection()
            if self.db.connect():
                logger.info("✅ Database connection established")
                return True
            else:
                logger.error("❌ Failed to establish database connection")
                return False
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            return False
    
    def extract_monthly_revenue_by_category(self):
        """Extract monthly revenue by category using canonical SQL patterns"""
        logger.info("🔍 Extracting monthly revenue by category...")
        
        query = """
        SELECT 
            CONVERT(varchar(7), t.Time, 120) AS month,
            COALESCE(cat.Name, 'Unknown') AS category,
            SUM(te.Price * te.Quantity) AS total_revenue,
            COUNT(DISTINCT t.TransactionNumber) AS transaction_count,
            COUNT(te.ID) AS line_items
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= %s
          AND t.Time < DATEADD(DAY, 1, %s)
        GROUP BY CONVERT(varchar(7), t.Time, 120), cat.Name
        ORDER BY month DESC, total_revenue DESC
        """
        
        try:
            df = self.db.execute_query(
                query, 
                params=(self.start_date, self.end_date),
                description="Monthly Revenue by Category"
            )
            
            if not df.empty:
                self.extraction_data['monthly_revenue_by_category'] = df.to_dict('records')
                logger.info(f"✅ Extracted {len(df)} monthly category revenue records")
            else:
                logger.warning("⚠️ No monthly revenue data found")
                self.extraction_data['monthly_revenue_by_category'] = []
                
        except Exception as e:
            logger.error(f"❌ Error extracting monthly revenue: {e}")
            self.extraction_data['monthly_revenue_by_category'] = []
    
    def extract_gross_margin_by_category(self):
        """Extract gross margin by category with tobacco uplifts"""
        logger.info("🔍 Extracting gross margin by category with tobacco uplifts...")
        
        query = """
        SELECT 
            COALESCE(cat.Name, 'Unknown') AS category,
            SUM(te.Price * te.Quantity) AS total_revenue,
            SUM(
                CASE
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                    ELSE te.Cost
                END * te.Quantity
            ) AS total_cost_with_uplifts,
            SUM(
                te.Price * te.Quantity - (
                    CASE
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                        ELSE te.Cost
                    END
                ) * te.Quantity
            ) AS gross_profit,
            COUNT(DISTINCT te.TransactionNumber) AS transactions,
            SUM(te.Quantity) AS total_units_sold,
            AVG(te.Price) AS avg_item_price,
            COUNT(DISTINCT i.ID) AS unique_products
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= %s
          AND t.Time < DATEADD(DAY, 1, %s)
        GROUP BY cat.Name
        ORDER BY gross_profit DESC
        """
        
        try:
            df = self.db.execute_query(
                query,
                params=(self.start_date, self.end_date),
                description="Gross Margin by Category with Tobacco Uplifts"
            )
            
            if not df.empty:
                # Calculate margin percentages
                df['gross_margin_pct'] = ((df['total_revenue'] - df['total_cost_with_uplifts']) / df['total_revenue'] * 100).round(2)
                df['avg_units_per_transaction'] = (df['total_units_sold'] / df['transactions']).round(2)
                
                self.extraction_data['gross_margin_by_category'] = df.to_dict('records')
                logger.info(f"✅ Extracted gross margin for {len(df)} categories")
            else:
                logger.warning("⚠️ No gross margin data found")
                self.extraction_data['gross_margin_by_category'] = []
                
        except Exception as e:
            logger.error(f"❌ Error extracting gross margin: {e}")
            self.extraction_data['gross_margin_by_category'] = []
    
    def extract_top_products_by_revenue(self):
        """Extract top 50 products by revenue and velocity"""
        logger.info("🔍 Extracting top 50 products by revenue and velocity...")
        
        query = """
        SELECT TOP 50
            i.ID as product_id,
            COALESCE(i.Description, 'Unknown Product') AS product_name,
            COALESCE(i.ItemLookupCode, '') AS lookup_code,
            COALESCE(cat.Name, 'Unknown') AS category,
            SUM(te.Price * te.Quantity) AS total_revenue,
            SUM(te.Quantity) AS total_units_sold,
            COUNT(DISTINCT te.TransactionNumber) AS transaction_count,
            COUNT(DISTINCT t.CustomerID) AS unique_customers,
            AVG(te.Price) AS avg_selling_price,
            MAX(te.Price) AS max_price,
            MIN(te.Price) AS min_price,
            SUM(te.Cost * te.Quantity) AS total_base_cost,
            SUM(
                te.Price * te.Quantity - (
                    CASE
                        WHEN cat.Name = 'CIGARS' THEN te.Cost * 1.23
                        WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10
                        ELSE te.Cost
                    END
                ) * te.Quantity
            ) AS gross_profit_with_uplifts
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= %s
          AND t.Time < DATEADD(DAY, 1, %s)
        GROUP BY i.ID, i.Description, i.ItemLookupCode, cat.Name
        ORDER BY total_revenue DESC
        """
        
        try:
            df = self.db.execute_query(
                query,
                params=(self.start_date, self.end_date),
                description="Top 50 Products by Revenue"
            )
            
            if not df.empty:
                # Calculate additional metrics
                df['avg_units_per_transaction'] = (df['total_units_sold'] / df['transaction_count']).round(2)
                df['revenue_per_customer'] = (df['total_revenue'] / df['unique_customers']).round(2)
                df['gross_margin_pct'] = ((df['gross_profit_with_uplifts'] / df['total_revenue']) * 100).round(2)
                
                self.extraction_data['top_products_by_revenue'] = df.to_dict('records')
                logger.info(f"✅ Extracted top {len(df)} products by revenue")
            else:
                logger.warning("⚠️ No top products data found")
                self.extraction_data['top_products_by_revenue'] = []
                
        except Exception as e:
            logger.error(f"❌ Error extracting top products: {e}")
            self.extraction_data['top_products_by_revenue'] = []
    
    def extract_customer_transaction_metrics(self):
        """Extract customer count and transaction frequency metrics"""
        logger.info("🔍 Extracting customer transaction metrics...")
        
        # Overall customer metrics
        customer_query = """
        SELECT 
            COUNT(DISTINCT t.CustomerID) as total_active_customers,
            COUNT(DISTINCT t.TransactionNumber) as total_transactions,
            SUM(t.Total) as total_sales_amount,
            AVG(t.Total) as avg_transaction_value,
            COUNT(DISTINCT CONVERT(varchar(10), t.Time, 120)) as active_days,
            SUM(te.Quantity) as total_items_sold
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= %s
          AND t.Time < DATEADD(DAY, 1, %s)
          AND t.CustomerID IS NOT NULL
        """
        
        # Customer frequency analysis
        frequency_query = """
        SELECT 
            customer_transactions,
            COUNT(*) as customer_count,
            SUM(total_spent) as total_revenue_for_frequency
        FROM (
            SELECT 
                t.CustomerID,
                COUNT(DISTINCT t.TransactionNumber) as customer_transactions,
                SUM(t.Total) as total_spent
            FROM [dbo].[Transaction] t
            WHERE t.Time >= %s
              AND t.Time < DATEADD(DAY, 1, %s)
              AND t.CustomerID IS NOT NULL
            GROUP BY t.CustomerID
        ) customer_summary
        GROUP BY customer_transactions
        ORDER BY customer_transactions DESC
        """
        
        try:
            # Get overall metrics
            overall_df = self.db.execute_query(
                customer_query,
                params=(self.start_date, self.end_date),
                description="Overall Customer Metrics"
            )
            
            # Get frequency distribution
            frequency_df = self.db.execute_query(
                frequency_query,
                params=(self.start_date, self.end_date),
                description="Customer Transaction Frequency"
            )
            
            customer_metrics = {}
            
            if not overall_df.empty:
                overall_data = overall_df.iloc[0].to_dict()
                customer_metrics['overall'] = overall_data
                
                # Calculate additional metrics
                if overall_data['total_active_customers'] > 0:
                    customer_metrics['overall']['avg_transactions_per_customer'] = round(
                        overall_data['total_transactions'] / overall_data['total_active_customers'], 2
                    )
                    customer_metrics['overall']['avg_revenue_per_customer'] = round(
                        overall_data['total_sales_amount'] / overall_data['total_active_customers'], 2
                    )
                
                if overall_data['total_transactions'] > 0:
                    customer_metrics['overall']['avg_items_per_transaction'] = round(
                        overall_data['total_items_sold'] / overall_data['total_transactions'], 2
                    )
            
            if not frequency_df.empty:
                customer_metrics['frequency_distribution'] = frequency_df.to_dict('records')
            
            self.extraction_data['customer_transaction_metrics'] = customer_metrics
            logger.info("✅ Extracted customer transaction metrics")
            
        except Exception as e:
            logger.error(f"❌ Error extracting customer metrics: {e}")
            self.extraction_data['customer_transaction_metrics'] = {}
    
    def extract_basket_analysis(self):
        """Extract average basket size and composition metrics"""
        logger.info("🔍 Extracting basket size and composition analysis...")
        
        # Basket size analysis
        basket_query = """
        SELECT 
            CONVERT(varchar(7), t.Time, 120) AS month,
            AVG(basket_data.items_per_transaction) as avg_items_per_basket,
            AVG(basket_data.value_per_transaction) as avg_basket_value,
            AVG(basket_data.categories_per_transaction) as avg_categories_per_basket,
            COUNT(*) as transaction_count,
            SUM(basket_data.total_items) as total_items_sold
        FROM (
            SELECT 
                t.TransactionNumber,
                t.Time,
                COUNT(te.ID) as items_per_transaction,
                SUM(te.Price * te.Quantity) as value_per_transaction,
                COUNT(DISTINCT cat.Name) as categories_per_transaction,
                SUM(te.Quantity) as total_items
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.Time >= %s
              AND t.Time < DATEADD(DAY, 1, %s)
            GROUP BY t.TransactionNumber, t.Time
        ) basket_data
        GROUP BY CONVERT(varchar(7), t.Time, 120)
        ORDER BY month DESC
        """
        
        # Category mix in baskets
        category_mix_query = """
        SELECT 
            COALESCE(cat.Name, 'Unknown') AS category,
            COUNT(DISTINCT t.TransactionNumber) as transactions_containing_category,
            COUNT(DISTINCT t.TransactionNumber) * 100.0 / 
                (SELECT COUNT(DISTINCT TransactionNumber) 
                 FROM [dbo].[Transaction] 
                 WHERE Time >= %s AND Time < DATEADD(DAY, 1, %s)) as basket_penetration_pct,
            AVG(category_items.items_per_transaction) as avg_category_items_per_basket,
            SUM(te.Quantity) as total_category_units
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        JOIN (
            SELECT 
                te2.TransactionNumber,
                cat2.Name as category_name,
                COUNT(te2.ID) as items_per_transaction
            FROM TransactionEntry te2
            LEFT JOIN Item i2 ON te2.ItemID = i2.ID
            LEFT JOIN Category cat2 ON i2.CategoryID = cat2.ID
            GROUP BY te2.TransactionNumber, cat2.Name
        ) category_items ON category_items.TransactionNumber = t.TransactionNumber 
                          AND category_items.category_name = cat.Name
        WHERE t.Time >= %s
          AND t.Time < DATEADD(DAY, 1, %s)
        GROUP BY cat.Name
        ORDER BY basket_penetration_pct DESC
        """
        
        try:
            # Get basket size metrics
            basket_df = self.db.execute_query(
                basket_query,
                params=(self.start_date, self.end_date),
                description="Basket Size Analysis"
            )
            
            # Get category mix metrics  
            category_mix_df = self.db.execute_query(
                category_mix_query,
                params=(self.start_date, self.end_date, self.start_date, self.end_date),
                description="Category Mix in Baskets"
            )
            
            basket_analysis = {}
            
            if not basket_df.empty:
                basket_analysis['monthly_basket_metrics'] = basket_df.to_dict('records')
                
                # Calculate overall averages
                basket_analysis['overall_averages'] = {
                    'avg_items_per_basket': round(basket_df['avg_items_per_basket'].mean(), 2),
                    'avg_basket_value': round(basket_df['avg_basket_value'].mean(), 2),
                    'avg_categories_per_basket': round(basket_df['avg_categories_per_basket'].mean(), 2),
                    'total_transactions': int(basket_df['transaction_count'].sum()),
                    'total_items': int(basket_df['total_items_sold'].sum())
                }
            
            if not category_mix_df.empty:
                basket_analysis['category_penetration'] = category_mix_df.to_dict('records')
            
            self.extraction_data['basket_analysis'] = basket_analysis
            logger.info("✅ Extracted basket analysis metrics")
            
        except Exception as e:
            logger.error(f"❌ Error extracting basket analysis: {e}")
            self.extraction_data['basket_analysis'] = {}
    
    def extract_summary_metrics(self):
        """Extract high-level summary metrics for the period"""
        logger.info("🔍 Extracting summary business metrics...")
        
        summary_query = """
        SELECT 
            COUNT(DISTINCT t.TransactionNumber) as total_transactions,
            COUNT(DISTINCT t.CustomerID) as unique_customers,
            COUNT(DISTINCT CONVERT(varchar(10), t.Time, 120)) as active_days,
            SUM(t.Total) as total_revenue,
            AVG(t.Total) as avg_transaction_value,
            MAX(t.Total) as max_transaction_value,
            MIN(t.Total) as min_transaction_value,
            SUM(te.Quantity) as total_items_sold,
            COUNT(DISTINCT i.ID) as unique_products_sold,
            COUNT(DISTINCT cat.Name) as categories_with_sales
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= %s
          AND t.Time < DATEADD(DAY, 1, %s)
        """
        
        try:
            df = self.db.execute_query(
                summary_query,
                params=(self.start_date, self.end_date),
                description="Summary Business Metrics"
            )
            
            if not df.empty:
                summary_data = df.iloc[0].to_dict()
                
                # Calculate derived metrics
                if summary_data['total_transactions'] > 0:
                    summary_data['avg_items_per_transaction'] = round(
                        summary_data['total_items_sold'] / summary_data['total_transactions'], 2
                    )
                
                if summary_data['unique_customers'] > 0:
                    summary_data['avg_transactions_per_customer'] = round(
                        summary_data['total_transactions'] / summary_data['unique_customers'], 2
                    )
                    summary_data['avg_revenue_per_customer'] = round(
                        summary_data['total_revenue'] / summary_data['unique_customers'], 2
                    )
                
                if summary_data['active_days'] > 0:
                    summary_data['avg_daily_transactions'] = round(
                        summary_data['total_transactions'] / summary_data['active_days'], 2
                    )
                    summary_data['avg_daily_revenue'] = round(
                        summary_data['total_revenue'] / summary_data['active_days'], 2
                    )
                
                self.extraction_data['summary_metrics'] = summary_data
                logger.info("✅ Extracted summary business metrics")
            else:
                logger.warning("⚠️ No summary data found")
                self.extraction_data['summary_metrics'] = {}
                
        except Exception as e:
            logger.error(f"❌ Error extracting summary metrics: {e}")
            self.extraction_data['summary_metrics'] = {}
    
    def run_complete_extraction(self):
        """Run complete data extraction process"""
        logger.info("🚀 Starting Strategic Data Extraction...")
        logger.info("=" * 60)
        
        # Connect to database
        if not self.connect_database():
            logger.error("❌ Cannot proceed without database connection")
            return None
        
        try:
            # Run all extraction modules
            self.extract_summary_metrics()
            self.extract_monthly_revenue_by_category()
            self.extract_gross_margin_by_category()
            self.extract_top_products_by_revenue()
            self.extract_customer_transaction_metrics()
            self.extract_basket_analysis()
            
            # Add metadata
            self.extraction_data['extraction_metadata'] = {
                'extraction_timestamp': self.extraction_timestamp,
                'analysis_period': {
                    'start_date': self.start_date.strftime('%Y-%m-%d'),
                    'end_date': self.end_date.strftime('%Y-%m-%d'),
                    'total_days': (self.end_date - self.start_date).days
                },
                'data_modules_extracted': [
                    'summary_metrics',
                    'monthly_revenue_by_category', 
                    'gross_margin_by_category',
                    'top_products_by_revenue',
                    'customer_transaction_metrics',
                    'basket_analysis'
                ]
            }
            
            logger.info("✅ All data extraction modules completed")
            return self.extraction_data
            
        except Exception as e:
            logger.error(f"❌ Error during extraction process: {e}")
            return None
        finally:
            # Clean up database connection
            if self.db:
                self.db.close()
                logger.info("🔌 Database connection closed")
    
    def export_to_json(self, filename=None):
        """Export extracted data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'/Users/akbarchranya/georgiadashboard/strategic_data_extraction_{timestamp}.json'
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.extraction_data, f, indent=2, default=str)
            
            logger.info(f"✅ Data exported to: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Error exporting data: {e}")
            return None

def main():
    """Main execution function"""
    try:
        print("🎯 Strategic Data Extraction for Georgia Convenience Store")
        print("Extracting core business metrics for last 12 months")
        print("=" * 60)
        
        # Initialize extractor and run complete extraction
        extractor = StrategicDataExtractor()
        data = extractor.run_complete_extraction()
        
        if data:
            # Export to JSON
            json_file = extractor.export_to_json()
            
            print("\n" + "=" * 60)
            print("✅ STRATEGIC DATA EXTRACTION COMPLETE")
            print("=" * 60)
            
            if json_file:
                print(f"📊 Data exported to: {json_file}")
            
            # Display summary statistics
            if 'summary_metrics' in data and data['summary_metrics']:
                summary = data['summary_metrics']
                print(f"\n📈 EXTRACTION SUMMARY:")
                print(f"• Analysis period: {data['extraction_metadata']['analysis_period']['total_days']} days")
                print(f"• Total transactions: {summary.get('total_transactions', 0):,}")
                print(f"• Total revenue: ${summary.get('total_revenue', 0):,.2f}")
                print(f"• Unique customers: {summary.get('unique_customers', 0):,}")
                print(f"• Unique products: {summary.get('unique_products_sold', 0):,}")
                print(f"• Categories with sales: {summary.get('categories_with_sales', 0)}")
            
            print("=" * 60)
            return json_file
        else:
            print("❌ Data extraction failed")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error in main execution: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()