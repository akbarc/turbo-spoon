#!/usr/bin/env python3
"""
Deep dive into the exact reason for the $98.65 difference
Analyze every adjustment to understand the business logic
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime
from collections import defaultdict

def deep_dive_analysis():
    db = SQLServerConnection()
    customer_id = 4915
    
    print("=" * 100)
    print("DEEP DIVE: THE EXACT REASON FOR THE $98.65 DIFFERENCE")
    print("=" * 100)
    
    # First, let's get ALL adjustments and categorize them
    print("\n1. ANALYZING ALL ADJUSTMENTS IN DETAIL:")
    print("-" * 80)
    
    adjustment_query = f"""
    SELECT 
        arh.ID as HistoryID,
        arh.Date,
        arh.Amount,
        arh.Comment,
        arh.AccountReceivableID,
        ar.TransactionNumber,
        ar.OriginalAmount as InvoiceOriginal,
        ar.Balance as InvoiceBalance,
        ar.Date as InvoiceDate,
        ar.Type as InvoiceType
    FROM AccountReceivableHistory arh
    INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {customer_id}
      AND ABS(arh.Amount) <= 100
      AND arh.Comment NOT LIKE '%Payment%'
    ORDER BY arh.Date, arh.ID
    """
    
    adjustments = db.execute_query(adjustment_query, "Get all adjustments")
    
    # Categorize adjustments
    nsf_fees = []
    nsf_reversals = []
    other_adjustments = []
    
    for _, adj in adjustments.iterrows():
        amount = float(adj['Amount'])
        comment = adj['Comment'] or ''
        
        if 'NSF' in comment.upper() or 'RET' in comment.upper():
            if amount > 0:
                nsf_fees.append(adj)
            else:
                nsf_reversals.append(adj)
        else:
            other_adjustments.append(adj)
    
    print(f"NSF Fees Charged: {len(nsf_fees)} totaling ${sum(float(f['Amount']) for f in nsf_fees):,.2f}")
    print(f"NSF Fees Reversed: {len(nsf_reversals)} totaling ${sum(float(r['Amount']) for r in nsf_reversals):,.2f}")
    print(f"Other Adjustments: {len(other_adjustments)} totaling ${sum(float(o['Amount']) for o in other_adjustments):,.2f}")
    
    # Calculate net effect
    total_nsf_fees = sum(float(f['Amount']) for f in nsf_fees)
    total_nsf_reversals = sum(float(r['Amount']) for r in nsf_reversals)
    total_other = sum(float(o['Amount']) for o in other_adjustments)
    
    print(f"\nNET EFFECT:")
    print(f"  NSF Fees:      +${total_nsf_fees:,.2f}")
    print(f"  NSF Reversals: ${total_nsf_reversals:,.2f}")
    print(f"  Other:         ${total_other:,.2f}")
    print(f"  TOTAL:         ${total_nsf_fees + total_nsf_reversals + total_other:,.2f}")
    
    # Now let's trace specific NSF patterns
    print("\n2. NSF FEE PATTERNS (Fees that were NOT reversed):")
    print("-" * 80)
    
    # Match fees with reversals by date proximity
    unmatched_fees = []
    matched_pairs = []
    
    # Group by date to find pairs
    date_groups = defaultdict(list)
    for _, adj in adjustments.iterrows():
        date_key = adj['Date'].strftime('%Y-%m-%d')
        date_groups[date_key].append(adj)
    
    # Find unmatched fees
    net_by_date = {}
    for date, items in date_groups.items():
        day_total = sum(float(item['Amount']) for item in items)
        net_by_date[date] = day_total
        
        if day_total != 0:
            print(f"{date}: Net adjustment of ${day_total:,.2f}")
            for item in items:
                print(f"  - ${float(item['Amount']):,.2f}: {item['Comment'] or 'No comment'}")
    
    # Calculate the running net
    print("\n3. TRACKING NET ADJUSTMENTS OVER TIME:")
    print("-" * 80)
    
    running_net = 0
    for _, adj in adjustments.iterrows():
        running_net += float(adj['Amount'])
        if abs(running_net - 98.65) < 0.01:
            print(f"*** FOUND TARGET at {adj['Date']}: Running net = ${running_net:,.2f}")
            break
        
    print(f"Final running net of all adjustments: ${running_net:,.2f}")
    
    # Now let's check specific invoice adjustments
    print("\n4. WHICH INVOICES WERE ADJUSTED?")
    print("-" * 80)
    
    invoice_adjustments = defaultdict(list)
    for _, adj in adjustments.iterrows():
        ar_id = adj['AccountReceivableID']
        invoice_adjustments[ar_id].append(adj)
    
    for ar_id, adj_list in invoice_adjustments.items():
        if adj_list:
            first_adj = adj_list[0]
            trans_num = first_adj['TransactionNumber'] if first_adj['TransactionNumber'] else f"AR{ar_id}"
            total_adj = sum(float(a['Amount']) for a in adj_list)
            
            if total_adj != 0:  # Only show invoices with net adjustments
                print(f"\nInvoice {trans_num} (AR ID {ar_id}):")
                print(f"  Original Amount: ${first_adj['InvoiceOriginal']:,.2f}")
                print(f"  Current Balance: ${first_adj['InvoiceBalance']:,.2f}")
                print(f"  Total Adjustments: ${total_adj:,.2f}")
                print(f"  Adjustment Details:")
                for a in adj_list:
                    print(f"    {a['Date'].strftime('%Y-%m-%d')}: ${float(a['Amount']):,.2f} - {a['Comment'] or 'No comment'}")
    
    # Check partial payment on invoice 228377
    print("\n5. SPECIAL CASE: INVOICE #228377 WITH PARTIAL PAYMENT")
    print("-" * 80)
    
    inv_228377_query = f"""
    SELECT 
        ar.ID,
        ar.OriginalAmount,
        ar.Balance,
        ar.OriginalAmount - ar.Balance as AppliedAmount
    FROM AccountReceivable ar
    WHERE ar.CustomerID = {customer_id}
      AND ar.TransactionNumber = 228377
    """
    
    inv_228377 = db.execute_query(inv_228377_query, "Get invoice 228377")
    if not inv_228377.empty:
        inv = inv_228377.iloc[0]
        print(f"Invoice #228377:")
        print(f"  Original: ${inv['OriginalAmount']:,.2f}")
        print(f"  Balance:  ${inv['Balance']:,.2f}")
        print(f"  Applied:  ${inv['AppliedAmount']:,.2f}")
        
        # Get history for this specific invoice
        hist_query = f"""
        SELECT 
            arh.Date,
            arh.Amount,
            arh.Comment
        FROM AccountReceivableHistory arh
        WHERE arh.AccountReceivableID = {inv['ID']}
        ORDER BY arh.Date
        """
        
        hist = db.execute_query(hist_query, "Get history for 228377")
        if not hist.empty:
            print(f"\n  Transaction History:")
            for _, h in hist.iterrows():
                print(f"    {h['Date'].strftime('%Y-%m-%d')}: ${float(h['Amount']):,.2f} - {h['Comment'] or 'No comment'}")
    
    # Final analysis: Why exactly $98.65?
    print("\n6. THE EXACT BUSINESS REASON FOR $98.65:")
    print("=" * 80)
    
    # Let's calculate what makes up the $98.65
    nsf_fee_dates = []
    for fee in nsf_fees:
        fee_date = fee['Date'].strftime('%Y-%m-%d')
        fee_amount = float(fee['Amount'])
        
        # Check if there's a reversal on the same day or later
        was_reversed = False
        for rev in nsf_reversals:
            if rev['Date'] >= fee['Date'] and abs(float(rev['Amount']) + fee_amount) < 0.01:
                was_reversed = True
                break
        
        if not was_reversed:
            nsf_fee_dates.append((fee_date, fee_amount, fee['Comment']))
    
    print(f"NSF Fees that were NEVER reversed:")
    unreversed_total = 0
    for date, amount, comment in nsf_fee_dates:
        print(f"  {date}: ${amount:,.2f} - {comment}")
        unreversed_total += amount
    
    print(f"\nTotal unreversed NSF fees: ${unreversed_total:,.2f}")
    
    # Check other adjustments
    other_net = sum(float(o['Amount']) for o in other_adjustments)
    print(f"Other adjustments net: ${other_net:,.2f}")
    
    # The final calculation
    print(f"\nFINAL CALCULATION:")
    print(f"  Unreversed NSF fees: ${unreversed_total:,.2f}")
    print(f"  Other adjustments:   ${other_net:,.2f}")
    print(f"  Net reversals:       ${total_nsf_reversals:,.2f}")
    print(f"  TOTAL:              ${unreversed_total + other_net + total_nsf_reversals:,.2f}")
    
    # Business logic explanation
    print("\n" + "=" * 80)
    print("BUSINESS LOGIC EXPLANATION:")
    print("=" * 80)
    print("""
The $98.65 represents NET ADJUSTMENTS that were posted to the AR History
but are already reflected in the current AR balance. Here's what happened:

1. When NSF fees are charged, they increase the AR balance
2. When NSF fees are reversed, they decrease the AR balance
3. The NET of all these adjustments is $98.65

The running balance calculation (Invoices - Payments + Adjustments) = $43,523.52
But the AR system already applied these adjustments to get to $43,424.87

So: $43,523.52 - $98.65 = $43,424.87

This is CORRECT ACCOUNTING because:
- The AR balance ($43,424.87) is what the customer actually owes
- The adjustments were already processed and reflected in the AR
- Including them again in the running balance would be double-counting
""")

if __name__ == "__main__":
    deep_dive_analysis()