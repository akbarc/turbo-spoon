import pandas as pd

def check_all_columns(file_path):
    """Check ALL columns in the Excel file, including hidden or far-right columns"""
    try:
        # Read with no limits
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        
        print(f"Total shape: {df.shape}")
        print(f"Total columns: {len(df.columns)}")
        
        # Show ALL column names with their index
        print("\nALL COLUMNS:")
        for i, col in enumerate(df.columns):
            print(f"{i:2d}: '{col}'")
        
        # Check for columns that might contain addresses
        print(f"\nLooking for address-related columns:")
        address_keywords = ['address', 'addr', 'street', 'st', 'avenue', 'ave', 'road', 'rd', 
                          'drive', 'dr', 'lane', 'ln', 'boulevard', 'blvd', 'highway', 'hwy',
                          'city', 'state', 'zip', 'postal', 'location', 'loc']
        
        potential_address_cols = []
        for i, col in enumerate(df.columns):
            col_lower = str(col).lower()
            for keyword in address_keywords:
                if keyword in col_lower:
                    potential_address_cols.append((i, col))
                    break
        
        if potential_address_cols:
            print("Found potential address columns:")
            for idx, col in potential_address_cols:
                print(f"  Column {idx}: '{col}'")
                # Show sample data
                sample_data = df[col].dropna().head(10).tolist()
                print(f"    Sample data: {sample_data[:3]}")
        
        # Show data from columns beyond the first 13
        if len(df.columns) > 13:
            print(f"\nColumns beyond index 13:")
            for i in range(13, len(df.columns)):
                col = df.columns[i]
                sample_data = df[col].dropna().head(5).tolist()
                print(f"  Column {i}: '{col}' - Sample: {sample_data[:3] if sample_data else 'No data'}")
        
        # Try to find any column with actual address-like content
        print(f"\nScanning ALL columns for address-like content:")
        for i, col in enumerate(df.columns):
            # Get non-null values
            non_null_data = df[col].dropna()
            if len(non_null_data) > 0:
                # Check if any values look like addresses
                sample_values = non_null_data.head(10).astype(str).tolist()
                for val in sample_values:
                    val_str = str(val).upper()
                    # Look for street indicators
                    if any(street in val_str for street in ['STREET', 'ST ', ' ST', 'AVENUE', 'AVE ', ' AVE', 
                                                          'ROAD', 'RD ', ' RD', 'DRIVE', 'DR ', ' DR',
                                                          'LANE', 'LN ', ' LN', 'BOULEVARD', 'BLVD', 'HIGHWAY', 'HWY']):
                        print(f"  Column {i} '{col}' has address-like content: {val}")
                        break
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    file_path = "/Users/akbarchranya/georgiadashboard/5.20 akbar (3).xlsx"
    check_all_columns(file_path)
