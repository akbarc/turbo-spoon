#!/usr/bin/env python3
"""
Customer Ledger - Production Version
Complete redesign with proper reference numbers, standardized descriptions, and accurate tender types
Maintains accurate running balance that starts from 0 and matches current AR
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_pymssql import SQLServerConnection
from datetime import datetime, timedelta
import pandas as pd
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AccurateCustomerLedger:
    """
    Production customer ledger with comprehensive transaction details
    """
    
    def __init__(self):
        self.db = SQLServerConnection()
        
    def get_complete_ledger(self, customer_id: int, days_back: Optional[int] = None) -> Dict[str, Any]:
        """
        Get complete customer ledger with proper details
        """
        try:
            # Get customer information
            customer_info = self._get_customer_info(customer_id)
            if customer_info.empty:
                return {'error': f'Customer {customer_id} not found'}
            
            # Get ALL history for accurate balance calculation
            all_entries = self._get_comprehensive_history(customer_id)
            
            # Calculate running balance on ALL entries
            all_with_balance = self._calculate_running_balance(all_entries)
            
            # Filter to requested period if specified
            if days_back is not None:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                ledger_with_balance = all_with_balance[
                    pd.to_datetime(all_with_balance['TransactionDate']) >= cutoff_date
                ].copy()
            else:
                ledger_with_balance = all_with_balance
            
            # Get current AR balance for verification
            current_ar_balance = self._get_current_ar_balance(customer_id)
            
            # Verify calculation
            if not ledger_with_balance.empty:
                most_recent_balance = ledger_with_balance.iloc[0]['RunningBalance']
                calculated_balance = most_recent_balance
            else:
                calculated_balance = 0
            
            balance_matches = abs(float(calculated_balance) - float(current_ar_balance)) < 0.01
            
            # Get active AR records
            active_ar = self._get_active_ar_records(customer_id)
            
            # Calculate summary
            summary = self._calculate_summary(ledger_with_balance, current_ar_balance, active_ar)
            
            return {
                'customer_info': customer_info.iloc[0].to_dict(),
                'ledger': ledger_with_balance.to_dict('records'),
                'active_ar': active_ar.to_dict('records'),
                'summary': summary,
                'verification': {
                    'calculated_balance': float(calculated_balance),
                    'current_ar_balance': float(current_ar_balance),
                    'balance_matches': balance_matches,
                    'starting_balance': 0.00,
                    'ending_balance': float(calculated_balance)
                },
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'days_included': days_back if days_back else 'all',
                    'record_count': len(ledger_with_balance)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating ledger for customer {customer_id}: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def get_ledger(self, customer_id: int, days_back: Optional[int] = None) -> Dict[str, Any]:
        """Backward compatibility method"""
        return self.get_complete_ledger(customer_id, days_back)
    
    def _get_customer_info(self, customer_id: int) -> pd.DataFrame:
        """Get customer information"""
        query = """
        SELECT 
            c.ID,
            c.AccountNumber,
            c.Company,
            c.FirstName,
            c.LastName,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.PhoneNumber,
            c.EmailAddress,
            c.CreditLimit,
            c.TaxExempt,
            c.Notes,
            c.AccountBalance
        FROM Customer c
        WHERE c.ID = %s
        """
        return self.db.execute_query(query, (customer_id,))
    
    def _get_comprehensive_history(self, customer_id: int) -> pd.DataFrame:
        """
        Get comprehensive transaction history with all details
        SQL Server 2008 compatible version
        """
        query = f"""
        WITH CompleteLedger AS (
            -- 1. SALES TRANSACTIONS (Invoices) WITH TENDER TYPES
            SELECT 
                arh.Date as TransactionDate,
                'SALE' as TransactionType,
                'Invoice' as Category,
                CAST(ar.TransactionNumber as VARCHAR(20)) as ReferenceNumber,
                'Invoice #' + CAST(ar.TransactionNumber as VARCHAR) + ' - $' + 
                    CONVERT(VARCHAR, CAST(ar.OriginalAmount as MONEY), 1) as StandardDescription,
                ISNULL(t.Comment, '') as Comments,
                -- Get tender types used for this sale transaction
                ISNULL(
                    STUFF((
                        SELECT DISTINCT ', ' + td.Description
                        FROM TenderEntry te
                        INNER JOIN Tender td ON te.TenderID = td.ID
                        WHERE te.TransactionNumber = ar.TransactionNumber
                        FOR XML PATH(''), TYPE
                    ).value('.', 'NVARCHAR(MAX)'), 1, 2, ''),
                    -- Fallback to parsing comment
                    CASE 
                        WHEN t.Comment LIKE '%COD%' THEN 'COD'
                        WHEN t.Comment LIKE '%CASH%' THEN 'CASH'
                        ELSE ''
                    END
                ) as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                1 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            LEFT JOIN [Transaction] t ON ar.TransactionNumber = t.TransactionNumber
            WHERE ar.CustomerID = {customer_id}
              AND arh.HistoryType = 0
              AND ar.TransactionNumber IS NOT NULL
              AND ar.TransactionNumber > 0
            
            UNION ALL
            
            -- 2. DIRECT CHARGES
            SELECT 
                arh.Date as TransactionDate,
                'CHARGE' as TransactionType,
                'Direct Charge' as Category,
                'DC-' + CAST(ar.ID as VARCHAR(20)) as ReferenceNumber,
                'Direct AR Charge #' + CAST(ar.ID as VARCHAR) + ' - $' + 
                    CONVERT(VARCHAR, CAST(ar.OriginalAmount as MONEY), 1) as StandardDescription,
                ISNULL(arh.Comment, '') as Comments,
                '' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                2 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.HistoryType = 0
              AND (ar.TransactionNumber IS NULL OR ar.TransactionNumber = 0)
              AND ar.Type = 2
            
            UNION ALL
            
            -- 3. PAYMENTS WITH PROPER TENDER TYPES
            SELECT 
                arh.Date as TransactionDate,
                'PAYMENT' as TransactionType,
                'Payment' as Category,
                'PMT-' + CAST(p.ID as VARCHAR(20)) as ReferenceNumber,
                'Payment #' + CAST(p.ID as VARCHAR) + ' - $' + 
                    CONVERT(VARCHAR, CAST(ABS(arh.Amount) as MONEY), 1) +
                    CASE 
                        WHEN ar.TransactionNumber > 0 
                        THEN ' on Invoice #' + CAST(ar.TransactionNumber as VARCHAR)
                        ELSE ''
                    END as StandardDescription,
                ISNULL(p.Comment, ISNULL(arh.Comment, '')) as Comments,
                -- Get actual tender type from TenderEntry/Tender tables or use comment fallback
                COALESCE(
                    -- First try: Get tender types from TenderEntry linked to this payment
                    STUFF((
                        SELECT DISTINCT ', ' + td.Description
                        FROM TenderEntry te
                        INNER JOIN Tender td ON te.TenderID = td.ID
                        WHERE te.PaymentID = p.ID
                        FOR XML PATH(''), TYPE
                    ).value('.', 'NVARCHAR(MAX)'), 1, 2, ''),
                    -- Second try: Parse comment for tender information
                    CASE 
                        WHEN p.Comment LIKE '%NSF%' THEN 'CHECK'  -- NSF implies check
                        WHEN p.Comment LIKE '%ECHK%' OR p.Comment LIKE '%ACH%' THEN 'ACH/ECHK'
                        WHEN p.Comment LIKE '%CASH%' OR p.Comment = 'C' THEN 'CASH'
                        WHEN p.Comment LIKE '%CHECK%' OR p.Comment LIKE '%CHK%' OR p.Comment LIKE '%CK%' THEN 'CHECK'
                        WHEN p.Comment LIKE '%CREDIT%' OR p.Comment LIKE '%CC%' THEN 'CREDIT CARD'
                        WHEN p.Comment LIKE '%DEBIT%' THEN 'DEBIT CARD'
                        WHEN p.Comment LIKE '%MONEY ORDER%' OR p.Comment LIKE '%MO%' THEN 'MONEY ORDER'
                        WHEN p.Comment LIKE '%STORE CREDIT%' THEN 'STORE CREDIT'
                        ELSE ''
                    END,
                    ''
                ) as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                3 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            LEFT JOIN Payment p ON arh.PaymentID = p.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.HistoryType = 2
              AND arh.PaymentID IS NOT NULL
            
            UNION ALL
            
            -- 4. NSF RETURNS
            SELECT 
                arh.Date as TransactionDate,
                'NSF-RETURN' as TransactionType,
                'NSF Return' as Category,
                'NSF-' + CAST(arh.ID as VARCHAR(20)) as ReferenceNumber,
                'NSF Return - ' + 
                    CASE 
                        WHEN arh.Comment LIKE '%CK%[0-9]%' THEN arh.Comment
                        WHEN arh.Comment LIKE '%CHECK%[0-9]%' THEN arh.Comment
                        ELSE 'Check #' + CAST(arh.ID as VARCHAR)
                    END + ' - $' + CONVERT(VARCHAR, CAST(arh.Amount as MONEY), 1) as StandardDescription,
                arh.Comment as Comments,
                'NSF CHECK' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                4 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.Comment LIKE '%NSF%'
              AND arh.Comment NOT LIKE '%FEE%'
              AND arh.Amount > 0
            
            UNION ALL
            
            -- 5. NSF FEES
            SELECT 
                arh.Date as TransactionDate,
                'NSF-FEE' as TransactionType,
                'NSF Fee' as Category,
                'FEE-' + CAST(arh.ID as VARCHAR(20)) as ReferenceNumber,
                'NSF Fee - $' + CONVERT(VARCHAR, CAST(arh.Amount as MONEY), 1) as StandardDescription,
                arh.Comment as Comments,
                '' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                5 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.Comment LIKE '%NSF%FEE%'
            
            UNION ALL
            
            -- 6. COLLECTION FEES
            SELECT 
                arh.Date as TransactionDate,
                'FEE' as TransactionType,
                'Collection Fee' as Category,
                'FEE-' + CAST(arh.ID as VARCHAR(20)) as ReferenceNumber,
                'Collection Fee - $' + CONVERT(VARCHAR, CAST(arh.Amount as MONEY), 1) as StandardDescription,
                arh.Comment as Comments,
                '' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                6 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.Comment LIKE '%COLLECTION%'
              AND arh.Amount > 0
            
            UNION ALL
            
            -- 7. ADJUSTMENTS
            SELECT 
                arh.Date as TransactionDate,
                CASE 
                    WHEN arh.Amount > 0 THEN 'ADJUSTMENT-DEBIT'
                    ELSE 'ADJUSTMENT-CREDIT'
                END as TransactionType,
                CASE 
                    WHEN arh.Amount > 0 THEN 'Debit Adjustment'
                    ELSE 'Credit Adjustment'
                END as Category,
                'ADJ-' + CAST(arh.ID as VARCHAR(20)) as ReferenceNumber,
                CASE 
                    WHEN arh.Amount > 0 THEN 'Debit Adjustment'
                    ELSE 'Credit Adjustment'
                END + ' - $' + CONVERT(VARCHAR, CAST(ABS(arh.Amount) as MONEY), 1) +
                CASE 
                    WHEN LEN(ISNULL(arh.Comment, '')) > 0 
                    THEN ' - ' + LEFT(arh.Comment, 50)
                    ELSE ''
                END as StandardDescription,
                ISNULL(arh.Comment, '') as Comments,
                '' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                7 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.HistoryType = 1
            
            UNION ALL
            
            -- 8. OTHER FEES
            SELECT 
                arh.Date as TransactionDate,
                'FEE' as TransactionType,
                'Other Fee' as Category,
                'FEE-' + CAST(arh.ID as VARCHAR(20)) as ReferenceNumber,
                'Fee/Charge - $' + CONVERT(VARCHAR, CAST(arh.Amount as MONEY), 1) +
                CASE 
                    WHEN LEN(ISNULL(arh.Comment, '')) > 0 
                    THEN ' - ' + LEFT(arh.Comment, 50)
                    ELSE ''
                END as StandardDescription,
                ISNULL(arh.Comment, '') as Comments,
                '' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                8 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.HistoryType = 5
              AND arh.Comment NOT LIKE '%NSF%'
              AND arh.Comment NOT LIKE '%COLLECTION%'
            
            UNION ALL
            
            -- 9. FINANCE CHARGES
            SELECT 
                arh.Date as TransactionDate,
                'FINANCE-CHARGE' as TransactionType,
                'Finance Charge' as Category,
                'FC-' + CAST(ar.ID as VARCHAR(20)) as ReferenceNumber,
                'Finance Charge - $' + CONVERT(VARCHAR, CAST(ar.OriginalAmount as MONEY), 1) as StandardDescription,
                ISNULL(arh.Comment, '') as Comments,
                '' as TenderType,
                arh.Amount,
                CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
                CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
                arh.ID as HistoryID,
                ar.ID as ARID,
                ar.TransactionNumber,
                9 as SortPriority
            FROM AccountReceivableHistory arh
            INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
            WHERE ar.CustomerID = {customer_id}
              AND arh.HistoryType = 0
              AND ar.Type = 1
        )
        SELECT 
            TransactionDate,
            TransactionType,
            Category,
            ReferenceNumber,
            StandardDescription,
            Comments,
            TenderType,
            Amount,
            Debit,
            Credit,
            HistoryID,
            ARID,
            TransactionNumber,
            SortPriority
        FROM CompleteLedger
        ORDER BY TransactionDate ASC, SortPriority ASC, HistoryID ASC
        """
        
        return self.db.execute_query(query, "Get comprehensive history")
    
    def _calculate_running_balance(self, ledger_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate running balance starting from 0
        """
        if ledger_df.empty:
            return ledger_df
        
        # Ensure chronological order for calculation
        ledger_df = ledger_df.sort_values(['TransactionDate', 'SortPriority', 'HistoryID'], ascending=True)
        
        # Calculate running balance
        running_balance = Decimal('0.00')
        balances = []
        
        for idx, row in ledger_df.iterrows():
            amount = Decimal(str(row['Amount']))
            running_balance += amount
            balances.append(float(running_balance))
        
        ledger_df['RunningBalance'] = balances
        
        # Sort DESC for display (newest first)
        ledger_df = ledger_df.sort_values(['TransactionDate', 'SortPriority', 'HistoryID'], ascending=False)
        ledger_df = ledger_df.reset_index(drop=True)
        
        # Add display-friendly columns that match old format for compatibility
        ledger_df['Description'] = ledger_df['StandardDescription']
        ledger_df['RefNumber'] = ledger_df['ReferenceNumber']
        ledger_df['DaysOld'] = (datetime.now() - pd.to_datetime(ledger_df['TransactionDate'])).dt.days
        ledger_df['AgingBracket'] = ledger_df['DaysOld'].apply(self._get_aging_bracket)
        
        return ledger_df
    
    def _get_aging_bracket(self, days: int) -> str:
        """Get aging bracket for days old"""
        if days <= 0:
            return 'Current'
        elif days <= 30:
            return '1-30 days'
        elif days <= 60:
            return '31-60 days'
        elif days <= 90:
            return '61-90 days'
        else:
            return 'Over 90 days'
    
    def _get_current_ar_balance(self, customer_id: int) -> Decimal:
        """Get current AR balance"""
        query = """
        SELECT ISNULL(SUM(arh.Amount), 0) as CurrentBalance
        FROM AccountReceivableHistory arh
        INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
        WHERE ar.CustomerID = %s
        """
        result = self.db.execute_query(query, (customer_id,))
        if not result.empty:
            return Decimal(str(result.iloc[0]['CurrentBalance']))
        return Decimal('0.00')
    
    def _get_active_ar_records(self, customer_id: int) -> pd.DataFrame:
        """Get currently active AR records"""
        query = """
        SELECT 
            ar.ID as AR_ID,
            ar.TransactionNumber,
            ar.Date,
            ar.OriginalAmount,
            ar.Balance,
            ar.DueDate,
            CASE 
                WHEN ar.Type = 0 THEN 'Invoice'
                WHEN ar.Type = 1 THEN 'Finance Charge'
                WHEN ar.Type = 2 THEN 'Direct Charge'
                ELSE 'Other'
            END as TypeDescription,
            DATEDIFF(day, ar.Date, GETDATE()) as DaysOld,
            CASE 
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 0 THEN 'Current'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '1-30 days'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 days'
                WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 days'
                ELSE 'Over 90 days'
            END as AgingCategory
        FROM AccountReceivable ar
        WHERE ar.CustomerID = %s
          AND ar.Balance != 0
        ORDER BY ar.Date DESC
        """
        return self.db.execute_query(query, (customer_id,))
    
    def _calculate_summary(self, ledger_df: pd.DataFrame, current_ar_balance: Decimal, 
                          active_ar: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics"""
        
        if ledger_df.empty:
            return {
                'total_invoiced': 0.00,
                'total_payments': 0.00,
                'total_nsf_returns': 0.00,
                'total_nsf_fees': 0.00,
                'total_collection_fees': 0.00,
                'total_adjustments': 0.00,
                'total_debits': 0.00,
                'total_credits': 0.00,
                'starting_balance': 0.00,
                'ending_balance': 0.00,
                'current_ar_balance': float(current_ar_balance),
                'active_ar_count': len(active_ar),
                'active_ar_total': float(active_ar['Balance'].sum()) if not active_ar.empty else 0.00
            }
        
        summary = {
            'total_invoiced': float(ledger_df[ledger_df['TransactionType'] == 'SALE']['Debit'].sum()),
            'total_payments': float(ledger_df[ledger_df['TransactionType'] == 'PAYMENT']['Credit'].sum()),
            'total_nsf_returns': float(ledger_df[ledger_df['TransactionType'] == 'NSF-RETURN']['Debit'].sum()),
            'total_nsf_fees': float(ledger_df[ledger_df['TransactionType'] == 'NSF-FEE']['Debit'].sum()),
            'total_collection_fees': float(ledger_df[ledger_df['Category'] == 'Collection Fee']['Debit'].sum()),
            'total_adjustments': float(ledger_df[ledger_df['TransactionType'].str.contains('ADJUSTMENT', na=False)]['Amount'].sum()),
            'total_debits': float(ledger_df['Debit'].sum()),
            'total_credits': float(ledger_df['Credit'].sum()),
            'starting_balance': 0.00,
            'ending_balance': float(ledger_df.iloc[0]['RunningBalance']) if not ledger_df.empty else 0.00,
            'current_ar_balance': float(current_ar_balance),
            'active_ar_count': len(active_ar),
            'active_ar_total': float(active_ar['Balance'].sum()) if not active_ar.empty else 0.00,
            'transaction_count': len(ledger_df)
        }
        
        # Tender type breakdown
        tender_breakdown = {}
        for tender in ledger_df['TenderType'].unique():
            if tender and tender != '':
                tender_data = ledger_df[ledger_df['TenderType'] == tender]
                tender_breakdown[tender] = {
                    'count': len(tender_data),
                    'total_amount': float(tender_data['Amount'].abs().sum())
                }
        summary['tender_breakdown'] = tender_breakdown
        
        # Category breakdown
        category_breakdown = {}
        for category in ledger_df['Category'].unique():
            cat_data = ledger_df[ledger_df['Category'] == category]
            category_breakdown[category] = {
                'count': len(cat_data),
                'debits': float(cat_data['Debit'].sum()),
                'credits': float(cat_data['Credit'].sum()),
                'net': float(cat_data['Amount'].sum())
            }
        summary['category_breakdown'] = category_breakdown
        
        return summary
    
    def get_customer_list(self, search: Optional[str] = None) -> pd.DataFrame:
        """Get list of customers"""
        where_clause = ""
        params = ()
        
        if search:
            where_clause = """
            WHERE c.Company LIKE %s 
               OR c.FirstName LIKE %s 
               OR c.LastName LIKE %s
               OR c.AccountNumber LIKE %s
               OR CAST(c.ID as VARCHAR) = %s
            """
            search_pattern = f'%{search}%'
            params = (search_pattern, search_pattern, search_pattern, search_pattern, search)
        
        query = f"""
        SELECT TOP 100
            c.ID,
            c.AccountNumber,
            c.Company,
            c.FirstName,
            c.LastName,
            COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.PhoneNumber,
            c.EmailAddress,
            c.CreditLimit,
            (SELECT ISNULL(SUM(arh.Amount), 0)
             FROM AccountReceivableHistory arh
             INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
             WHERE ar.CustomerID = c.ID) as CurrentBalance
        FROM Customer c
        {where_clause}
        ORDER BY c.Company, c.LastName, c.FirstName
        """
        
        return self.db.execute_query(query, params if params else None)