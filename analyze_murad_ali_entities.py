"""
Comprehensive analysis of all Murad Ali entities
Checks account status, recent activity, and business metrics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('.')))
from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta

def get_murad_ali_exact_matches():
    """Get all exact Murad Ali customer records"""
    with SQLServerConnection() as db:
        query = """
        SELECT
            ID,
            Company,
            FirstName,
            LastName,
            PhoneNumber,
            Address,
            City,
            State,
            AccountBalance,
            CreditLimit,
            TotalSales,
            LastVisit,
            DateOpened,
            Active
        FROM dbo.Customer
        WHERE FirstName = 'MURAD' AND LastName = 'ALI'
        ORDER BY AccountBalance DESC
        """
        return db.execute_query(query)

def get_recent_transactions(customer_id):
    """Get recent transaction history for a customer"""
    with SQLServerConnection() as db:
        # Try different table name formats
        tables_to_try = ['[Transaction]', 'Transactions', 'Transaction_Header']

        for table_name in tables_to_try:
            try:
                query = f"""
                SELECT TOP 10
                    Time as TransactionDate,
                    Total as Amount,
                    Tax,
                    TransactionType,
                    PaymentType
                FROM {table_name}
                WHERE CustomerID = %s
                ORDER BY Time DESC
                """
                result = db.execute_query(query, [customer_id])
                if not result.empty:
                    return result
            except:
                continue
        return pd.DataFrame()

def get_payment_history(customer_id):
    """Get payment history for a customer"""
    with SQLServerConnection() as db:
        query = """
        SELECT TOP 10
            Time as PaymentDate,
            Amount,
            PaymentType,
            CheckNumber
        FROM dbo.Payment
        WHERE CustomerID = %s
        ORDER BY Time DESC
        """
        return db.execute_query(query, [customer_id])

def get_outstanding_invoices(customer_id):
    """Get outstanding AR invoices"""
    with SQLServerConnection() as db:
        query = """
        SELECT
            InvoiceNumber,
            Date as InvoiceDate,
            DueDate,
            Balance,
            DATEDIFF(day, DueDate, GETDATE()) as DaysOverdue
        FROM dbo.AccountReceivable
        WHERE CustomerID = %s AND Balance > 0
        ORDER BY Date DESC
        """
        return db.execute_query(query, [customer_id])

def analyze_cigarette_purchases(customer_id):
    """Analyze cigarette purchasing patterns"""
    with SQLServerConnection() as db:
        # Check multiple table name formats
        queries = [
            # Format 1: Transaction with TransactionDetail
            """
            SELECT
                YEAR(t.Time) as Year,
                MONTH(t.Time) as Month,
                COUNT(DISTINCT t.ID) as TransactionCount,
                SUM(CASE WHEN i.SubDepartmentID = 25 OR i.CategoryID = 5 THEN td.SellQty ELSE 0 END) as CigaretteUnits,
                SUM(CASE WHEN i.SubDepartmentID = 25 OR i.CategoryID = 5 THEN td.SellQty * td.SellPrice ELSE 0 END) as CigaretteSales
            FROM [Transaction] t
            INNER JOIN TransactionDetail td ON t.ID = td.TransactionID
            INNER JOIN Items i ON td.ItemID = i.ID
            WHERE t.CustomerID = %s
            GROUP BY YEAR(t.Time), MONTH(t.Time)
            ORDER BY Year DESC, Month DESC
            """,
            # Format 2: Transaction_Header with Transaction_Detail
            """
            SELECT
                YEAR(t.Time) as Year,
                MONTH(t.Time) as Month,
                COUNT(DISTINCT t.ID) as TransactionCount,
                SUM(CASE WHEN i.SubDepartmentID = 25 OR i.CategoryID = 5 THEN td.SellQty ELSE 0 END) as CigaretteUnits,
                SUM(CASE WHEN i.SubDepartmentID = 25 OR i.CategoryID = 5 THEN td.SellQty * td.SellPrice ELSE 0 END) as CigaretteSales
            FROM Transaction_Header t
            INNER JOIN Transaction_Detail td ON t.ID = td.TransactionID
            INNER JOIN Items i ON td.ItemID = i.ID
            WHERE t.CustomerID = %s
            GROUP BY YEAR(t.Time), MONTH(t.Time)
            ORDER BY Year DESC, Month DESC
            """,
            # Format 3: Simple aggregation from Transaction table only
            """
            SELECT
                YEAR(Time) as Year,
                MONTH(Time) as Month,
                COUNT(*) as TransactionCount,
                SUM(Total) as TotalSales,
                AVG(Total) as AvgTransactionSize
            FROM [Transaction]
            WHERE CustomerID = %s
            GROUP BY YEAR(Time), MONTH(Time)
            ORDER BY Year DESC, Month DESC
            """
        ]

        for query in queries:
            try:
                result = db.execute_query(query, [customer_id])
                if not result.empty:
                    return result.head(12)  # Last 12 months
            except:
                continue

        return pd.DataFrame()

def main():
    print("="*120)
    print("MURAD ALI ENTITIES - COMPREHENSIVE ANALYSIS")
    print("="*120)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Get all exact Murad Ali matches
    murad_customers = get_murad_ali_exact_matches()

    if murad_customers.empty:
        print("No exact Murad Ali matches found")
        return

    print(f"Found {len(murad_customers)} exact 'MURAD ALI' entities\n")

    # Summary statistics
    total_ar = murad_customers['AccountBalance'].sum()
    total_credit = murad_customers['CreditLimit'].sum()
    active_count = murad_customers['Active'].sum() if 'Active' in murad_customers.columns else len(murad_customers)

    print("SUMMARY STATISTICS")
    print("-"*120)
    print(f"Total Entities: {len(murad_customers)}")
    print(f"Active Accounts: {active_count}")
    print(f"Total AR Balance: ${total_ar:,.2f}")
    print(f"Total Credit Limit: ${total_credit:,.2f}")
    print(f"Entities with AR > 0: {len(murad_customers[murad_customers['AccountBalance'] > 0])}")
    print()

    # Detailed entity analysis
    print("DETAILED ENTITY ANALYSIS")
    print("="*120)

    for idx, customer in murad_customers.iterrows():
        cust_id = customer['ID']
        company = customer['Company'] or 'N/A'
        ar_balance = float(customer['AccountBalance'] or 0)
        credit_limit = float(customer['CreditLimit'] or 0)
        total_sales = float(customer['TotalSales'] or 0)
        last_visit = customer['LastVisit']

        print(f"\n{'='*120}")
        print(f"Entity #{idx+1}: {company}")
        print(f"Customer ID: {cust_id}")
        print("-"*120)

        # Basic Information
        print(f"Contact: {customer['FirstName']} {customer['LastName']}")
        print(f"Phone: {customer['PhoneNumber'] or 'N/A'}")
        print(f"Address: {customer['Address'] or 'N/A'}, {customer['City'] or ''} {customer['State'] or ''}")
        print(f"Account Opened: {customer['DateOpened'] or 'N/A'}")
        print(f"Status: {'ACTIVE' if customer.get('Active', True) else 'INACTIVE'}")
        print()

        # Financial Summary
        print("FINANCIAL SUMMARY:")
        print(f"  • AR Balance: ${ar_balance:,.2f}")
        print(f"  • Credit Limit: ${credit_limit:,.2f}")
        print(f"  • Available Credit: ${max(0, credit_limit - ar_balance):,.2f}")
        print(f"  • Total Lifetime Sales: ${total_sales:,.2f}")
        print(f"  • Last Visit: {last_visit or 'No recent activity'}")

        # Skip detailed analysis for inactive accounts with no AR
        if ar_balance <= 0 and (not last_visit or (isinstance(last_visit, pd.Timestamp) and (datetime.now() - last_visit).days > 365)):
            print("  • Status: INACTIVE - No recent activity or outstanding balance")
            continue

        # Get outstanding invoices
        invoices = get_outstanding_invoices(cust_id)
        if not invoices.empty:
            print(f"\nOUTSTANDING INVOICES ({len(invoices)} total):")
            for _, inv in invoices.head(5).iterrows():
                days_overdue = int(inv['DaysOverdue']) if pd.notna(inv['DaysOverdue']) else 0
                status = "OVERDUE" if days_overdue > 0 else "CURRENT"
                print(f"  • Invoice {inv['InvoiceNumber']}: ${float(inv['Balance']):,.2f} - {status} ({days_overdue} days)")

        # Get recent payments
        payments = get_payment_history(cust_id)
        if not payments.empty:
            print(f"\nRECENT PAYMENTS (Last 5):")
            for _, pay in payments.head(5).iterrows():
                pay_date = pay['PaymentDate']
                if isinstance(pay_date, pd.Timestamp):
                    pay_date_str = pay_date.strftime('%Y-%m-%d')
                else:
                    pay_date_str = str(pay_date)
                print(f"  • {pay_date_str}: ${float(pay['Amount']):,.2f} - {pay['PaymentType'] or 'N/A'}")

        # Get recent transactions
        transactions = get_recent_transactions(cust_id)
        if not transactions.empty:
            print(f"\nRECENT TRANSACTIONS (Last 5):")
            for _, trans in transactions.head(5).iterrows():
                trans_date = trans['TransactionDate']
                if isinstance(trans_date, pd.Timestamp):
                    trans_date_str = trans_date.strftime('%Y-%m-%d')
                else:
                    trans_date_str = str(trans_date)
                print(f"  • {trans_date_str}: ${float(trans['Amount']):,.2f}")

        # Cigarette purchase analysis
        cig_purchases = analyze_cigarette_purchases(cust_id)
        if not cig_purchases.empty:
            print(f"\nCIGARETTE PURCHASE HISTORY (Recent months):")
            for _, purchase in cig_purchases.head(6).iterrows():
                year = int(purchase['Year'])
                month = int(purchase['Month'])
                if 'CigaretteSales' in purchase and pd.notna(purchase['CigaretteSales']):
                    cig_sales = float(purchase['CigaretteSales'])
                    if cig_sales > 0:
                        print(f"  • {year}-{month:02d}: ${cig_sales:,.2f} ({int(purchase.get('CigaretteUnits', 0))} units)")
                elif 'TotalSales' in purchase:
                    total = float(purchase['TotalSales'])
                    print(f"  • {year}-{month:02d}: ${total:,.2f} total sales")

    print(f"\n{'='*120}")
    print("RISK ASSESSMENT SUMMARY")
    print("-"*120)

    # Categorize accounts by risk
    high_risk = murad_customers[murad_customers['AccountBalance'] > 50000]
    medium_risk = murad_customers[(murad_customers['AccountBalance'] > 10000) & (murad_customers['AccountBalance'] <= 50000)]
    low_risk = murad_customers[(murad_customers['AccountBalance'] > 0) & (murad_customers['AccountBalance'] <= 10000)]

    if not high_risk.empty:
        print(f"\nHIGH RISK (AR > $50,000): {len(high_risk)} accounts")
        for _, cust in high_risk.iterrows():
            print(f"  • {cust['Company']}: ${float(cust['AccountBalance']):,.2f}")

    if not medium_risk.empty:
        print(f"\nMEDIUM RISK ($10,000 < AR <= $50,000): {len(medium_risk)} accounts")
        for _, cust in medium_risk.iterrows():
            print(f"  • {cust['Company']}: ${float(cust['AccountBalance']):,.2f}")

    if not low_risk.empty:
        print(f"\nLOW RISK (AR <= $10,000): {len(low_risk)} accounts")
        for _, cust in low_risk.iterrows():
            print(f"  • {cust['Company']}: ${float(cust['AccountBalance']):,.2f}")

    print(f"\n{'='*120}")
    print("Analysis complete")

if __name__ == "__main__":
    main()