#!/usr/bin/env python3
"""
Investigate the $98.65 difference between running balance and AR balance
"""

from database_pymssql import SQLServerConnection
import pandas as pd

def investigate_difference():
    db = SQLServerConnection()
    customer_id = 4915
    
    print("=" * 80)
    print("INVESTIGATING BALANCE DIFFERENCE")
    print("=" * 80)
    
    # 1. Get current AR balance from Customer table
    customer_query = f"""
    SELECT 
        ID,
        AccountNumber,
        COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
        AccountBalance
    FROM Customer
    WHERE ID = {customer_id}
    """
    customer = db.execute_query(customer_query, "Get customer").iloc[0]
    print(f"\nCustomer: {customer['CustomerName']}")
    print(f"Current AR Balance in Customer Table: ${customer['AccountBalance']:,.2f}")
    
    # 2. Get sum of active AR records
    ar_query = f"""
    SELECT 
        SUM(Balance) as TotalBalance,
        SUM(OriginalAmount) as TotalOriginal,
        COUNT(*) as RecordCount
    FROM AccountReceivable
    WHERE CustomerID = {customer_id}
      AND Balance != 0
    """
    ar_summary = db.execute_query(ar_query, "Get AR summary").iloc[0]
    print(f"\nActive AR Summary:")
    print(f"  Total Balance: ${ar_summary['TotalBalance']:,.2f}")
    print(f"  Total Original: ${ar_summary['TotalOriginal']:,.2f}")
    print(f"  Number of Records: {ar_summary['RecordCount']}")
    
    # 3. Get detailed AR records to see the difference
    ar_details_query = f"""
    SELECT 
        ID,
        TransactionNumber,
        Date,
        OriginalAmount,
        Balance,
        OriginalAmount - Balance as PaidAmount,
        Type
    FROM AccountReceivable
    WHERE CustomerID = {customer_id}
      AND Balance != 0
    ORDER BY Date
    """
    ar_details = db.execute_query(ar_details_query, "Get AR details")
    
    print(f"\nDetailed AR Records:")
    print("-" * 80)
    total_original = 0
    total_balance = 0
    total_paid = 0
    
    for _, row in ar_details.iterrows():
        total_original += row['OriginalAmount']
        total_balance += row['Balance']
        total_paid += row['PaidAmount']
        
        type_str = 'TR' if row['Type'] == 0 else 'DC'
        print(f"{type_str} #{row['TransactionNumber'] or row['ID']}: Original=${row['OriginalAmount']:,.2f}, Balance=${row['Balance']:,.2f}, Paid=${row['PaidAmount']:,.2f}")
    
    print(f"\nTotals:")
    print(f"  Total Original: ${total_original:,.2f}")
    print(f"  Total Balance: ${total_balance:,.2f}")
    print(f"  Total Paid: ${total_paid:,.2f}")
    
    # 4. Calculate the difference
    difference = float(total_balance) - float(customer['AccountBalance'])
    print(f"\nDifference Analysis:")
    print(f"  AR Records Total: ${total_balance:,.2f}")
    print(f"  Customer Table Balance: ${float(customer['AccountBalance']):,.2f}")
    print(f"  Difference: ${difference:,.2f}")
    
    # 5. Look for the specific difference amount in transactions
    print(f"\nSearching for transactions or adjustments of ${abs(difference):,.2f}...")
    
    # Check for recent adjustments
    adjustment_query = f"""
    SELECT TOP 20
        arh.ID,
        arh.Date,
        arh.Amount,
        arh.Comment,
        ar.TransactionNumber,
        ar.Balance as CurrentBalance
    FROM AccountReceivableHistory arh
    INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {customer_id}
      AND ABS(arh.Amount) BETWEEN {abs(difference) - 1} AND {abs(difference) + 1}
    ORDER BY arh.Date DESC
    """
    adjustments = db.execute_query(adjustment_query, "Find adjustments")
    
    if not adjustments.empty:
        print(f"\nFound adjustments near ${abs(difference):,.2f}:")
        for _, adj in adjustments.iterrows():
            print(f"  Date: {adj['Date']}, Amount: ${adj['Amount']:,.2f}, Comment: {adj['Comment']}")
    
    # 6. Check for partial payments on specific invoices
    print(f"\nChecking for partial payments...")
    
    # Look at invoices with partial payments
    for _, row in ar_details.iterrows():
        if row['PaidAmount'] > 0:
            print(f"\nInvoice {row['TransactionNumber'] or row['ID']} has partial payment:")
            print(f"  Original: ${row['OriginalAmount']:,.2f}")
            print(f"  Balance: ${row['Balance']:,.2f}")
            print(f"  Paid: ${row['PaidAmount']:,.2f}")
            
            # Check if the paid amount matches our difference
            if abs(row['PaidAmount'] - abs(difference)) < 1:
                print(f"  *** This paid amount (${row['PaidAmount']:,.2f}) matches the difference!")
    
    # 7. Get all transactions to compute running balance from scratch
    print(f"\n" + "=" * 80)
    print("COMPUTING RUNNING BALANCE FROM ALL TRANSACTIONS")
    print("=" * 80)
    
    all_trans_query = f"""
    WITH AllTransactions AS (
        -- All invoices
        SELECT 
            ar.Date as TransDate,
            'Invoice' as Type,
            ar.OriginalAmount as Amount,
            ar.TransactionNumber,
            ar.ID as RefID
        FROM AccountReceivable ar
        WHERE ar.CustomerID = {customer_id}
        
        UNION ALL
        
        -- All payments
        SELECT 
            p.Time as TransDate,
            'Payment' as Type,
            -p.Amount as Amount,
            0 as TransactionNumber,
            p.ID as RefID
        FROM Payment p
        WHERE p.CustomerID = {customer_id}
    )
    SELECT *
    FROM AllTransactions
    ORDER BY TransDate, Type DESC
    """
    
    all_trans = db.execute_query(all_trans_query, "Get all transactions")
    
    running_balance = 0
    invoice_total = 0
    payment_total = 0
    
    for _, trans in all_trans.iterrows():
        running_balance += trans['Amount']
        if trans['Type'] == 'Invoice':
            invoice_total += trans['Amount']
        else:
            payment_total += abs(trans['Amount'])
    
    print(f"\nTransaction Summary:")
    print(f"  Total Invoices: ${invoice_total:,.2f}")
    print(f"  Total Payments: ${payment_total:,.2f}")
    print(f"  Net (Invoices - Payments): ${invoice_total - payment_total:,.2f}")
    print(f"  Running Balance: ${running_balance:,.2f}")
    
    # Compare with AR
    print(f"\nComparison:")
    print(f"  Running Balance from Transactions: ${running_balance:,.2f}")
    print(f"  Active AR Total: ${total_balance:,.2f}")
    print(f"  Customer Table Balance: ${float(customer['AccountBalance']):,.2f}")
    
    # The key difference
    trans_vs_ar = running_balance - total_balance
    print(f"\nKey Finding:")
    print(f"  Transaction Running Balance: ${running_balance:,.2f}")
    print(f"  Active AR Balance: ${total_balance:,.2f}")
    print(f"  Difference: ${trans_vs_ar:,.2f}")
    print(f"\n  This ${abs(trans_vs_ar):,.2f} difference represents adjustments or corrections")
    print(f"  that were applied to reduce the AR balance.")

if __name__ == "__main__":
    investigate_difference()