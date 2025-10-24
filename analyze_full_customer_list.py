import pandas as pd

def analyze_full_customer_list(file_path):
    """Analyze the full customer list Excel file"""
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        print(f"Excel file contains {len(excel_file.sheet_names)} sheet(s): {excel_file.sheet_names}")
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            if len(df) == 0:
                print(f"\n=== Sheet: {sheet_name} ===")
                print("Empty sheet")
                continue
                
            print(f"\n=== Sheet: {sheet_name} ===")
            print(f"Shape: {df.shape}")
            print(f"Total columns: {len(df.columns)}")
            
            # Show ALL column names with their index
            print("\nALL COLUMNS:")
            for i, col in enumerate(df.columns):
                print(f"{i:2d}: '{col}'")
            
            # Look for address-related columns
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
                print(f"\nFound potential address columns:")
                for idx, col in potential_address_cols:
                    print(f"  Column {idx}: '{col}'")
                    # Show sample data
                    sample_data = df[col].dropna().head(5).tolist()
                    print(f"    Sample data: {sample_data}")
            
            # Show first few rows
            print(f"\nFirst 3 rows of data:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 30)
            print(df.head(3).to_string())
    
    except Exception as e:
        print(f"Error analyzing Excel file: {e}")

if __name__ == "__main__":
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    analyze_full_customer_list(file_path)
