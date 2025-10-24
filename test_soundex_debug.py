#!/usr/bin/env python3
"""
Debug SOUNDEX query issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_pymssql import SQLServerConnection

def test_query():
    """Test the exact query from the module"""
    try:
        with SQLServerConnection() as db:
            # Test the exact query
            query = """
            WITH CustomerGroups AS (
                SELECT
                    c.ID,
                    c.FirstName,
                    c.LastName,
                    c.AccountBalance,
                    SOUNDEX(ISNULL(c.LastName, '')) + '_' + SOUNDEX(ISNULL(c.FirstName, '')) as GroupKey,
                    CASE
                        WHEN c.LastVisit >= DATEADD(day, -30, GETDATE()) THEN 1
                        ELSE 0
                    END as HasRecentActivity
                FROM dbo.Customer c
                WHERE (c.FirstName IS NOT NULL OR c.LastName IS NOT NULL)
                    AND c.AccountBalance >= 0
            ),
            GroupedData AS (
                SELECT
                    GroupKey,
                    COUNT(*) as MemberCount,
                    SUM(AccountBalance) as TotalBalance,
                    MAX(HasRecentActivity) as HasRecentActivity,
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
            SELECT TOP 10
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
            ORDER BY TotalBalance DESC
            """

            print("Testing full query without parameters...")
            result = db.execute_query(query)
            print(f"Rows returned: {len(result)}")

            if not result.empty:
                print("\nFirst 5 groups:")
                for idx, row in result.head(5).iterrows():
                    print(f"  {row['group_key']}: {row['first_name']} {row['last_name']}, "
                          f"{row['member_count']} members, ${row['total_balance']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()