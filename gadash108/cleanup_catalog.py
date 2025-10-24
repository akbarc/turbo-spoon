import csv
import re

print("Cleaning up master_product_catalog_ENHANCED.csv...")

# Category mapping for invalid categories
CATEGORY_FIXES = {
    'Miscellaneous': 'Specialty Products',
    'Clothing & Apparel': 'General Merchandise',
    'Hardware & Tools': 'General Merchandise',
    'Electronics': 'General Merchandise',
    'Toys & Games': 'General Merchandise',
    'Smoking Accessories': 'Tobacco Accessories'
}

# Subcategory mapping for Miscellaneous
SUBCATEGORY_FIXES = {
    'Miscellaneous': {
        'Automotive': 'Car Accessories',
        'Beverages': 'Soft Drinks',
        'Specialty Products': 'Miscellaneous',  # Keep as is
        'General Merchandise': 'Miscellaneous',  # Keep as is
    }
}

def extract_size_from_description(desc):
    """Extract size from description if AI missed it"""
    desc = desc.upper()

    # Look for patterns like "12CT", "1.5OZ", "24PK", etc.
    patterns = [
        r'(\d+\.?\d*)\s*(OZ|ML|CT|PK|LB|G|MG|L|GAL|PACK)',
        r'(\d+)\s*(COUNT)',
        r'(\d+)/(\d+)\s*(OZ|CT|PK)',
    ]

    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1)} {match.group(2).lower()}"
            elif len(match.groups()) == 3:
                return f"{match.group(1)}/{match.group(2)} {match.group(3).lower()}"

    return None

# Read the file
with open('master_product_catalog_ENHANCED.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    items = list(reader)
    fieldnames = reader.fieldnames

fixed_categories = 0
fixed_subcategories = 0
fixed_sizes = 0

# Fix issues
for item in items:
    # Fix invalid main categories
    if item['MainCategory'] in CATEGORY_FIXES:
        item['MainCategory'] = CATEGORY_FIXES[item['MainCategory']]
        fixed_categories += 1

    # Fix Miscellaneous subcategories based on main category
    if item['Subcategory'] == 'Miscellaneous':
        main_cat = item['MainCategory']
        if main_cat in SUBCATEGORY_FIXES['Miscellaneous']:
            # Keep as Miscellaneous for now - would need more specific logic
            pass
        fixed_subcategories += 1

    # Fix missing sizes
    if item['Size'] == '1 count' or not item['Size'].strip():
        extracted = extract_size_from_description(item['Description'])
        if extracted:
            item['Size'] = extracted
            fixed_sizes += 1

# Write back
with open('master_product_catalog_ENHANCED.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(items)

print(f"✅ Cleanup complete!")
print(f"   Fixed {fixed_categories} invalid categories")
print(f"   Found {fixed_subcategories} Miscellaneous subcategories")
print(f"   Fixed {fixed_sizes} missing sizes")
print()

# Show final stats
from collections import Counter
categories = Counter(item['MainCategory'] for item in items)
subcategories = Counter(item['Subcategory'] for item in items)

print("FINAL CATEGORY DISTRIBUTION:")
for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cat:<35} {count:>5} items")

print()
print(f"Total unique categories: {len(categories)}")
print(f"Total unique subcategories: {len(subcategories)}")
