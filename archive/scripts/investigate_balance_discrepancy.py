#!/usr/bin/env python3
"""
Investigate Balance Discrepancy
Timeline: $49,326.97 vs Current AR: $43,424.87
Difference: $5,902.10
"""

import pandas as pd
from database_pymssql import quick_query
import logging
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CUSTOMER_ID = 4915

def get_ar_balance_verification():
    """Get current AR balance directly"""
    
    print("🔍 VERIFYING CURRENT AR BALANCE")
    print("="*60)
    
    query = f"""
    SELECT 
        SUM(ar.Balance) as TotalARBalance,
        COUNT(*) as ActiveARRecords
    FROM [dbo].[AccountReceivable] ar
    WHERE ar.CustomerID = {CUSTOMER_ID}
      AND ar.Balance != 0
    """
    
    result = quick_query(query)
    
    if not result.empty:
        total_balance = Decimal(str(result.iloc[0]['TotalARBalance']))
        count = result.iloc[0]['ActiveARRecords']
        print(f"Current AR Balance: ${total_balance:.2f}")
        print(f"Active AR Records: {count}")
        return total_balance
    else:
        print("No AR balance found")
        return Decimal('0.00')

def get_ar_history_sum():
    """Get sum of ALL AR History entries"""
    
    print("\n🔍 VERIFYING AR HISTORY SUM")
    print("="*60)
    
    query = f"""
    SELECT 
        SUM(arh.Amount) as TotalARHistory,
        COUNT(*) as TotalARHistoryRecords
    FROM [dbo].[AccountReceivableHistory] arh
    LEFT JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {CUSTOMER_ID}
    """
    
    result = quick_query(query)
    
    if not result.empty:
        total_history = Decimal(str(result.iloc[0]['TotalARHistory']))
        count = result.iloc[0]['TotalARHistoryRecords']
        print(f"AR History Sum: ${total_history:.2f}")
        print(f"AR History Records: {count}")
        return total_history
    else:
        print("No AR History found")
        return Decimal('0.00')

def check_duplicate_activities():
    """Check if we're double-counting activities in our timeline"""
    
    print("\n🔍 CHECKING FOR DUPLICATE COUNTING")
    print("="*60)
    
    # Check transactions vs AR History type 0 (Invoice Created)
    print("📋 Checking Transaction vs AR History Invoice Created overlap...")
    
    query = f"""
    SELECT 
        COUNT(DISTINCT t.TransactionNumber) as UniqueTransactions,
        COUNT(*) as TotalTransactions
    FROM [dbo].[Transaction] t
    WHERE t.CustomerID = {CUSTOMER_ID}
    """
    
    txn_result = quick_query(query)
    unique_txns = txn_result.iloc[0]['UniqueTransactions']
    total_txns = txn_result.iloc[0]['TotalTransactions']
    
    print(f"Unique Transactions: {unique_txns}")
    print(f"Total Transactions: {total_txns}")
    
    # Check AR History Invoice Created entries
    query = f"""
    SELECT 
        COUNT(*) as InvoiceCreatedEntries
    FROM [dbo].[AccountReceivableHistory] arh
    LEFT JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {CUSTOMER_ID}
      AND arh.HistoryType = 0
    """
    
    inv_result = quick_query(query)
    invoice_created = inv_result.iloc[0]['InvoiceCreatedEntries']
    
    print(f"AR History Invoice Created: {invoice_created}")
    
    # Check payments vs AR History type 2 (Payment Applied)
    print("\n📋 Checking Payment vs AR History Payment Applied overlap...")
    
    query = f"""
    SELECT 
        COUNT(*) as TotalPayments,
        SUM(p.Amount) as TotalPaymentAmount
    FROM [dbo].[Payment] p
    WHERE p.CustomerID = {CUSTOMER_ID}
    """
    
    pay_result = quick_query(query)
    total_payments = pay_result.iloc[0]['TotalPayments']
    total_pay_amount = Decimal(str(pay_result.iloc[0]['TotalPaymentAmount']))
    
    print(f"Total Payments: {total_payments}")
    print(f"Total Payment Amount: ${total_pay_amount:.2f}")
    
    # Check AR History Payment Applied entries
    query = f"""
    SELECT 
        COUNT(*) as PaymentAppliedEntries,
        SUM(arh.Amount) as PaymentAppliedAmount
    FROM [dbo].[AccountReceivableHistory] arh
    LEFT JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {CUSTOMER_ID}
      AND arh.HistoryType = 2
    """
    
    pay_applied_result = quick_query(query)
    payment_applied = pay_applied_result.iloc[0]['PaymentAppliedEntries']
    payment_applied_amount = Decimal(str(pay_applied_result.iloc[0]['PaymentAppliedAmount']))
    
    print(f"AR History Payment Applied: {payment_applied}")
    print(f"AR History Payment Applied Amount: ${payment_applied_amount:.2f}")
    
    # Check for duplication
    if unique_txns == invoice_created:
        print("✅ No duplication between Transactions and AR History Invoice Created")
    else:
        print("❌ Potential duplication between Transactions and AR History")
    
    if abs(total_pay_amount + payment_applied_amount) < 0.01:  # They should be negative of each other
        print("✅ Payments and AR History Payment Applied match")
    else:
        print("❌ Payments and AR History Payment Applied don't match")
        print(f"Difference: ${total_pay_amount + payment_applied_amount:.2f}")

def correct_timeline_calculation():
    """Calculate timeline using ONLY AR History (no duplicates)"""
    
    print("\n🔍 CORRECTED TIMELINE CALCULATION")
    print("="*60)
    print("Using ONLY AR History to avoid double-counting")
    
    query = f"""
    SELECT 
        arh.ID,
        arh.Date,
        arh.Amount,
        arh.HistoryType,
        arh.Comment,
        ar.TransactionNumber
    FROM [dbo].[AccountReceivableHistory] arh
    LEFT JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {CUSTOMER_ID}
    ORDER BY arh.Date ASC, arh.ID ASC
    """
    
    result = quick_query(query)
    
    if result.empty:
        print("No AR History found")
        return Decimal('0.00')
    
    # Calculate running balance using ONLY AR History
    running_balance = Decimal('0.00')
    
    history_types = {
        0: "INVOICE_CREATED",
        1: "ADJUSTMENT", 
        2: "PAYMENT_APPLIED",
        3: "TRANSFER/NSF",
        4: "WRITE_OFF",
        5: "OTHER"
    }
    
    print(f"\n📊 AR HISTORY TIMELINE (Corrected)")
    print("-" * 80)
    
    for _, row in result.iterrows():
        amount = Decimal(str(row['Amount']))
        running_balance += amount
        
        hist_type = history_types.get(row['HistoryType'], f"UNKNOWN_{row['HistoryType']}")
        date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'
        
        print(f"{date_str} | {hist_type:<15} | ${amount:>10,.2f} | ${running_balance:>12,.2f} | {str(row.get('Comment', 'N/A'))[:30]}")
    
    print("-" * 80)
    print(f"CORRECTED FINAL BALANCE: ${running_balance:.2f}")
    
    return running_balance

def find_recent_transactions_not_in_ar():
    """Check if there are recent transactions not yet in AR History"""
    
    print("\n🔍 CHECKING FOR RECENT TRANSACTIONS NOT IN AR HISTORY")
    print("="*60)
    
    # Get transactions from last 30 days
    query = f"""
    SELECT 
        t.TransactionNumber,
        t.Time,
        t.Total,
        ar.ID as ARID,
        ar.Balance
    FROM [dbo].[Transaction] t
    LEFT JOIN [dbo].[AccountReceivable] ar ON t.TransactionNumber = ar.TransactionNumber
    WHERE t.CustomerID = {CUSTOMER_ID}
      AND t.Time >= DATEADD(day, -30, GETDATE())
    ORDER BY t.Time DESC
    """
    
    result = quick_query(query)
    
    if not result.empty:
        print(f"Recent transactions (last 30 days): {len(result)}")
        for _, row in result.iterrows():
            ar_status = "HAS AR" if pd.notna(row['ARID']) else "NO AR"
            print(f"Txn #{row['TransactionNumber']} | {row['Time']} | ${row['Total']:.2f} | {ar_status}")
    else:
        print("No recent transactions found")

if __name__ == "__main__":
    print("🔍 BALANCE DISCREPANCY INVESTIGATION")
    print("=" * 70)
    print("Timeline showed: $49,326.97")
    print("Current AR shows: $43,424.87")
    print("Difference: $5,902.10")
    print("=" * 70)
    
    # 1. Verify current AR balance
    current_ar = get_ar_balance_verification()
    
    # 2. Verify AR History sum
    ar_history_sum = get_ar_history_sum()
    
    # 3. Check for duplicate counting
    check_duplicate_activities()
    
    # 4. Calculate corrected timeline
    corrected_balance = correct_timeline_calculation()
    
    # 5. Check for recent transactions
    find_recent_transactions_not_in_ar()
    
    print("\n" + "=" * 70)
    print("BALANCE RECONCILIATION SUMMARY")
    print("=" * 70)
    print(f"Current AR Balance:     ${current_ar:.2f}")
    print(f"AR History Sum:         ${ar_history_sum:.2f}")
    print(f"Corrected Timeline:     ${corrected_balance:.2f}")
    print(f"Original Timeline:      $49,326.97")
    
    if abs(current_ar - ar_history_sum) < 0.01:
        print("✅ Current AR matches AR History sum")
    else:
        print("❌ Current AR does NOT match AR History sum")
        print(f"   Difference: ${current_ar - ar_history_sum:.2f}")
    
    if abs(corrected_balance - ar_history_sum) < 0.01:
        print("✅ Corrected timeline matches AR History")
    else:
        print("❌ Corrected timeline does NOT match AR History")
    
    print("\n💡 CONCLUSION:")
    print("The accurate balance calculation method is:")
    print("1. Use ONLY AccountReceivableHistory table")
    print("2. Sum ALL amounts in chronological order") 
    print("3. This gives the true current AR balance")
    print("4. Avoid double-counting from Transaction/Payment tables")
