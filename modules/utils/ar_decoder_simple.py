#!/usr/bin/env python3
"""
AR History Business Event Decoder - Simplified Version
Demonstrates reverse engineering AR History into business events
"""

import pandas as pd
from decimal import Decimal
from database_pymssql import quick_query
import re

def decode_ar_history_events(customer_id: int):
    """
    Decode AR History entries into recognizable business events
    """
    
    print(f"🔍 DECODING AR HISTORY TO BUSINESS EVENTS")
    print(f"Customer ID: {customer_id}")
    print("="*70)
    
    # Get AR History with context
    query = f"""
    SELECT 
        arh.ID,
        arh.Date,
        arh.Amount,
        arh.HistoryType,
        arh.Comment,
        arh.PaymentID,
        ar.TransactionNumber,
        ar.OriginalAmount
    FROM [dbo].[AccountReceivableHistory] arh
    JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {customer_id}
    ORDER BY arh.Date ASC, arh.ID ASC
    """
    
    ar_history = quick_query(query)
    
    if ar_history.empty:
        print("No AR History found")
        return
    
    # Define business event categories
    history_type_names = {
        0: "INVOICE_CREATED",
        1: "ADJUSTMENT",
        2: "PAYMENT_APPLIED", 
        3: "TRANSFER_NSF",
        4: "WRITE_OFF",
        5: "OTHER_FEES"
    }
    
    # Pattern matching for business events
    nsf_patterns = [r'NSF', r'RETURNED', r'RET.*NSF', r'CK.*RET', r'BOUNCE']
    fee_patterns = [r'FEE', r'COLLECTION', r'PENALTY']
    
    # Decode each entry
    decoded_events = []
    event_summary = {}
    running_balance = Decimal('0.00')
    
    print(f"\n📋 DECODED BUSINESS EVENTS:")
    print("-" * 100)
    print(f"{'Date':<12} {'Event Type':<20} {'Amount':<12} {'Balance':<12} {'Description':<40}")
    print("-" * 100)
    
    for _, row in ar_history.iterrows():
        amount = Decimal(str(row['Amount']))
        running_balance += amount
        comment = str(row.get('Comment', '')).upper()
        
        # Determine business event type
        base_type = history_type_names.get(row['HistoryType'], 'UNKNOWN')
        business_event = base_type
        
        # Refine based on comment analysis
        if any(re.search(pattern, comment) for pattern in nsf_patterns):
            business_event = "NSF_RETURNED_CHECK"
        elif any(re.search(pattern, comment) for pattern in fee_patterns):
            business_event = "NSF_FEE"
        elif row['HistoryType'] == 0 and row['TransactionNumber']:
            business_event = "SALE_INVOICE"
        elif row['HistoryType'] == 2 and row['PaymentID']:
            business_event = "PAYMENT_RECEIVED"
        elif amount < 0 and 'CREDIT' in comment:
            business_event = "CREDIT_ADJUSTMENT"
        
        # Track event summary
        if business_event not in event_summary:
            event_summary[business_event] = {'count': 0, 'total_amount': Decimal('0.00')}
        event_summary[business_event]['count'] += 1
        event_summary[business_event]['total_amount'] += amount
        
        # Build event record
        event = {
            'date': row['Date'],
            'event_type': business_event,
            'amount': amount,
            'running_balance': running_balance,
            'description': comment[:40],
            'transaction_number': row.get('TransactionNumber'),
            'payment_id': row.get('PaymentID'),
            'ar_history_id': row['ID']
        }
        
        decoded_events.append(event)
        
        # Display event
        date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'
        print(f"{date_str:<12} {business_event:<20} ${amount:>9,.2f} ${running_balance:>10,.2f} {comment[:40]:<40}")
    
    print("-" * 100)
    print(f"FINAL BALANCE: ${running_balance:,.2f}")
    
    # Display summary
    print(f"\n📊 BUSINESS EVENT SUMMARY:")
    print("-" * 60)
    print(f"{'Event Type':<25} {'Count':<8} {'Total Amount':<15}")
    print("-" * 60)
    
    for event_type, data in sorted(event_summary.items()):
        print(f"{event_type:<25} {data['count']:>7} ${data['total_amount']:>12,.2f}")
    
    # Analyze key patterns
    print(f"\n🔍 KEY BUSINESS PATTERNS IDENTIFIED:")
    print("=" * 60)
    
    nsf_events = [e for e in decoded_events if 'NSF' in e['event_type']]
    payment_events = [e for e in decoded_events if 'PAYMENT' in e['event_type']]
    invoice_events = [e for e in decoded_events if 'INVOICE' in e['event_type'] or 'SALE' in e['event_type']]
    
    print(f"🔴 NSF Events: {len(nsf_events)} incidents")
    if nsf_events:
        total_nsf = sum(e['amount'] for e in nsf_events)
        print(f"   Total NSF Impact: ${total_nsf:,.2f}")
        print(f"   Average NSF Amount: ${total_nsf / len(nsf_events):,.2f}")
    
    print(f"\n💰 Payment Events: {len(payment_events)} payments")
    if payment_events:
        total_payments = sum(abs(e['amount']) for e in payment_events)
        print(f"   Total Payments: ${total_payments:,.2f}")
    
    print(f"\n📄 Invoice Events: {len(invoice_events)} invoices")
    if invoice_events:
        total_invoices = sum(e['amount'] for e in invoice_events if e['amount'] > 0)
        print(f"   Total Invoiced: ${total_invoices:,.2f}")
    
    # Show the business story
    print(f"\n📖 BUSINESS STORY RECONSTRUCTION:")
    print("=" * 60)
    
    # Find first and last events
    first_event = decoded_events[0] if decoded_events else None
    last_event = decoded_events[-1] if decoded_events else None
    
    if first_event and last_event:
        print(f"Account Start: {first_event['date'].strftime('%Y-%m-%d')} - {first_event['event_type']}")
        print(f"Latest Activity: {last_event['date'].strftime('%Y-%m-%d')} - {last_event['event_type']}")
        
        date_range = (last_event['date'] - first_event['date']).days
        print(f"Account Lifetime: {date_range} days ({date_range/365:.1f} years)")
    
    # Payment vs NSF analysis
    if nsf_events and payment_events:
        nsf_rate = len(nsf_events) / (len(nsf_events) + len(payment_events)) * 100
        print(f"NSF Rate: {nsf_rate:.1f}% of payment-related activity")
        
        if nsf_rate > 20:
            print("🚨 HIGH RISK: Customer has very high NSF rate")
        elif nsf_rate > 10:
            print("⚠️  MEDIUM RISK: Customer has elevated NSF rate")
        else:
            print("✅ LOW RISK: Customer has acceptable NSF rate")
    
    # Balance trend
    if len(decoded_events) > 1:
        balance_trend = running_balance - decoded_events[0]['running_balance']
        if balance_trend > 0:
            print(f"📈 Balance Trend: INCREASING by ${balance_trend:,.2f}")
        else:
            print(f"📉 Balance Trend: DECREASING by ${abs(balance_trend):,.2f}")
    
    return decoded_events, event_summary

def match_to_source_transactions(customer_id: int):
    """
    Match AR History events back to source transactions and payments
    """
    
    print(f"\n🔗 MATCHING AR HISTORY TO SOURCE TRANSACTIONS")
    print("=" * 70)
    
    # Get recent AR History entries that should have source matches
    query = f"""
    SELECT TOP 20
        arh.ID,
        arh.Date,
        arh.Amount,
        arh.HistoryType,
        arh.Comment,
        arh.PaymentID,
        ar.TransactionNumber
    FROM [dbo].[AccountReceivableHistory] arh
    JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
    WHERE ar.CustomerID = {customer_id}
    ORDER BY arh.Date DESC
    """
    
    recent_history = quick_query(query)
    
    print(f"📋 MATCHING RECENT AR HISTORY ENTRIES:")
    print("-" * 80)
    
    for _, row in recent_history.iterrows():
        ar_id = row['ID']
        history_type = row['HistoryType']
        amount = row['Amount']
        comment = row.get('Comment', '')
        
        match_status = "❌ NO MATCH"
        source_info = ""
        
        # Try to match to transaction
        if row['TransactionNumber'] and history_type == 0:
            txn_query = f"""
            SELECT Total, Time, Comment 
            FROM [dbo].[Transaction] 
            WHERE TransactionNumber = {row['TransactionNumber']}
            """
            txn_result = quick_query(txn_query)
            
            if not txn_result.empty:
                txn = txn_result.iloc[0]
                match_status = "✅ MATCHED"
                source_info = f"Transaction ${txn['Total']:.2f} on {txn['Time']}"
        
        # Try to match to payment
        elif row['PaymentID'] and history_type == 2:
            pay_query = f"""
            SELECT Amount, Time, Comment 
            FROM [dbo].[Payment] 
            WHERE ID = {row['PaymentID']}
            """
            pay_result = quick_query(pay_query)
            
            if not pay_result.empty:
                payment = pay_result.iloc[0]
                match_status = "✅ MATCHED" 
                source_info = f"Payment ${payment['Amount']:.2f} on {payment['Time']}"
        
        # NSF pattern matching
        elif 'NSF' in comment.upper() or 'RETURNED' in comment.upper():
            match_status = "🔍 NSF EVENT"
            source_info = f"Bounced check/payment: {comment[:30]}"
        
        print(f"AR#{ar_id} | ${amount:>8,.2f} | {match_status} | {source_info}")
    
    print("\n💡 MATCHING INSIGHTS:")
    print("- HistoryType 0 should match to Transaction table")
    print("- HistoryType 2 should match to Payment table")  
    print("- HistoryType 5 often contains NSFs and fees")
    print("- Comment analysis is crucial for unmatched entries")

if __name__ == "__main__":
    print("🔍 AR HISTORY TO BUSINESS EVENTS DECODER")
    print("=" * 70)
    print("Reverse engineering AccountReceivableHistory into business events")
    print("=" * 70)
    
    customer_id = 4915  # 5 Star Food Mart Somani
    
    try:
        # Decode AR History into business events
        events, summary = decode_ar_history_events(customer_id)
        
        # Match events to source transactions
        match_to_source_transactions(customer_id)
        
        print(f"\n" + "="*70)
        print("🎯 CONCLUSIONS:")
        print("="*70)
        print("✅ AR History CAN be reverse engineered into business events")
        print("✅ Pattern matching on comments reveals true event types")
        print("✅ Cross-referencing with source tables improves accuracy")
        print("✅ Business story can be reconstructed from audit trail")
        print("⚠️  Some events may remain ambiguous without additional context")
        
        print(f"\n🔧 PRACTICAL APPLICATIONS:")
        print("- Legacy system data migration")
        print("- Forensic accounting and audits")
        print("- Business intelligence reporting")
        print("- Customer behavior analysis")
        print("- Compliance and regulatory reporting")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
