import pandas as pd

def analyze_excel_detailed(file_path):
    """Detailed analysis of Excel file to find all columns and data"""
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
            print(f"All columns: {list(df.columns)}")
            
            # Show first few rows with all columns
            print(f"\nFirst 3 rows with ALL data:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 50)
            print(df.head(3).to_string())
            
            # Look for any column that might contain addresses
            print(f"\nLooking for address-related content in all columns:")
            for col in df.columns:
                sample_values = df[col].dropna().head(5).tolist()
                if sample_values:
                    print(f"\n{col}: {sample_values}")
    
    except Exception as e:
        print(f"Error analyzing Excel file: {e}")

if __name__ == "__main__":
    file_path = "/Users/akbarchranya/georgiadashboard/5.20 akbar (3).xlsx"
    analyze_excel_detailed(file_path)
