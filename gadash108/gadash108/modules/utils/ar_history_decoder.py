#!/usr/bin/env python3
"""
AR History Decoder - Reverse Engineering Business Events
Match AR History entries to actual business events (sales, payments, NSFs, adjustments)

This demonstrates how to decode AccountReceivableHistory when you need to 
understand what each entry represents in business terms.
"""

import pandas as pd
from decimal import Decimal
from database_pymssql import quick_query
import logging
from datetime import datetime, timedelta
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ARHistoryDecoder:
    """
    Decode AccountReceivableHistory entries into business events
    
    This class attempts to match each AR History entry to its underlying
    business event (sale, payment, NSF, adjustment, etc.)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Business event patterns for comment analysis
        self.nsf_patterns = [
            r'NSF', r'RETURNED', r'BOUNCE', r'INSUFFICIENT', 
            r'RET.*NSF', r'CK.*RET', r'ECK.*RET', r'PD.*CK.*RET'
        ]
        
        self.fee_patterns = [
            r'FEE', r'COLLECTION', r'LATE', r'PENALTY', r'CHARGE'
        ]
        
        self.adjustment_patterns = [
            r'CREDIT', r'ADJUST', r'CORRECTION', r'REFUND', r'DISCOUNT'
        ]
        
    def decode_customer_history(self, customer_id: int) -> dict:
        """
        Decode complete AR History for a customer into business events
        """
        
        print(f"🔍 DECODING AR HISTORY FOR CUSTOMER {customer_id}")
        print("="*70)
        
        # Get all AR History
        ar_history = self._get_ar_history_with_context(customer_id)
        
        if ar_history.empty:
            return {'error': 'No AR History found'}
        
        # Get supporting data for matching
        transactions = self._get_transactions(customer_id)
        payments = self._get_payments(customer_id)
        
        # Decode each history entry
        decoded_entries = []
        unmatched_entries = []
        
        for _, history_row in ar_history.iterrows():
            decoded = self._decode_single_entry(history_row, transactions, payments)
            
            if decoded['confidence'] >= 0.7:
                decoded_entries.append(decoded)
            else:
                unmatched_entries.append(decoded)
        
        # Generate summary
        summary = self._generate_summary(decoded_entries, unmatched_entries)
        
        return {
            'customer_id': customer_id,
            'total_entries': len(ar_history),
            'decoded_entries': decoded_entries,
            'unmatched_entries': unmatched_entries,
            'summary': summary
        }
    
    def _get_ar_history_with_context(self, customer_id: int) -> pd.DataFrame:
        """Get AR History with additional context"""
        
        query = f"""
        SELECT 
            arh.ID,
            arh.Date,
            arh.AccountReceivableID,
            arh.Amount,
            arh.PaymentID,
            arh.Comment,
            arh.CashierID,
            arh.HistoryType,
            arh.TransferArID,
            arh.ReasonCodeID,
            ar.TransactionNumber,
            ar.OriginalAmount as AROriginalAmount,
            ar.Type as ARType,
            ar.Date as ARDate
        FROM [dbo].[AccountReceivableHistory] arh
        JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
        WHERE ar.CustomerID = {customer_id}
        ORDER BY arh.Date ASC, arh.ID ASC
        """
        
        return quick_query(query)
    
    def _get_transactions(self, customer_id: int) -> pd.DataFrame:
        """Get all transactions for matching"""
        
        query = f"""
        SELECT 
            TransactionNumber,
            Time,
            Total,
            SalesTax,
            Comment,
            Status,
            BatchNumber
        FROM [dbo].[Transaction]
        WHERE CustomerID = {customer_id}
        ORDER BY Time ASC
        """
        
        return quick_query(query)
    
    def _get_payments(self, customer_id: int) -> pd.DataFrame:
        """Get all payments for matching"""
        
        query = f"""
        SELECT 
            ID,
            Time,
            Amount,
            Comment,
            BatchNumber,
            CashierID
        FROM [dbo].[Payment]
        WHERE CustomerID = {customer_id}
        ORDER BY Time ASC
        """
        
        return quick_query(query)
    
    def _decode_single_entry(self, history_row: pd.Series, transactions: pd.DataFrame, payments: pd.DataFrame) -> dict:
        """
        Decode a single AR History entry into a business event
        """
        
        entry = {
            'ar_history_id': history_row['ID'],
            'date': history_row['Date'],
            'amount': Decimal(str(history_row['Amount'])),
            'history_type': history_row['HistoryType'],
            'comment': history_row.get('Comment', ''),
            'payment_id': history_row.get('PaymentID'),
            'transaction_number': history_row.get('TransactionNumber'),
            'business_event': 'UNKNOWN',
            'event_details': {},
            'confidence': 0.0,
            'matching_logic': []
        }
        
        # Decode based on HistoryType first
        if history_row['HistoryType'] == 0:
            entry.update(self._decode_invoice_created(history_row, transactions))
        elif history_row['HistoryType'] == 1:
            entry.update(self._decode_adjustment(history_row))
        elif history_row['HistoryType'] == 2:
            entry.update(self._decode_payment_applied(history_row, payments))
        elif history_row['HistoryType'] == 3:
            entry.update(self._decode_transfer_nsf(history_row))
        elif history_row['HistoryType'] == 4:
            entry.update(self._decode_writeoff(history_row))
        elif history_row['HistoryType'] == 5:
            entry.update(self._decode_other(history_row))
        
        return entry
    
    def _decode_invoice_created(self, row: pd.Series, transactions: pd.DataFrame) -> dict:
        """Decode HistoryType 0 - Invoice Created"""
        
        result = {
            'business_event': 'INVOICE_CREATED',
            'confidence': 0.9,
            'matching_logic': ['HistoryType=0 indicates invoice creation']
        }
        
        # Try to match to actual transaction
        if row['TransactionNumber'] and not transactions.empty:
            matching_txn = transactions[transactions['TransactionNumber'] == row['TransactionNumber']]
            
            if not matching_txn.empty:
                txn = matching_txn.iloc[0]
                result['event_details'] = {
                    'transaction_number': row['TransactionNumber'],
                    'transaction_date': txn['Time'],
                    'transaction_total': float(txn['Total']),
                    'sales_tax': float(txn['SalesTax']),
                    'transaction_comment': txn.get('Comment', ''),
                    'status': txn['Status']
                }
                result['confidence'] = 1.0
                result['matching_logic'].append('Successfully matched to Transaction table')
            else:
                result['confidence'] = 0.7
                result['matching_logic'].append('TransactionNumber provided but no matching transaction found')
        
        return result
    
    def _decode_adjustment(self, row: pd.Series) -> dict:
        """Decode HistoryType 1 - Adjustment"""
        
        result = {
            'business_event': 'ADJUSTMENT',
            'confidence': 0.8,
            'matching_logic': ['HistoryType=1 indicates adjustment']
        }
        
        comment = str(row.get('Comment', '')).upper()
        amount = Decimal(str(row['Amount']))
        
        # Determine adjustment type based on comment and amount
        if any(re.search(pattern, comment) for pattern in self.adjustment_patterns):
            if amount < 0:
                result['business_event'] = 'CREDIT_ADJUSTMENT'
                result['event_details'] = {'type': 'Credit/Refund', 'reason': comment}
            else:
                result['business_event'] = 'DEBIT_ADJUSTMENT'
                result['event_details'] = {'type': 'Additional Charge', 'reason': comment}
            result['confidence'] = 0.9
            result['matching_logic'].append('Comment contains adjustment keywords')
        else:
            result['event_details'] = {'type': 'Unknown Adjustment', 'reason': comment}
        
        return result
    
    def _decode_payment_applied(self, row: pd.Series, payments: pd.DataFrame) -> dict:
        """Decode HistoryType 2 - Payment Applied"""
        
        result = {
            'business_event': 'PAYMENT_APPLIED',
            'confidence': 0.8,
            'matching_logic': ['HistoryType=2 indicates payment application']
        }
        
        # Try to match to actual payment
        if row['PaymentID'] and not payments.empty:
            matching_payment = payments[payments['ID'] == row['PaymentID']]
            
            if not matching_payment.empty:
                payment = matching_payment.iloc[0]
                result['event_details'] = {
                    'payment_id': row['PaymentID'],
                    'payment_date': payment['Time'],
                    'payment_amount': float(payment['Amount']),
                    'payment_comment': payment.get('Comment', ''),
                    'batch_number': payment.get('BatchNumber'),
                    'cashier_id': payment.get('CashierID')
                }
                result['confidence'] = 1.0
                result['matching_logic'].append('Successfully matched to Payment table')
            else:
                result['confidence'] = 0.6
                result['matching_logic'].append('PaymentID provided but no matching payment found')
        
        return result
    
    def _decode_transfer_nsf(self, row: pd.Series) -> dict:
        """Decode HistoryType 3 - Transfer/NSF"""
        
        result = {
            'business_event': 'TRANSFER_NSF',
            'confidence': 0.7,
            'matching_logic': ['HistoryType=3 indicates transfer or NSF']
        }
        
        comment = str(row.get('Comment', '')).upper()
        amount = Decimal(str(row['Amount']))
        
        # Check if it's an NSF
        if any(re.search(pattern, comment) for pattern in self.nsf_patterns):
            result['business_event'] = 'NSF_RETURNED_CHECK'
            result['event_details'] = {
                'type': 'NSF - Returned Check',
                'nsf_amount': float(amount),
                'check_info': comment,
                'impact': 'Increases customer balance'
            }
            result['confidence'] = 0.95
            result['matching_logic'].append('Comment contains NSF keywords')
        
        # Check for transfer
        elif row.get('TransferArID'):
            if amount > 0:
                result['business_event'] = 'TRANSFER_IN'
                result['event_details'] = {
                    'type': 'Transfer In',
                    'from_ar_id': row['TransferArID'],
                    'amount': float(amount)
                }
            else:
                result['business_event'] = 'TRANSFER_OUT'
                result['event_details'] = {
                    'type': 'Transfer Out',
                    'to_ar_id': row['TransferArID'],
                    'amount': float(amount)
                }
            result['confidence'] = 0.9
            result['matching_logic'].append('TransferArID indicates balance transfer')
        
        return result
    
    def _decode_writeoff(self, row: pd.Series) -> dict:
        """Decode HistoryType 4 - Write-off"""
        
        return {
            'business_event': 'WRITE_OFF',
            'confidence': 0.9,
            'event_details': {
                'type': 'Bad Debt Write-off',
                'amount': float(row['Amount']),
                'reason': row.get('Comment', 'Bad debt')
            },
            'matching_logic': ['HistoryType=4 indicates write-off']
        }
    
    def _decode_other(self, row: pd.Series) -> dict:
        """Decode HistoryType 5 - Other"""
        
        result = {
            'business_event': 'OTHER',
            'confidence': 0.6,
            'matching_logic': ['HistoryType=5 indicates other/miscellaneous']
        }
        
        comment = str(row.get('Comment', '')).upper()
        amount = Decimal(str(row['Amount']))
        
        # Check for NSF (many NSFs are coded as type 5)
        if any(re.search(pattern, comment) for pattern in self.nsf_patterns):
            result['business_event'] = 'NSF_RETURNED_CHECK'
            result['event_details'] = {
                'type': 'NSF - Returned Check',
                'nsf_amount': float(amount),
                'check_info': comment
            }
            result['confidence'] = 0.95
            result['matching_logic'].append('Comment indicates NSF despite HistoryType=5')
        
        # Check for fees
        elif any(re.search(pattern, comment) for pattern in self.fee_patterns):
            result['business_event'] = 'FEE_CHARGE'
            result['event_details'] = {
                'type': 'Fee/Penalty',
                'fee_amount': float(amount),
                'fee_description': comment
            }
            result['confidence'] = 0.9
            result['matching_logic'].append('Comment indicates fee/penalty')
        
        # Generic other
        else:
            result['event_details'] = {
                'type': 'Miscellaneous',
                'description': comment,
                'amount': float(amount)
            }
        
        return result
    
    def _generate_summary(self, decoded_entries: list, unmatched_entries: list) -> dict:
        """Generate summary of decoded events"""
        
        # Count by business event type
        event_counts = {}
        total_amounts = {}
        
        for entry in decoded_entries + unmatched_entries:
            event_type = entry['business_event']
            amount = entry['amount']
            
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            total_amounts[event_type] = total_amounts.get(event_type, Decimal('0.00')) + amount
        
        # Calculate confidence statistics
        total_entries = len(decoded_entries) + len(unmatched_entries)
        high_confidence = len([e for e in decoded_entries if e['confidence'] >= 0.9])
        medium_confidence = len([e for e in decoded_entries if 0.7 <= e['confidence'] < 0.9])
        low_confidence = len([e for e in decoded_entries if e['confidence'] < 0.7]) + len(unmatched_entries)
        
        return {
            'total_entries': total_entries,
            'successfully_decoded': len(decoded_entries),
            'unmatched': len(unmatched_entries),
            'confidence_breakdown': {
                'high_confidence': high_confidence,
                'medium_confidence': medium_confidence,
                'low_confidence': low_confidence
            },
            'event_type_summary': {
                event_type: {
                    'count': event_counts[event_type],
                    'total_amount': float(total_amounts[event_type])
                }
                for event_type in event_counts
            }
        }
    
    def export_decoded_history(self, customer_id: int, filename: str = None) -> str:
        """Export decoded history to detailed report"""
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"decoded_ar_history_{customer_id}_{timestamp}.csv"
        
        decoded_result = self.decode_customer_history(customer_id)
        
        if 'error' in decoded_result:
            print(f"❌ Error: {decoded_result['error']}")
            return None
        
        # Flatten data for CSV export
        csv_data = []
        
        for entry in decoded_result['decoded_entries'] + decoded_result['unmatched_entries']:
            csv_row = {
                'AR_History_ID': entry['ar_history_id'],
                'Date': entry['date'],
                'Amount': float(entry['amount']),
                'History_Type': entry['history_type'],
                'Business_Event': entry['business_event'],
                'Confidence': entry['confidence'],
                'Comment': entry['comment'],
                'Transaction_Number': entry.get('transaction_number'),
                'Payment_ID': entry.get('payment_id'),
                'Event_Details': str(entry['event_details']),
                'Matching_Logic': '; '.join(entry['matching_logic'])
            }
            csv_data.append(csv_row)
        
        # Create DataFrame and export
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False)
        
        print(f"📄 Decoded history exported to: {filename}")
        return filename

def demonstrate_ar_history_decoding():
    """
    Demonstrate AR History decoding process
    """
    
    print("🔍 AR HISTORY DECODER DEMONSTRATION")
    print("=" * 70)
    print("Reverse engineering business events from AccountReceivableHistory")
    print("=" * 70)
    
    decoder = ARHistoryDecoder()
    customer_id = 4915  # 5 Star Food Mart Somani
    
    try:
        # Decode the history
        result = decoder.decode_customer_history(customer_id)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"\n📊 DECODING RESULTS:")
        print(f"Customer ID: {result['customer_id']}")
        print(f"Total AR History Entries: {result['total_entries']}")
        print(f"Successfully Decoded: {result['successfully_decoded']}")
        print(f"Unmatched/Low Confidence: {len(result['unmatched_entries'])}")
        
        # Show confidence breakdown
        conf = result['summary']['confidence_breakdown']
        print(f"\n🎯 CONFIDENCE BREAKDOWN:")
        print(f"High Confidence (≥90%): {conf['high_confidence']}")
        print(f"Medium Confidence (70-89%): {conf['medium_confidence']}")
        print(f"Low Confidence (<70%): {conf['low_confidence']}")
        
        # Show event type summary
        print(f"\n📋 BUSINESS EVENT SUMMARY:")
        for event_type, data in result['summary']['event_type_summary'].items():
            print(f"{event_type:<25}: {data['count']:>3} events | ${data['total_amount']:>12,.2f}")
        
        # Show sample decoded entries
        print(f"\n🔍 SAMPLE DECODED ENTRIES (first 10):")
        print("-" * 80)
        
        sample_entries = result['decoded_entries'][:10]
        for entry in sample_entries:
            confidence_indicator = "🟢" if entry['confidence'] >= 0.9 else "🟡" if entry['confidence'] >= 0.7 else "🔴"
            print(f"{confidence_indicator} {entry['date'].strftime('%Y-%m-%d')} | {entry['business_event']:<20} | ${entry['amount']:>10,.2f}")
            print(f"   {entry['comment'][:60]}")
            if entry['event_details']:
                print(f"   Details: {str(entry['event_details'])[:80]}")
            print()
        
        # Export detailed report
        print(f"📄 EXPORTING DETAILED REPORT:")
        export_file = decoder.export_decoded_history(customer_id)
        
        print(f"\n" + "="*70)
        print("💡 KEY INSIGHTS FROM DECODING:")
        print("="*70)
        print("1. AR History can be reverse engineered into business events")
        print("2. Comment analysis is crucial for accurate classification")
        print("3. HistoryType provides good starting point but isn't always reliable")
        print("4. Cross-referencing with Transaction/Payment tables improves accuracy")
        print("5. NSFs often appear as HistoryType 5 (Other) rather than 3 (Transfer)")
        print("6. Pattern matching on comments reveals true business meaning")
        
        print(f"\n🔧 PRACTICAL APPLICATIONS:")
        print("- Data migration from legacy systems")
        print("- Audit trail reconstruction")  
        print("- Business intelligence and reporting")
        print("- Compliance and regulatory reporting")
        print("- Customer dispute resolution")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demonstrate_ar_history_decoding()
