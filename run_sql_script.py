#!/usr/bin/env python3
"""
Run SQL script to create vw_TransactionGrossProfit view
"""
import os
import sys

# Set TDS version BEFORE importing pymssql
os.environ['TDSVER'] = '7.0'

import pymssql

# Database configuration - Using sa account for CREATE VIEW permission
DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'sa',
    'password': 'Tech7World',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 60,
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

    conn = pymssql.connect(
        server=DB_CONFIG['server'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        tds_version=DB_CONFIG['tds_version'],
        timeout=DB_CONFIG['timeout'],
        login_timeout=DB_CONFIG['login_timeout']
    )

    cursor = conn.cursor()

    for i, command in enumerate(commands, 1):
        # Skip comments and empty lines
        if not command or command.startswith('--'):
            continue

        print(f"\nExecuting command {i}/{len(commands)}...")
        print(f"Command preview: {command[:100]}...")

        try:
            cursor.execute(command)
            conn.commit()
            print(f"✅ Command {i} executed successfully")
        except Exception as e:
            print(f"❌ Error executing command {i}: {e}")
            conn.rollback()
            # Continue with next command

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ SQL script execution completed!")

if __name__ == '__main__':
    script_path = 'sql/create_view_transaction_gross_profit.sql'

    if not os.path.exists(script_path):
        print(f"❌ Error: SQL file not found: {script_path}")
        sys.exit(1)

    try:
        run_sql_file(script_path)
        print("\n🎉 View 'vw_TransactionGrossProfit' should now be created!")
        print("You can now test it with: python3 data_foundation/gross_profit.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
