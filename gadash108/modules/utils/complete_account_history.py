#!/usr/bin/env python3
"""
Complete Account Activity History for 5 Star Food Mart Somani
Shows chronological timeline of all account activity with running AR balance
"""

import pandas as pd
from database_pymssql import quick_query
import logging
from decimal import Decimal
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Customer details
CUSTOMER_ID = 4915
CUSTOMER_NAME = "5 STAR FOOD MART LLC - SAMEER SOMANI"
ACCOUNT_NUMBER = "2058737683"

def get_complete_activity_timeline(customer_id):
    """Get complete chronological timeline of all account activity"""
    
    print(f"🔍 COMPLETE ACCOUNT ACTIVITY TIMELINE")
    print("="*80)
    print(f"Customer: {CUSTOMER_NAME}")
    print(f"Customer ID: {customer_id} | Account: {ACCOUNT_NUMBER}")
    print("="*80)
    
    # Get all activities in chronological order
    activities = []
    
    # 1. Get all transactions (invoices/sales)
    print("\n📋 Gathering transaction history...")
    txn_query = f"""
    SELECT 
        'INVOICE' as ActivityType,
        t.TransactionNumber as ReferenceNumber,
        t.Time as ActivityDate,
        t.Total as Amount,
        t.SalesTax as Tax,
        t.Comment,
        t.Status,
        t.BatchNumber,
        0 as PaymentID,
        0 as ARHistoryID
    FROM [dbo].[Transaction] t
    WHERE t.CustomerID = {customer_id}
    """
    
    transactions = quick_query(txn_query)
    for _, row in transactions.iterrows():
        activities.append({
            'date': row['ActivityDate'],
            'type': 'INVOICE',
            'reference': f"Invoice #{row['ReferenceNumber']}",
            'amount': Decimal(str(row['Amount'])),
            'description': f"Sale - {row.get('Comment', 'N/A')}",
            'batch': row['BatchNumber'],
            'status': row['Status'],
            'payment_id': None,
            'ar_history_id': None
        })
    
    # 2. Get all payments
    print("📋 Gathering payment history...")
    payment_query = f"""
    SELECT 
        'PAYMENT' as ActivityType,
        p.ID as ReferenceNumber,
        p.Time as ActivityDate,
        p.Amount as Amount,
        p.Comment,
        p.BatchNumber,
        p.CashierID
    FROM [dbo].[Payment] p
    WHERE p.CustomerID = {customer_id}
    """
    
    payments = quick_query(payment_query)
    for _, row in payments.iterrows():
        activities.append({
            'date': row['ActivityDate'],
            'type': 'PAYMENT',
            'reference': f"Payment #{row['ReferenceNumber']}",
            'amount': -Decimal(str(row['Amount'])),  # Negative for balance calculation
            'description': f"Payment - {row.get('Comment', 'N/A')}",
            'batch': row['BatchNumber'],
            'cashier': row['CashierID'],
            'payment_id': row['ReferenceNumber'],
            'ar_history_id': None
        })
    
    # 3. Get all AR History entries (adjustments, NSFs, etc.)
    print("📋 Gathering AR history...")
    ar_history_query = f"""
    SELECT 
        arh.ID as ARHistoryID,
        arh.Date as ActivityDate,
        arh.AccountReceivableID,
        arh.Amount,
        arh.PaymentID,
        arh.Comment,
        arh.CashierID,
        arh.HistoryType,
        arh.TransferArID,
        arh.ReasonCodeID,
        ar.TransactionNumber,
        ar.OriginalAmount as AROriginalAmount
    FROM [dbo].[AccountReceivableHistory] arh
    LEFT JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {customer_id}
    """
    
    ar_history = quick_query(ar_history_query)
    
    # Define history types
    history_types = {
        0: "INVOICE_CREATED",
        1: "ADJUSTMENT", 
        2: "PAYMENT_APPLIED",
        3: "TRANSFER/NSF",
        4: "WRITE_OFF",
        5: "OTHER"
    }
    
    for _, row in ar_history.iterrows():
        hist_type = history_types.get(row['HistoryType'], f"UNKNOWN_{row['HistoryType']}")
        
        # Skip INVOICE_CREATED and PAYMENT_APPLIED as they're already captured above
        if row['HistoryType'] in [0, 2]:
            continue
            
        activities.append({
            'date': row['ActivityDate'],
            'type': hist_type,
            'reference': f"AR History #{row['ARHistoryID']}",
            'amount': Decimal(str(row['Amount'])),
            'description': f"{hist_type} - {row.get('Comment', 'N/A')}",
            'batch': None,
            'cashier': row['CashierID'],
            'payment_id': row.get('PaymentID'),
            'ar_history_id': row['ARHistoryID'],
            'transfer_from': row.get('TransferArID')
        })
    
    # Sort all activities by date
    activities.sort(key=lambda x: x['date'] if pd.notna(x['date']) else datetime.min)
    
    return activities

def calculate_running_balance_timeline(activities):
    """Calculate running AR balance for each activity"""
    
    print(f"\n📊 ACCOUNT ACTIVITY TIMELINE WITH RUNNING BALANCE")
    print("="*100)
    
    running_balance = Decimal('0.00')
    timeline = []
    
    print(f"{'Date':<20} {'Type':<15} {'Reference':<20} {'Amount':<12} {'Running Balance':<15} {'Description'}")
    print("-" * 100)
    
    for activity in activities:
        # Update running balance
        running_balance += activity['amount']
        
        # Format date
        date_str = activity['date'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(activity['date']) else 'N/A'
        
        # Format amount with proper sign
        amount = activity['amount']
        amount_str = f"${amount:,.2f}" if amount >= 0 else f"-${abs(amount):,.2f}"
        
        # Add to timeline
        timeline_entry = {
            'date': activity['date'],
            'type': activity['type'],
            'reference': activity['reference'],
            'amount': amount,
            'running_balance': running_balance,
            'description': activity['description'],
            'batch': activity.get('batch'),
            'cashier': activity.get('cashier'),
            'payment_id': activity.get('payment_id'),
            'ar_history_id': activity.get('ar_history_id')
        }
        timeline.append(timeline_entry)
        
        # Print timeline entry
        balance_str = f"${running_balance:,.2f}"
        print(f"{date_str:<20} {activity['type']:<15} {activity['reference']:<20} {amount_str:<12} {balance_str:<15} {activity['description'][:40]}")
    
    print("-" * 100)
    print(f"FINAL BALANCE: ${running_balance:,.2f}")
    
    return timeline

def analyze_balance_trends(timeline):
    """Analyze balance trends and patterns"""
    
    print(f"\n📈 BALANCE TREND ANALYSIS")
    print("="*60)
    
    if not timeline:
        print("No timeline data available")
        return
    
    # Calculate statistics
    balances = [entry['running_balance'] for entry in timeline]
    max_balance = max(balances)
    min_balance = min(balances)
    current_balance = balances[-1]
    
    # Find highest and lowest points
    max_entry = next(entry for entry in timeline if entry['running_balance'] == max_balance)
    min_entry = next(entry for entry in timeline if entry['running_balance'] == min_balance)
    
    print(f"📊 BALANCE STATISTICS:")
    print(f"  Current Balance:    ${current_balance:,.2f}")
    print(f"  Highest Balance:    ${max_balance:,.2f} on {max_entry['date'].strftime('%Y-%m-%d')}")
    print(f"  Lowest Balance:     ${min_balance:,.2f} on {min_entry['date'].strftime('%Y-%m-%d')}")
    print(f"  Balance Range:      ${max_balance - min_balance:,.2f}")
    
    # Activity type summary
    print(f"\n📋 ACTIVITY SUMMARY:")
    activity_counts = {}
    activity_amounts = {}
    
    for entry in timeline:
        activity_type = entry['type']
        activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        activity_amounts[activity_type] = activity_amounts.get(activity_type, Decimal('0.00')) + entry['amount']
    
    for activity_type in sorted(activity_counts.keys()):
        count = activity_counts[activity_type]
        total_amount = activity_amounts[activity_type]
        print(f"  {activity_type:<15}: {count:>3} transactions | Total: ${total_amount:>10,.2f}")
    
    # Recent activity (last 90 days)
    recent_cutoff = datetime.now() - pd.Timedelta(days=90)
    recent_activities = [entry for entry in timeline if entry['date'] >= recent_cutoff]
    
    print(f"\n🕒 RECENT ACTIVITY (Last 90 Days): {len(recent_activities)} transactions")
    if recent_activities:
        recent_balance_change = recent_activities[-1]['running_balance'] - recent_activities[0]['running_balance']
        print(f"  Balance Change: ${recent_balance_change:,.2f}")
    
    # NSF Analysis
    nsf_entries = [entry for entry in timeline if 'NSF' in entry['type'] or 'NSF' in entry['description']]
    if nsf_entries:
        total_nsf_amount = sum(entry['amount'] for entry in nsf_entries)
        print(f"\n💳 NSF ANALYSIS:")
        print(f"  Total NSF Events: {len(nsf_entries)}")
        print(f"  Total NSF Amount: ${total_nsf_amount:,.2f}")

def generate_monthly_summary(timeline):
    """Generate monthly balance summary"""
    
    print(f"\n📅 MONTHLY BALANCE SUMMARY")
    print("="*60)
    
    if not timeline:
        print("No timeline data available")
        return
    
    # Group by month
    monthly_data = {}
    
    for entry in timeline:
        if pd.notna(entry['date']):
            month_key = entry['date'].strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'ending_balance': Decimal('0.00'),
                    'activities': 0,
                    'invoices': 0,
                    'payments': 0,
                    'adjustments': 0
                }
            
            monthly_data[month_key]['ending_balance'] = entry['running_balance']
            monthly_data[month_key]['activities'] += 1
            
            if entry['type'] == 'INVOICE':
                monthly_data[month_key]['invoices'] += 1
            elif entry['type'] == 'PAYMENT':
                monthly_data[month_key]['payments'] += 1
            elif 'ADJUSTMENT' in entry['type'] or 'NSF' in entry['type']:
                monthly_data[month_key]['adjustments'] += 1
    
    print(f"{'Month':<10} {'Ending Balance':<15} {'Activities':<10} {'Invoices':<10} {'Payments':<10} {'Adjustments':<12}")
    print("-" * 80)
    
    for month in sorted(monthly_data.keys()):
        data = monthly_data[month]
        print(f"{month:<10} ${data['ending_balance']:>12,.2f} {data['activities']:>9} {data['invoices']:>9} {data['payments']:>9} {data['adjustments']:>11}")

if __name__ == "__main__":
    print("🔍 COMPLETE ACCOUNT ACTIVITY HISTORY")
    print("=" * 80)
    print(f"Customer: {CUSTOMER_NAME}")
    print(f"Customer ID: {CUSTOMER_ID} | Account: {ACCOUNT_NUMBER}")
    print("Analysis Date:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 80)
    
    # 1. Get complete activity timeline
    activities = get_complete_activity_timeline(CUSTOMER_ID)
    
    # 2. Calculate running balance timeline
    timeline = calculate_running_balance_timeline(activities)
    
    # 3. Analyze balance trends
    analyze_balance_trends(timeline)
    
    # 4. Generate monthly summary
    generate_monthly_summary(timeline)
    
    print("\n" + "="*80)
    print("COMPLETE ACCOUNT HISTORY ANALYSIS FINISHED")
    print("="*80)
    print("\n💡 KEY INSIGHTS:")
    print("- Timeline shows chronological order of all account activities")
    print("- Running balance is calculated after each transaction")
    print("- NSFs and adjustments significantly impact the balance")
    print("- Payment patterns can be analyzed for collection strategies")
    print("- Monthly summaries help identify seasonal patterns")
    print("\n📋 BALANCE CALCULATION METHOD:")
    print("1. Start with $0.00 balance")
    print("2. Add each invoice amount (positive)")
    print("3. Subtract each payment amount (negative)")
    print("4. Add NSFs, fees, and adjustments")
    print("5. Running total = Current AR Balance")
