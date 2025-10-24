"""
Database Investigation - Find and examine excise tables in the POS system
Task 12: Connect to actual POS database and identify excise table structures
"""

from database_pymssql import SQLServerConnection
import pandas as pd

def find_excise_tables():
    """Find all tables with 'EXCISE' in the name"""
    query = """
    SELECT
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%EXCISE%'
    ORDER BY TABLE_NAME
    """

    with SQLServerConnection() as db:
        df = db.execute_query(query, description="Find EXCISE tables")
        print("\n" + "="*80)
        print("EXCISE TABLES FOUND:")
        print("="*80)
        print(df.to_string(index=False))
        return df

def examine_table_structure(schema, table_name):
    """Get detailed structure of a table"""
    query = """
    SELECT
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        IS_NULLABLE,
        COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """

    with SQLServerConnection() as db:
        df = db.execute_query(query, params=[schema, table_name],
                             description=f"Examine structure of {schema}.{table_name}")
        print(f"\n{'='*80}")
        print(f"STRUCTURE OF {schema}.{table_name}:")
        print("="*80)
        print(df.to_string(index=False))
        return df

def get_sample_data(schema, table_name, limit=5):
    """Get sample data from a table"""
    query = f"SELECT TOP {limit} * FROM [{schema}].[{table_name}]"

    with SQLServerConnection() as db:
        df = db.execute_query(query, description=f"Sample data from {schema}.{table_name}")
        print(f"\n{'='*80}")
        print(f"SAMPLE DATA FROM {schema}.{table_name} (TOP {limit}):")
        print("="*80)
        print(df.to_string(index=False))
        return df

def get_row_count(schema, table_name):
    """Get row count for a table"""
    query = f"SELECT COUNT(*) as row_count FROM [{schema}].[{table_name}]"

    with SQLServerConnection() as db:
        df = db.execute_query(query, description=f"Row count for {schema}.{table_name}")
        if not df.empty:
            count = df.iloc[0]['row_count']
            print(f"\n{schema}.{table_name} has {count:,} rows")
            return count
        return 0

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DATABASE INVESTIGATION - EXCISE TABLES")
    print("Task 12: Find exact excise tables used by POS system")
    print("="*80)

    # Step 1: Find all excise tables
    excise_tables = find_excise_tables()

    if excise_tables.empty:
        print("\n⚠️ NO EXCISE TABLES FOUND!")
        print("The POS system may not have dedicated excise tables.")
        print("Searching for related tables...")

        # Search for TAX tables as alternative
        query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%TAX%'
        ORDER BY TABLE_NAME
        """

        with SQLServerConnection() as db:
            tax_tables = db.execute_query(query, description="Find TAX tables")
            print("\n" + "="*80)
            print("TAX-RELATED TABLES FOUND:")
            print("="*80)
            print(tax_tables.to_string(index=False))
    else:
        # Step 2: Examine structure of each excise table found
        for _, row in excise_tables.iterrows():
            schema = row['TABLE_SCHEMA']
            table_name = row['TABLE_NAME']

            # Get structure
            examine_table_structure(schema, table_name)

            # Get row count
            get_row_count(schema, table_name)

            # Get sample data
            get_sample_data(schema, table_name, limit=10)

    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80)
