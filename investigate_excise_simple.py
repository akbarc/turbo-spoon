"""
Simplified Database Investigation - Find and examine excise tables
"""

from database_pymssql import SQLServerConnection

def main():
    print("\n" + "="*80)
    print("DATABASE INVESTIGATION - EXCISE TABLES")
    print("="*80)

    with SQLServerConnection() as db:
        # Step 1: Find all EXCISE tables
        print("\n1. Finding EXCISE tables...")
        query1 = """
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%EXCISE%'
        ORDER BY TABLE_NAME
        """
        excise_tables = db.execute_query(query1, description="Find EXCISE tables")
        print("\nEXCISE TABLES FOUND:")
        print(excise_tables.to_string(index=False))

        # Step 2: Examine PUExciseEntry structure (no parameters)
        print("\n" + "="*80)
        print("\n2. Examining PUExciseEntry structure...")
        query2 = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PUExciseEntry'
        ORDER BY ORDINAL_POSITION
        """
        structure = db.execute_query(query2, description="PUExciseEntry structure")
        print("\nPUExciseEntry STRUCTURE:")
        print(structure.to_string(index=False))

        # Step 3: Get sample data from PUExciseEntry
        print("\n" + "="*80)
        print("\n3. Getting sample data from PUExciseEntry...")
        query3 = "SELECT TOP 10 * FROM dbo.PUExciseEntry"
        sample = db.execute_query(query3, description="PUExciseEntry sample data")
        print("\nSAMPLE DATA:")
        print(sample.to_string(index=False))

        # Step 4: Check if there's a relationship to POSInvoice
        print("\n" + "="*80)
        print("\n4. Checking for Invoice/Excise relationships...")
        query4 = """
        SELECT TOP 5
            i.InvoiceID,
            i.InvoiceDate,
            i.InvoiceNumber,
            e.*
        FROM dbo.POSInvoice i
        LEFT JOIN dbo.PUExciseEntry e ON i.InvoiceID = e.InvoiceID
        WHERE e.InvoiceID IS NOT NULL
        ORDER BY i.InvoiceDate DESC
        """
        relationships = db.execute_query(query4, description="Invoice-Excise relationships")
        print("\nINVOICE-EXCISE RELATIONSHIPS:")
        print(relationships.to_string(index=False))

        # Step 5: Examine PUVIEWEXCISECOLLECT columns
        print("\n" + "="*80)
        print("\n5. Examining PUVIEWEXCISECOLLECT structure...")
        query5 = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PUVIEWEXCISECOLLECT'
        ORDER BY ORDINAL_POSITION
        """
        view_structure = db.execute_query(query5, description="PUVIEWEXCISECOLLECT structure")
        print("\nPUVIEWEXCISECOLLECT STRUCTURE:")
        print(view_structure.to_string(index=False))

    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
