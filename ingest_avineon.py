import pandas as pd
import duckdb
import re
import os

base_dir = os.path.dirname(__file__)
excel_file = os.path.join(base_dir, 'Avineon_Tensing.xlsx')
db_file = os.path.join(base_dir, 'leads.duckdb')

print("Reading Avineon_Tensing.xlsx ...")
df = pd.read_excel(excel_file, sheet_name='Sheet1')
print(f"  → {len(df):,} rows, {len(df.columns)} columns")

# Clean column names for easier SQL querying (same logic as original ingest.py)
def clean_col(name):
    name = str(name).strip()
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()

df.columns = [clean_col(c) for c in df.columns]

print("Columns renamed to:")
print(list(df.columns))

print(f"Connecting to DuckDB ({db_file}) ...")
con = duckdb.connect(db_file)

# Recreate the leads table
con.execute("DROP TABLE IF EXISTS leads")
print("Registering DataFrame and creating 'leads' table ...")
con.register('df_view', df)
con.execute("CREATE TABLE leads AS SELECT * FROM df_view")

count = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
print(f"Successfully loaded {count:,} rows into leads table.")

# --- Optional: load C-Suite Briefing if present ---
briefing_file = os.path.join(base_dir, 'csuite_briefing.md')
if os.path.exists(briefing_file):
    print("Loading C-Suite Briefing into DuckDB ...")
    with open(briefing_file, 'r', encoding='utf-8') as f:
        briefing_text = f.read()
    con.execute("DROP TABLE IF EXISTS csuite_briefing")
    con.execute("CREATE TABLE csuite_briefing (content TEXT)")
    con.execute("INSERT INTO csuite_briefing VALUES (?)", (briefing_text,))
    print("  → Done.")
else:
    print("Skipping C-Suite Briefing (file not found).")

# --- Optional: load NotebookLM template if present ---
nb_file = os.path.join(base_dir, 'notebooklm_template.md')
if os.path.exists(nb_file):
    print("Loading NotebookLM Template into DuckDB ...")
    with open(nb_file, 'r', encoding='utf-8') as f:
        nb_text = f.read()
    con.execute("DROP TABLE IF EXISTS notebooklm_template")
    con.execute("CREATE TABLE notebooklm_template (content TEXT)")
    con.execute("INSERT INTO notebooklm_template VALUES (?)", (nb_text,))
    print("  → Done.")
else:
    print("Skipping NotebookLM Template (file not found).")

con.close()
print(f"\nAll done! Upload '{os.path.basename(db_file)}' in the Streamlit sidebar.")
