"""
Customer Groups Module - SOUNDEX-based grouping with comprehensive analytics

This module handles:
- Syncing customers from GAWDB to overlay_db using SOUNDEX phonetic matching
- Analytics for customer groups (purchases, AR, GP, categories, payment velocity)
- Group drill-down to individual store level
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from src.database.sql_server import db as sql_db
from src.database.overlay_db import overlay_db


def execute_query(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """Execute a SELECT query and return results as a DataFrame."""
    return sql_db.execute_query(query, params)

logger = logging.getLogger(__name__)


class CustomerGroupManager:
    """Manages customer groups with SOUNDEX-based matching and analytics."""

    def __init__(self):
        self.overlay = overlay_db

    def sync_customer_groups(self, force_rebuild: bool = False) -> Dict:
        """
        Sync customers from GAWDB to overlay_db using SOUNDEX grouping.

        Args:
            force_rebuild: If True, rebuild all groups from scratch

        Returns:
            Dict with sync statistics
        """
        logger.info("Starting customer group sync...")

        if force_rebuild:
            logger.info("Force rebuild requested - clearing existing groups")
            self._clear_all_groups()

        # Get existing customer IDs in overlay
        existing_customers = set(self.overlay.get_customers_not_in_groups())

        # Get all customers from GAWDB with SOUNDEX codes
        query = """
            SELECT
                c.ID as customer_id,
                ISNULL(c.FirstName, '') as first_name,
                ISNULL(c.LastName, '') as last_name,
                ISNULL(c.Company, '') as company,
                SOUNDEX(ISNULL(c.LastName, '')) as soundex_last,
                SOUNDEX(ISNULL(c.FirstName, '')) as soundex_first
            FROM dbo.Customer c
            WHERE (c.FirstName IS NOT NULL AND c.FirstName != '')
               OR (c.LastName IS NOT NULL AND c.LastName != '')
               OR (c.Company IS NOT NULL AND c.Company != '')
            ORDER BY c.ID
        """

        logger.info("Fetching customers from GAWDB...")
        customers_df = execute_query(query)

        if customers_df.empty:
            logger.warning("No customers found in GAWDB")
            return {'status': 'error', 'message': 'No customers found'}

        logger.info(f"Found {len(customers_df)} customers in GAWDB")

        # Filter to only new customers if not force rebuild
        if not force_rebuild:
            new_customers = customers_df[~customers_df['customer_id'].isin(existing_customers)]
            logger.info(f"Found {len(new_customers)} new customers to add")
        else:
            new_customers = customers_df

        if new_customers.empty and not force_rebuild:
            logger.info("No new customers to sync")
            return {
                'status': 'success',
                'message': 'No new customers to sync',
                'customers_processed': 0,
                'groups_created': 0,
                'groups_updated': 0
            }

        # Group customers by SOUNDEX key
        customers_df['soundex_key'] = customers_df['soundex_last'] + '_' + customers_df['soundex_first']
        grouped = customers_df.groupby('soundex_key')

        groups_created = 0
        groups_updated = 0
        customers_processed = 0

        logger.info("Processing customer groups...")
        for soundex_key, group_df in grouped:
            # Skip groups with only one member
            if len(group_df) == 1:
                continue

            # Use the FIRST customer's name as the group name (primary member)
            first_customer = group_df.iloc[0]
            if first_customer['company'] and str(first_customer['company']).strip():
                group_name = str(first_customer['company']).strip()
            else:
                group_name = f"{first_customer['first_name']} {first_customer['last_name']}".strip()

            soundex_last = group_df.iloc[0]['soundex_last']
            soundex_first = group_df.iloc[0]['soundex_first']

            # Create or update group in overlay
            try:
                group_id = self.overlay.upsert_soundex_group(
                    group_key=soundex_key,
                    group_name=group_name,
                    soundex_last=soundex_last,
                    soundex_first=soundex_first
                )

                # Add all customers to the group
                for idx, customer in group_df.iterrows():
                    customer_name = f"{customer['first_name']} {customer['last_name']}".strip()

                    # First customer in group is marked as primary
                    is_primary = (idx == group_df.index[0])

                    self.overlay.add_customer_to_soundex_group(
                        group_id=group_id,
                        customer_id=int(customer['customer_id']),
                        customer_name=customer_name,
                        customer_company=customer['company'],
                        soundex_last=customer['soundex_last'],
                        soundex_first=customer['soundex_first'],
                        is_primary=is_primary
                    )
                    customers_processed += 1

                if soundex_key in [g for g in grouped.groups.keys()]:
                    groups_updated += 1
                else:
                    groups_created += 1

            except Exception as e:
                logger.error(f"Error processing group {soundex_key}: {str(e)}")
                continue

        # Update member counts
        self.overlay.update_group_member_counts()

        logger.info(f"Sync complete: {customers_processed} customers, {groups_created} groups created, {groups_updated} groups updated")

        return {
            'status': 'success',
            'message': 'Customer groups synced successfully',
            'customers_processed': customers_processed,
            'groups_created': groups_created,
            'groups_updated': groups_updated,
            'timestamp': datetime.now().isoformat()
        }

    def get_group_analytics(self, group_id: int, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict:
        """
        Get comprehensive analytics for a customer group.

        Args:
            group_id: The overlay database group ID
            start_date: Start date for metrics (YYYY-MM-DD)
            end_date: End date for metrics (YYYY-MM-DD)

        Returns:
            Dict with group analytics
        """
        # Get group members
        members_df = self.overlay.get_group_members(group_id)
        if members_df.empty:
            return {'error': 'Group not found or has no members'}

        customer_ids = members_df['customer_id'].tolist()
        customer_ids_str = ','.join([str(cid) for cid in customer_ids])

        # Build date filter
        date_filter = self._build_date_filter(start_date, end_date)

        # Get financial metrics
        # Note: Calculate GP from TransactionEntry since Transaction table doesn't have Cost
        financial_query = f"""
            SELECT
                COUNT(DISTINCT t.TransactionNumber) as transaction_count,
                SUM(t.Total) as total_sales,
                ISNULL((
                    SELECT SUM((te.Price - te.Cost) * te.Quantity)
                    FROM dbo.TransactionEntry te
                    INNER JOIN dbo.[Transaction] t2 ON te.TransactionNumber = t2.TransactionNumber
                    WHERE t2.CustomerID IN ({customer_ids_str})
                        {date_filter.replace('t.Time', 't2.Time')}
                ), 0) as gross_profit,
                AVG(t.Total) as avg_transaction_value,
                MIN(t.Time) as first_purchase,
                MAX(t.Time) as last_purchase
            FROM dbo.[Transaction] t
            WHERE t.CustomerID IN ({customer_ids_str})
                {date_filter}
        """

        financial_df = execute_query(financial_query)

        # Get AR balance (current, not time-filtered)
        ar_query = f"""
            SELECT
                SUM(c.AccountBalance) as total_ar_balance
            FROM dbo.Customer c
            WHERE c.ID IN ({customer_ids_str})
        """

        ar_df = execute_query(ar_query)

        # Get post-dated checks
        # Column is 'Description' not 'Comment'
        pd_checks_query = f"""
            SELECT
                COUNT(*) as pd_check_count,
                SUM(te.Amount) as pd_check_total
            FROM dbo.TenderEntry te
            INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.CustomerID IN ({customer_ids_str})
                AND (
                    te.Description LIKE '%post%date%'
                    OR te.Description LIKE '%PD%'
                )
                AND te.Amount > 0
        """
        pd_checks_df = execute_query(pd_checks_query)

        # Get payment velocity (average days to pay)
        # TenderEntry doesn't have a Time column - disable for now
        # TODO: Find correct way to calculate payment velocity
        # payment_velocity_query = f"""
        #     SELECT
        #         AVG(DATEDIFF(day, t.Time, te.Time)) as avg_days_to_pay
        #     FROM dbo.[Transaction] t
        #     INNER JOIN dbo.TenderEntry te ON t.TransactionNumber = te.TransactionNumber
        #     WHERE t.CustomerID IN ({customer_ids_str})
        #         AND te.TenderID != 0  -- Exclude account payments
        #         AND DATEDIFF(day, t.Time, te.Time) >= 0
        #         AND DATEDIFF(day, t.Time, te.Time) <= 365
        #         {date_filter.replace('t.Time', 'te.Time')}
        # """
        # payment_velocity_df = execute_query(payment_velocity_query)

        # Return zeros for payment velocity until we find correct calculation
        payment_velocity_df = pd.DataFrame([{'avg_days_to_pay': 0}])

        # Combine results
        result = {
            'group_id': group_id,
            'member_count': len(members_df),
            'customer_ids': customer_ids,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'financial': {
                'transaction_count': int(financial_df.iloc[0]['transaction_count'] or 0),
                'total_sales': float(financial_df.iloc[0]['total_sales'] or 0),
                'gross_profit': float(financial_df.iloc[0]['gross_profit'] or 0),
                'gp_percentage': (float(financial_df.iloc[0]['gross_profit'] or 0) /
                                 float(financial_df.iloc[0]['total_sales']) * 100)
                                if financial_df.iloc[0]['total_sales'] else 0,
                'avg_transaction_value': float(financial_df.iloc[0]['avg_transaction_value'] or 0),
                'first_purchase': str(financial_df.iloc[0]['first_purchase']) if financial_df.iloc[0]['first_purchase'] else None,
                'last_purchase': str(financial_df.iloc[0]['last_purchase']) if financial_df.iloc[0]['last_purchase'] else None,
            },
            'ar': {
                'total_balance': float(ar_df.iloc[0]['total_ar_balance'] or 0)
            },
            'post_dated_checks': {
                'count': int(pd_checks_df.iloc[0]['pd_check_count'] or 0),
                'total_amount': float(pd_checks_df.iloc[0]['pd_check_total'] or 0)
            },
            'payment_velocity': {
                'avg_days_to_pay': float(payment_velocity_df.iloc[0]['avg_days_to_pay'] or 0)
            }
        }

        return result

    def get_group_category_analysis(self, group_id: int, start_date: Optional[str] = None,
                                   end_date: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """
        Get category breakdown for a customer group.

        Args:
            group_id: The overlay database group ID
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Number of top categories to return (0 for all)

        Returns:
            List of dicts with category analysis
        """
        # Get group members
        members_df = self.overlay.get_group_members(group_id)
        if members_df.empty:
            return []

        customer_ids = members_df['customer_id'].tolist()
        customer_ids_str = ','.join([str(cid) for cid in customer_ids])

        date_filter = self._build_date_filter(start_date, end_date)

        # Get category sales for this group
        category_query = f"""
            WITH GroupSales AS (
                SELECT
                    cat.Name as category_name,
                    SUM(te.Price * te.Quantity) as group_sales,
                    SUM((te.Price - te.Cost) * te.Quantity) as group_gp,
                    COUNT(DISTINCT te.TransactionNumber) as transaction_count
                FROM dbo.TransactionEntry te
                INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                INNER JOIN dbo.Item i ON te.ItemID = i.ID
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                WHERE t.CustomerID IN ({customer_ids_str})
                    {date_filter}
                GROUP BY cat.Name
            ),
            TotalSales AS (
                SELECT
                    cat.Name as category_name,
                    SUM(te.Price * te.Quantity) as total_sales
                FROM dbo.TransactionEntry te
                INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                INNER JOIN dbo.Item i ON te.ItemID = i.ID
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                WHERE 1=1
                    {date_filter}
                GROUP BY cat.Name
            )
            SELECT
                gs.category_name,
                gs.group_sales,
                gs.group_gp,
                gs.transaction_count,
                ts.total_sales,
                (gs.group_sales / NULLIF(ts.total_sales, 0) * 100) as pct_of_total_category_sales
            FROM GroupSales gs
            LEFT JOIN TotalSales ts ON gs.category_name = ts.category_name
            ORDER BY gs.group_sales DESC
        """

        if limit > 0:
            category_query = category_query.replace("ORDER BY", f"ORDER BY gs.group_sales DESC\n            OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY\n            ORDER BY")

        categories_df = execute_query(category_query)

        results = []
        for _, row in categories_df.iterrows():
            results.append({
                'category_name': row['category_name'] or 'Uncategorized',
                'group_sales': float(row['group_sales'] or 0),
                'group_gp': float(row['group_gp'] or 0),
                'gp_percentage': (float(row['group_gp'] or 0) / float(row['group_sales']) * 100)
                                if row['group_sales'] else 0,
                'transaction_count': int(row['transaction_count'] or 0),
                'pct_of_total_category_sales': float(row['pct_of_total_category_sales'] or 0)
            })

        return results

    def get_group_member_details(self, group_id: int, start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[Dict]:
        """
        Get detailed analytics for each member (store) in a group.

        Args:
            group_id: The overlay database group ID
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            List of dicts with per-store analytics
        """
        # Get group members
        members_df = self.overlay.get_group_members(group_id)
        if members_df.empty:
            return []

        date_filter = self._build_date_filter(start_date, end_date)

        results = []
        for _, member in members_df.iterrows():
            customer_id = int(member['customer_id'])

            # Get metrics for this specific customer
            metrics_query = f"""
                SELECT
                    COUNT(DISTINCT t.TransactionNumber) as transaction_count,
                    SUM(t.Total) as total_sales,
                    ISNULL((
                        SELECT SUM((te.Price - te.Cost) * te.Quantity)
                        FROM dbo.TransactionEntry te
                        WHERE te.TransactionNumber IN (
                            SELECT TransactionNumber FROM dbo.[Transaction]
                            WHERE CustomerID = {customer_id}
                        )
                    ), 0) as gross_profit,
                    MAX(t.Time) as last_purchase
                FROM dbo.[Transaction] t
                WHERE t.CustomerID = {customer_id}
                    {date_filter}
            """

            metrics_df = execute_query(metrics_query)

            # Get AR balance
            ar_query = f"""
                SELECT AccountBalance as ar_balance
                FROM dbo.Customer
                WHERE ID = {customer_id}
            """

            ar_df = execute_query(ar_query)

            total_sales = float(metrics_df.iloc[0]['total_sales'] or 0)
            gross_profit = float(metrics_df.iloc[0]['gross_profit'] or 0)

            results.append({
                'customer_id': customer_id,
                'customer_name': member['customer_name'],
                'company': member['customer_company'],
                'is_primary': bool(member['is_primary']),
                'transaction_count': int(metrics_df.iloc[0]['transaction_count'] or 0),
                'total_sales': total_sales,
                'gross_profit': gross_profit,
                'gp_percentage': (gross_profit / total_sales * 100) if total_sales > 0 else 0,
                'ar_balance': float(ar_df.iloc[0]['ar_balance'] or 0) if not ar_df.empty else 0,
                'last_purchase': str(metrics_df.iloc[0]['last_purchase']) if metrics_df.iloc[0]['last_purchase'] else None
            })

        return results

    def get_all_groups_summary(self, min_sales: float = 0, start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get summary data for all customer groups with filters.

        Args:
            min_sales: Minimum sales amount to include group
            start_date: Start date for sales filter
            end_date: End date for sales filter

        Returns:
            DataFrame with group summaries
        """
        # Get all groups from overlay
        groups_df = self.overlay.get_soundex_groups()

        if groups_df.empty:
            return pd.DataFrame()

        # Get analytics for each group
        summaries = []
        for _, group in groups_df.iterrows():
            group_id = int(group['id'])

            # Get basic analytics
            analytics = self.get_group_analytics(group_id, start_date, end_date)

            # Filter by min_sales
            if analytics['financial']['total_sales'] < min_sales:
                continue

            summaries.append({
                'group_id': group_id,
                'group_key': group['group_key'],
                'group_name': group['group_name'],
                'member_count': analytics['member_count'],
                'total_sales': analytics['financial']['total_sales'],
                'gross_profit': analytics['financial']['gross_profit'],
                'gp_percentage': analytics['financial']['gp_percentage'],
                'ar_balance': analytics['ar']['total_balance'],
                'pd_checks_amount': analytics['post_dated_checks']['total_amount'],
                'avg_days_to_pay': analytics['payment_velocity']['avg_days_to_pay'],
                'last_purchase': analytics['financial']['last_purchase'],
                'transaction_count': analytics['financial']['transaction_count']
            })

        return pd.DataFrame(summaries)

    def calculate_and_cache_all_analytics(self) -> Dict:
        """
        Calculate analytics for ALL groups in one efficient batch and cache results.
        This is much faster than querying each group individually.

        Returns:
            Dict with calculation statistics
        """
        from datetime import datetime, timedelta

        logger.info("Starting bulk analytics calculation...")

        # Clear existing cache
        self.overlay.clear_analytics_cache()

        # Get all groups
        groups_df = self.overlay.get_soundex_groups()

        if groups_df.empty:
            return {
                'status': 'success',
                'groups_processed': 0,
                'message': 'No groups to calculate'
            }

        # Calculate date range (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        logger.info(f"Calculating analytics for {len(groups_df)} groups...")

        groups_processed = 0
        for _, group in groups_df.iterrows():
            group_id = int(group['id'])

            try:
                # Get members for this group
                members_df = self.overlay.get_group_members(group_id)
                if members_df.empty:
                    continue

                customer_ids = members_df['customer_id'].tolist()
                customer_ids_str = ','.join([str(cid) for cid in customer_ids])

                # Calculate financial metrics (30 days)
                financial_query = f"""
                    SELECT
                        COUNT(DISTINCT t.TransactionNumber) as transaction_count,
                        ISNULL(SUM(t.Total), 0) as total_sales,
                        MAX(t.Time) as last_purchase
                    FROM dbo.[Transaction] t
                    WHERE t.CustomerID IN ({customer_ids_str})
                        AND t.Time >= '{start_date_str}'
                        AND t.Time <= '{end_date_str}'
                """

                financial_df = execute_query(financial_query)

                # Calculate GP from TransactionEntry
                gp_query = f"""
                    SELECT
                        ISNULL(SUM((te.Price - te.Cost) * te.Quantity), 0) as gross_profit
                    FROM dbo.TransactionEntry te
                    INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                    WHERE t.CustomerID IN ({customer_ids_str})
                        AND t.Time >= '{start_date_str}'
                        AND t.Time <= '{end_date_str}'
                """

                gp_df = execute_query(gp_query)

                # Get AR balance (current)
                ar_query = f"""
                    SELECT ISNULL(SUM(AccountBalance), 0) as ar_balance
                    FROM dbo.Customer
                    WHERE ID IN ({customer_ids_str})
                """

                ar_df = execute_query(ar_query)

                # Get PD checks
                pd_query = f"""
                    SELECT
                        COUNT(*) as pd_count,
                        ISNULL(SUM(te.Amount), 0) as pd_total
                    FROM dbo.TenderEntry te
                    INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                    WHERE t.CustomerID IN ({customer_ids_str})
                        AND (te.Description LIKE '%post%date%' OR te.Description LIKE '%PD%')
                        AND te.Amount > 0
                """

                pd_df = execute_query(pd_query)

                # Build analytics dict
                total_sales = float(financial_df.iloc[0]['total_sales'] or 0)
                gross_profit = float(gp_df.iloc[0]['gross_profit'] or 0)

                analytics = {
                    'total_sales': total_sales,
                    'gross_profit': gross_profit,
                    'gp_percentage': (gross_profit / total_sales * 100) if total_sales > 0 else 0,
                    'ar_balance': float(ar_df.iloc[0]['ar_balance'] or 0),
                    'pd_checks_count': int(pd_df.iloc[0]['pd_count'] or 0),
                    'pd_checks_total': float(pd_df.iloc[0]['pd_total'] or 0),
                    'transaction_count': int(financial_df.iloc[0]['transaction_count'] or 0),
                    'last_purchase': str(financial_df.iloc[0]['last_purchase']) if financial_df.iloc[0]['last_purchase'] else None
                }

                # Cache the analytics
                self.overlay.cache_group_analytics(group_id, analytics)
                groups_processed += 1

                if groups_processed % 10 == 0:
                    logger.info(f"Processed {groups_processed}/{len(groups_df)} groups...")

            except Exception as e:
                logger.error(f"Error calculating analytics for group {group_id}: {str(e)}")
                continue

        logger.info(f"Analytics calculation complete: {groups_processed} groups processed")

        return {
            'status': 'success',
            'groups_processed': groups_processed,
            'message': f'Calculated and cached analytics for {groups_processed} groups',
            'timestamp': datetime.now().isoformat()
        }

    def get_cached_groups_summary(self, min_sales: float = 0) -> pd.DataFrame:
        """
        Get group summaries from cache (instant load).

        Args:
            min_sales: Minimum sales to include

        Returns:
            DataFrame with cached group summaries
        """
        df = self.overlay.get_cached_analytics()

        if df.empty:
            return df

        # Filter by min_sales
        if min_sales > 0:
            df = df[df['total_sales_30d'] >= min_sales]

        # Rename columns to match expected format
        df = df.rename(columns={
            'total_sales_30d': 'total_sales',
            'gross_profit_30d': 'gross_profit',
            'gp_percentage_30d': 'gp_percentage',
            'transaction_count_30d': 'transaction_count',
            'pd_checks_total': 'pd_checks_amount'
        })

        # Add avg_days_to_pay as 0 for now (not cached yet)
        df['avg_days_to_pay'] = 0

        return df

    def get_group_members(self, group_id: int) -> pd.DataFrame:
        """Get all members of a customer group from overlay database."""
        return self.overlay.get_group_members(group_id)

    def _build_date_filter(self, start_date: Optional[str], end_date: Optional[str]) -> str:
        """Build SQL date filter clause."""
        if not start_date and not end_date:
            return ""

        filters = []
        if start_date:
            filters.append(f"t.Time >= '{start_date}'")
        if end_date:
            filters.append(f"t.Time <= '{end_date}'")

        return " AND " + " AND ".join(filters) if filters else ""

    def _clear_all_groups(self):
        """Clear all SOUNDEX groups from overlay database."""
        with self.overlay.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM customer_group_members WHERE group_id IN (SELECT id FROM customer_groups WHERE group_type = 'soundex')")
            cursor.execute("DELETE FROM customer_groups WHERE group_type = 'soundex'")
            conn.commit()
        logger.info("Cleared all existing SOUNDEX groups")


# Global instance
customer_group_manager = CustomerGroupManager()
