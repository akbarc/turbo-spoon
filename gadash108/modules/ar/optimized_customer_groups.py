"""
Optimized Customer Groups Module with Lazy Loading
Provides fast group detection with progressive data loading
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from difflib import SequenceMatcher
import logging
import sys
import os
import json
import hashlib
from datetime import datetime, timedelta
from functools import lru_cache

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)


class OptimizedCustomerGrouper:
    """Optimized customer grouping with lazy loading and caching"""

    def __init__(self):
        self.similarity_threshold = 0.85
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 3600  # 1 hour cache TTL

    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key from method and parameters"""
        params = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(f"{method}:{params}".encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            cached_time, value = self._cache[key]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, value: any) -> None:
        """Set value in cache with timestamp"""
        self._cache[key] = (datetime.now(), value)
        logger.debug(f"Cached key: {key}")

    def get_groups_summary(self, page: int = 1, limit: int = 20,
                           min_balance: float = 0) -> Dict:
        """
        Get lightweight summary of customer groups
        Returns only group headers without member details
        """
        cache_key = self._get_cache_key('groups_summary', page=page, limit=limit, min_balance=min_balance)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            with SQLServerConnection() as db:
                # Use SOUNDEX for fast phonetic grouping
                # This is much faster than fuzzy matching
                query = """
                WITH CustomerGroups AS (
                    SELECT
                        c.ID,
                        c.FirstName,
                        c.LastName,
                        c.AccountBalance,
                        -- Create group key using SOUNDEX (SQL Server 2008 compatible)
                        SOUNDEX(ISNULL(c.LastName, '')) + '_' + SOUNDEX(ISNULL(c.FirstName, '')) as GroupKey,
                        -- Check for recent activity
                        CASE
                            WHEN c.LastVisit >= DATEADD(day, -30, GETDATE()) THEN 1
                            ELSE 0
                        END as HasRecentActivity
                    FROM dbo.Customer c
                    WHERE (c.FirstName IS NOT NULL OR c.LastName IS NOT NULL)
                        AND c.AccountBalance >= %s
                ),
                GroupedData AS (
                    SELECT
                        GroupKey,
                        COUNT(*) as MemberCount,
                        SUM(AccountBalance) as TotalBalance,
                        MAX(HasRecentActivity) as HasRecentActivity,
                        -- Get most common name for display
                        (SELECT TOP 1 FirstName FROM CustomerGroups g2
                         WHERE g2.GroupKey = g1.GroupKey
                         GROUP BY FirstName
                         ORDER BY COUNT(*) DESC) as DisplayFirstName,
                        (SELECT TOP 1 LastName FROM CustomerGroups g2
                         WHERE g2.GroupKey = g1.GroupKey
                         GROUP BY LastName
                         ORDER BY COUNT(*) DESC) as DisplayLastName,
                        MIN(ID) as PrimaryID
                    FROM CustomerGroups g1
                    GROUP BY GroupKey
                    HAVING COUNT(*) > 1  -- Only groups with multiple members
                )
                SELECT * FROM (
                    SELECT
                        GroupKey as group_key,
                        PrimaryID as primary_id,
                        DisplayFirstName as first_name,
                        DisplayLastName as last_name,
                        MemberCount as member_count,
                        TotalBalance as total_balance,
                        HasRecentActivity as has_recent_activity,
                        ROW_NUMBER() OVER (ORDER BY TotalBalance DESC) as row_num,
                        COUNT(*) OVER() as total_groups
                    FROM GroupedData
                ) AS PaginatedData
                WHERE row_num > %s AND row_num <= %s
                ORDER BY row_num
                """

                offset = (page - 1) * limit
                end_row = page * limit
                result = db.execute_query(query, (min_balance, offset, end_row))

                if result.empty:
                    response = {
                        'groups': [],
                        'total_groups': 0,
                        'page': page,
                        'limit': limit,
                        'has_more': False
                    }
                else:
                    # Convert to list of dicts
                    groups = []
                    total_groups = int(result.iloc[0]['total_groups']) if not result.empty else 0

                    for _, row in result.iterrows():
                        groups.append({
                            'group_id': f"GRP_{row['group_key']}",
                            'primary_id': int(row['primary_id']),
                            'display_name': f"{row['first_name'] or ''} {row['last_name'] or ''}".strip(),
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'member_count': int(row['member_count']),
                            'total_balance': float(row['total_balance'] or 0),
                            'has_recent_activity': bool(row['has_recent_activity'])
                        })

                    response = {
                        'groups': groups,
                        'total_groups': total_groups,
                        'page': page,
                        'limit': limit,
                        'has_more': (page * limit) < total_groups
                    }

                self._set_cache(cache_key, response)
                return response

        except Exception as e:
            logger.error(f"Error getting groups summary: {e}")
            return {
                'groups': [],
                'total_groups': 0,
                'page': page,
                'limit': limit,
                'has_more': False,
                'error': str(e)
            }

    def get_group_preview(self, group_key: str) -> Dict:
        """
        Get group with member names only (no full details)
        Used for hover previews and quick views
        """
        cache_key = self._get_cache_key('group_preview', group_key=group_key)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            # Extract SOUNDEX key from group_id
            soundex_key = group_key.replace('GRP_', '')

            with SQLServerConnection() as db:
                query = """
                SELECT
                    c.ID as customer_id,
                    c.FirstName as first_name,
                    c.LastName as last_name,
                    c.Company as company,
                    c.AccountBalance as balance,
                    c.LastVisit as last_visit
                FROM dbo.Customer c
                WHERE SOUNDEX(ISNULL(c.LastName, '')) + '_' + SOUNDEX(ISNULL(c.FirstName, '')) = %s
                ORDER BY c.AccountBalance DESC
                """

                result = db.execute_query(query, (soundex_key,))

                if result.empty:
                    response = {'group_key': group_key, 'members': []}
                else:
                    members = []
                    for _, row in result.iterrows():
                        members.append({
                            'customer_id': int(row['customer_id']),
                            'name': f"{row['first_name'] or ''} {row['last_name'] or ''}".strip(),
                            'company': row['company'],
                            'balance': float(row['balance'] or 0),
                            'last_visit': row['last_visit'].isoformat() if row['last_visit'] and not pd.isna(row['last_visit']) else None
                        })

                    response = {
                        'group_key': group_key,
                        'members': members,
                        'total_balance': sum(m['balance'] for m in members)
                    }

                self._set_cache(cache_key, response)
                return response

        except Exception as e:
            logger.error(f"Error getting group preview: {e}")
            return {'group_key': group_key, 'members': [], 'error': str(e)}

    def get_group_full_details(self, group_key: str, days_filter: int = 30) -> Dict:
        """
        Get complete group details including payment history
        Only loaded when user clicks on a specific group
        """
        cache_key = self._get_cache_key('group_full', group_key=group_key, days_filter=days_filter)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            # First get member IDs
            soundex_key = group_key.replace('GRP_', '')

            with SQLServerConnection() as db:
                # Get customer IDs in this group
                id_query = """
                SELECT c.ID
                FROM dbo.Customer c
                WHERE SOUNDEX(ISNULL(c.LastName, '')) + '_' + SOUNDEX(ISNULL(c.FirstName, '')) = %s
                """

                id_result = db.execute_query(id_query, (soundex_key,))

                if id_result.empty:
                    return {'group_key': group_key, 'members': [], 'payments': [], 'transactions': []}

                customer_ids = id_result['ID'].tolist()
                id_list = ','.join(str(id) for id in customer_ids)

                # Get full customer details
                customer_query = f"""
                SELECT
                    c.ID,
                    c.FirstName,
                    c.LastName,
                    c.Company,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.Address,
                    c.City,
                    c.State,
                    c.Zip,
                    c.AccountBalance,
                    c.CreditLimit,
                    c.LastVisit,
                    c.TotalSales,
                    c.TotalVisits
                FROM dbo.Customer c
                WHERE c.ID IN ({id_list})
                ORDER BY c.AccountBalance DESC
                """

                customers = db.execute_query(customer_query)

                # Get recent payments
                payment_query = f"""
                SELECT TOP 20
                    p.CustomerID,
                    p.Time as payment_date,
                    p.Amount,
                    p.Comment,
                    c.FirstName + ' ' + c.LastName as customer_name
                FROM dbo.Payment p
                INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
                WHERE p.CustomerID IN ({id_list})
                    AND p.Time >= DATEADD(day, -{days_filter}, GETDATE())
                ORDER BY p.Time DESC
                """

                payments = db.execute_query(payment_query)

                # Get recent transactions
                transaction_query = f"""
                SELECT TOP 20
                    t.CustomerID,
                    t.Time as transaction_date,
                    t.Total,
                    t.Comment,
                    c.FirstName + ' ' + c.LastName as customer_name
                FROM dbo.[Transaction] t
                INNER JOIN dbo.Customer c ON t.CustomerID = c.ID
                WHERE t.CustomerID IN ({id_list})
                    AND t.Time >= DATEADD(day, -{days_filter}, GETDATE())
                    AND t.Total > 0
                ORDER BY t.Time DESC
                """

                transactions = db.execute_query(transaction_query)

                # Format response
                members = []
                for _, row in customers.iterrows():
                    members.append({
                        'customer_id': int(row['ID']),
                        'first_name': row['FirstName'],
                        'last_name': row['LastName'],
                        'company': row['Company'],
                        'phone': row['PhoneNumber'],
                        'email': row['EmailAddress'],
                        'address': {
                            'street': row['Address'],
                            'city': row['City'],
                            'state': row['State'],
                            'zip': row['Zip']
                        },
                        'balance': float(row['AccountBalance'] or 0),
                        'credit_limit': float(row['CreditLimit'] or 0),
                        'last_visit': row['LastVisit'].isoformat() if row['LastVisit'] and not pd.isna(row['LastVisit']) else None,
                        'total_sales': float(row['TotalSales'] or 0),
                        'total_visits': int(row['TotalVisits'] or 0)
                    })

                # Format payments
                payment_list = []
                for _, row in payments.iterrows():
                    payment_list.append({
                        'customer_id': int(row['CustomerID']),
                        'customer_name': row['customer_name'],
                        'date': row['payment_date'].isoformat() if row['payment_date'] else None,
                        'amount': float(row['Amount'] or 0),
                        'comment': row['Comment']
                    })

                # Format transactions
                transaction_list = []
                for _, row in transactions.iterrows():
                    transaction_list.append({
                        'customer_id': int(row['CustomerID']),
                        'customer_name': row['customer_name'],
                        'date': row['transaction_date'].isoformat() if row['transaction_date'] else None,
                        'total': float(row['Total'] or 0),
                        'comment': row['Comment']
                    })

                response = {
                    'group_key': group_key,
                    'members': members,
                    'member_count': len(members),
                    'total_balance': sum(m['balance'] for m in members),
                    'total_credit_limit': sum(m['credit_limit'] for m in members),
                    'payments': payment_list,
                    'transactions': transaction_list,
                    'days_filter': days_filter
                }

                self._set_cache(cache_key, response)
                return response

        except Exception as e:
            logger.error(f"Error getting group full details: {e}")
            return {
                'group_key': group_key,
                'members': [],
                'payments': [],
                'transactions': [],
                'error': str(e)
            }

    def search_groups(self, search_term: str, limit: int = 10) -> List[Dict]:
        """
        Fast search for customer groups by name
        Returns lightweight results for autocomplete
        """
        if not search_term or len(search_term) < 2:
            return []

        cache_key = self._get_cache_key('search', term=search_term, limit=limit)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            with SQLServerConnection() as db:
                query = """
                WITH CustomerGroups AS (
                    SELECT
                        c.ID,
                        c.FirstName,
                        c.LastName,
                        c.AccountBalance,
                        SOUNDEX(ISNULL(c.LastName, '')) + '_' + SOUNDEX(ISNULL(c.FirstName, '')) as GroupKey
                    FROM dbo.Customer c
                    WHERE (c.FirstName LIKE %s OR c.LastName LIKE %s)
                        AND (c.AccountBalance > 0 OR c.LastVisit >= DATEADD(month, -12, GETDATE()))
                ),
                GroupedData AS (
                    SELECT
                        GroupKey,
                        COUNT(*) as MemberCount,
                        SUM(AccountBalance) as TotalBalance,
                        (SELECT TOP 1 FirstName FROM CustomerGroups g2
                         WHERE g2.GroupKey = g1.GroupKey
                         GROUP BY FirstName
                         ORDER BY COUNT(*) DESC) as DisplayFirstName,
                        (SELECT TOP 1 LastName FROM CustomerGroups g2
                         WHERE g2.GroupKey = g1.GroupKey
                         GROUP BY LastName
                         ORDER BY COUNT(*) DESC) as DisplayLastName
                    FROM CustomerGroups g1
                    GROUP BY GroupKey
                    HAVING COUNT(*) > 1
                )
                SELECT TOP %s
                    GroupKey as group_key,
                    DisplayFirstName as first_name,
                    DisplayLastName as last_name,
                    MemberCount as member_count,
                    TotalBalance as total_balance
                FROM GroupedData
                ORDER BY TotalBalance DESC
                """

                search_pattern = f"%{search_term}%"
                result = db.execute_query(query, (search_pattern, search_pattern, limit))

                groups = []
                for _, row in result.iterrows():
                    groups.append({
                        'group_id': f"GRP_{row['group_key']}",
                        'display_name': f"{row['first_name'] or ''} {row['last_name'] or ''}".strip(),
                        'member_count': int(row['member_count']),
                        'total_balance': float(row['total_balance'] or 0)
                    })

                self._set_cache(cache_key, groups)
                return groups

        except Exception as e:
            logger.error(f"Error searching groups: {e}")
            return []

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        return {
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys()),
            'ttl_seconds': self._cache_ttl
        }

    def clear_cache(self) -> None:
        """Clear all cached data"""
        self._cache.clear()
        logger.info("Cache cleared")