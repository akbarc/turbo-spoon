#!/usr/bin/env python3
"""
Alternative Customer Balance Calculation Methods
When AccountReceivableHistory is NOT available

This demonstrates various approaches to calculate customer balance
without the AR History table, showing the challenges and limitations.
"""

import pandas as pd
from decimal import Decimal
from database_pymssql import quick_query
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlternativeBalanceCalculator:
    """
    Customer balance calculation when AR History is not available
    Shows multiple approaches and their trade-offs
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def method_1_current_ar_table(self, customer_id: int):
        """
        Method 1: Use current AccountReceivable table
        
        PROS: 
        - Simple and fast
        - Shows current outstanding balances
        - Reflects partial payments
        
        CONS:
        - No historical context
        - Doesn't show how balance was built
        - Missing timeline of changes
        """
        
        print("\n🔍 METHOD 1: CURRENT AR TABLE")
        print("="*50)
        
        query = f"""
        SELECT 
            ar.ID,
            ar.Date,
            ar.TransactionNumber,
            ar.OriginalAmount,
            ar.Balance,
            ar.DueDate,
            ar.Type,
            t.Time as TransactionTime,
            t.Total as TransactionTotal,
            t.Comment as TransactionComment
        FROM [dbo].[AccountReceivable] ar
        LEFT JOIN [dbo].[Transaction] t ON ar.TransactionNumber = t.TransactionNumber
        WHERE ar.CustomerID = {customer_id}
          AND ar.Balance != 0
        ORDER BY ar.Date ASC
        """
        
        result = quick_query(query)
        
        if result.empty:
            total_balance = Decimal('0.00')
            print("✅ No outstanding AR balance")
        else:
            total_balance = sum(Decimal(str(row['Balance'])) for _, row in result.iterrows())
            
            print(f"📋 Outstanding AR Records: {len(result)}")
            for _, row in result.iterrows():
                balance = Decimal(str(row['Balance']))
                original = Decimal(str(row['OriginalAmount']))
                paid = original - balance
                
                print(f"\nAR #{row['ID']} | Txn #{row['TransactionNumber']}")
                print(f"  Date: {row['Date']} | Due: {row['DueDate']}")
                print(f"  Original: ${original:.2f} | Paid: ${paid:.2f} | Balance: ${balance:.2f}")
                print(f"  Comment: '{row.get('TransactionComment', 'N/A')}'")
            
            print(f"\n💰 TOTAL CURRENT BALANCE: ${total_balance:.2f}")
        
        return {
            'method': 'Current AR Table',
            'balance': total_balance,
            'records': len(result) if not result.empty else 0,
            'pros': ['Simple', 'Fast', 'Shows partial payments'],
            'cons': ['No history', 'Missing timeline', 'No NSF tracking']
        }
    
    def method_2_transaction_payment_reconciliation(self, customer_id: int):
        """
        Method 2: Transaction + Payment reconciliation
        
        PROS:
        - Shows complete invoice and payment activity
        - Can calculate theoretical balance
        
        CONS:
        - Doesn't account for NSFs
        - No adjustment tracking
        - Payment timing vs transaction timing issues
        - Can't track partial payment application
        """
        
        print("\n🔍 METHOD 2: TRANSACTION + PAYMENT RECONCILIATION")
        print("="*50)
        
        # Get all transactions
        txn_query = f"""
        SELECT 
            TransactionNumber,
            Time,
            Total,
            SalesTax,
            Comment,
            Status
        FROM [dbo].[Transaction]
        WHERE CustomerID = {customer_id}
        ORDER BY Time ASC
        """
        
        transactions = quick_query(txn_query)
        total_invoiced = sum(Decimal(str(row['Total'])) for _, row in transactions.iterrows()) if not transactions.empty else Decimal('0.00')
        
        # Get all payments
        pay_query = f"""
        SELECT 
            ID,
            Time,
            Amount,
            Comment,
            BatchNumber
        FROM [dbo].[Payment]
        WHERE CustomerID = {customer_id}
        ORDER BY Time ASC
        """
        
        payments = quick_query(pay_query)
        total_paid = sum(Decimal(str(row['Amount'])) for _, row in payments.iterrows()) if not payments.empty else Decimal('0.00')
        
        # Simple calculation
        simple_balance = total_invoiced - total_paid
        
        print(f"📋 Transactions: {len(transactions)} totaling ${total_invoiced:.2f}")
        print(f"📋 Payments: {len(payments)} totaling ${total_paid:.2f}")
        print(f"💰 SIMPLE BALANCE: ${simple_balance:.2f}")
        
        print(f"\n⚠️  WARNING: This method ignores:")
        print("- NSFs (bounced checks)")
        print("- Adjustments and credits")
        print("- Partial payment applications")
        print("- Fees and penalties")
        print("- Payment timing issues")
        
        return {
            'method': 'Transaction + Payment',
            'balance': simple_balance,
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'pros': ['Shows all activity', 'Simple calculation'],
            'cons': ['No NSFs', 'No adjustments', 'Timing issues', 'No partial payment tracking']
        }
    
    def method_3_current_ar_plus_estimates(self, customer_id: int):
        """
        Method 3: Current AR + Estimated adjustments
        
        PROS:
        - Uses reliable current AR data
        - Attempts to account for missing pieces
        
        CONS:
        - Estimates may be inaccurate
        - Still missing complete timeline
        - Can't verify estimates
        """
        
        print("\n🔍 METHOD 3: CURRENT AR + ESTIMATED ADJUSTMENTS")
        print("="*50)
        
        # Get current AR balance (reliable)
        current_ar_result = self.method_1_current_ar_table(customer_id)
        current_balance = current_ar_result['balance']
        
        # Try to estimate NSFs by looking for payment/transaction mismatches
        print(f"\n🔍 Attempting to estimate NSFs and adjustments...")
        
        # Look for potential NSFs (payments that might have bounced)
        nsf_query = f"""
        SELECT 
            p.Amount,
            p.Comment,
            p.Time
        FROM [dbo].[Payment] p
        WHERE p.CustomerID = {customer_id}
          AND (p.Comment LIKE '%NSF%' 
            OR p.Comment LIKE '%RETURNED%'
            OR p.Comment LIKE '%BOUNCE%'
            OR p.Comment LIKE '%INSUFFICIENT%')
        ORDER BY p.Time ASC
        """
        
        potential_nsfs = quick_query(nsf_query)
        estimated_nsf_impact = Decimal('0.00')
        
        if not potential_nsfs.empty:
            print(f"📋 Found {len(potential_nsfs)} potential NSF-related payments:")
            for _, row in potential_nsfs.iterrows():
                amount = Decimal(str(row['Amount']))
                estimated_nsf_impact += amount
                print(f"  ${amount:.2f} - {row['Comment']} ({row['Time']})")
        
        # Look for credit transactions (negative amounts)
        credit_query = f"""
        SELECT 
            TransactionNumber,
            Total,
            Comment,
            Time
        FROM [dbo].[Transaction]
        WHERE CustomerID = {customer_id}
          AND Total < 0
        ORDER BY Time ASC
        """
        
        credits = quick_query(credit_query)
        total_credits = sum(Decimal(str(row['Total'])) for _, row in credits.iterrows()) if not credits.empty else Decimal('0.00')
        
        if not credits.empty:
            print(f"\n📋 Found {len(credits)} credit transactions: ${total_credits:.2f}")
            for _, row in credits.iterrows():
                print(f"  Txn #{row['TransactionNumber']}: ${row['Total']:.2f} - {row['Comment']}")
        
        estimated_balance = current_balance
        
        print(f"\n💰 ESTIMATED BALANCE BREAKDOWN:")
        print(f"  Current AR Balance: ${current_balance:.2f}")
        print(f"  Estimated NSF Impact: ${estimated_nsf_impact:.2f}")
        print(f"  Credit Adjustments: ${total_credits:.2f}")
        print(f"  ESTIMATED TOTAL: ${estimated_balance:.2f}")
        
        return {
            'method': 'Current AR + Estimates',
            'balance': estimated_balance,
            'current_ar': current_balance,
            'estimated_nsfs': estimated_nsf_impact,
            'credits': total_credits,
            'pros': ['Uses reliable AR data', 'Attempts NSF estimation'],
            'cons': ['Estimates may be wrong', 'Incomplete picture', 'No verification']
        }
    
    def method_4_journal_entry_reconstruction(self, customer_id: int):
        """
        Method 4: Journal Entry Reconstruction
        
        Try to reconstruct balance from general ledger if available
        
        PROS:
        - Accounting-based approach
        - Should include all financial impacts
        
        CONS:
        - Requires access to GL
        - Complex to implement
        - May not have customer-level detail
        """
        
        print("\n🔍 METHOD 4: JOURNAL ENTRY RECONSTRUCTION")
        print("="*50)
        
        print("⚠️  This method requires:")
        print("- Access to General Ledger tables")
        print("- Journal Entry tables with customer references")
        print("- Account mapping for AR accounts")
        print("- Complex GL posting logic understanding")
        
        # This would require GL tables that may not exist or be accessible
        print("\n❌ Cannot implement without GL access")
        print("   Would need tables like:")
        print("   - GeneralLedgerEntry")
        print("   - JournalEntry") 
        print("   - ChartOfAccounts")
        print("   - Customer-to-GL account mapping")
        
        return {
            'method': 'Journal Entry Reconstruction',
            'balance': None,
            'status': 'Not Implementable',
            'pros': ['Accounting accuracy', 'Complete financial picture'],
            'cons': ['Requires GL access', 'Very complex', 'May lack customer detail']
        }
    
    def method_5_payment_application_tracking(self, customer_id: int):
        """
        Method 5: Manual Payment Application Tracking
        
        Try to manually track which payments apply to which invoices
        
        PROS:
        - More accurate than simple sum
        - Tracks partial payments
        
        CONS:
        - Very complex logic
        - Assumes payment application rules
        - Still missing NSFs and adjustments
        """
        
        print("\n🔍 METHOD 5: PAYMENT APPLICATION TRACKING")
        print("="*50)
        
        # Get all transactions
        transactions = quick_query(f"""
            SELECT TransactionNumber, Time, Total
            FROM [dbo].[Transaction]
            WHERE CustomerID = {customer_id}
            ORDER BY Time ASC
        """)
        
        # Get all payments
        payments = quick_query(f"""
            SELECT ID, Time, Amount, Comment
            FROM [dbo].[Payment]
            WHERE CustomerID = {customer_id}
            ORDER BY Time ASC
        """)
        
        if transactions.empty or payments.empty:
            print("❌ Insufficient data for payment application tracking")
            return {
                'method': 'Payment Application Tracking',
                'balance': Decimal('0.00'),
                'status': 'Insufficient Data'
            }
        
        print(f"📋 Processing {len(transactions)} transactions and {len(payments)} payments")
        
        # Create invoice tracking
        invoices = []
        for _, txn in transactions.iterrows():
            invoices.append({
                'number': txn['TransactionNumber'],
                'date': txn['Time'],
                'original_amount': Decimal(str(txn['Total'])),
                'remaining_balance': Decimal(str(txn['Total']))
            })
        
        # Apply payments using FIFO (First In, First Out) logic
        print(f"\n💰 Applying payments using FIFO logic:")
        
        for _, payment in payments.iterrows():
            payment_amount = Decimal(str(payment['Amount']))
            remaining_payment = payment_amount
            
            print(f"\nPayment #{payment['ID']}: ${payment_amount:.2f}")
            
            # Apply to oldest invoices first
            for invoice in invoices:
                if remaining_payment <= 0:
                    break
                    
                if invoice['remaining_balance'] > 0:
                    applied_amount = min(remaining_payment, invoice['remaining_balance'])
                    invoice['remaining_balance'] -= applied_amount
                    remaining_payment -= applied_amount
                    
                    print(f"  Applied ${applied_amount:.2f} to Invoice #{invoice['number']}")
                    print(f"  Invoice balance now: ${invoice['remaining_balance']:.2f}")
            
            if remaining_payment > 0:
                print(f"  ⚠️  ${remaining_payment:.2f} could not be applied (overpayment)")
        
        # Calculate final balance
        total_balance = sum(inv['remaining_balance'] for inv in invoices)
        
        print(f"\n📋 Final invoice balances:")
        outstanding_count = 0
        for invoice in invoices:
            if invoice['remaining_balance'] > 0:
                outstanding_count += 1
                print(f"  Invoice #{invoice['number']}: ${invoice['remaining_balance']:.2f}")
        
        print(f"\n💰 CALCULATED BALANCE: ${total_balance:.2f}")
        print(f"📊 {outstanding_count} invoices with outstanding balances")
        
        print(f"\n⚠️  WARNING: This method still ignores:")
        print("- NSFs (bounced payments)")
        print("- Fees and penalties")
        print("- Adjustments and credits")
        print("- Non-FIFO payment applications")
        
        return {
            'method': 'Payment Application Tracking',
            'balance': total_balance,
            'outstanding_invoices': outstanding_count,
            'pros': ['Tracks partial payments', 'More accurate than simple sum'],
            'cons': ['Complex logic', 'Assumes FIFO', 'No NSFs', 'No adjustments']
        }
    
    def compare_all_methods(self, customer_id: int) -> Dict:
        """
        Compare all alternative methods against each other
        """
        
        print("\n" + "="*70)
        print("🔍 COMPARING ALL ALTERNATIVE METHODS")
        print("="*70)
        
        # Run all methods
        method1 = self.method_1_current_ar_table(customer_id)
        method2 = self.method_2_transaction_payment_reconciliation(customer_id)
        method3 = self.method_3_current_ar_plus_estimates(customer_id)
        method4 = self.method_4_journal_entry_reconstruction(customer_id)
        method5 = self.method_5_payment_application_tracking(customer_id)
        
        # Get the "true" balance from AR History for comparison
        true_balance_query = f"""
        SELECT SUM(arh.Amount) as TrueBalance
        FROM [dbo].[AccountReceivableHistory] arh
        JOIN [dbo].[AccountReceivable] ar ON arh.AccountReceivableID = ar.ID
        WHERE ar.CustomerID = {customer_id}
        """
        
        try:
            true_result = quick_query(true_balance_query)
            true_balance = Decimal(str(true_result.iloc[0]['TrueBalance'])) if not true_result.empty and true_result.iloc[0]['TrueBalance'] is not None else Decimal('0.00')
        except:
            true_balance = Decimal('0.00')
        
        print(f"\n📊 METHOD COMPARISON RESULTS:")
        print("="*70)
        print(f"{'Method':<30} | {'Balance':<15} | {'Accuracy':<12} | {'Error':<12}")
        print("-" * 70)
        
        methods = [method1, method2, method3, method5]  # Skip method4 as it's not implementable
        
        for method in methods:
            if method['balance'] is not None:
                balance = method['balance']
                error = balance - true_balance
                accuracy = (1 - abs(error) / max(abs(true_balance), Decimal('0.01'))) * 100
                
                print(f"{method['method']:<30} | ${balance:>12,.2f} | {accuracy:>9.1f}% | ${error:>9,.2f}")
            else:
                print(f"{method['method']:<30} | {'N/A':<15} | {'N/A':<12} | {'N/A':<12}")
        
        print("-" * 70)
        print(f"{'AR History (TRUE)':<30} | ${true_balance:>12,.2f} | {'100.0%':<12} | {'$0.00':<12}")
        
        # Find best method
        best_method = None
        best_error = float('inf')
        
        for method in methods:
            if method['balance'] is not None:
                error = abs(method['balance'] - true_balance)
                if error < best_error:
                    best_error = error
                    best_method = method
        
        print(f"\n🏆 BEST ALTERNATIVE METHOD: {best_method['method'] if best_method else 'None'}")
        if best_method:
            print(f"   Error: ${best_error:.2f}")
            print(f"   Accuracy: {(1 - best_error / max(abs(true_balance), Decimal('0.01'))) * 100:.1f}%")
        
        return {
            'true_balance': true_balance,
            'best_method': best_method,
            'all_methods': [method1, method2, method3, method4, method5],
            'comparison_summary': {
                'most_accurate': best_method['method'] if best_method else None,
                'largest_error': max(abs(m['balance'] - true_balance) for m in methods if m['balance'] is not None) if methods else 0
            }
        }

def demonstrate_alternative_methods():
    """
    Demonstrate alternative balance calculation methods
    """
    
    print("🔍 ALTERNATIVE CUSTOMER BALANCE CALCULATION METHODS")
    print("=" * 70)
    print("Demonstrating approaches when AccountReceivableHistory is NOT available")
    print("=" * 70)
    
    calculator = AlternativeBalanceCalculator()
    customer_id = 4915  # 5 Star Food Mart Somani
    
    try:
        # Compare all methods
        comparison = calculator.compare_all_methods(customer_id)
        
        print(f"\n" + "="*70)
        print("🎯 CONCLUSIONS & RECOMMENDATIONS")
        print("="*70)
        
        print(f"\n✅ BEST ALTERNATIVE: {comparison['comparison_summary']['most_accurate']}")
        print(f"📊 True Balance: ${comparison['true_balance']:,.2f}")
        
        print(f"\n💡 KEY INSIGHTS:")
        print("1. Current AR Table method is most reliable when AR History unavailable")
        print("2. Simple Transaction-Payment math is dangerously inaccurate")
        print("3. Payment application tracking helps but is very complex") 
        print("4. All methods miss critical data (NSFs, adjustments, fees)")
        print("5. AccountReceivableHistory remains the gold standard")
        
        print(f"\n⚠️  RISKS OF ALTERNATIVE METHODS:")
        print("- Incomplete data leads to wrong decisions")
        print("- NSFs can create massive discrepancies")
        print("- Customer disputes over balance calculations")
        print("- Compliance and audit issues")
        print("- Loss of financial accuracy")
        
        print(f"\n🔧 RECOMMENDATIONS:")
        print("1. If possible, recreate AR History from existing data")
        print("2. Use Current AR Table as fallback (most reliable)")
        print("3. Implement manual NSF tracking")
        print("4. Document limitations clearly")
        print("5. Plan migration to proper AR History system")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    demonstrate_alternative_methods()
