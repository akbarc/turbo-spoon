#!/usr/bin/env python3
"""
Query ALL POS database resources - Reports, Tables, and Views
Task 18: Complete inventory of POS system resources
"""

import pymssql
import json
from datetime import datetime

# Database connection details
SERVER = '10.0.12.13'
DATABASE = 'RMSStore'
USERNAME = 'sa'
PASSWORD = 'g30rg!@'

def get_all_reports():
    """Get all reports from dbo.Report table"""
    try:
        conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE)
        cursor = conn.cursor(as_dict=True)

        query = "SELECT * FROM dbo.Report"
        cursor.execute(query)
        reports = cursor.fetchall()

        cursor.close()
        conn.close()

        return reports
    except Exception as e:
        print(f"Error querying reports: {str(e)}")
        return []

def get_all_tables():
    """Get all tables from INFORMATION_SCHEMA.TABLES"""
    try:
        conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE)
        cursor = conn.cursor(as_dict=True)

        query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        cursor.execute(query)
        tables = cursor.fetchall()

        cursor.close()
        conn.close()

        return tables
    except Exception as e:
        print(f"Error querying tables: {str(e)}")
        return []

def get_all_views():
    """Get all views from INFORMATION_SCHEMA.VIEWS"""
    try:
        conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE)
        cursor = conn.cursor(as_dict=True)

        query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            VIEW_DEFINITION
        FROM INFORMATION_SCHEMA.VIEWS
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        cursor.execute(query)
        views = cursor.fetchall()

        cursor.close()
        conn.close()

        return views
    except Exception as e:
        print(f"Error querying views: {str(e)}")
        return []

def get_table_columns(table_name, schema='dbo'):
    """Get all columns for a specific table"""
    try:
        conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE)
        cursor = conn.cursor(as_dict=True)

        query = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, (schema, table_name))
        columns = cursor.fetchall()

        cursor.close()
        conn.close()

        return columns
    except Exception as e:
        print(f"Error querying columns for {schema}.{table_name}: {str(e)}")
        return []

def main():
    print("=" * 80)
    print("TASK 18: COMPLETE POS DATABASE RESOURCE INVENTORY")
    print("=" * 80)

    # Get all reports
    print("\n1. Querying dbo.Report table...")
    reports = get_all_reports()
    print(f"   Found {len(reports)} reports")

    # Get all tables
    print("\n2. Querying INFORMATION_SCHEMA.TABLES...")
    tables = get_all_tables()
    print(f"   Found {len(tables)} tables")

    # Get all views
    print("\n3. Querying INFORMATION_SCHEMA.VIEWS...")
    views = get_all_views()
    print(f"   Found {len(views)} views")

    # Display Reports
    print("\n" + "=" * 80)
    print("REPORTS (dbo.Report)")
    print("=" * 80)
    for i, report in enumerate(reports, 1):
        print(f"\nReport #{i}:")
        for key, value in report.items():
            if value is not None and str(value).strip():
                print(f"  {key}: {value}")

    # Display Tables Summary
    print("\n" + "=" * 80)
    print("TABLES (INFORMATION_SCHEMA.TABLES)")
    print("=" * 80)
    schema_groups = {}
    for table in tables:
        schema = table['TABLE_SCHEMA']
        if schema not in schema_groups:
            schema_groups[schema] = []
        schema_groups[schema].append(table['TABLE_NAME'])

    for schema, table_names in sorted(schema_groups.items()):
        print(f"\nSchema: {schema} ({len(table_names)} tables)")
        for table_name in sorted(table_names):
            print(f"  - {table_name}")

    # Display Views Summary
    print("\n" + "=" * 80)
    print("VIEWS (INFORMATION_SCHEMA.VIEWS)")
    print("=" * 80)
    view_groups = {}
    for view in views:
        schema = view['TABLE_SCHEMA']
        if schema not in view_groups:
            view_groups[schema] = []
        view_groups[schema].append(view['TABLE_NAME'])

    for schema, view_names in sorted(view_groups.items()):
        print(f"\nSchema: {schema} ({len(view_names)} views)")
        for view_name in sorted(view_names):
            print(f"  - {view_name}")

    # Save detailed results to JSON
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'database': DATABASE,
        'summary': {
            'total_reports': len(reports),
            'total_tables': len(tables),
            'total_views': len(views)
        },
        'reports': reports,
        'tables': tables,
        'views': [{'schema': v['TABLE_SCHEMA'], 'name': v['TABLE_NAME']} for v in views]
    }

    output_file = f"POS_COMPLETE_INVENTORY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)

    print(f"\n" + "=" * 80)
    print(f"Complete inventory saved to: {output_file}")
    print("=" * 80)

    # Get detailed column info for Report table
    print("\n" + "=" * 80)
    print("DETAILED SCHEMA: dbo.Report")
    print("=" * 80)
    report_columns = get_table_columns('Report')
    for col in report_columns:
        print(f"\n  Column: {col['COLUMN_NAME']}")
        print(f"    Type: {col['DATA_TYPE']}", end="")
        if col['CHARACTER_MAXIMUM_LENGTH']:
            print(f"({col['CHARACTER_MAXIMUM_LENGTH']})", end="")
        print()
        print(f"    Nullable: {col['IS_NULLABLE']}")
        if col['COLUMN_DEFAULT']:
            print(f"    Default: {col['COLUMN_DEFAULT']}")

if __name__ == "__main__":
    main()
