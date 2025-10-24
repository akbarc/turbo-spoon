"""
Run customer grouping and export to CSV
"""

import sys
import os
import csv
from datetime import datetime

# Add modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ar.enhanced_customer_grouping import EnhancedCustomerGrouper

print('╔════════════════════════════════════════════════════════════════╗')
print('║         CUSTOMER GROUPING ANALYSIS & CSV EXPORT               ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

# Initialize grouper
print('Step 1: Initializing customer grouper...')
grouper = EnhancedCustomerGrouper()

# Find customer groups (using fuzzy matching by default)
print('Step 2: Finding customer groups with fuzzy matching...')
print('(This may take a minute...)')
groups = grouper.find_customer_groups(min_similarity=0.75, use_soundex=False)

if not groups:
    print('❌ No customer groups found.')
    sys.exit(0)

print(f'✅ Found {len(groups)} customer groups')
print()

# Prepare CSV data
print('Step 3: Preparing CSV data...')
csv_rows = []

for group in groups:
    group_id = group['group_id']
    primary = group['primary_customer']
    primary_first = primary.get('first_name') or ''
    primary_last = primary.get('last_name') or ''
    
    # Add each member as a row
    for member in group['members']:
        csv_rows.append({
            'CustomerID': member['id'],
            'GroupID': group_id,
            'GroupFirstName': primary_first,
            'GroupLastName': primary_last,
            'MemberName': member['name'],
            'MemberFirstName': member.get('first_name') or '',
            'MemberLastName': member.get('last_name') or '',
            'MemberPhone': member.get('phone') or '',
            'MemberEmail': member.get('email') or '',
            'AccountBalance': member['balance'],
            'CreditLimit': member['credit_limit'],
            'TotalGroupBalance': group['total_balance'],
            'GroupMemberCount': group['member_count'],
            'Confidence': group.get('confidence', '')
        })

print(f'✅ Prepared {len(csv_rows)} customer records in {len(groups)} groups')
print()

# Save to Downloads folder
downloads_path = os.path.expanduser('~/Downloads')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = os.path.join(downloads_path, f'customer_groups_{timestamp}.csv')

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
print(f'Total groups found:        {len(groups):>6}')
print(f'Total customers in groups: {len(csv_rows):>6}')
print(f'Total AR balance:          ${sum(row["TotalGroupBalance"] for row in csv_rows):>12,.2f}')
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
        print(f"{count:2}. {row['GroupFirstName']} {row['GroupLastName']:<25} "
              f"({row['GroupMemberCount']} members) - ${row['TotalGroupBalance']:>10,.2f}")

print()
print('✅ COMPLETE!')

