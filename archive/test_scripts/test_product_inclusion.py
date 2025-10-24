#!/usr/bin/env python3
"""Test product inclusion to see what we might be missing"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database_pymssql import SQLServerConnection

def test_product_queries():
    """Test different product query approaches"""
    
    db = SQLServerConnection()
    
    # MSA Categories
    MSA_CATEGORIES = {
        48: "CIGARETTE",
        72: "LITTLE CIGAR-GA",
        23: "CIGARS",
        56: "CIGAR GA",
        51: "LIT CIGARS 003251",
        53: "TOB 003211",
        41: "TOB 003212",
        54: "TOB 003213",
        76: "TOB 003214",
        55: "TOB 003215",
        49: "LT-TAX-COLLECTED",
        52: "LT-RYO-TAX COLLECTED",
        57: "LT-TAX PAID",
        59: "LT-NON-GA/ROL UR OWN",
        66: "ELECTRONIC CIG",
        81: "ECIG - PODS",
        83: "NICOTINE POUCHES",
        11: "CIG ROLLING PAPER",
        31: "BLUNT WRAP"
    }
    
    categories = ','.join(str(k) for k in MSA_CATEGORIES.keys())
    
    print("Testing Product Inclusion Queries")
    print("=" * 60)
    
    with db:
        # Query 1: With ItemLookupCode filters (current)
        query1 = f"""
        SELECT COUNT(*) as count
        FROM dbo.Item i
        WHERE CAST(i.CategoryID as INT) IN ({categories})
            AND i.ItemLookupCode IS NOT NULL
            AND i.ItemLookupCode != ''
        """
        result1 = db.execute_query(query1, description="Count with ItemLookupCode filters")
        count1 = result1.iloc[0]['count'] if not result1.empty else 0
        
        # Query 2: Without ItemLookupCode filters
        query2 = f"""
        SELECT COUNT(*) as count
        FROM dbo.Item i
        WHERE CAST(i.CategoryID as INT) IN ({categories})
        """
        result2 = db.execute_query(query2, description="Count without filters")
        count2 = result2.iloc[0]['count'] if not result2.empty else 0
        
        # Query 3: Check NULL ItemLookupCode
        query3 = f"""
        SELECT COUNT(*) as count
        FROM dbo.Item i
        WHERE CAST(i.CategoryID as INT) IN ({categories})
            AND (i.ItemLookupCode IS NULL OR i.ItemLookupCode = '')
        """
        result3 = db.execute_query(query3, description="Count NULL/empty ItemLookupCode")
        count3 = result3.iloc[0]['count'] if not result3.empty else 0
        
        print(f"\nProduct counts:")
        print(f"  With ItemLookupCode filters: {count1}")
        print(f"  Without any filters: {count2}")
        print(f"  With NULL/empty ItemLookupCode: {count3}")
        print(f"  Difference: {count2 - count1} products excluded by filters")
        
        # Query 4: Sample products with NULL/empty ItemLookupCode
        if count3 > 0:
            query4 = f"""
            SELECT TOP 10
                i.ID,
                i.Description,
                i.ItemLookupCode,
                CAST(i.CategoryID as INT) as CategoryID
            FROM dbo.Item i
            WHERE CAST(i.CategoryID as INT) IN ({categories})
                AND (i.ItemLookupCode IS NULL OR i.ItemLookupCode = '')
            """
            result4 = db.execute_query(query4, description="Sample NULL ItemLookupCode products")
            
            if not result4.empty:
                print(f"\nSample products with NULL/empty ItemLookupCode:")
                for _, row in result4.iterrows():
                    print(f"  ID: {row['ID']}, Desc: {row['Description'][:50]}, Code: '{row['ItemLookupCode']}'")
        
        # Query 5: Check for special ItemLookupCode patterns
        query5 = f"""
        SELECT TOP 20
            i.ItemLookupCode,
            i.Description
        FROM dbo.Item i
        WHERE CAST(i.CategoryID as INT) IN ({categories})
            AND i.ItemLookupCode LIKE '000000000%'
        ORDER BY i.ItemLookupCode
        """
        result5 = db.execute_query(query5, description="Products with special codes")
        
        if not result5.empty:
            print(f"\nProducts with special codes (00000000...):")
            for _, row in result5.iterrows():
                print(f"  Code: {row['ItemLookupCode']}, Desc: {row['Description'][:50]}")

# Run the test
test_product_queries()