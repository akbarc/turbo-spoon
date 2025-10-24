"""
Quick script to check actual column names in POS database tables
"""
from database_pymssql import SQLServerConnection

# Create database instance
db = SQLServerConnection()

# Tables to check
tables = [
    'Batch',
    'TaxEntry',
    'Tax',
    'Transaction',
    'TenderEntry',
    'Tender',
    'TransactionEntry'
]

for table in tables:
    print(f"\n{'='*60}")
    print(f"Table: {table}")
    print('='*60)
    try:
        query = f"SELECT TOP 1 * FROM dbo.[{table}]"
        result = db.execute_query(query, description=f"Get columns for {table}")
        if not result.empty:
            print("Columns:")
            for col in result.columns:
                print(f"  - {col}")
        else:
            print("  (No data)")
    except Exception as e:
        print(f"  ERROR: {e}")

# Close connection
db.close()
