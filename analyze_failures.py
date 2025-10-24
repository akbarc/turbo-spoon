import pandas as pd
import re

def analyze_failed_addresses():
    """Analyze why addresses are failing to find patterns"""
    
    # Read the results
    df = pd.read_csv("/Users/akbarchranya/georgiadashboard/super_clean_results.csv")
    
    # Separate successful vs failed
    failed = df[df['geocoding_status'] == 'not_found'].copy()
    successful = df[df['geocoding_status'].str.contains('success', na=False)].copy()
    
    print(f"Analyzing {len(failed)} failed addresses vs {len(successful)} successful ones")
    
    print(f"\n=== FAILED ADDRESS PATTERNS ===")
    
    # Look for common patterns in failed addresses
    common_issues = {
        'MLK_VARIATIONS': [],
        'SUITE_ISSUES': [],
        'HIGHWAY_ISSUES': [],
        'MISSPELLINGS': [],
        'INCOMPLETE_STREETS': [],
        'WRONG_ABBREVIATIONS': []
    }
    
    for idx, row in failed.iterrows():
        addr = str(row['cleaned_address'])
        company = str(row['company'])
        
        # MLK variations
        if 'MLK' in addr:
            common_issues['MLK_VARIATIONS'].append((company, addr))
        
        # Suite issues
        if 'STE' in addr or 'SUITE' in addr:
            common_issues['SUITE_ISSUES'].append((company, addr))
        
        # Highway issues
        if any(x in addr for x in ['HWY', 'HIGHWAY']):
            common_issues['HIGHWAY_ISSUES'].append((company, addr))
        
        # Check for potential misspellings
        if any(x in addr.upper() for x in ['GAINSEVILLE', 'LAWRENCEVILL', 'ANNISTOWN']):
            common_issues['MISSPELLINGS'].append((company, addr))
        
        # Incomplete street names (no street type)
        if re.search(r'\d+\s+[A-Z\s]+,\s+[A-Z\s]+,\s+GA', addr) and not re.search(r'\b(ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|BLVD|BOULEVARD|HWY|HIGHWAY|WAY|LANE|LN|PKWY|PARKWAY|PL|PLACE|CT|COURT|CIR|CIRCLE)\b', addr):
            common_issues['INCOMPLETE_STREETS'].append((company, addr))
    
    # Print analysis
    for issue_type, addresses in common_issues.items():
        if addresses:
            print(f"\n{issue_type} ({len(addresses)} cases):")
            for company, addr in addresses[:5]:  # Show first 5
                print(f"  {company}: {addr}")
            if len(addresses) > 5:
                print(f"  ... and {len(addresses) - 5} more")
    
    print(f"\n=== SUCCESSFUL ADDRESS PATTERNS ===")
    print("Sample successful addresses:")
    for idx, row in successful.head(10).iterrows():
        print(f"  {row['company']}: {row['cleaned_address']}")
        print(f"    Found as: {row['found_address']}")
        print()

if __name__ == "__main__":
    analyze_failed_addresses()


