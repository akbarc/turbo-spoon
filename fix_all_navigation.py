#!/usr/bin/env python3
"""
Fix navigation for all pages that need it
"""

import os
import re
from pathlib import Path

TEMPLATE_DIR = Path('/Users/akbarchranya/georgiadashboard/templates')

# Pages that need fixing
PAGES_TO_FIX = [
    'sales_ops.html',
    'customer_ledger.html', 
    'suppliers.html',
    'gp_analysis.html',
    'wholesale_retail_improved.html'
]

def create_fixed_template(original_file, new_file):
    """Create a fixed version of a template with unified navigation"""
    
    with open(original_file, 'r') as f:
        content = f.read()
    
    # Remove any existing sidebar CSS
    content = re.sub(r'/\*.*?[Ss]idebar.*?\*/.*?\.sidebar\s*\{[^}]*\}[^}]*\}', 
                     '/* Sidebar styles removed - using unified navigation */', 
                     content, flags=re.DOTALL)
    
    # Fix margin-left in main content
    content = re.sub(r'margin-left:\s*\d+px;', 'margin-left: 260px;', content)
    
    # Replace the sidebar HTML with the include
    # Look for patterns like <div class="sidebar"> or <!-- Sidebar --> or <nav class="sidebar">
    sidebar_patterns = [
        r'<!-- [Ss]idebar -->.*?</div>\s*</div>',
        r'<div class="sidebar">.*?</div>\s*</div>',
        r'<nav class="sidebar">.*?</nav>',
        r'<!-- Left Sidebar.*?</div>\s*</div>',
        r'<aside class="sidebar">.*?</aside>'
    ]
    
    for pattern in sidebar_patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, 
                           '<!-- Include Unified Navigation -->\n    {% include \'unified_navigation.html\' %}',
                           content, flags=re.DOTALL)
            break
    
    # If no sidebar found, add the include after body tag
    if '{% include \'unified_navigation.html\' %}' not in content:
        content = content.replace('<body>', 
                                '<body>\n    <!-- Include Unified Navigation -->\n    {% include \'unified_navigation.html\' %}')
    
    # Ensure main content has proper wrapper
    if 'main-content' in content and 'margin-left' not in content:
        content = re.sub(r'\.main-content\s*\{', '.main-content {\n            margin-left: 260px;', content)
    
    # Write the new file
    with open(new_file, 'w') as f:
        f.write(content)
    
    return new_file

def main():
    """Fix all templates"""
    print("🔧 Fixing navigation for all pages...")
    
    fixed_count = 0
    
    for template in PAGES_TO_FIX:
        original_path = TEMPLATE_DIR / template
        
        if original_path.exists():
            # Create new filename (e.g., sales_ops_new.html)
            new_name = template.replace('.html', '_new.html')
            new_path = TEMPLATE_DIR / new_name
            
            try:
                create_fixed_template(original_path, new_path)
                print(f"✅ Fixed: {template} -> {new_name}")
                fixed_count += 1
            except Exception as e:
                print(f"❌ Error fixing {template}: {e}")
        else:
            print(f"⚠️  {template} not found")
    
    print(f"\n✨ Fixed {fixed_count} templates")
    print("\n📝 Next steps:")
    print("1. Update dashboard_app.py to use the new templates")
    print("2. Add inventory route")
    print("3. Test all pages")

if __name__ == "__main__":
    main()