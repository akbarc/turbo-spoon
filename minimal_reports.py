#!/usr/bin/env python3
"""Minimal report query"""

import pymssql
import sys

SERVER = '10.0.12.13'
DATABASE = 'RMSStore'
USERNAME = 'sa'
PASSWORD = 'g30rg!@'

try:
    print("Connecting...", file=sys.stderr)
    conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE, timeout=10, login_timeout=10)
    cursor = conn.cursor(as_dict=True)

    print("Checking if Report table exists...", file=sys.stderr)
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = 'Report'
    """)
    result = cursor.fetchone()
    print(f"Report table exists: {result['cnt'] > 0}", file=sys.stderr)

    if result['cnt'] > 0:
        print("Getting Report columns...", file=sys.stderr)
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Report'
            ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        print(f"Report columns: {[c['COLUMN_NAME'] for c in columns]}")

        print("Getting Report count...", file=sys.stderr)
        cursor.execute("SELECT COUNT(*) as cnt FROM dbo.Report")
        count = cursor.fetchone()
        print(f"Total reports in table: {count['cnt']}")

        print("Getting first 5 reports...", file=sys.stderr)
        cursor.execute("SELECT TOP 5 * FROM dbo.Report")
        reports = cursor.fetchall()

        for i, report in enumerate(reports, 1):
            print(f"\nReport #{i}:")
            for key, value in report.items():
                print(f"  {key}: {value}")

    cursor.close()
    conn.close()
    print("\nDone!", file=sys.stderr)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
