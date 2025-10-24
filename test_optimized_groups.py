#!/usr/bin/env python3
"""
Test script for optimized customer groups
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ar.optimized_customer_groups import OptimizedCustomerGrouper
from database_pymssql import SQLServerConnection

def test_soundex_query():
    """Test if SOUNDEX is working in SQL Server"""
    try:
        with SQLServerConnection() as db:
            # Simple test query
            query = """
            SELECT TOP 10
                c.ID,
                c.FirstName,
                c.LastName,
                c.AccountBalance,
                SOUNDEX(ISNULL(c.LastName, '')) as LastNameSoundex,
                SOUNDEX(ISNULL(c.FirstName, '')) as FirstNameSoundex
            FROM dbo.Customer c
            WHERE c.FirstName IS NOT NULL OR c.LastName IS NOT NULL
                AND c.AccountBalance > 0
            ORDER BY c.AccountBalance DESC
            """

            result = db.execute_query(query)
            print("Sample customers with SOUNDEX:")
            for _, row in result.iterrows():
                print(f"ID: {row['ID']}, Name: {row['FirstName']} {row['LastName']}, "
                      f"Balance: {row['AccountBalance']}, "
                      f"SOUNDEX: {row['FirstNameSoundex']}_{row['LastNameSoundex']}")

            # Test grouping
            query2 = """
            SELECT TOP 10
                COUNT(*) as GroupCount,
                SOUNDEX(ISNULL(LastName, '')) + '_' + SOUNDEX(ISNULL(FirstName, '')) as GroupKey,
                MIN(FirstName) as SampleFirst,
                MIN(LastName) as SampleLast
            FROM dbo.Customer
            WHERE (FirstName IS NOT NULL OR LastName IS NOT NULL)
                AND AccountBalance > 0
            GROUP BY SOUNDEX(ISNULL(LastName, '')) + '_' + SOUNDEX(ISNULL(FirstName, ''))
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            """

            result2 = db.execute_query(query2)
            print("\n\nGroups found:")
            for _, row in result2.iterrows():
                print(f"GroupKey: {row['GroupKey']}, Count: {row['GroupCount']}, "
                      f"Sample: {row['SampleFirst']} {row['SampleLast']}")

    except Exception as e:
        print(f"Error: {e}")

def test_optimized_grouper():
    """Test the optimized grouper"""
    grouper = OptimizedCustomerGrouper()

    print("\n\nTesting OptimizedCustomerGrouper.get_groups_summary():")
    result = grouper.get_groups_summary(page=1, limit=5, min_balance=0)

    print(f"Total groups: {result['total_groups']}")
    print(f"Groups returned: {len(result['groups'])}")

    for group in result['groups']:
        print(f"  - {group['display_name']}: {group['member_count']} members, ${group['total_balance']}")

if __name__ == "__main__":
    test_soundex_query()
    test_optimized_grouper()