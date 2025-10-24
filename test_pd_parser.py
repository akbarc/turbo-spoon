"""
Test PD Check Parser - Show all PD checks and how they're being parsed
"""

import sys
from datetime import date
import pandas as pd

print("=" * 80)
print("PD CHECK PARSER TEST")
print("=" * 80)
print()

# Test imports
print("Step 1: Testing database connection...")
try:
    from src.database.sql_server import execute_query, test_connection
    from src.modules.pd_check_parser import PDCheckParser

    if not test_connection():
        print("❌ Cannot connect to database")
        sys.exit(1)

    print("✅ Database connection successful")
    print("✅ PD Check Parser loaded")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
print("FETCHING ALL PD CHECKS FROM DATABASE")
print("=" * 80)
print()

# Query all PD checks
query = """
    SELECT
        p.ID,
        p.Time as payment_date,
        p.Amount,
        p.Comment,
        p.CustomerID,
        c.Company,
        COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as customer_name
    FROM dbo.Payment p
    LEFT JOIN dbo.Customer c ON p.CustomerID = c.ID
    WHERE (
        UPPER(p.Comment) LIKE '%PD%'
        OR UPPER(p.Comment) LIKE '%POST DATE%'
        OR UPPER(p.Comment) LIKE '%P D%'
        OR UPPER(p.Comment) LIKE '%POSTDATE%'
    )
    AND p.Amount > 0
    ORDER BY p.Time DESC
"""

try:
    df = execute_query(query)
    print(f"✅ Found {len(df)} PD check records in database")
    print()
except Exception as e:
    print(f"❌ Error querying database: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Parse each check
print("=" * 80)
print("PARSING RESULTS")
print("=" * 80)
print()

parsed_successfully = 0
parsing_failed = 0
active_checks = 0
matured_checks = 0
today = date.today()

results = []

for idx, row in df.iterrows():
    comment = row['Comment']
    amount = float(row['Amount'])
    payment_date = row['payment_date']
    customer_name = row['customer_name']

    # Parse the check
    pd_info = PDCheckParser.extract_pd_info(comment)

    result = {
        'payment_id': row['ID'],
        'payment_date': payment_date,
        'customer': customer_name,
        'amount': amount,
        'comment': comment,
        'parsed': pd_info.get('parsed_successfully', False),
        'pd_date': pd_info.get('deposit_date'),
        'days_until': pd_info.get('days_until_deposit', 'N/A'),
        'is_active': False
    }

    if pd_info.get('parsed_successfully'):
        parsed_successfully += 1
        pd_date = pd_info['deposit_date']

        if pd_date >= today:
            result['is_active'] = True
            active_checks += 1
        else:
            matured_checks += 1
    else:
        parsing_failed += 1

    results.append(result)

# Display summary
print(f"📊 SUMMARY:")
print(f"   Total PD Checks: {len(df)}")
print(f"   ✅ Parsed Successfully: {parsed_successfully}")
print(f"   ❌ Parsing Failed: {parsing_failed}")
print(f"   🟢 Active (Future): {active_checks}")
print(f"   🔴 Matured (Past): {matured_checks}")
print()

# Show parsing failures first
if parsing_failed > 0:
    print("=" * 80)
    print("❌ PARSING FAILURES (Cannot extract PD date)")
    print("=" * 80)
    print()

    for result in results:
        if not result['parsed']:
            print(f"Payment ID: {result['payment_id']}")
            print(f"  Date Recorded: {result['payment_date']}")
            print(f"  Customer: {result['customer']}")
            print(f"  Amount: ${result['amount']:,.2f}")
            print(f"  Comment: {result['comment']}")
            print(f"  ❌ FAILED TO PARSE PD DATE")
            print()

# Show active checks
if active_checks > 0:
    print("=" * 80)
    print("🟢 ACTIVE PD CHECKS (Future dates)")
    print("=" * 80)
    print()

    active_results = [r for r in results if r['is_active']]
    active_results.sort(key=lambda x: x['pd_date'])

    for result in active_results:
        print(f"Payment ID: {result['payment_id']}")
        print(f"  Customer: {result['customer']}")
        print(f"  Amount: ${result['amount']:,.2f}")
        print(f"  PD Date: {result['pd_date']} (in {result['days_until']} days)")
        print(f"  Comment: {result['comment']}")
        print()

# Show matured checks (sample)
if matured_checks > 0:
    print("=" * 80)
    print("🔴 MATURED PD CHECKS (Past dates - showing last 20)")
    print("=" * 80)
    print()

    matured_results = [r for r in results if result['parsed'] and not result['is_active']]
    matured_results.sort(key=lambda x: x['pd_date'], reverse=True)

    for result in matured_results[:20]:  # Show only last 20
        print(f"Payment ID: {result['payment_id']}")
        print(f"  Customer: {result['customer']}")
        print(f"  Amount: ${result['amount']:,.2f}")
        print(f"  PD Date: {result['pd_date']} ({abs(result['days_until'])} days ago)")
        print(f"  Comment: {result['comment']}")
        print()

# Export to CSV for detailed analysis
print("=" * 80)
print("EXPORTING TO CSV")
print("=" * 80)
print()

results_df = pd.DataFrame(results)
csv_filename = 'pd_checks_parsing_test_results.csv'
results_df.to_csv(csv_filename, index=False)
print(f"✅ Exported all results to: {csv_filename}")
print()

# Show some example formats that worked
print("=" * 80)
print("✅ EXAMPLE FORMATS THAT PARSED SUCCESSFULLY")
print("=" * 80)
print()

successful_examples = [r for r in results if r['parsed']][:10]
for result in successful_examples:
    print(f"Comment: {result['comment']}")
    print(f"  → Parsed Date: {result['pd_date']}")
    print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print()
print(f"Full results saved to: {csv_filename}")
print()
