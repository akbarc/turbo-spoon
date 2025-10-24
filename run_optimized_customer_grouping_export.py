"""
Run OPTIMIZED customer grouping (same as dashboard) and export to CSV
Uses SQL SOUNDEX phonetic matching for fast performance
"""

import sys
import os
import csv
from datetime import datetime

# Add modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ar.optimized_customer_groups import OptimizedCustomerGrouper

print('╔════════════════════════════════════════════════════════════════╗')
print('║    OPTIMIZED CUSTOMER GROUPING (DASHBOARD VERSION) - EXPORT   ║')
print('║              Using SQL SOUNDEX Phonetic Matching              ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

# Initialize optimized grouper
print('Step 1: Initializing optimized customer grouper...')
grouper = OptimizedCustomerGrouper()

# Get all groups (no pagination limit for export)
print('Step 2: Finding customer groups with SOUNDEX matching...')
print('(This is much faster than fuzzy matching...)')

# Get summary with high limit to get all groups
summary = grouper.get_groups_summary(page=1, limit=1000, min_balance=0)

if not summary['groups']:
    print('❌ No customer groups found.')
    sys.exit(0)

print(f'✅ Found {summary["total_groups"]} customer groups')
print()

# Prepare CSV data
print('Step 3: Loading group members...')
csv_rows = []
groups_processed = 0

for group_summary in summary['groups']:
    groups_processed += 1
    if groups_processed % 10 == 0:
        print(f'   Processing group {groups_processed}/{len(summary["groups"])}...')
    
    group_key = group_summary['group_id']
    
    # Get full group preview to get all member names
    group_detail = grouper.get_group_preview(group_key)
    
    if not group_detail.get('members'):
        continue
    
    # Use the summary info for group names
    group_first = group_summary['first_name'] or ''
    group_last = group_summary['last_name'] or ''
    
    # Add each member as a row
    for member in group_detail['members']:
        csv_rows.append({
            'CustomerID': member['customer_id'],
            'GroupID': group_key,
            'GroupFirstName': group_first,
            'GroupLastName': group_last,
            'GroupDisplayName': f"{group_first} {group_last}".strip(),
            'MemberName': member['name'],
            'MemberCompany': member.get('company') or '',
            'AccountBalance': member['balance'],
            'LastVisit': member.get('last_visit') or '',
            'TotalGroupBalance': group_detail['total_balance'],
            'GroupMemberCount': group_summary['member_count'],
            'HasRecentActivity': 'Yes' if group_summary.get('has_recent_activity') else 'No',
            'MatchingMethod': 'SOUNDEX_Phonetic'
        })

print(f'✅ Prepared {len(csv_rows)} customer records in {groups_processed} groups')
print()

# Save to Downloads folder
downloads_path = os.path.expanduser('~/Downloads')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = os.path.join(downloads_path, f'customer_groups_optimized_{timestamp}.csv')

print(f'Step 4: Saving to {output_file}...')

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    if csv_rows:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)

print(f'✅ CSV file saved successfully!')
print()

# Print summary
print('═' * 70)
print('SUMMARY')
print('═' * 70)
print(f'Total groups found:        {groups_processed:>6}')
print(f'Total customers in groups: {len(csv_rows):>6}')
print(f'Total AR balance:          ${sum(row["TotalGroupBalance"] for row in csv_rows):>12,.2f}')
print(f'Matching method:           SOUNDEX (Phonetic)')
print()
print(f'📁 File location: {output_file}')
print()

# Show top 10 groups by balance
print('Top 10 Groups by Total Balance:')
print('-' * 70)
seen_groups = set()
count = 0
for row in sorted(csv_rows, key=lambda x: x['TotalGroupBalance'], reverse=True):
    if row['GroupID'] not in seen_groups and count < 10:
        seen_groups.add(row['GroupID'])
        count += 1
        print(f"{count:2}. {row['GroupDisplayName']:<30} "
              f"({row['GroupMemberCount']} members) - ${row['TotalGroupBalance']:>10,.2f}")

print()
print('✅ COMPLETE!')
print()
print('Note: This uses the SAME grouping algorithm as the dashboard.')
print('      Groups are matched by SOUNDEX (phonetic similarity).')

