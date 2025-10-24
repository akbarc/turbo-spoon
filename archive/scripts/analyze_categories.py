import csv
from collections import Counter

items_file = 'Items- 06202025.csv'
sales_with_categories = 'Sales_with_Categories_06202025.csv'

print("Analyzing categories from Items data...")
all_categories = []
with open(items_file, 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2:
            category = row[1].strip()
            all_categories.append(category)

unique_categories = sorted(set(all_categories))
category_counts = Counter(all_categories)

print(f"\nTotal unique categories: {len(unique_categories)}")
print("\nAll unique category codes:")
print("-" * 40)
for cat in unique_categories:
    count = category_counts[cat]
    print(f"Category {cat:>3}: {count:>4} items")

# Now analyze which categories are actually used in sales
print("\n" + "="*50)
print("Categories actually used in Sales:")
print("="*50)

sales_categories = []
with open(sales_with_categories, 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    for row in reader:
        if len(row) >= 3:
            category = row[2].strip()
            sales_categories.append(category)

sales_category_counts = Counter(sales_categories)
sorted_sales_categories = sorted(sales_category_counts.items(), key=lambda x: int(x[0]) if x[0].lstrip('-').isdigit() else float('inf'))

print(f"\nCategories with sales (total {len(sorted_sales_categories)} categories):")
print("-" * 50)
for cat, count in sorted_sales_categories:
    print(f"Category {cat:>3}: {count:>5} sales transactions")

# Category mapping based on typical retail/grocery categories
category_names = {
    '-1': 'Unknown/Invalid',
    '0': 'Uncategorized/General',
    '1': 'Beverages - Soft Drinks',
    '2': 'Beverages - Juices',
    '3': 'Beverages - Water',
    '4': 'Beverages - Sports/Energy',
    '5': 'Beverages - Tea',
    '6': 'Snacks - Chips',
    '7': 'Snacks - Crackers',
    '8': 'Snacks - Nuts/Seeds',
    '9': 'Snacks - Popcorn',
    '10': 'Candy - Chocolate',
    '11': 'Candy - Gummies',
    '12': 'Candy - Hard Candy',
    '13': 'Candy - Mints',
    '14': 'Candy - Sour',
    '15': 'Cookies',
    '16': 'Cookies - Chocolate Chip',
    '17': 'Pastries/Baked Goods',
    '18': 'Breakfast Bars',
    '19': 'Granola/Cereal Bars',
    '20': 'Protein/Nutrition Bars',
    '21': 'Fruit Snacks',
    '22': 'Jerky/Meat Snacks',
    '23': 'Ice Cream/Frozen',
    '24': 'Dairy Products',
    '25': 'Coffee Products',
    '26': 'Hot Beverages',
    '27': 'Condiments/Sauces',
    '28': 'Seasoning/Spices',
    '29': 'Canned Goods',
    '30': 'Pasta/Noodles',
    '31': 'Rice/Grains',
    '32': 'Bread/Bakery',
    '33': 'Frozen Foods',
    '34': 'Fresh Produce',
    '35': 'Meat/Poultry',
    '36': 'Seafood',
    '37': 'Deli Items',
    '38': 'Cheese Products',
    '39': 'Health/Wellness',
    '40': 'Vitamins/Supplements',
    '41': 'Personal Care',
    '42': 'Household Items',
    '43': 'Paper Products',
    '44': 'Cleaning Supplies',
    '45': 'Pet Supplies',
    '46': 'Baby Products',
    '47': 'Tobacco Products',
    '48': 'Alcohol - Beer',
    '49': 'Alcohol - Wine',
    '50': 'Alcohol - Spirits',
    '51': 'Electronics/Batteries',
    '52': 'Office Supplies',
    '53': 'Seasonal Items',
    '54': 'Gift Cards',
    '55': 'Magazines/Books',
    '56': 'Lottery/Gaming',
    '57': 'Automotive',
    '58': 'Hardware/Tools',
    '59': 'Toys/Games',
    '60': 'Clothing/Apparel',
    '61': 'Footwear',
    '62': 'Accessories',
    '63': 'Cosmetics/Beauty',
    '64': 'Hair Care',
    '65': 'Skin Care',
    '66': 'Oral Care',
    '67': 'First Aid/Medical',
    '68': 'OTC Medicine',
    '69': 'Pain Relief',
    '70': 'Cold/Flu Medicine',
    '71': 'Digestive Health',
    '72': 'Allergy Medicine',
    '73': 'Eye/Ear Care',
    '74': 'Feminine Care',
    '75': 'Shaving/Grooming',
    '76': 'Deodorants',
    '77': 'Bath/Body',
    '78': 'Hand Sanitizer',
    '79': 'Face Masks',
    '80': 'Garden Supplies',
    '81': 'Outdoor/Camping',
    '82': 'Sports Equipment',
    '83': 'Fitness/Exercise',
    '84': 'School Supplies',
    '85': 'Art/Craft Supplies',
    '86': 'Party Supplies',
    '87': 'Greeting Cards',
    '88': 'Kitchen Utensils',
    '89': 'Cookware',
    '90': 'Storage Containers',
    '91': 'Disposable Plates/Cups',
    '92': 'Napkins/Tissues',
    '93': 'Toilet Paper',
    '94': 'Paper Towels',
    '95': 'Trash Bags',
    '96': 'Food Storage Bags',
    '97': 'Aluminum Foil/Wrap',
    '98': 'Laundry Detergent',
    '99': 'Fabric Softener',
    '100': 'Dish Soap',
    '101': 'Air Fresheners',
    '102': 'Candles',
    '103': 'Light Bulbs',
    '104': 'Batteries',
    '105': 'Phone Accessories',
    '106': 'Computer Accessories',
    '107': 'Audio/Video',
    '108': 'Travel Accessories',
    '109': 'Luggage/Bags',
    '110': 'Watches',
    '111': 'Jewelry',
    '112': 'Sunglasses',
    '113': 'Reading Glasses',
    '114': 'Contact Lens Care',
    '115': 'Dental Floss',
    '116': 'Mouthwash',
    '117': 'Toothbrushes',
    '118': 'Toothpaste',
    '119': 'Hand Lotion',
    '120': 'Body Lotion',
    '121': 'Sunscreen',
    '122': 'Lip Care',
    '123': 'Nail Care',
    '124': 'Hair Accessories',
    '125': 'Combs/Brushes',
    '126': 'Hair Styling',
    '127': 'Hair Color',
    '128': 'Shampoo',
    '129': 'Conditioner',
    '130': 'Body Wash',
    '131': 'Bar Soap',
    '132': 'Hand Soap',
    '133': 'Cotton Products',
    '134': 'Bandages',
    '135': 'Thermometers',
    '136': 'Blood Pressure Monitors',
    '137': 'Diabetic Supplies',
    '138': 'Hearing Aid Batteries',
    '139': 'Walking Aids',
    '140': 'Braces/Supports',
    '141': 'Hot/Cold Packs',
    '142': 'Insect Repellent',
    '143': 'Anti-Itch/Rash',
    '144': 'Antacids',
    '145': 'Laxatives',
    '146': 'Anti-Diarrheal',
    '147': 'Probiotics',
    '148': 'Sleep Aids',
    '149': 'Energy/Alertness',
    '150': 'Smoking Cessation'
}

print("\n" + "="*50)
print("Categories with descriptive names (used in sales):")
print("="*50)
for cat, count in sorted_sales_categories:
    name = category_names.get(cat, f'Category {cat}')
    print(f"{cat:>3}: {name:<35} ({count:>5} sales)")

print(f"\n{'='*50}")
print(f"SUMMARY:")
print(f"{'='*50}")
print(f"Total unique categories in Items file: {len(unique_categories)}")
print(f"Categories actually used in sales: {len(sorted_sales_categories)}")
print(f"Total sales transactions: {sum(sales_category_counts.values())}")