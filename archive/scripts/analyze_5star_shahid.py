#!/usr/bin/env python3
"""
Analyze 5 Star Food Mart LLC (Shahid) - Customer ID 4915
Phone: 229 573 2401-SHAHID
"""

from customer_ledger_enhanced import EnhancedCustomerLedger
import json
from datetime import datetime

print('='*60)
print('ANALYZING 5 STAR FOOD MART LLC (SHAHID)')
print('='*60)

ledger = EnhancedCustomerLedger()

# Get the correct customer - ID 4915
customer_id = 4915
print(f'\nCustomer ID: {customer_id}')
print('Phone: 229 573 2401-SHAHID')
print('Address: 205 S CARROLL ROAD, VILLA RICA, 30180')
print('Current Balance: $43,424.87')
print('Lifetime Sales: $221,633.95')
print('Last Payment: May 12, 2025')

# Get enhanced ledger for last 120 days to capture last payment
print('\nGenerating enhanced ledger for last 120 days...')
result = ledger.get_enhanced_ledger(customer_id, days_back=120)

if 'error' in result:
    print(f'ERROR: {result["error"]}')
else:
    # Display payment methods
    print('\n' + '='*60)
    print('PAYMENT METHODS USED')
    print('='*60)
    payment_methods = result['summary'].get('payment_methods', {})
    if payment_methods:
        for method, data in payment_methods.items():
            print(f'{method:20s}: {data["count"]:3d} payments, Total: ${data["total"]:,.2f}, Avg: ${data["average"]:,.2f}')
    else:
        print('No payments found in this period')
    
    # Look for all payments
    ledger_entries = result['ledger']
    payments = [e for e in ledger_entries if e['TransactionType'] == 'PMT']
    
    if payments:
        print(f'\nFound {len(payments)} payments:')
        for p in payments:
            print(f"  {p['TransactionDate']}: ${abs(p['Amount']):,.2f} via {p.get('PaymentMethod', 'UNKNOWN')}")
            if p.get('OriginalComment'):
                print(f"    Comment: {p['OriginalComment']}")
    
    # Display recent transactions with tender types
    print('\n' + '='*60)
    print('RECENT TRANSACTIONS WITH TENDER TYPES & EXPLANATIONS')
    print('='*60)
    
    if ledger_entries:
        # Show last 20 transactions
        recent = ledger_entries[-20:] if len(ledger_entries) > 20 else ledger_entries
        
        for entry in recent:
            print(f'\nDate: {entry["TransactionDate"]}')
            print(f'  Type: {entry["TransactionType"]:8s} Amount: ${entry["Amount"]:,.2f}')
            
            if entry['TransactionType'] == 'PMT':
                print(f'  Payment Method: {entry.get("PaymentMethod", "UNSPECIFIED")}')
            elif entry['TransactionType'] == 'SALE' and entry.get('PaymentMethod'):
                print(f'  Tender Used: {entry["PaymentMethod"]}')
            
            print(f'  Explanation: {entry.get("Explanation", "No explanation")}')
            if entry.get('OriginalComment') and entry['OriginalComment'] not in [None, '', '.']:
                print(f'  Comment: {entry["OriginalComment"]}')
    
    # Show NSF and adjustment analysis
    print('\n' + '='*60)
    print('ADJUSTMENTS & NSF ANALYSIS')
    print('='*60)
    
    # Look for NSF transactions specifically
    nsf_transactions = [e for e in ledger_entries if 'NSF' in str(e.get('TransactionType', '')) or 'NSF' in str(e.get('OriginalComment', ''))]
    if nsf_transactions:
        print(f'\nFound {len(nsf_transactions)} NSF-related transactions:')
        for nsf in nsf_transactions[:5]:
            print(f"  {nsf['TransactionDate']}: {nsf['TransactionType']} - ${nsf['Amount']:,.2f}")
            if nsf.get('Explanation'):
                print(f"    {nsf['Explanation']}")
    
    adjustments = result['summary'].get('adjustment_types', {})
    if adjustments:
        print('\nAdjustment Summary:')
        for adj_type, data in adjustments.items():
            print(f'  {adj_type:25s}: {data["count"]:3d} items, Net: ${data["total_amount"]:,.2f}')
    
    # Check for returns (negative transactions)
    returns = [e for e in ledger_entries if e['TransactionType'] == 'SALE' and e['Amount'] < 0]
    if returns:
        print(f'\nFound {len(returns)} return transactions:')
        for r in returns[:5]:
            print(f"  {r['TransactionDate']}: ${r['Amount']:,.2f}")
    
    # Show summary
    print('\n' + '='*60)
    print('FINANCIAL SUMMARY')
    print('='*60)
    summary = result['summary']
    print(f'Period: Last 120 days')
    print(f'Total Sales: ${summary["total_sales"]:,.2f}')
    print(f'Total Payments: ${summary["total_payments"]:,.2f}')
    print(f'Total Adjustments: ${summary["total_adjustments"]:,.2f}')
    print(f'Total NSF Fees: ${summary.get("total_nsf_fees", 0):,.2f}')
    print(f'Total Returns: ${summary.get("total_returns", 0):,.2f}')
    print(f'Net Activity: ${summary["total_debits"] - summary["total_credits"]:,.2f}')
    print(f'Current AR Balance: ${summary["current_ar_balance"]:,.2f}')
    
    # Active AR aging
    if result.get('active_ar'):
        print('\n' + '='*60)
        print('ACTIVE AR AGING')
        print('='*60)
        ar_items = result['active_ar']
        aging = {}
        for item in ar_items:
            cat = item.get('AgingCategory', 'Unknown')
            if cat not in aging:
                aging[cat] = {'count': 0, 'total': 0}
            aging[cat]['count'] += 1
            aging[cat]['total'] += item['Balance']
        
        for category, data in aging.items():
            print(f'{category:15s}: {data["count"]:3d} items, ${data["total"]:,.2f}')
    
    # Save report
    report_file = f'5star_shahid_{customer_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'\n✓ Detailed report saved to: {report_file}')
    
    # Data quality check
    print('\n' + '='*60)
    print('DATA QUALITY & CLARITY CHECK')
    print('='*60)
    
    # Check payment method identification
    if payments:
        identified = [p for p in payments if p.get('PaymentMethod') and p['PaymentMethod'] != 'UNSPECIFIED']
        print(f'Payment method identified: {len(identified)}/{len(payments)} ({len(identified)*100/len(payments):.1f}%)')
    
    # Check adjustment explanations
    adj_entries = [e for e in ledger_entries if 'Adjustment' in e.get('Category', '')]
    if adj_entries:
        explained = [a for a in adj_entries if a.get('Explanation') and 'Manual Adjustment' not in a['Explanation']]
        print(f'Clear explanations: {len(explained)}/{len(adj_entries)} ({len(explained)*100/len(adj_entries):.1f}%)')
    
    print('\n✓ Analysis complete!')