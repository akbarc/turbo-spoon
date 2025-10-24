#!/usr/bin/env python3
"""Query all reports from database and display organized by category"""

import sys
sys.path.insert(0, '/Users/akbarchranya/georgiadashboard')
from database_pymssql import quick_query
import json

# Get all reports
reports_query = '''
SELECT
    ReportId,
    ReportName,
    ReportPath,
    ReportType,
    Category,
    Description,
    IsActive
FROM Report
ORDER BY Category, ReportName
'''

print('=== All Reports in Database ===\n')
try:
    df = quick_query(reports_query)
    print(f'Found {len(df)} total reports\n')

    # Group by category
    categories = {}
    for _, row in df.iterrows():
        cat = row.get('Category', 'Uncategorized') or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(row)

    # Print organized by category
    for cat in sorted(categories.keys()):
        print(f'\n{cat}:')
        print('-' * 80)
        for report in categories[cat]:
            active = '✓' if report.get('IsActive', True) else '✗'
            rtype = report.get('ReportType', 'N/A') or 'N/A'
            print(f"  [{active}] ID:{report['ReportId']:3d} | {report['ReportName']:50s} | Type:{rtype}")

    # Summary
    print(f'\n\n=== SUMMARY ===')
    print(f'Total reports: {len(df)}')
    print(f'Categories: {len(categories)}')
    for cat, reports in sorted(categories.items()):
        print(f'  {cat}: {len(reports)} reports')

    # Save to JSON for analysis
    report_data = df.to_dict('records')
    with open('/Users/akbarchranya/georgiadashboard/all_reports_inventory.json', 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    print('\n✅ Full report data saved to: all_reports_inventory.json')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
