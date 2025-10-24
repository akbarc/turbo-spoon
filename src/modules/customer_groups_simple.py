"""
Simple CSV-based customer groups with per-store analytics.

Loads customer groups from customer_groups.csv (static, fast)
Calculates analytics per store when viewing a group.
"""

import pandas as pd
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from pathlib import Path

from src.database.sql_server import db as sql_db

logger = logging.getLogger(__name__)


def execute_query(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """Execute a SELECT query and return results as a DataFrame."""
    return sql_db.execute_query(query, params)


class SimpleCustomerGroupManager:
    """CSV-based customer group management with per-store analytics."""

    def __init__(self, csv_path: str = "customer_groups.csv"):
        self.csv_path = Path(csv_path)
        self.groups_cache = None
        self.last_loaded = None

    def load_groups_from_csv(self) -> pd.DataFrame:
        """
        Load customer groups from CSV file.
        Returns DataFrame with columns: GroupName, CustomerID, CustomerName, Company
        """
        if not self.csv_path.exists():
            logger.warning(f"CSV file not found: {self.csv_path}")
            return pd.DataFrame(columns=['GroupName', 'CustomerID', 'CustomerName', 'Company'])

        # Read CSV, skipping comment lines
        rows = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                rows.append(line)

        if not rows:
            return pd.DataFrame(columns=['GroupName', 'CustomerID', 'CustomerName', 'Company'])

        # Parse CSV from remaining lines
        from io import StringIO
        csv_data = StringIO('\n'.join(rows))
        df = pd.read_csv(csv_data)

        # Cache it
        self.groups_cache = df
        self.last_loaded = datetime.now()

        logger.info(f"Loaded {len(df)} customer-group assignments from CSV")
        return df

    def get_group_summary(self) -> pd.DataFrame:
        """
        Get summary of all groups with counts.
        Fast operation - just reads CSV and counts.
        """
        df = self.load_groups_from_csv()

        if df.empty:
            return pd.DataFrame()

        # Group by GroupName and count
        summary = df.groupby('GroupName').agg({
            'CustomerID': 'count',
            'CustomerName': 'first'  # Just to have a value
        }).reset_index()

        summary = summary.rename(columns={'CustomerID': 'member_count'})

        return summary

    def get_group_analytics_by_store(self, group_name: str,
                                     days: int = 30) -> List[Dict]:
        """
        Get analytics for each store in a group individually.

        Args:
            group_name: Name of the group
            days: Number of days to look back (default 30)

        Returns:
            List of dicts, one per store with their individual metrics
        """
        # Load groups from CSV
        df = self.load_groups_from_csv()

        # Get customers in this group
        group_customers = df[df['GroupName'] == group_name]

        if group_customers.empty:
            return []

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        results = []

        for _, customer in group_customers.iterrows():
            customer_id = int(customer['CustomerID'])
            customer_name = customer['CustomerName']
            company = customer['Company']

            try:
                # Sales metrics
                sales_query = f"""
                    SELECT
                        COUNT(DISTINCT TransactionNumber) as transaction_count,
                        ISNULL(SUM(Total), 0) as total_sales,
                        MAX(Time) as last_purchase
                    FROM dbo.[Transaction]
                    WHERE CustomerID = {customer_id}
                        AND Time >= '{start_date_str}'
                        AND Time <= '{end_date_str}'
                """

                sales_df = execute_query(sales_query)

                # GP calculation
                gp_query = f"""
                    SELECT
                        ISNULL(SUM((te.Price - te.Cost) * te.Quantity), 0) as gross_profit
                    FROM dbo.TransactionEntry te
                    INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                    WHERE t.CustomerID = {customer_id}
                        AND t.Time >= '{start_date_str}'
                        AND t.Time <= '{end_date_str}'
                """

                gp_df = execute_query(gp_query)

                # AR Balance
                ar_query = f"""
                    SELECT ISNULL(AccountBalance, 0) as ar_balance
                    FROM dbo.Customer
                    WHERE ID = {customer_id}
                """

                ar_df = execute_query(ar_query)

                # PD Checks from Payment table (WORKING VERSION)
                pd_query = f"""
                    SELECT
                        COUNT(*) as pd_count,
                        ISNULL(SUM(Amount), 0) as pd_total
                    FROM dbo.Payment
                    WHERE CustomerID = {customer_id}
                        AND (
                            UPPER(Comment) LIKE '%PD%'
                            OR UPPER(Comment) LIKE '%POST DATE%'
                            OR UPPER(Comment) LIKE '%P D%'
                            OR UPPER(Comment) LIKE '%POSTDATE%'
                            OR Comment LIKE '%/%/%'
                        )
                        AND Amount > 0
                """

                pd_df = execute_query(pd_query)

                # Compile results
                total_sales = float(sales_df.iloc[0]['total_sales'] or 0)
                gross_profit = float(gp_df.iloc[0]['gross_profit'] or 0)

                results.append({
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'company': company,
                    'transaction_count': int(sales_df.iloc[0]['transaction_count'] or 0),
                    'total_sales': total_sales,
                    'gross_profit': gross_profit,
                    'gp_percentage': (gross_profit / total_sales * 100) if total_sales > 0 else 0,
                    'ar_balance': float(ar_df.iloc[0]['ar_balance'] or 0),
                    'pd_checks_count': int(pd_df.iloc[0]['pd_count'] or 0),
                    'pd_checks_total': float(pd_df.iloc[0]['pd_total'] or 0),
                    'last_purchase': str(sales_df.iloc[0]['last_purchase']) if sales_df.iloc[0]['last_purchase'] else None
                })

            except Exception as e:
                logger.error(f"Error calculating analytics for customer {customer_id}: {str(e)}")
                continue

        return results

    def get_group_totals(self, group_name: str, days: int = 30) -> Dict:
        """
        Get totals for a group (sum of all stores).

        Args:
            group_name: Name of the group
            days: Number of days to look back

        Returns:
            Dict with aggregated metrics
        """
        store_analytics = self.get_group_analytics_by_store(group_name, days)

        if not store_analytics:
            return {
                'total_sales': 0,
                'gross_profit': 0,
                'gp_percentage': 0,
                'ar_balance': 0,
                'pd_checks_total': 0,
                'transaction_count': 0,
                'store_count': 0
            }

        total_sales = sum(s['total_sales'] for s in store_analytics)
        total_gp = sum(s['gross_profit'] for s in store_analytics)

        return {
            'total_sales': total_sales,
            'gross_profit': total_gp,
            'gp_percentage': (total_gp / total_sales * 100) if total_sales > 0 else 0,
            'ar_balance': sum(s['ar_balance'] for s in store_analytics),
            'pd_checks_total': sum(s['pd_checks_total'] for s in store_analytics),
            'pd_checks_count': sum(s['pd_checks_count'] for s in store_analytics),
            'transaction_count': sum(s['transaction_count'] for s in store_analytics),
            'store_count': len(store_analytics),
            'stores': store_analytics
        }

    def get_group_category_analysis(self, group_name: str, days: int = 30,
                                    limit: int = 5) -> List[Dict]:
        """
        Get category breakdown for a group.

        Args:
            group_name: Name of the group
            days: Number of days to look back
            limit: Number of top categories to return (0 for all)

        Returns:
            List of dicts with category analysis including % of total category sales
        """
        # Load groups from CSV
        df = self.load_groups_from_csv()

        # Get customers in this group
        group_customers = df[df['GroupName'] == group_name]

        if group_customers.empty:
            return []

        customer_ids = group_customers['CustomerID'].tolist()
        customer_ids_str = ','.join([str(cid) for cid in customer_ids])

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # Category sales for this group + total sales per category
        category_query = f"""
            WITH GroupSales AS (
                SELECT
                    ISNULL(cat.Name, 'Uncategorized') as category_name,
                    SUM(te.Price * te.Quantity) as group_sales,
                    SUM((te.Price - te.Cost) * te.Quantity) as group_gp,
                    COUNT(DISTINCT te.TransactionNumber) as transaction_count
                FROM dbo.TransactionEntry te
                INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                INNER JOIN dbo.Item i ON te.ItemID = i.ID
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                WHERE t.CustomerID IN ({customer_ids_str})
                    AND t.Time >= '{start_date_str}'
                    AND t.Time <= '{end_date_str}'
                GROUP BY cat.Name
            ),
            TotalSales AS (
                SELECT
                    ISNULL(cat.Name, 'Uncategorized') as category_name,
                    SUM(te.Price * te.Quantity) as total_sales
                FROM dbo.TransactionEntry te
                INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                INNER JOIN dbo.Item i ON te.ItemID = i.ID
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                WHERE t.Time >= '{start_date_str}'
                    AND t.Time <= '{end_date_str}'
                GROUP BY cat.Name
            )
            SELECT TOP {limit if limit > 0 else 1000}
                gs.category_name,
                gs.group_sales,
                gs.group_gp,
                gs.transaction_count,
                ts.total_sales,
                CASE
                    WHEN ts.total_sales > 0 THEN (gs.group_sales / ts.total_sales * 100)
                    ELSE 0
                END as pct_of_total_category_sales
            FROM GroupSales gs
            LEFT JOIN TotalSales ts ON gs.category_name = ts.category_name
            ORDER BY gs.group_sales DESC
        """

        try:
            categories_df = execute_query(category_query)

            results = []
            for _, row in categories_df.iterrows():
                group_sales = float(row['group_sales'] or 0)
                group_gp = float(row['group_gp'] or 0)

                results.append({
                    'category_name': row['category_name'],
                    'group_sales': group_sales,
                    'group_gp': group_gp,
                    'gp_percentage': (group_gp / group_sales * 100) if group_sales > 0 else 0,
                    'transaction_count': int(row['transaction_count'] or 0),
                    'pct_of_total_category_sales': float(row['pct_of_total_category_sales'] or 0)
                })

            return results

        except Exception as e:
            logger.error(f"Error getting category analysis: {str(e)}")
            return []


# Global instance
simple_customer_group_manager = SimpleCustomerGroupManager()
