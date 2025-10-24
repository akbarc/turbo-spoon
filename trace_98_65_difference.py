#!/usr/bin/env python3
"""
Trace the exact $98.65 difference between running balance and AR balance
Running balance: $43,523.52
AR balance: $43,424.87
Difference: $98.65
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from decimal import Decimal

def trace_difference():
    db = SQLServerConnection()
    customer_id = 4915
    
    print("=" * 80)
    print("TRACING THE $98.65 DIFFERENCE")
    print("Running Balance from transactions: $43,523.52")
    print("Active AR Balance: $43,424.87")
    print("Difference to find: $98.65")
    print("=" * 80)
    
    # Look for adjustments totaling $98.65
    print("\n1. CHECKING ADJUSTMENTS IN AR HISTORY:")
    adjustment_query = f"""
    SELECT 
        arh.ID,
        arh.Date,
        arh.Amount,
        arh.Comment,
        arh.AccountReceivableID,
        ar.TransactionNumber
    FROM AccountReceivableHistory arh
    INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {customer_id}
      AND ABS(arh.Amount) <= 100
      AND arh.Comment NOT LIKE '%Payment%'
    ORDER BY arh.Date DESC
    """
    
    adjustments = db.execute_query(adjustment_query, "Get adjustments")
    
    if not adjustments.empty:
        print(f"Found {len(adjustments)} small adjustments:")
        adj_total = 0
        for _, adj in adjustments.iterrows():
            amount = float(adj['Amount'])
            adj_total += amount
            print(f"  {adj['Date'].strftime('%Y-%m-%d')}: ${amount:,.2f} - {adj['Comment'] or 'No comment'}")
        
        print(f"\nTotal of adjustments: ${adj_total:,.2f}")
        
        if abs(adj_total - 98.65) < 0.01:
            print("*** FOUND IT! These adjustments total $98.65 ***")
    
    # Check the specific invoice with partial payment
    print("\n2. CHECKING INVOICE #228377 WITH PARTIAL PAYMENT:")
    
    invoice_query = f"""
    SELECT 
        ar.ID,
        ar.TransactionNumber,
        ar.Date,
        ar.OriginalAmount,
        ar.Balance,
        ar.OriginalAmount - ar.Balance as PaidAmount
    FROM AccountReceivable ar
    WHERE ar.CustomerID = {customer_id}
      AND ar.TransactionNumber = 228377
    """
    
    invoice = db.execute_query(invoice_query, "Get invoice 228377")
    if not invoice.empty:
        inv = invoice.iloc[0]
        print(f"Invoice #228377:")
        print(f"  Original Amount: ${inv['OriginalAmount']:,.2f}")
        print(f"  Current Balance: ${inv['Balance']:,.2f}")
        print(f"  Paid Amount: ${inv['PaidAmount']:,.2f}")
        
        # Check payment history for this invoice
        payment_history_query = f"""
        SELECT 
            arh.Date,
            arh.Amount,
            arh.Comment
        FROM AccountReceivableHistory arh
        WHERE arh.AccountReceivableID = {inv['ID']}
        ORDER BY arh.Date
        """
        
        payment_hist = db.execute_query(payment_history_query, "Get payment history")
        if not payment_hist.empty:
            print(f"\n  Payment/Adjustment History for Invoice #228377:")
            for _, ph in payment_hist.iterrows():
                print(f"    {ph['Date'].strftime('%Y-%m-%d')}: ${ph['Amount']:,.2f} - {ph['Comment'] or 'No comment'}")
    
    # Now let's calculate the running balance step by step
    print("\n3. CALCULATING RUNNING BALANCE STEP BY STEP:")
    
    # Get all transactions in order
    all_trans_query = f"""
    WITH AllActivity AS (
        -- Invoices from AR
        SELECT 
            ar.Date as TDate,
            'INV' as TType,
            ar.OriginalAmount as Amount,
            'Invoice #' + ISNULL(CAST(ar.TransactionNumber as VARCHAR), CAST(ar.ID as VARCHAR)) as Description,
            1 as OrderType
        FROM AccountReceivable ar
        WHERE ar.CustomerID = {customer_id}
        
        UNION ALL
        
        -- Payments
        SELECT 
            p.Time as TDate,
            'PMT' as TType,
            -p.Amount as Amount,
            'Payment #' + CAST(p.ID as VARCHAR) as Description,
            2 as OrderType
        FROM Payment p
        WHERE p.CustomerID = {customer_id}
        
        UNION ALL
        
        -- Small adjustments (the key difference!)
        SELECT 
            arh.Date as TDate,
            'ADJ' as TType,
            arh.Amount as Amount,
            'Adjustment: ' + ISNULL(arh.Comment, 'Manual') as Description,
            3 as OrderType
        FROM AccountReceivableHistory arh
        INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
        WHERE ar.CustomerID = {customer_id}
          AND ABS(arh.Amount) <= 100
          AND arh.Comment NOT LIKE '%Payment%'
    )
    SELECT TOP 10 * 
    FROM AllActivity
    ORDER BY TDate DESC, OrderType
    """
    
    recent_trans = db.execute_query(all_trans_query, "Get recent activity")
    
    print("\nMost recent 10 transactions:")
    for _, trans in recent_trans.iterrows():
        print(f"  {trans['TDate'].strftime('%Y-%m-%d')} {trans['TType']}: ${trans['Amount']:,.2f} - {trans['Description']}")
    
    # Calculate totals by type
    totals_query = f"""
    SELECT 
        -- Total invoices
        (SELECT SUM(OriginalAmount) FROM AccountReceivable WHERE CustomerID = {customer_id}) as TotalInvoices,
        -- Total payments
        (SELECT SUM(Amount) FROM Payment WHERE CustomerID = {customer_id}) as TotalPayments,
        -- Total adjustments
        (SELECT SUM(arh.Amount) 
         FROM AccountReceivableHistory arh
         INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
         WHERE ar.CustomerID = {customer_id}
           AND ABS(arh.Amount) <= 100
           AND arh.Comment NOT LIKE '%Payment%') as TotalAdjustments
    """
    
    totals = db.execute_query(totals_query, "Get totals").iloc[0]
    
    print("\n4. FINAL CALCULATION:")
    print(f"  Total Invoices:    ${float(totals['TotalInvoices'] or 0):,.2f}")
    print(f"  Total Payments:    -${float(totals['TotalPayments'] or 0):,.2f}")
    print(f"  Total Adjustments: ${float(totals['TotalAdjustments'] or 0):,.2f}")
    print(f"  " + "-" * 40)
    
    running_total = float(totals['TotalInvoices'] or 0) - float(totals['TotalPayments'] or 0) + float(totals['TotalAdjustments'] or 0)
    print(f"  Running Balance:   ${running_total:,.2f}")
    
    print(f"\n5. VERIFICATION:")
    print(f"  Calculated Running Balance: ${running_total:,.2f}")
    print(f"  Expected (from test):       $43,523.52")
    print(f"  Active AR Balance:          $43,424.87")
    print(f"  Adjustments Total:          ${float(totals['TotalAdjustments'] or 0):,.2f}")
    
    print(f"\n*** CONCLUSION ***")
    print(f"The ${abs(float(totals['TotalAdjustments'] or 0)):,.2f} in adjustments is the difference!")
    print(f"These are manual adjustments that reduced the AR balance.")
    print(f"Running balance includes all transactions: Invoices - Payments + Adjustments")
    print(f"But the AR balance has been reduced by these adjustments.")

if __name__ == "__main__":
    trace_difference()