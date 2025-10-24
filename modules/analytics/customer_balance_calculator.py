#!/usr/bin/env python3
"""
Customer Balance Calculator - Production Implementation
Demonstrates the deep logic for calculating customer AR balances accurately
"""

import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from database_pymssql import quick_query
import logging
from datetime import datetime
from typing import Tuple, Optional, Dict, List
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerBalanceCalculator:
    """
    Production-ready customer balance calculator using AccountReceivableHistory
    
    This class implements the definitive methodology for calculating customer
    AR balances by using the AccountReceivableHistory table as the single
    source of truth.
    """
    
    # History type constants for readability
    HISTORY_TYPES = {
        0: "INVOICE_CREATED",
        1: "ADJUSTMENT", 
        2: "PAYMENT_APPLIED",
        3: "TRANSFER_NSF",
        4: "WRITE_OFF",
        5: "OTHER_FEES"
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def calculate_balance(self, customer_id: int, include_timeline: bool = False) -> Dict:
        """
        Calculate current AR balance for customer using AccountReceivableHistory
        
        Args:
            customer_id: Customer ID to calculate balance for
            include_timeline: Whether to include detailed transaction timeline
            
        Returns:
            Dict containing:
                - current_balance: Decimal current AR balance
                - transaction_count: Number of AR history entries
                - first_transaction: Date of first transaction
                - last_transaction: Date of last transaction  
                - timeline: List of transactions (if include_timeline=True)
                - verification: Verification against AR table
                
        Raises:
            ValueError: If customer_id is invalid
            DatabaseError: If query fails
        """
        
        self.logger.info(f"Calculating balance for customer {customer_id}")
        
        # Validate input
        if not isinstance(customer_id, int) or customer_id <= 0:
            raise ValueError(f"Invalid customer_id: {customer_id}")
            
        try:
            # Get customer info
            customer_info = self._get_customer_info(customer_id)
            if customer_info is None:
                raise ValueError(f"Customer {customer_id} not found")
                
            # Get all AR history for customer
            history_records = self._get_ar_history(customer_id)
            
            if history_records.empty:
                self.logger.info(f"No AR history found for customer {customer_id}")
                return {
                    'customer_id': customer_id,
                    'customer_name': customer_info['name'],
                    'current_balance': Decimal('0.00'),
                    'transaction_count': 0,
                    'first_transaction': None,
                    'last_transaction': None,
                    'timeline': [],
                    'verification': {'status': 'passed', 'difference': Decimal('0.00')}
                }
                
            # Calculate running balance and build timeline
            result = self._process_history_records(history_records, include_timeline)
            
            # Verify against current AR table
            verification = self._verify_balance(customer_id, result['current_balance'])
            
            # Build final result
            final_result = {
                'customer_id': customer_id,
                'customer_name': customer_info['name'],
                'current_balance': result['current_balance'],
                'transaction_count': result['transaction_count'],
                'first_transaction': result['first_transaction'],
                'last_transaction': result['last_transaction'],
                'verification': verification
            }
            
            if include_timeline:
                final_result['timeline'] = result['timeline']
                
            self.logger.info(f"Balance calculation completed: ${result['current_balance']:,.2f}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error calculating balance for customer {customer_id}: {e}")
            raise
            
    def _get_customer_info(self, customer_id: int) -> Optional[Dict]:
        """Get basic customer information"""
        
        query = """
        SELECT 
            ID,
            AccountNumber,
            Company,
            FirstName,
            LastName
        FROM [dbo].[Customer]
        WHERE ID = %s
        """
        
        result = quick_query(query, (customer_id,))
        
        if result.empty:
            return None
            
        row = result.iloc[0]
        company = row.get('Company', '')
        name = f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip()
        
        return {
            'id': row['ID'],
            'account_number': row.get('AccountNumber', ''),
            'name': company if company else name if name else f"Customer {customer_id}"
        }
        
    def _get_ar_history(self, customer_id: int) -> pd.DataFrame:
        """
        Get all AccountReceivableHistory records for customer
        
        This is the core query that retrieves the complete audit trail
        of all AR movements for the customer.
        """
        
        query = """
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
            ar.Type as ARType
        FROM [dbo].[AccountReceivableHistory] arh WITH (NOLOCK)
        JOIN [dbo].[AccountReceivable] ar WITH (NOLOCK) 
            ON arh.AccountReceivableID = ar.ID
        WHERE ar.CustomerID = %s
        ORDER BY arh.Date ASC, arh.ID ASC
        """
        
        self.logger.debug(f"Executing AR history query for customer {customer_id}")
        return quick_query(query, (customer_id,))
        
    def _process_history_records(self, history_records: pd.DataFrame, include_timeline: bool) -> Dict:
        """
        Process AR history records to calculate running balance
        
        This is where the core calculation logic happens:
        1. Start with $0.00 balance
        2. For each history record in chronological order:
           - Add the amount to running balance
           - Track transaction details
        3. Final running balance = Current AR balance
        """
        
        running_balance = Decimal('0.00')
        timeline = []
        transaction_count = 0
        first_transaction = None
        last_transaction = None
        
        self.logger.debug(f"Processing {len(history_records)} history records")
        
        for _, record in history_records.iterrows():
            # Convert amount to Decimal for precise arithmetic
            amount = Decimal(str(record['Amount']))
            running_balance += amount
            transaction_count += 1
            
            # Track date range
            transaction_date = record['Date']
            if first_transaction is None:
                first_transaction = transaction_date
            last_transaction = transaction_date
            
            # Build timeline entry if requested
            if include_timeline:
                timeline_entry = self._build_timeline_entry(record, amount, running_balance)
                timeline.append(timeline_entry)
                
            # Log significant transactions
            if abs(amount) >= 1000:
                self.logger.debug(
                    f"Large transaction: {transaction_date} | "
                    f"Type {self._get_history_type_name(record['HistoryType'])} | "
                    f"Amount ${amount:,.2f} | "
                    f"Balance ${running_balance:,.2f}"
                )
                
        return {
            'current_balance': running_balance,
            'transaction_count': transaction_count,
            'first_transaction': first_transaction,
            'last_transaction': last_transaction,
            'timeline': timeline
        }
        
    def _build_timeline_entry(self, record: pd.Series, amount: Decimal, running_balance: Decimal) -> Dict:
        """Build detailed timeline entry for a history record"""
        
        return {
            'id': record['ID'],
            'date': record['Date'].isoformat() if pd.notna(record['Date']) else None,
            'type': self._get_history_type_name(record['HistoryType']),
            'type_code': record['HistoryType'],
            'amount': float(amount),
            'running_balance': float(running_balance),
            'comment': record.get('Comment', ''),
            'transaction_number': record.get('TransactionNumber'),
            'ar_id': record['AccountReceivableID'],
            'payment_id': record.get('PaymentID'),
            'cashier_id': record.get('CashierID'),
            'transfer_ar_id': record.get('TransferArID'),
            'ar_original_amount': float(record.get('AROriginalAmount', 0))
        }
        
    def _verify_balance(self, customer_id: int, calculated_balance: Decimal) -> Dict:
        """
        Verify calculated balance against current AR table
        
        This provides a critical validation check to ensure our calculation
        matches the current state in the AccountReceivable table.
        """
        
        query = """
        SELECT 
            ISNULL(SUM(ar.Balance), 0) as CurrentARBalance,
            COUNT(*) as ActiveARRecords
        FROM [dbo].[AccountReceivable] ar WITH (NOLOCK)
        WHERE ar.CustomerID = %s
          AND ar.Balance != 0
        """
        
        result = quick_query(query, (customer_id,))
        current_ar_balance = Decimal(str(result.iloc[0]['CurrentARBalance']))
        active_records = result.iloc[0]['ActiveARRecords']
        
        difference = calculated_balance - current_ar_balance
        
        # Allow for small rounding differences (< 1 cent)
        verification_passed = abs(difference) < Decimal('0.01')
        
        if not verification_passed:
            self.logger.warning(
                f"Balance verification failed for customer {customer_id}: "
                f"Calculated ${calculated_balance:,.2f} vs AR ${current_ar_balance:,.2f} "
                f"(difference: ${difference:,.2f})"
            )
        else:
            self.logger.debug(f"Balance verification passed: ${calculated_balance:,.2f}")
            
        return {
            'status': 'passed' if verification_passed else 'failed',
            'calculated_balance': float(calculated_balance),
            'ar_table_balance': float(current_ar_balance),
            'difference': float(difference),
            'active_ar_records': active_records
        }
        
    def _get_history_type_name(self, history_type: int) -> str:
        """Convert history type number to readable name"""
        return self.HISTORY_TYPES.get(history_type, f"UNKNOWN_{history_type}")
        
    def analyze_customer_patterns(self, customer_id: int) -> Dict:
        """
        Analyze customer payment and transaction patterns
        
        This provides insights into customer behavior:
        - NSF frequency and amounts
        - Payment patterns
        - Adjustment history
        - Balance trends
        """
        
        self.logger.info(f"Analyzing patterns for customer {customer_id}")
        
        # Get full timeline
        result = self.calculate_balance(customer_id, include_timeline=True)
        timeline = result['timeline']
        
        if not timeline:
            return {'error': 'No transaction history available'}
            
        # Analyze patterns
        patterns = {
            'total_transactions': len(timeline),
            'date_range': {
                'first': result['first_transaction'].isoformat() if result['first_transaction'] else None,
                'last': result['last_transaction'].isoformat() if result['last_transaction'] else None
            },
            'balance_summary': {
                'current': result['current_balance'],
                'peak': max(entry['running_balance'] for entry in timeline),
                'lowest': min(entry['running_balance'] for entry in timeline)
            }
        }
        
        # Analyze by transaction type
        type_analysis = {}
        for entry in timeline:
            type_name = entry['type']
            if type_name not in type_analysis:
                type_analysis[type_name] = {
                    'count': 0,
                    'total_amount': 0.0,
                    'avg_amount': 0.0
                }
            
            type_analysis[type_name]['count'] += 1
            type_analysis[type_name]['total_amount'] += entry['amount']
            
        # Calculate averages
        for type_name, data in type_analysis.items():
            data['avg_amount'] = data['total_amount'] / data['count'] if data['count'] > 0 else 0.0
            
        patterns['transaction_types'] = type_analysis
        
        # NSF Analysis
        nsf_entries = [e for e in timeline if 'NSF' in e['comment'].upper()]
        patterns['nsf_analysis'] = {
            'total_nsf_events': len(nsf_entries),
            'total_nsf_amount': sum(e['amount'] for e in nsf_entries),
            'avg_nsf_amount': sum(e['amount'] for e in nsf_entries) / len(nsf_entries) if nsf_entries else 0
        }
        
        # Recent activity (last 90 days)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(days=90)
        recent_entries = [
            e for e in timeline 
            if e['date'] and datetime.fromisoformat(e['date']) >= recent_cutoff
        ]
        
        patterns['recent_activity'] = {
            'transactions_last_90_days': len(recent_entries),
            'balance_change_last_90_days': recent_entries[-1]['running_balance'] - recent_entries[0]['running_balance'] if len(recent_entries) >= 2 else 0
        }
        
        return patterns
        
    def export_customer_report(self, customer_id: int, filename: Optional[str] = None) -> str:
        """
        Export comprehensive customer balance report to JSON file
        
        Args:
            customer_id: Customer to export report for
            filename: Optional filename, defaults to customer_balance_report_{id}.json
            
        Returns:
            str: Filename of exported report
        """
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"customer_balance_report_{customer_id}_{timestamp}.json"
            
        # Generate comprehensive report
        balance_result = self.calculate_balance(customer_id, include_timeline=True)
        patterns = self.analyze_customer_patterns(customer_id)
        
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'customer_id': customer_id,
                'report_type': 'comprehensive_balance_analysis'
            },
            'balance_calculation': balance_result,
            'customer_patterns': patterns,
            'methodology': {
                'calculation_method': 'AccountReceivableHistory sum',
                'verification': 'Against current AR table',
                'precision': 'Decimal arithmetic',
                'data_source': 'Complete AR audit trail'
            }
        }
        
        # Convert Decimal and Timestamp objects for JSON serialization
        def json_converter(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif hasattr(obj, 'isoformat'):  # datetime/timestamp objects
                return obj.isoformat()
            elif hasattr(obj, 'item'):  # numpy types
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy arrays
                return obj.tolist()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=json_converter)
            
        self.logger.info(f"Customer report exported to {filename}")
        return filename

def demo_calculation_logic():
    """
    Demonstration of the customer balance calculation logic
    """
    
    print("🔍 CUSTOMER BALANCE CALCULATION DEMONSTRATION")
    print("=" * 70)
    
    # Initialize calculator
    calculator = CustomerBalanceCalculator()
    
    # Example customer (5 Star Food Mart Somani)
    customer_id = 4915
    
    try:
        # Calculate balance with timeline
        print(f"\n📊 Calculating balance for customer {customer_id}...")
        result = calculator.calculate_balance(customer_id, include_timeline=True)
        
        print(f"\n✅ RESULTS:")
        print(f"Customer: {result['customer_name']}")
        print(f"Current Balance: ${result['current_balance']:,.2f}")
        print(f"Transaction Count: {result['transaction_count']:,}")
        print(f"Date Range: {result['first_transaction']} to {result['last_transaction']}")
        print(f"Verification: {result['verification']['status'].upper()}")
        
        if result['verification']['status'] == 'failed':
            print(f"  ⚠️  Difference: ${result['verification']['difference']:,.2f}")
        
        # Show sample timeline entries
        if result['timeline']:
            print(f"\n📋 SAMPLE TIMELINE ENTRIES (first 10):")
            print("-" * 60)
            for i, entry in enumerate(result['timeline'][:10]):
                print(f"{entry['date'][:10]} | {entry['type']:<15} | ${entry['amount']:>10,.2f} | ${entry['running_balance']:>12,.2f}")
            
            if len(result['timeline']) > 10:
                print(f"... and {len(result['timeline']) - 10} more entries")
        
        # Analyze patterns
        print(f"\n📈 CUSTOMER PATTERN ANALYSIS:")
        patterns = calculator.analyze_customer_patterns(customer_id)
        
        print(f"Balance Range: ${patterns['balance_summary']['lowest']:,.2f} to ${patterns['balance_summary']['peak']:,.2f}")
        print(f"NSF Events: {patterns['nsf_analysis']['total_nsf_events']}")
        print(f"NSF Amount: ${patterns['nsf_analysis']['total_nsf_amount']:,.2f}")
        print(f"Recent Activity: {patterns['recent_activity']['transactions_last_90_days']} transactions in last 90 days")
        
        # Export report
        print(f"\n📄 EXPORTING COMPREHENSIVE REPORT:")
        report_file = calculator.export_customer_report(customer_id)
        print(f"Report saved to: {report_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print(f"\n" + "=" * 70)
    print("💡 KEY INSIGHTS:")
    print("- AccountReceivableHistory is the single source of truth")
    print("- Running balance calculation accounts for all business logic")
    print("- Verification against AR table ensures accuracy")
    print("- Timeline provides complete audit trail")
    print("- Pattern analysis reveals customer behavior")

if __name__ == "__main__":
    demo_calculation_logic()
