#!/usr/bin/env python3
# Read the file
with open('/Users/akbarchranya/georgiadashboard/app/main.py', 'r') as f:
    lines = f.readlines()

# Find and fix the excise_reports issue
output = []
i = 0
fixed = False
while i < len(lines):
    line = lines[i]

    # If we find the broken line, add the excise_reports definition before it
    if 'all_reports.extend(excise_reports)' in line and not fixed:
        # Check if excise_reports is already defined in previous 20 lines
        prev_lines = ''.join(lines[max(0,i-20):i])
        if 'excise_reports = [' not in prev_lines:
            # Add excise_reports definition
            output.append('\n')
            output.append('        # Add Excise Tax Reports (using PUExciseEntry table directly - OPTIMIZED)\n')
            output.append('        # NOTE: Broken excise views (PUVIEWEXCISECOLLECT, etc.) removed - caused timeouts\n')
            output.append('        excise_reports = [\n')
            output.append("            {'id': 'excise_simple', 'name': 'Excise Tax Transactions', 'type': 'Excise Report', 'category': 'Tax Reports', 'description': 'Detailed excise tax transactions (FAST)'},\n")
            output.append("            {'id': 'pu_excise_summary', 'name': 'Daily Excise Tax Summary', 'type': 'Excise Report', 'category': 'Tax Reports', 'description': 'Daily excise tax totals (FAST)'},\n")
            output.append("            {'id': 'excise_by_category', 'name': 'Excise Tax by Category', 'type': 'Excise Report', 'category': 'Tax Reports', 'description': 'Excise tax by product category (FAST)'},\n")
            output.append('        ]\n')
            output.append('\n')
            fixed = True

    output.append(line)
    i += 1

# Write back
with open('/Users/akbarchranya/georgiadashboard/app/main.py', 'w') as f:
    f.writelines(output)

print("✅ Fixed excise_reports undefined variable")
