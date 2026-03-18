import pandas as pd

excel_file = '/Users/cherrytian/Documents/GitHub/ws1/WS1.xlsx'
print(f"Analyzing {excel_file}...")

try:
    xl = pd.ExcelFile(excel_file)
    print(f"\nSheets found: {xl.sheet_names}\n")
    
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        print(f"--- Sheet: {sheet} ---")
        print(f"Dimensions: {df.shape[0]} rows, {df.shape[1]} columns")
        print("Columns:\n", list(df.columns))
        print("\nData Sample (first 5 rows):")
        print(df.head())
        print("="*50 + "\n")
except Exception as e:
    print(f"Error reading Excel file: {e}")
