"""Extract stored procedures, views, and report definitions from GAWDB."""
import os
os.environ['TDSVER'] = '7.0'
import pymssql
import json

# Configuration
SERVER = '10.1.10.105'
USER = 'amchranya'
PASSWORD = '2000Akbar!'
DATABASE = 'GAWDB'

def extract_reports():
    """Extract all report definitions and SQL objects."""

    print("=" * 80)
    print("EXTRACTING REPORTS AND SQL QUERIES FROM GAWDB")
    print("=" * 80)
    print()

    results = {}

    try:
        conn = pymssql.connect(
            server=SERVER,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            tds_version='7.0',
            timeout=30
        )
        cursor = conn.cursor()
        print("✅ Connected\n")

        # 1. Get report definitions from Report table
        print("=" * 80)
        print("REPORT DEFINITIONS")
        print("=" * 80)
        cursor.execute("""
            SELECT ID, ReportFilename, Description, Settings
            FROM dbo.Report
            ORDER BY ID
        """)
        reports = cursor.fetchall()

        results['reports'] = []
        for report_id, filename, description, settings in reports:
            print(f"\n[{report_id}] {filename}")
            print(f"    Description: {description}")
            if settings:
                print(f"    Settings (first 500 chars): {str(settings)[:500]}")

            results['reports'].append({
                'id': report_id,
                'filename': filename,
                'description': description,
                'settings': str(settings)[:1000] if settings else None
            })

        # 2. Get all stored procedures
        print("\n" + "=" * 80)
        print("STORED PROCEDURES")
        print("=" * 80)
        cursor.execute("""
            SELECT
                ROUTINE_NAME,
                ROUTINE_DEFINITION
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE ROUTINE_TYPE = 'PROCEDURE'
            ORDER BY ROUTINE_NAME
        """)
        procedures = cursor.fetchall()

        results['stored_procedures'] = []
        print(f"\nFound {len(procedures)} stored procedures:\n")
        for name, definition in procedures:
            print(f"  - {name}")
            results['stored_procedures'].append({
                'name': name,
                'definition': definition
            })

        # 3. Get all views
        print("\n" + "=" * 80)
        print("VIEWS")
        print("=" * 80)
        cursor.execute("""
            SELECT
                TABLE_NAME,
                VIEW_DEFINITION
            FROM INFORMATION_SCHEMA.VIEWS
            ORDER BY TABLE_NAME
        """)
        views = cursor.fetchall()

        results['views'] = []
        print(f"\nFound {len(views)} views:\n")
        for name, definition in views:
            print(f"  - {name}")
            results['views'].append({
                'name': name,
                'definition': definition
            })

        # 4. Get any saved queries or templates
        print("\n" + "=" * 80)
        print("CHECKING FOR OTHER QUERY TABLES")
        print("=" * 80)

        # Look for common report-related tables
        check_tables = [
            'SavedQuery', 'QueryDefinition', 'ReportQuery',
            'ReportTemplate', 'CustomReport', 'UserQuery'
        ]

        for table_name in check_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM dbo.{table_name}")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"\n✅ Found dbo.{table_name} with {count} rows")
                    cursor.execute(f"SELECT TOP 5 * FROM dbo.{table_name}")
                    rows = cursor.fetchall()
                    print(f"Sample data: {rows}")
            except:
                pass  # Table doesn't exist

        # 5. Save everything to JSON
        with open('reports_and_queries.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print("\n" + "=" * 80)
        print("✅ EXTRACTION COMPLETE!")
        print("=" * 80)
        print(f"Found:")
        print(f"  - {len(results['reports'])} report definitions")
        print(f"  - {len(results['stored_procedures'])} stored procedures")
        print(f"  - {len(results['views'])} views")
        print("\n📄 Saved to: reports_and_queries.json")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    extract_reports()
