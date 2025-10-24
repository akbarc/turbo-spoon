#!/usr/bin/env python3
"""Get complete inventory of all reports from database"""

import sys
sys.path.insert(0, '/Users/akbarchranya/georgiadashboard')
from database_pymssql import quick_query
import json
from collections import defaultdict

print('=' * 100)
print('POS REPORTS COMPLETE INVENTORY')
print('=' * 100)

# Get all reports
reports_query = '''
SELECT
    ID,
    ReportFilename,
    Description,
    Settings,
    StoreID
FROM Report
ORDER BY ReportFilename, Description
'''

try:
    df = quick_query(reports_query)
    print(f'\n✅ Found {len(df)} total reports in database\n')

    # Parse report filenames to extract report types
    report_types = defaultdict(list)
    excise_reports = []

    for _, row in df.iterrows():
        filename = row['ReportFilename']
        description = row['Description']
        report_id = row['ID']

        # Extract report type from filename
        if 'CrystalReports\\' in filename:
            report_type = filename.split('CrystalReports\\')[-1].replace('.def', '')
        else:
            report_type = filename.split('\\')[-1].replace('.def', '')

        report_types[report_type].append({
            'id': report_id,
            'description': description,
            'filename': filename
        })

        # Check for excise-related reports
        desc_lower = description.lower()
        if 'excise' in desc_lower or 'tax' in desc_lower:
            excise_reports.append({
                'id': report_id,
                'type': report_type,
                'description': description,
                'filename': filename
            })

    # Print report types summary
    print(f'📊 REPORT TYPES SUMMARY')
    print('-' * 100)
    print(f'Total unique report types: {len(report_types)}\n')

    for report_type in sorted(report_types.keys()):
        reports = report_types[report_type]
        print(f'\n{report_type} ({len(reports)} variants):')
        for r in reports[:5]:  # Show first 5
            print(f'  ID {r["id"]:4d}: {r["description"][:60]}')
        if len(reports) > 5:
            print(f'  ... and {len(reports) - 5} more')

    # Print excise reports
    print(f'\n\n🔖 EXCISE/TAX RELATED REPORTS')
    print('-' * 100)
    print(f'Found {len(excise_reports)} excise/tax related reports:\n')
    for r in excise_reports:
        print(f'  ID {r["id"]:4d}: [{r["type"]:20s}] {r["description"]}')

    # Get unique report types (base Crystal Reports)
    unique_types = sorted(set(report_types.keys()))
    print(f'\n\n📋 UNIQUE CRYSTAL REPORT TYPES')
    print('-' * 100)
    print(f'Total: {len(unique_types)}\n')
    for i, rtype in enumerate(unique_types, 1):
        count = len(report_types[rtype])
        print(f'{i:3d}. {rtype:40s} ({count} memorized variants)')

    # Save complete inventory to JSON
    inventory_data = {
        'total_reports': len(df),
        'unique_report_types': len(unique_types),
        'report_types': {k: v for k, v in report_types.items()},
        'excise_reports': excise_reports,
        'all_reports': df.to_dict('records')
    }

    with open('/Users/akbarchranya/georgiadashboard/COMPLETE_REPORTS_INVENTORY.json', 'w') as f:
        json.dump(inventory_data, f, indent=2, default=str)

    print(f'\n\n✅ Complete inventory saved to: COMPLETE_REPORTS_INVENTORY.json')
    print(f'\n' + '=' * 100)

except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
