#!/usr/bin/env python3
"""
Analyze 5 Star Food Mart transactions to understand ALL tender types, 
payment methods, and adjustment explanations
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_5star_tender_types():
    """Deep dive into 5 Star Food Mart payment methods and adjustments"""
    
    db = SQLServerConnection()
    
    try:
        # First find 5 Star Food Mart customer
        customer_query = """
        SELECT TOP 5 
            ID, 
            AccountNumber,
            FirstName,
            LastName,
            Company,
            COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
            AccountBalance
        FROM Customer 
        WHERE Company LIKE '%5 Star%' 
           OR Company LIKE '%Sameer%'
           OR FirstName LIKE '%Sameer%'
           OR LastName LIKE '%Somani%'
        ORDER BY AccountBalance DESC
        """
        
        customers = db.execute_query(customer_query, "Find 5 Star Food Mart")
        
        if customers.empty:
            logger.error("Could not find 5 Star Food Mart customer")
            return
        
        print("\n=== 5 STAR FOOD MART CUSTOMERS ===")
        for _, c in customers.iterrows():
            print(f"ID: {c['ID']}, Name: {c['CustomerName']}, Company: {c['Company']}, Balance: ${c['AccountBalance']:,.2f}")
        
        # Use the first customer found
        customer_id = customers.iloc[0]['ID']
        customer_name = customers.iloc[0]['CustomerName']
        
        print(f"\nAnalyzing Customer ID {customer_id}: {customer_name}")
        
        # 1. Get all available tender types from Tender table
        tender_query = """
        SELECT 
            ID,
            Code,
            Description,
            TenderType
        FROM Tender
        ORDER BY ID
        """
        
        tenders = db.execute_query(tender_query, "Get tender types")
        
        print("\n=== AVAILABLE TENDER TYPES IN SYSTEM ===")
        for _, t in tenders.iterrows():
            print(f"ID: {t['ID']:2d}, Code: {t['Code']:10s}, Type: {t.get('TenderType', 'N/A'):2s}, Description: {t['Description']}")
        
        # 2. Analyze payments for this customer with tender information
        payment_query = f"""
        SELECT TOP 100
            p.ID as PaymentID,
            p.Time as PaymentDate,
            p.Amount,
            p.TenderID,
            t.Code as TenderCode,
            t.Description as TenderDescription,
            p.Comment,
            p.CheckNumber,
            p.ReferenceNumber,
            CASE 
                WHEN p.Comment LIKE '%NSF%' THEN 'NSF/Returned'
                WHEN p.Comment LIKE '%RETURN%' THEN 'Returned'
                WHEN p.Comment LIKE '%VOID%' THEN 'Voided'
                ELSE 'Applied'
            END as PaymentStatus
        FROM Payment p
        LEFT JOIN Tender t ON p.TenderID = t.ID
        WHERE p.CustomerID = {customer_id}
        ORDER BY p.Time DESC
        """
        
        payments = db.execute_query(payment_query, "Get customer payments with tender types")
        
        print(f"\n=== RECENT PAYMENTS FOR {customer_name} ===")
        print(f"Total payments found: {len(payments)}")
        
        if not payments.empty:
            # Group by tender type
            tender_summary = payments.groupby(['TenderCode', 'TenderDescription']).agg({
                'Amount': ['count', 'sum', 'mean']
            }).round(2)
            
            print("\n=== PAYMENT SUMMARY BY TENDER TYPE ===")
            print(tender_summary)
            
            # Show sample payments with tender info
            print("\n=== SAMPLE PAYMENTS WITH TENDER DETAILS ===")
            for i, p in payments.head(10).iterrows():
                print(f"\nDate: {p['PaymentDate']}")
                print(f"  Amount: ${p['Amount']:,.2f}")
                print(f"  Tender: {p['TenderCode']} - {p['TenderDescription']}")
                print(f"  Check#: {p.get('CheckNumber', 'N/A')}")
                print(f"  Ref#: {p.get('ReferenceNumber', 'N/A')}")
                print(f"  Status: {p['PaymentStatus']}")
                print(f"  Comment: {p.get('Comment', 'None')}")
        
        # 3. Analyze AR History for adjustments with detailed explanations
        ar_history_query = f"""
        SELECT TOP 100
            arh.ID as HistoryID,
            arh.Date as AdjustmentDate,
            arh.Amount,
            arh.Comment,
            arh.AccountReceivableID,
            ar.TransactionNumber,
            ar.Type as ARType,
            CASE 
                WHEN arh.Comment LIKE '%NSF%' AND arh.Amount > 0 THEN 'NSF Fee Charged'
                WHEN arh.Comment LIKE '%NSF%' AND arh.Amount < 0 THEN 'NSF Fee Reversal'
                WHEN arh.Comment LIKE '%RETURN%' AND arh.Amount > 0 THEN 'Returned Payment Fee'
                WHEN arh.Comment LIKE '%RETURN%' AND arh.Amount < 0 THEN 'Return Reversal'
                WHEN arh.Comment LIKE '%FEE%' AND arh.Amount > 0 THEN 'Fee Charge'
                WHEN arh.Comment LIKE '%FEE%' AND arh.Amount < 0 THEN 'Fee Credit'
                WHEN arh.Comment LIKE '%CREDIT%' THEN 'Credit Adjustment'
                WHEN arh.Comment LIKE '%DEBIT%' THEN 'Debit Adjustment'
                WHEN arh.Comment LIKE '%Payment%' AND arh.Amount < 0 THEN 'Payment Application'
                WHEN arh.Comment LIKE '%Payment%' AND arh.Amount > 0 THEN 'Payment Reversal'
                WHEN arh.Amount > 0 THEN 'Charge/Debit'
                WHEN arh.Amount < 0 THEN 'Credit/Payment'
                ELSE 'Manual Adjustment'
            END as AdjustmentType,
            CASE
                WHEN arh.Comment LIKE '%NSF%' THEN 'Check returned - insufficient funds. Fee charged to account.'
                WHEN arh.Comment LIKE '%RETURN%' THEN 'Payment returned/reversed. Original payment amount added back.'
                WHEN arh.Comment LIKE '%FEE%' THEN 'Service or processing fee applied to account.'
                WHEN arh.Comment LIKE '%CREDIT%' THEN 'Credit applied to reduce account balance.'
                WHEN arh.Comment LIKE '%DEBIT%' THEN 'Additional charge applied to account.'
                WHEN arh.Comment LIKE '%Payment%' THEN 'Customer payment applied to outstanding balance.'
                WHEN arh.Amount > 0 THEN 'Charge added to account balance.'
                WHEN arh.Amount < 0 THEN 'Credit reducing account balance.'
                ELSE ISNULL(arh.Comment, 'Manual account adjustment')
            END as DetailedExplanation
        FROM AccountReceivableHistory arh
        INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
        WHERE ar.CustomerID = {customer_id}
        ORDER BY arh.Date DESC
        """
        
        ar_history = db.execute_query(ar_history_query, "Get AR adjustment history")
        
        print(f"\n=== AR ADJUSTMENTS FOR {customer_name} ===")
        print(f"Total adjustments found: {len(ar_history)}")
        
        if not ar_history.empty:
            # Group by adjustment type
            adj_summary = ar_history.groupby('AdjustmentType').agg({
                'Amount': ['count', 'sum', 'mean']
            }).round(2)
            
            print("\n=== ADJUSTMENT SUMMARY BY TYPE ===")
            print(adj_summary)
            
            # Show unique adjustment types with explanations
            print("\n=== ADJUSTMENT TYPES AND EXPLANATIONS ===")
            unique_types = ar_history[['AdjustmentType', 'DetailedExplanation']].drop_duplicates()
            for _, row in unique_types.iterrows():
                print(f"\nType: {row['AdjustmentType']}")
                print(f"Explanation: {row['DetailedExplanation']}")
            
            # Show sample adjustments
            print("\n=== SAMPLE ADJUSTMENTS WITH DETAILS ===")
            for i, adj in ar_history.head(10).iterrows():
                print(f"\nDate: {adj['AdjustmentDate']}")
                print(f"  Amount: ${adj['Amount']:,.2f}")
                print(f"  Type: {adj['AdjustmentType']}")
                print(f"  Explanation: {adj['DetailedExplanation']}")
                print(f"  Original Comment: {adj.get('Comment', 'None')}")
                print(f"  Transaction#: {adj.get('TransactionNumber', 'N/A')}")
        
        # 4. Check if Payment table has additional tender-related columns
        column_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Payment'
        AND (
            COLUMN_NAME LIKE '%Tender%'
            OR COLUMN_NAME LIKE '%Type%'
            OR COLUMN_NAME LIKE '%Method%'
            OR COLUMN_NAME LIKE '%Card%'
            OR COLUMN_NAME LIKE '%Check%'
            OR COLUMN_NAME LIKE '%Cash%'
        )
        ORDER BY ORDINAL_POSITION
        """
        
        payment_columns = db.execute_query(column_query, "Get payment table columns")
        
        print("\n=== PAYMENT TABLE TENDER-RELATED COLUMNS ===")
        for _, col in payment_columns.iterrows():
            print(f"{col['COLUMN_NAME']}: {col['DATA_TYPE']}")
        
        # 5. Generate comprehensive summary
        print("\n" + "="*60)
        print("COMPREHENSIVE TENDER TYPE ANALYSIS COMPLETE")
        print("="*60)
        print(f"\nCustomer: {customer_name} (ID: {customer_id})")
        print(f"Total Tender Types Available: {len(tenders)}")
        print(f"Total Payments Analyzed: {len(payments)}")
        print(f"Total Adjustments Analyzed: {len(ar_history)}")
        
        if not payments.empty:
            print(f"\nMost Common Payment Method: {payments['TenderDescription'].mode().iloc[0] if not payments['TenderDescription'].mode().empty else 'N/A'}")
            print(f"Average Payment Amount: ${payments['Amount'].mean():,.2f}")
        
        if not ar_history.empty:
            nsf_count = len(ar_history[ar_history['AdjustmentType'].str.contains('NSF', na=False)])
            fee_total = ar_history[ar_history['AdjustmentType'].str.contains('Fee', na=False)]['Amount'].sum()
            print(f"\nNSF Related Adjustments: {nsf_count}")
            print(f"Total Fees Charged: ${fee_total:,.2f}")
        
        # Save detailed report
        report = {
            'customer': {
                'id': int(customer_id),
                'name': customer_name,
                'balance': float(customers.iloc[0]['AccountBalance'])
            },
            'tender_types': tenders.to_dict('records'),
            'payment_summary': payments.groupby('TenderDescription')['Amount'].agg(['count', 'sum', 'mean']).to_dict() if not payments.empty else {},
            'adjustment_summary': ar_history.groupby('AdjustmentType')['Amount'].agg(['count', 'sum', 'mean']).to_dict() if not ar_history.empty else {},
            'generated_at': datetime.now().isoformat()
        }
        
        with open('5star_tender_analysis.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print("\nDetailed report saved to: 5star_tender_analysis.json")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    analyze_5star_tender_types()