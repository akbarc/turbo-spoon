#!/usr/bin/env python3
"""Quick POS inventory without heavy queries"""

import pymssql

SERVER = '10.0.12.13'
DATABASE = 'RMSStore'
USERNAME = 'sa'
PASSWORD = 'g30rg!@'

print("Connecting to POS database...")
conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE)
cursor = conn.cursor(as_dict=True)

# 1. Get Reports
print("\n" + "=" * 80)
print("1. QUERYING dbo.Report")
print("=" * 80)
cursor.execute("SELECT TOP 100 * FROM dbo.Report")
reports = cursor.fetchall()
print(f"Found {len(reports)} reports (showing first 100)")

for i, report in enumerate(reports, 1):
    print(f"\n#{i}:")
    for key, value in report.items():
        if value is not None:
            val_str = str(value).strip()
            if val_str:
                print(f"  {key}: {val_str[:200]}")

# 2. Get Tables
print("\n" + "=" * 80)
print("2. QUERYING ALL TABLES")
print("=" * 80)
cursor.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    ORDER BY TABLE_SCHEMA, TABLE_NAME
""")
tables = cursor.fetchall()
print(f"Found {len(tables)} tables/views")

schema_groups = {}
for table in tables:
    schema = table['TABLE_SCHEMA']
    ttype = table['TABLE_TYPE']
    if schema not in schema_groups:
        schema_groups[schema] = {'BASE TABLE': [], 'VIEW': []}
    if ttype in schema_groups[schema]:
        schema_groups[schema][ttype].append(table['TABLE_NAME'])

for schema in sorted(schema_groups.keys()):
    base_tables = schema_groups[schema].get('BASE TABLE', [])
    views = schema_groups[schema].get('VIEW', [])

    if base_tables:
        print(f"\n{schema} TABLES ({len(base_tables)}):")
        for name in sorted(base_tables):
            print(f"  - {name}")

    if views:
        print(f"\n{schema} VIEWS ({len(views)}):")
        for name in sorted(views):
            print(f"  - {name}")

# 3. Get Views (just names, no definitions)
print("\n" + "=" * 80)
print("3. VIEW NAMES ONLY")
print("=" * 80)
cursor.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.VIEWS
    ORDER BY TABLE_SCHEMA, TABLE_NAME
""")
views = cursor.fetchall()
print(f"Total views: {len(views)}\n")

for view in views:
    print(f"  {view['TABLE_SCHEMA']}.{view['TABLE_NAME']}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("INVENTORY COMPLETE")
print("=" * 80)
