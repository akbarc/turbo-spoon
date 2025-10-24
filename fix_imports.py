#!/usr/bin/env python3
"""
Quick fix for import paths in app files
"""
import os

print("Fixing import paths...")

# Fix app/customer_ledger_api.py
file_path = 'app/customer_ledger_api.py'
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    content = content.replace('from customer_ledger import', 'from app.customer_ledger import')
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"✅ Fixed {file_path}")

# Fix app/ar_dashboard.py
file_path = 'app/ar_dashboard.py'
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    if 'sys.path.append' not in content:
        # Add import fix at the top
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'import' in line and 'from' not in line:
                lines.insert(i, 'import sys, os')
                lines.insert(i+1, 'sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))')
                break
        content = '\n'.join(lines)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Fixed {file_path}")

print("\nImport paths fixed! You can now run: python3 run.py")