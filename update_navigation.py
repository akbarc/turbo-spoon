#!/usr/bin/env python3
"""
Script to update all template files with unified navigation
"""

import os
import re
from pathlib import Path

# Define the templates that need updating
TEMPLATES_TO_UPDATE = [
    'customer_ledger.html',
    'sales_ops.html', 
    'suppliers.html',
    'wholesale_retail_improved.html',
    'gp_analysis.html'
]

TEMPLATE_DIR = Path('/Users/akbarchranya/georgiadashboard/templates')

def update_template(filepath):
    """Update a single template file with unified navigation"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if '{% include \'shared_navigation.html\' %}' in content:
        print(f"✓ {filepath.name} already updated")
        return False
    
    # Pattern to find sidebar HTML
    sidebar_pattern = r'<div class="sidebar">.*?</div>\s*</div>'
    
    # Remove existing sidebar CSS
    # Pattern for sidebar CSS block
    css_sidebar_pattern = r'/\*.*?[Ss]idebar.*?\*/.*?\.sidebar\s*{[^}]*}.*?(?=\.main-content|/\*|<\/style>)'
    content = re.sub(css_sidebar_pattern, '', content, flags=re.DOTALL)
    
    # Remove nav-item CSS if it exists separately
    nav_css_pattern = r'\.nav-item\s*{[^}]*}.*?\.nav-item\.active\s*{[^}]*}'
    content = re.sub(nav_css_pattern, '', content, flags=re.DOTALL)
    
    # Update main-content CSS to remove margin-left
    content = re.sub(
        r'\.main-content\s*{\s*margin-left:\s*\d+px;',
        '.main-content {\n            /* margin-left removed for unified nav */',
        content
    )
    
    # Replace sidebar HTML with include
    if '<div class="sidebar">' in content:
        # Find the complete sidebar section
        start_idx = content.find('<div class="sidebar">')
        if start_idx != -1:
            # Find the matching closing div
            div_count = 1
            idx = start_idx + len('<div class="sidebar">')
            
            while div_count > 0 and idx < len(content):
                if content[idx:idx+4] == '<div':
                    div_count += 1
                    idx += 4
                elif content[idx:idx+6] == '</div>':
                    div_count -= 1
                    idx += 6
                else:
                    idx += 1
            
            # Replace sidebar with include
            sidebar_end = idx
            
            # Find where main content starts
            main_content_start = content.find('<div class="main-content">', sidebar_end)
            if main_content_start == -1:
                main_content_start = content.find('<!-- Main Content', sidebar_end)
            
            if main_content_start != -1:
                # Build replacement
                before_sidebar = content[:start_idx]
                after_sidebar = content[main_content_start:]
                
                # Update main-content div to main-content-wrapper
                after_sidebar = after_sidebar.replace(
                    '<div class="main-content">',
                    '<div class="main-content-wrapper">\n        <div class="main-content">',
                    1
                )
                
                # Add the include
                new_content = before_sidebar + \
                    '<!-- Include Shared Navigation -->\n    {% include \'shared_navigation.html\' %}\n\n    ' + \
                    after_sidebar
                
                content = new_content
    
    # Write updated content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {filepath.name}")
    return True

def main():
    """Main function to update all templates"""
    print("🚀 Starting navigation update for all templates...")
    
    updated_count = 0
    
    for template in TEMPLATES_TO_UPDATE:
        filepath = TEMPLATE_DIR / template
        if filepath.exists():
            if update_template(filepath):
                updated_count += 1
        else:
            print(f"❌ {template} not found")
    
    print(f"\n✨ Updated {updated_count} template files")
    print("💡 Remember to test all pages after update!")

if __name__ == "__main__":
    main()