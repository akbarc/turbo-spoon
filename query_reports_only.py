#!/usr/bin/env python3
"""Query only dbo.Report table"""

import pymssql
import json
from datetime import datetime

SERVER = '10.0.12.13'
DATABASE = 'RMSStore'
USERNAME = 'sa'
PASSWORD = 'g30rg!@'

conn = pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE)
cursor = conn.cursor(as_dict=True)

print("Querying dbo.Report...")
cursor.execute("SELECT * FROM dbo.Report")
reports = cursor.fetchall()

print(f"\nFound {len(reports)} reports\n")
print("=" * 80)

for i, report in enumerate(reports, 1):
    print(f"\nReport #{i}:")
    for key, value in report.items():
        if value is not None and str(value).strip():
            print(f"  {key}: {value}")

# Save to JSON
output = {
    'timestamp': datetime.now().isoformat(),
    'total_reports': len(reports),
    'reports': reports
}

filename = f"POS_REPORTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(output, f, indent=2, default=str)

print(f"\n{'=' * 80}")
print(f"Saved to: {filename}")

cursor.close()
conn.close()
