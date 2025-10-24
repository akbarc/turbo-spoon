#!/usr/bin/env python3
"""
Create GP_Daily_Summary table for fast category queries
"""
import os
import sys

os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'sa',  # Need SA permissions to create table
    'password': 'Tech7World',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 300,  # 5 minutes for initial population
    'login_timeout': 10
}

def run_sql_file(filepath):
    """Execute SQL commands from a file"""
    print(f"Reading SQL file: {filepath}")

    with open(filepath, 'r') as f:
        sql_content = f.read()

    # Split by GO statements
    commands = [cmd.strip() for cmd in sql_content.split('GO') if cmd.strip()]

    print(f"Found {len(commands)} SQL commands to execute")
    print("=" * 60)

    conn = pymssql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for i, command in enumerate(commands, 1):
        # Skip comments and empty lines
        if not command or command.startswith('--'):
            continue

        preview = command[:100].replace('\n', ' ')
        print(f"\n[{i}/{len(commands)}] {preview}...")

        try:
            cursor.execute(command)
            conn.commit()
            print(f"✅ Success")
        except Exception as e:
            error_str = str(e)
            if 'already exists' in error_str or 'Cannot drop' in error_str:
                print(f"⚠️  Warning: {e}")
                conn.rollback()
            else:
                print(f"❌ Error: {e}")
                conn.rollback()

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ SQL script execution completed!")

if __name__ == '__main__':
    script_path = 'sql/create_gp_daily_summary.sql'

    if not os.path.exists(script_path):
        print(f"❌ Error: SQL file not found: {script_path}")
        sys.exit(1)

    try:
        print("Creating GP_Daily_Summary table...")
        print("This will pre-calculate category GP for the last 30 days")
        print("This may take a few minutes...\n")

        run_sql_file(script_path)

        print("\n🎉 GP_Daily_Summary table created!")
        print("\n✅ What this gives you:")
        print("  • INSTANT category GP queries (pre-calculated)")
        print("  • Last 30 days of data already loaded")
        print("  • Automatic daily updates via stored procedure")
        print("\n📝 To update manually:")
        print("  EXEC sp_UpdateGPDailySummary '2025-10-15', '2025-10-15'")
        print("\n🚀 Test it now:")
        print("  python3 test_category_summary.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
