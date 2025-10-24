import pandas as pd
import re

def analyze_address_quality():
    """Check what the raw addresses look like"""
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Analyzing address quality from {len(df)} records...")
    
    print("\n=== RAW ADDRESS SAMPLES ===")
    for i in range(20):
        row = df.iloc[i]
        print(f"\nRecord {i+1}:")
        print(f"  Company: '{row.get('Company', 'N/A')}'")
        print(f"  Address: '{row.get('Address', 'N/A')}'")
        print(f"  City: '{row.get('City', 'N/A')}'")
        print(f"  State: '{row.get('State', 'N/A')}'")
        print(f"  Zip: '{row.get('Zip', 'N/A')}'")
        
        # Show what a combined address would look like
        addr = str(row.get('Address', '')).strip()
        city = str(row.get('City', '')).strip()
        state = str(row.get('State', 'GA')).strip()
        zip_code = str(row.get('Zip', '')).strip()
        
        if addr and addr != 'nan' and city and city != 'nan':
            combined = f"{addr}, {city}, {state}"
            if zip_code and zip_code != 'nan':
                zip_clean = re.sub(r'\.0$', '', zip_code)
                combined += f", {zip_clean}"
            print(f"  Combined: '{combined}'")
        else:
            print(f"  Combined: INVALID - missing address or city")
    
    # Check for common problems
    print(f"\n=== ADDRESS QUALITY ANALYSIS ===")
    
    # Check for empty addresses
    empty_addr = df['Address'].isna().sum()
    empty_city = df['City'].isna().sum()
    empty_state = df['State'].isna().sum()
    
    print(f"Empty addresses: {empty_addr}/{len(df)} ({empty_addr/len(df)*100:.1f}%)")
    print(f"Empty cities: {empty_city}/{len(df)} ({empty_city/len(df)*100:.1f}%)")
    print(f"Empty states: {empty_state}/{len(df)} ({empty_state/len(df)*100:.1f}%)")
    
    # Check for addresses that might need cleaning
    problematic = 0
    for idx, row in df.head(100).iterrows():
        addr = str(row.get('Address', '')).strip()
        if 'INC' in addr or 'LLC' in addr or not re.search(r'\d+', addr):
            problematic += 1
    
    print(f"Potentially problematic addresses (first 100): {problematic}/100")
    
    # Show some specific examples that might need cleaning
    print(f"\n=== ADDRESSES THAT NEED CLEANING ===")
    for idx, row in df.head(50).iterrows():
        addr = str(row.get('Address', '')).strip()
        if 'INC' in addr or 'LLC' in addr:
            print(f"  Has business suffix: '{addr}'")
        elif not re.search(r'\d+', addr):
            print(f"  No street number: '{addr}'")

if __name__ == "__main__":
    analyze_address_quality()
