"""
Test script to verify the fixed POS reports
"""
from database_pymssql import SQLServerConnection
from datetime import datetime, timedelta

# Create database instance
db = SQLServerConnection()

# Test date range
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

reports_to_test = {
    'cash_drawer_report': """
        SELECT TOP 5
            b.BatchNumber,
            b.OpeningTime as OpenDate,
            b.ClosingTime as CloseDate,
            r.Description as RegisterName,
            b.OpeningTotal as ExpectedAmount,
            b.ClosingTotal as CountedAmount,
            b.ClosingTotal - b.OpeningTotal as Variance,
            b.Dropped as DepositTotal,
            b.PaidOut as PayoutTotal
        FROM dbo.Batch b
        LEFT JOIN dbo.Register r ON b.RegisterID = r.ID
        WHERE b.OpeningTime >= %s AND b.OpeningTime <= %s
        ORDER BY b.OpeningTime DESC
    """,

    'tax_summary': """
        SELECT TOP 5
            COALESCE(tax.Description, 'Unknown') as TaxType,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            SUM(taxe.Tax) as TotalTaxCollected,
            AVG(taxe.Tax) as AvgTaxPerTransaction,
            SUM(taxe.TaxableAmount) as TaxableAmount
        FROM [dbo].[Transaction] t
        JOIN dbo.TaxEntry taxe ON t.TransactionNumber = taxe.TransactionNumber
        LEFT JOIN dbo.Tax tax ON taxe.TaxID = tax.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY tax.ID, tax.Description
        ORDER BY TotalTaxCollected DESC
    """,

    'void_report': """
        SELECT TOP 5
            t.TransactionNumber,
            t.Time as VoidTime,
            t.Total as VoidedAmount,
            t.Comment as Reason,
            t.Status
        FROM [dbo].[Transaction] t
        WHERE (t.Status < 0 OR t.Comment LIKE '%void%' OR t.Comment LIKE '%cancel%')
          AND t.Time >= %s AND t.Time <= %s
        ORDER BY t.Time DESC
    """,

    'tender_types_detail': """
        SELECT TOP 5
            COALESCE(tender.Description, te.Description, 'Unknown') as TenderType,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            SUM(te.Amount) as TotalAmount,
            AVG(te.Amount) as AvgAmount
        FROM [dbo].[Transaction] t
        JOIN dbo.TenderEntry te ON t.TransactionNumber = te.TransactionNumber
        LEFT JOIN dbo.Tender tender ON te.TenderID = tender.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY tender.ID, tender.Description, te.Description
        ORDER BY TotalAmount DESC
    """,

    'discount_report': """
        SELECT TOP 5
            CAST(t.Time AS DATE) as DiscountDate,
            i.Description as ItemName,
            te.FullPrice as OriginalPrice,
            te.Price as DiscountedPrice,
            te.FullPrice - te.Price as DiscountAmount,
            CASE WHEN te.FullPrice > 0
                 THEN ((te.FullPrice - te.Price) / te.FullPrice) * 100
                 ELSE 0
            END as DiscountPercent,
            te.Quantity
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        WHERE te.FullPrice > te.Price AND te.FullPrice > 0
          AND t.Time >= %s AND t.Time <= %s
        ORDER BY t.Time DESC
    """
}

print("="*80)
print("TESTING FIXED POS REPORTS")
print("="*80)
print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print()

for report_name, query in reports_to_test.items():
    print(f"\n{'='*80}")
    print(f"Testing: {report_name}")
    print('='*80)

    try:
        result = db.execute_query(
            query,
            params=[start_date, end_date],
            description=f"Test {report_name}"
        )

        if result.empty:
            print(f"✅ SUCCESS - Query executed but returned no data (may be expected)")
        else:
            print(f"✅ SUCCESS - Query returned {len(result)} rows")
            print("\nSample data:")
            print(result.head().to_string())

    except Exception as e:
        print(f"❌ FAILED - Error: {str(e)}")

print(f"\n\n{'='*80}")
print("TEST COMPLETE")
print('='*80)

# Close connection
db.close()
