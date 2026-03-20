import pandas as pd
import duckdb
import re
import os

base_dir = os.path.dirname(__file__)
excel_file = os.path.join(base_dir, 'Avineon_Tensing_Cr2V022.xlsx')
db_file = os.path.join(base_dir, 'cr2v022_leads.duckdb')

print("Reading Avineon_Tensing_Cr2V022.xlsx ...")
df = pd.read_excel(excel_file, sheet_name='Sheet1')
print(f"  → {len(df):,} rows, {len(df.columns)} columns")

# Clean column names for easier SQL querying (same logic as other ingest scripts)
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

# ---------------------------------------------------------------------------
# Generate C-Suite Strategy Deck dynamically from the ingested data
# ---------------------------------------------------------------------------
print("\nGenerating C-Suite Strategy Deck from live data ...")

total = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

# Geo breakdown
geo_rows = con.execute("""
    SELECT geo_tag, COUNT(*) as cnt,
           ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads), 1) as pct
    FROM leads WHERE geo_tag IS NOT NULL
    GROUP BY geo_tag ORDER BY cnt DESC
""").fetchall()

# Premium & Open profile stats
premium_count = con.execute("SELECT COUNT(*) FROM leads WHERE premium_linkedin_ = True").fetchone()[0]
open_count = con.execute("SELECT COUNT(*) FROM leads WHERE open_profile_ = True").fetchone()[0]
pct_premium = round(premium_count / total * 100, 1) if total else 0
pct_open = round(open_count / total * 100, 1) if total else 0
inmail_savings = open_count * 2  # $2 per InMail

# Top locations
top_locations = con.execute("""
    SELECT person_s_location, COUNT(*) as cnt,
           ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads), 1) as pct
    FROM leads WHERE person_s_location IS NOT NULL
    GROUP BY person_s_location ORDER BY cnt DESC LIMIT 6
""").fetchall()

# Top industries
top_industries = con.execute("""
    SELECT industry, COUNT(*) as cnt
    FROM leads WHERE industry IS NOT NULL
    GROUP BY industry ORDER BY cnt DESC LIMIT 10
""").fetchall()

# Top 3 industries share
top3_ind_count = sum(r[1] for r in top_industries[:3])
top3_ind_pct = round(top3_ind_count / total * 100, 1) if total else 0

# Seniority breakdown
seniority = con.execute("""
    SELECT
        CASE
            WHEN job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%'
                 OR job_title ILIKE '%CFO%' OR job_title ILIKE '%Founder%' OR job_title ILIKE '%Co-Founder%'
                 THEN 'C-Level & Founders'
            WHEN job_title ILIKE '%VP%' OR job_title ILIKE '%Vice President%' THEN 'VP Level'
            WHEN job_title ILIKE '%Director%' THEN 'Directors'
            WHEN job_title ILIKE '%Manager%' OR job_title ILIKE '%Head%' THEN 'Managers & Heads'
            ELSE 'Individual Contributors'
        END as band,
        COUNT(*) as cnt
    FROM leads WHERE job_title IS NOT NULL
    GROUP BY band ORDER BY cnt DESC
""").fetchall()

titled_total = sum(r[1] for r in seniority) if seniority else 1
seniority_pcts = {r[0]: round(r[1] / titled_total * 100, 1) for r in seniority}

# Top individual titles
top_titles = con.execute("""
    SELECT job_title, COUNT(*) as cnt
    FROM leads WHERE job_title IS NOT NULL
    GROUP BY job_title ORDER BY cnt DESC LIMIT 10
""").fetchall()

# Top companies
top_companies = con.execute("""
    SELECT company_name, COUNT(*) as cnt
    FROM leads WHERE company_name IS NOT NULL
    GROUP BY company_name ORDER BY cnt DESC LIMIT 8
""").fetchall()

# Decision-maker segments for TAM
tam_segments = con.execute("""
    SELECT
        CASE
            WHEN job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%'
                 OR job_title ILIKE '%CFO%' OR job_title ILIKE '%Founder%' OR job_title ILIKE '%Co-Founder%'
                 THEN 'C-Level & Founders'
            WHEN job_title ILIKE '%Director%' OR job_title ILIKE '%Managing Director%' THEN 'Directors'
            WHEN job_title ILIKE '%Manager%' OR job_title ILIKE '%Head%' THEN 'Managers & Heads'
            ELSE NULL
        END as band,
        COUNT(*) as cnt
    FROM leads WHERE job_title IS NOT NULL
    GROUP BY band HAVING band IS NOT NULL
    ORDER BY cnt DESC
""").fetchall()

open_decision_makers = con.execute("""
    SELECT COUNT(*) FROM leads
    WHERE open_profile_ = True
    AND (job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%'
         OR job_title ILIKE '%Director%' OR job_title ILIKE '%Founder%'
         OR job_title ILIKE '%Managing Director%' OR job_title ILIKE '%Partner%'
         OR job_title ILIKE '%Owner%')
""").fetchone()[0]

# Data quality
missing_company = con.execute("SELECT ROUND(100.0 - COUNT(company_name) * 100.0 / COUNT(*), 1) FROM leads").fetchone()[0]
missing_industry = con.execute("SELECT ROUND(100.0 - COUNT(industry) * 100.0 / COUNT(*), 1) FROM leads").fetchone()[0]
missing_title = con.execute("SELECT ROUND(100.0 - COUNT(job_title) * 100.0 / COUNT(*), 1) FROM leads").fetchone()[0]
missing_hq = con.execute("SELECT ROUND(100.0 - COUNT(company_hq) * 100.0 / COUNT(*), 1) FROM leads").fetchone()[0]

# Determine dominant region for strategic context
dominant_geo = geo_rows[0][0] if geo_rows else "Global"
dominant_location = top_locations[0][0] if top_locations else "various locations"

# ---------------------------------------------------------------------------
# Assemble the briefing markdown
# ---------------------------------------------------------------------------

# Geo table rows
geo_table = ""
for tag, cnt, pct in geo_rows:
    geo_table += f"| **{tag}** | {cnt:,} | {pct}% |\n"

# Location table rows
loc_table = ""
for loc, cnt, pct in top_locations:
    loc_table += f"| {loc} | {cnt:,} | {pct}% |\n"

# Industry table rows
ind_table = ""
for rank, (ind, cnt) in enumerate(top_industries, 1):
    ind_table += f"| {rank} | **{ind}** | {cnt:,} |\n"

# Seniority table rows
sen_table = ""
for band, cnt in seniority:
    pct = seniority_pcts.get(band, 0)
    sen_table += f"| **{band}** | {cnt:,} | {pct}% |\n"

# Titles table rows
title_table = ""
for title, cnt in top_titles:
    title_table += f"| {title} | {cnt:,} |\n"

# Companies table rows
comp_table = ""
for comp, cnt in top_companies:
    comp_table += f"| **{comp}** | {cnt:,} |\n"

# Director+ percentage
director_plus = sum(r[1] for r in seniority if r[0] in ('C-Level & Founders', 'Directors', 'VP Level'))
director_plus_pct = round(director_plus / titled_total * 100, 1)

briefing_md = f"""# C-Suite Strategy Deck — Avineon / Tensing LinkedIn Follower Intelligence

## Executive Overview

The combined Avineon / Tensing LinkedIn follower base comprises **{total:,} followers** — a professional audience whose follow action signals brand awareness, category interest, or commercial intent in the geospatial, IT services, and engineering sectors. This briefing converts that raw follower base into actionable strategic intelligence.

---

## 1. Audience Composition at a Glance

| KPI | Value | Insight |
|-----|-------|---------|
| **Total Followers** | {total:,} | Solid B2B audience for a geo-IT / engineering services provider |
{geo_table}| **Premium LinkedIn Users** | {pct_premium}% ({premium_count:,}) | Active networkers who invest in LinkedIn |
| **Open Profiles (Free InMail)** | {pct_open}% ({open_count:,}) | Reachable via free InMail — **${inmail_savings:,} in InMail savings** |

---

## 2. Geographic Concentration

| Location | Followers | % of Total |
|----------|-----------|------------|
{loc_table}
> **Strategic Takeaway:** The follower base is concentrated in **{dominant_location.split(',')[0] if ',' in dominant_location else dominant_location}** and surrounding areas. Content strategy, ABM campaigns, and event marketing should be targeted to the dominant regions first.

---

## 3. Industry Verticals — Where the Revenue Sits

| Rank | Industry | Followers |
|------|----------|-----------|
{ind_table}
> **Key Insight:** The top 3 industries represent **{top3_ind_pct}%** of the total follower base ({top3_ind_count:,} followers). These verticals should receive prioritized marketing investment.

---

## 4. Decision-Maker Density — The Power Base

| Seniority Band | Followers | % of Titled Followers |
|---|---|---|
{sen_table}
> **This is a strong professional audience.** {director_plus_pct}% are Director-level or above. Content and outreach should speak to **strategic decisions** — not just operational details.

### Top Individual Titles

| Title | Count |
|-------|-------|
{title_table}

---

## 5. Key Companies Following

| Company | Followers |
|---------|-----------|
{comp_table}

---

## 6. Addressable Market Sizing (TAM from Follower Data)

Using follower data as a proxy for Total Addressable Market:

| Segment | Follower Pool | Est. Conversion Rate | Potential Opportunities |
|---------|--------------|----------------------|------------------------|
"""

# Add TAM segment rows dynamically
conversion_rates = {
    'C-Level & Founders': ('5-8%', 0.05, 0.08),
    'Directors': ('3-5%', 0.03, 0.05),
    'Managers & Heads': ('4-7%', 0.04, 0.07),
}

for band, cnt in tam_segments:
    if band in conversion_rates:
        rate_str, lo, hi = conversion_rates[band]
        opp_lo = int(cnt * lo)
        opp_hi = int(cnt * hi)
        briefing_md += f"| **{band}** | {cnt:,} | {rate_str} | {opp_lo}—{opp_hi} qualified leads |\n"

briefing_md += f"| **Open Profile + Decision Maker** | {open_decision_makers:,} | 6-10% | {int(open_decision_makers*0.06)}—{int(open_decision_makers*0.10)} qualified leads |\n"

total_opp_lo = sum(int(r[1] * conversion_rates.get(r[0], (None, 0.04, 0.07))[1]) for r in tam_segments if r[0] in conversion_rates) + int(open_decision_makers * 0.06)
total_opp_hi = sum(int(r[1] * conversion_rates.get(r[0], (None, 0.04, 0.07))[2]) for r in tam_segments if r[0] in conversion_rates) + int(open_decision_makers * 0.10)

briefing_md += f"""
> **Bottom Line:** The follower base contains an estimated **{total_opp_lo}–{total_opp_hi} high-conviction opportunities** among decision-makers who already know the brand.

---

## 7. Strategic Recommendations

### Immediate Actions (0–30 Days)
1. **Launch an Open Profile InMail campaign** targeting the {open_count:,} free-to-message followers — zero media cost, immediate pipeline impact
2. **Create industry-specific thought leadership content** for the top 3 verticals — these audiences will convert at above-benchmark rates
3. **Activate Account-Based Marketing** on companies with multiple followers — these are warm accounts

### Medium-Term Plays (30–90 Days)
4. **Industry-specific landing pages** for the top verticals — highest-converting segments
5. **LinkedIn Thought Leadership Ads** featuring leadership — the senior audience responds to peer-level content
6. **Geographic expansion content** targeting secondary regions beyond {dominant_geo}

### Long-Term Strategy (90+ Days)
7. **Partner referral programme** for industry followers — turn passive followers into active deal-flow partners
8. **Follower growth campaign** — at {total:,} followers, scaling to {int(total * 1.5):,} within 12 months would significantly expand the addressable funnel
9. **Data enrichment** to reduce the {missing_industry}% missing industry gap and improve segmentation accuracy

---

## 8. Data Quality Notes

| Metric | Value | Impact |
|--------|-------|--------|
| Missing Company Name | {missing_company}% | Freelancers & self-employed — addressable via targeted messaging |
| Missing Industry | {missing_industry}% | Limits segmentation accuracy; consider enrichment |
| Missing Job Title | {missing_title}% | Modest gap; most followers have title data |
| Missing Company HQ | {missing_hq}% | Limits HQ-vs-remote analysis |

---

*Generated from Avineon / Tensing LinkedIn Follower Data ({total:,} followers). Data-driven strategy briefing for executive review.*
"""

# Store briefing in DuckDB
con.execute("DROP TABLE IF EXISTS csuite_briefing")
con.execute("CREATE TABLE csuite_briefing (content TEXT)")
con.execute("INSERT INTO csuite_briefing VALUES (?)", (briefing_md,))
print("Successfully stored C-Suite Strategy Deck in DuckDB.")

con.close()
print(f"\nAll done! Upload '{os.path.basename(db_file)}' in the Streamlit sidebar.")
