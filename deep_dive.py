import pandas as pd

excel_file = '/Users/cherrytian/Documents/GitHub/ws1/WS1.xlsx'

try:
    df = pd.read_excel(excel_file, sheet_name='Sheet1')
    
    print("# Massive Deep Dive: LinkedIn Leads Analysis (WS1.xlsx)")
    print(f"**Total Records:** {len(df):,}\n")
    
    print("## 1. Data Completeness & Missing Values")
    print("| Column | Missing Values | % Missing |")
    print("|--------|----------------|-----------|")
    for col in df.columns:
        missing = df[col].isnull().sum()
        perc = (missing / len(df)) * 100
        print(f"| {col} | {missing:,} | {perc:.1f}% |")
    
    print("\n## 2. Industry Distribution (Top 15)")
    print("| Industry | Count | % of Total |")
    print("|----------|-------|------------|")
    ind_counts = df['Industry'].value_counts()
    for ind, count in ind_counts.head(15).items():
        perc = (count / len(df)) * 100
        print(f"| {ind} | {count:,} | {perc:.1f}% |")
        
    print("\n## 3. Job Title Analysis (Top 15)")
    print("| Job Title | Count |")
    print("|-----------|-------|")
    title_counts = df['Job Title'].value_counts()
    for title, count in title_counts.head(15).items():
        print(f"| {title} | {count:,} |")

    print("\n## 4. Top Companies (Top 15)")
    print("| Company Name | Count |")
    print("|--------------|-------|")
    comp_counts = df['Company Name'].value_counts()
    for comp, count in comp_counts.head(15).items():
        print(f"| {comp} | {count:,} |")
        
    print("\n## 5. Location Insights")
    print("### Geo Tag Distribution")
    geo_counts = df['Geo Tag'].value_counts()
    for geo, count in geo_counts.items():
        print(f"- **{geo}**: {count:,} ({(count/len(df))*100:.1f}%)")
        
    print("\n### Top Person Locations (Top 10)")
    loc_counts = df["Person's Location"].value_counts()
    for loc, count in loc_counts.head(10).items():
        print(f"- {loc}: {count:,}")
        
    print("\n## 6. Profile Status")
    
    open_counts = df['Open Profile?'].value_counts()
    print("\n### Open Profiles")
    for k, v in open_counts.items():
        print(f"- {k}: {v:,} ({(v/len(df))*100:.1f}%)")
        
    prem_counts = df['Premium LinkedIn?'].value_counts()
    print("\n### Premium LinkedIn Users")
    for k, v in prem_counts.items():
        print(f"- {k}: {v:,} ({(v/len(df))*100:.1f}%)")

except Exception as e:
    print(f"Error reading Excel file: {e}")
