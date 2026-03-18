import pandas as pd
import duckdb
import re

import os

base_dir = os.path.dirname(__file__)
excel_file = os.path.join(base_dir, 'WS1.xlsx')
db_file = os.path.join(base_dir, 'leads.duckdb')

print("Reading Excel file...")
df = pd.read_excel(excel_file, sheet_name='Sheet1')

# Clean column names for easier SQL querying
def clean_col(name):
    name = str(name).strip()
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()

df.columns = [clean_col(c) for c in df.columns]

print("Columns renamed to:")
print(list(df.columns))

print("Connecting to DuckDB...")
con = duckdb.connect(db_file)

# We will recreate the table each time
con.execute("DROP TABLE IF EXISTS leads")
print("Registering DataFrame and creating table...")
con.register('df_view', df)
con.execute("CREATE TABLE leads AS SELECT * FROM df_view")

con.execute("SELECT COUNT(*) FROM leads").fetchone()
count = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
print(f"Successfully loaded {count} rows into '{db_file}'.")

print("Loading C-Suite Briefing into DuckDB...")
briefing_file = os.path.join(base_dir, 'csuite_briefing.md')
try:
    with open(briefing_file, 'r', encoding='utf-8') as f:
        briefing_text = f.read()
    con.execute("DROP TABLE IF EXISTS csuite_briefing")
    con.execute("CREATE TABLE csuite_briefing (content TEXT)")
    con.execute("INSERT INTO csuite_briefing VALUES (?)", (briefing_text,))
    print("Successfully loaded C-Suite Briefing.")
except Exception as e:
    print(f"Warning: Could not load C-Suite Briefing. Error: {e}")

con.close()
