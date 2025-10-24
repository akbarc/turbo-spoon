#!/usr/bin/env python3
"""
NSF (Non-Sufficient Funds) Logic Investigation
===============================================
This script investigates how NSF checks are handled in the system:
1. Original check amount that gets reversed
2. $65 NSF fee that gets added
3. The relationship between AccountReceivable and AccountReceivableHistory
"""

import pandas as pd
import logging
from database_pymssql import SQLServerConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigate_nsf_logic():
    """Deep dive into NSF handling"""
    db = SQLServerConnection()
    
    logger.info("🔍 Investigating NSF Logic in AccountReceivable...")
    
    # First, let's look at a specific customer with NSF issues
    nsf_pattern_query = """
    -- Find all NSF-related AR entries with their history
    WITH NSFAnalysis AS (
        SELECT 
            ar.ID as AR_ID,
            ar.CustomerID,
            c.Company,
            ar.Date,
            ar.TransactionNumber,
            ar.OriginalAmount,
            ar.Balance,
            arh.ID as History_ID,
            arh.Comment,
            arh.PaymentID,
            -- Identify the type of AR entry
            CASE 
                WHEN ar.OriginalAmount = 65.00 AND ar.TransactionNumber = 0 THEN 'NSF_FEE'
                WHEN arh.Comment LIKE '%NSF%' OR arh.Comment LIKE '%RET%' THEN 'NSF_REVERSAL'
                WHEN ar.TransactionNumber = 0 THEN 'MANUAL_ADJUSTMENT'
                ELSE 'REGULAR_AR'
            END as Entry_Type
        FROM dbo.AccountReceivable ar
        INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
        LEFT JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
        WHERE 
            -- Look for NSF patterns
            (ar.OriginalAmount = 65.00 AND ar.TransactionNumber = 0) -- NSF fees
            OR arh.Comment LIKE '%NSF%'
            OR arh.Comment LIKE '%RET%'
            OR arh.Comment LIKE '%RETURN%'
            OR arh.Comment LIKE '%INSUFFICIENT%'
    )
    SELECT TOP 100 * 
    FROM NSFAnalysis
    ORDER BY CustomerID, Date DESC
    """
    
    try:
        nsf_data = db.execute_query(nsf_pattern_query)
        
        if not nsf_data.empty:
            logger.info(f"Found {len(nsf_data)} NSF-related entries")
            
            # Group by customer to see patterns
            print("\n📊 NSF Pattern Analysis by Customer:")
            print("=" * 100)
            
            customer_groups = nsf_data.groupby('Company')
            for company, group in list(customer_groups)[:5]:  # Show first 5 companies
                print(f"\n🏢 Customer: {company}")
                print("-" * 80)
                
                nsf_fees = group[group['Entry_Type'] == 'NSF_FEE']
                nsf_reversals = group[group['Entry_Type'] == 'NSF_REVERSAL']
                
                print(f"  NSF Fees ($65): {len(nsf_fees)} entries, Total: ${len(nsf_fees) * 65:.2f}")
                print(f"  NSF Reversals: {len(nsf_reversals)} entries")
                
                # Show the entries
                for _, row in group.iterrows():
                    print(f"    [{row['Date']}] {row['Entry_Type']}: ${row['OriginalAmount']:.2f} - {row['Comment'] or 'No comment'}")
            
            # Now let's understand the complete NSF flow
            print("\n📈 NSF Summary Statistics:")
            print("=" * 100)
            
            nsf_summary_query = """
            WITH NSFSummary AS (
                -- NSF Fees ($65 charges)
                SELECT 
                    'NSF_FEES' as Category,
                    COUNT(DISTINCT ar.ID) as Entry_Count,
                    COUNT(DISTINCT ar.CustomerID) as Customer_Count,
                    SUM(ar.OriginalAmount) as Total_Amount,
                    AVG(ar.Balance) as Avg_Outstanding
                FROM dbo.AccountReceivable ar
                WHERE ar.OriginalAmount = 65.00 
                    AND ar.TransactionNumber = 0
                    AND ar.Date >= DATEADD(day, -90, GETDATE())
                
                UNION ALL
                
                -- Returned checks (reversals)
                SELECT 
                    'RETURNED_CHECKS' as Category,
                    COUNT(DISTINCT ar.ID) as Entry_Count,
                    COUNT(DISTINCT ar.CustomerID) as Customer_Count,
                    SUM(ar.OriginalAmount) as Total_Amount,
                    AVG(ar.Balance) as Avg_Outstanding
                FROM dbo.AccountReceivable ar
                INNER JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
                WHERE (arh.Comment LIKE '%NSF%' 
                    OR arh.Comment LIKE '%RET%' 
                    OR arh.Comment LIKE '%RETURN%')
                    AND ar.OriginalAmount != 65.00
                    AND ar.Date >= DATEADD(day, -90, GETDATE())
            )
            SELECT * FROM NSFSummary
            """
            
            summary = db.execute_query(nsf_summary_query)
            if not summary.empty:
                print(summary.to_string(index=False))
            
            # Look at recent NSF activity
            print("\n🕐 Recent NSF Activity (Last 30 days):")
            print("=" * 100)
            
            recent_nsf_query = """
            SELECT TOP 20
                ar.Date,
                c.Company,
                ar.OriginalAmount,
                ar.Balance,
                arh.Comment,
                CASE 
                    WHEN ar.OriginalAmount = 65.00 THEN 'NSF Fee'
                    ELSE 'Returned Check'
                END as Type
            FROM dbo.AccountReceivable ar
            INNER JOIN dbo.Customer c ON ar.CustomerID = c.ID
            LEFT JOIN dbo.AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID
            WHERE ar.Date >= DATEADD(day, -30, GETDATE())
                AND (
                    (ar.OriginalAmount = 65.00 AND ar.TransactionNumber = 0)
                    OR arh.Comment LIKE '%NSF%'
                    OR arh.Comment LIKE '%RET%'
                )
            ORDER BY ar.Date DESC
            """
            
            recent = db.execute_query(recent_nsf_query)
            if not recent.empty:
                for _, row in recent.iterrows():
                    print(f"  [{row['Date']}] {row['Company'][:30]:<30} | {row['Type']:<15} | ${row['OriginalAmount']:>10,.2f} | Balance: ${row['Balance']:>10,.2f}")
                    if row['Comment']:
                        print(f"     Comment: {row['Comment']}")
                        
        else:
            logger.info("No NSF patterns found")
            
    except Exception as e:
        logger.error(f"Error investigating NSF logic: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    investigate_nsf_logic()