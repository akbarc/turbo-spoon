"""
Export existing SOUNDEX customer groups to CSV for manual editing.

This creates a CSV file with all current groups that you can edit and use as
the source of truth going forward.
"""

import csv
from datetime import datetime
from src.database.overlay_db import overlay_db

print("=" * 70)
print("EXPORT CUSTOMER GROUPS TO CSV")
print("=" * 70)
print()

# Get all groups and members
print("Step 1: Loading groups from overlay database...")
groups_df = overlay_db.get_soundex_groups()

if groups_df.empty:
    print("❌ No groups found. Please run customer sync first.")
    exit(1)

print(f"✅ Found {len(groups_df)} groups")
print()

# Prepare CSV data
print("Step 2: Loading group members...")
csv_rows = []

for _, group in groups_df.iterrows():
    group_id = int(group['id'])
    group_name = group['group_name']

    # Get members for this group
    members_df = overlay_db.get_group_members(group_id)

    for _, member in members_df.iterrows():
        csv_rows.append({
            'GroupName': group_name,
            'CustomerID': int(member['customer_id']),
            'CustomerName': member['customer_name'],
            'Company': member['customer_company'] or ''
        })

print(f"✅ Found {len(csv_rows)} customer-group assignments")
print()

# Save to CSV
output_file = 'customer_groups.csv'
print(f"Step 3: Saving to {output_file}...")

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    # Write header with instructions
    f.write("# Customer Groups Configuration\n")
    f.write("#\n")
    f.write("# Edit this file to:\n")
    f.write("#  - Rename groups (change GroupName column)\n")
    f.write("#  - Move customers between groups (change GroupName for that customer)\n")
    f.write("#  - Remove customers from groups (delete the row)\n")
    f.write("#\n")
    f.write("# After editing, the dashboard will use this file as the source of truth.\n")
    f.write("# Dashboard will reload this file on startup (no database queries needed).\n")
    f.write("#\n")
    f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("#\n")
    f.write("\n")

    # Write CSV data
    if csv_rows:
        writer = csv.DictWriter(f, fieldnames=['GroupName', 'CustomerID', 'CustomerName', 'Company'])
        writer.writeheader()
        writer.writerows(csv_rows)

print("✅ CSV file created successfully!")
print()
print("=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print()
print(f"1. Open {output_file} in Excel or a text editor")
print("2. Edit group names as needed")
print("3. Move customers between groups by changing their GroupName")
print("4. Save the file")
print("5. Restart the dashboard - it will load from the CSV")
print()
print("The dashboard will be MUCH faster because it reads from the CSV")
print("instead of querying the database every time!")
print()
