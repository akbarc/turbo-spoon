"""Database exploration script - generates comprehensive schema and data analysis."""
import os
os.environ['TDSVER'] = '7.0'
import pymssql
import pandas as pd
from datetime import datetime
import json

# Configuration
SERVER = '10.1.10.105'
USER = 'amchranya'
PASSWORD = '2000Akbar!'
DATABASE = 'GAWDB'

def explore_database():
    """Comprehensive database exploration."""

    print("=" * 80)
    print("GAWDB Database Exploration Report")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Server: {SERVER}")
    print(f"Database: {DATABASE}")
    print("=" * 80)
    print()

    try:
        # Connect
        print("Connecting to SQL Server...")
        conn = pymssql.connect(
            server=SERVER,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            tds_version='7.0',
            timeout=30
        )
        cursor = conn.cursor()
        print("✅ Connected successfully!\n")

        # 1. SQL Server Version
        print("=" * 80)
        print("SQL SERVER VERSION")
        print("=" * 80)
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(version)
        print()

        # 2. Database Size
        print("=" * 80)
        print("DATABASE SIZE")
        print("=" * 80)
        cursor.execute("""
            SELECT
                database_name = DB_NAME(),
                log_size_mb = CAST(SUM(CASE WHEN type_desc = 'LOG' THEN size END) * 8. / 1024 AS DECIMAL(10,2)),
                data_size_mb = CAST(SUM(CASE WHEN type_desc = 'ROWS' THEN size END) * 8. / 1024 AS DECIMAL(10,2))
            FROM sys.master_files WITH(NOWAIT)
            WHERE database_id = DB_ID()
        """)
        size_info = cursor.fetchone()
        if size_info:
            print(f"Database: {size_info[0]}")
            print(f"Data Size: {size_info[2]:.2f} MB")
            print(f"Log Size: {size_info[1]:.2f} MB")
        print()

        # 3. List all tables
        print("=" * 80)
        print("DATABASE TABLES")
        print("=" * 80)
        cursor.execute("""
            SELECT
                TABLE_SCHEMA,
                TABLE_NAME,
                TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        tables = cursor.fetchall()

        table_list = []
        for schema, table, ttype in tables:
            table_list.append(f"{schema}.{table}")
            print(f"  {schema}.{table}")

        print(f"\nTotal Tables: {len(tables)}")
        print()

        # 4. Detailed table analysis
        print("=" * 80)
        print("TABLE DETAILS")
        print("=" * 80)

        table_details = {}

        for schema, table, ttype in tables:
            full_table = f"{schema}.{table}"
            print(f"\n--- {full_table} ---")

            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}]")
                row_count = cursor.fetchone()[0]
                print(f"Row Count: {row_count:,}")
            except Exception as e:
                row_count = 0
                print(f"Row Count: Unable to retrieve ({str(e)[:50]})")

            # Get columns
            cursor.execute(f"""
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()

            print(f"Columns ({len(columns)}):")
            col_info = []
            for col_name, data_type, max_len, nullable, default in columns:
                len_str = f"({max_len})" if max_len else ""
                null_str = "NULL" if nullable == 'YES' else "NOT NULL"
                print(f"  - {col_name}: {data_type}{len_str} {null_str}")
                col_info.append({
                    'name': col_name,
                    'type': data_type,
                    'max_length': max_len,
                    'nullable': nullable
                })

            # Get primary keys
            cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = '{schema}'
                  AND TABLE_NAME = '{table}'
                  AND CONSTRAINT_NAME LIKE 'PK%'
            """)
            pk_cols = [row[0] for row in cursor.fetchall()]
            if pk_cols:
                print(f"Primary Key: {', '.join(pk_cols)}")

            # Sample data (first 3 rows)
            if row_count > 0 and row_count < 1000000:
                try:
                    cursor.execute(f"SELECT TOP 3 * FROM [{schema}].[{table}]")
                    sample = cursor.fetchall()
                    if sample:
                        print("\nSample Data (first 3 rows):")
                        for i, row in enumerate(sample, 1):
                            print(f"  Row {i}: {str(row)[:200]}{'...' if len(str(row)) > 200 else ''}")
                except Exception as e:
                    print(f"  Unable to retrieve sample data: {str(e)[:50]}")

            table_details[full_table] = {
                'row_count': row_count,
                'columns': col_info,
                'primary_keys': pk_cols
            }

        # 5. Identify key tables (likely sales, products, customers)
        print("\n" + "=" * 80)
        print("KEY TABLE IDENTIFICATION")
        print("=" * 80)

        sales_keywords = ['sale', 'invoice', 'order', 'transaction', 'receipt']
        product_keywords = ['product', 'item', 'inventory', 'stock']
        customer_keywords = ['customer', 'client', 'account', 'member']

        print("\nLikely Sales Tables:")
        for table in table_list:
            if any(kw in table.lower() for kw in sales_keywords):
                rows = table_details[table]['row_count']
                print(f"  - {table} ({rows:,} rows)")

        print("\nLikely Product Tables:")
        for table in table_list:
            if any(kw in table.lower() for kw in product_keywords):
                rows = table_details[table]['row_count']
                print(f"  - {table} ({rows:,} rows)")

        print("\nLikely Customer Tables:")
        for table in table_list:
            if any(kw in table.lower() for kw in customer_keywords):
                rows = table_details[table]['row_count']
                print(f"  - {table} ({rows:,} rows)")

        # 6. Save detailed report to JSON
        report = {
            'generated_at': datetime.now().isoformat(),
            'server': SERVER,
            'database': DATABASE,
            'tables': table_details,
            'table_list': table_list
        }

        with open('database_exploration_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print("\n" + "=" * 80)
        print("✅ Exploration complete!")
        print("📄 Detailed report saved to: database_exploration_report.json")
        print("=" * 80)

        conn.close()

    except Exception as e:
        print(f"❌ Error during exploration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_database()
