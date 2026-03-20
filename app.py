import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="LinkedIn Follower Analytics Dashboard", page_icon="📊", layout="wide")

import os
import tempfile

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Premium Metric Card Styling */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 24px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.2s ease;
        text-align: center;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
        border-color: #cbd5e1;
    }

    /* Hide default Streamlit artifacts */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sleeker Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px dashed #e2e8f0;
    }
    
    pre {
        background-color: #f1f5f9 !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 LinkedIn Follower Analytics")

st.sidebar.markdown("**Upload Database File**")
uploaded_file = st.sidebar.file_uploader("Upload leads.duckdb file", type=["duckdb", "db"])

if not uploaded_file:
    st.info("👋 Please upload the `leads.duckdb` file in the sidebar to proceed. This ensures no sensitive data is stored in the repository.")
    st.stop()

@st.cache_resource(show_spinner=False)
def get_connection(file_bytes):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb")
    tmp_file.write(file_bytes)
    tmp_file.close()
    return duckdb.connect(tmp_file.name, read_only=True)

con = get_connection(uploaded_file.getvalue())

# Sidebar navigation
page = st.sidebar.radio("Navigation", [
    "Overview & KPIs", 
    "Demographics & Geo", 
    "Companies & Roles", 
    "C-Suite Strategy Deck 🎯",
    "Spatial Maps 🌍",
    "Follower Database 🔗"
])

# Global Filters
st.sidebar.markdown('---')
st.sidebar.markdown("**Global Filters**")

chart_limit = st.sidebar.slider("Number of records in top charts:", min_value=5, max_value=100, value=20, step=5)

geo_tags = con.execute("SELECT DISTINCT geo_tag FROM leads WHERE geo_tag IS NOT NULL").fetchdf()
selected_geo = st.sidebar.multiselect("Select Geo Region:", geo_tags['geo_tag'].tolist(), default=geo_tags['geo_tag'].tolist())

industries_df = con.execute("SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL ORDER BY industry").fetchdf()
selected_industries = st.sidebar.multiselect("Filter by Industry:", industries_df['industry'].tolist(), help="Leave empty for all industries")

# Build WHERE clause
geo_list = tuple(selected_geo) if len(selected_geo) > 1 else f"('{selected_geo[0]}')" if len(selected_geo) == 1 else "('')"
conditions = [f"geo_tag IN {geo_list}"]
if selected_industries:
    escaped_ind = [i.replace("'", "''") for i in selected_industries]
    ind_values = ", ".join(f"'{v}'" for v in escaped_ind)
    conditions.append(f"industry IN ({ind_values})")
base_where = "WHERE " + " AND ".join(conditions)

if page == "Overview & KPIs":
    st.header("Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where}").fetchone()[0]
    prem_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND premium_linkedin_=True").fetchone()[0]
    open_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND open_profile_=True").fetchone()[0]
    companies = con.execute(f"SELECT COUNT(DISTINCT company_name) FROM leads {base_where}").fetchone()[0]
    
    col1.metric("Total Followers", f"{total_leads:,}")
    pct_prem = (prem_leads / total_leads * 100) if total_leads else 0
    col2.metric("Premium Users", f"{prem_leads:,}", f"{pct_prem:.1f}%")
    
    pct_open = (open_leads / total_leads * 100) if total_leads else 0
    col3.metric("Open Profiles", f"{open_leads:,}", f"{pct_open:.1f}%")
    col4.metric("Unique Companies", f"{companies:,}")
    
    st.markdown("---")
    st.markdown("### Data Completeness Overview")
    nulls_df = con.execute(f"""
    SELECT 
        100.0 - COUNT(company_name) * 100.0 / COUNT(*) as Missing_Company_Pct,
        100.0 - COUNT(industry) * 100.0 / COUNT(*) as Missing_Industry_Pct,
        100.0 - COUNT(job_title) * 100.0 / COUNT(*) as Missing_JobTitle_Pct
    FROM leads {base_where}
    """).fetchdf()
    
    colA, colB, colC = st.columns(3)
    colA.metric("Missing Company Name", f"{nulls_df['Missing_Company_Pct'][0]:.1f}%")
    colB.metric("Missing Industry", f"{nulls_df['Missing_Industry_Pct'][0]:.1f}%")
    colC.metric("Missing Job Title", f"{nulls_df['Missing_JobTitle_Pct'][0]:.1f}%")

    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### Top Industries")
        df_top_ind = con.execute(f"""
            SELECT industry, COUNT(*) as Count
            FROM leads {base_where} AND industry IS NOT NULL
            GROUP BY industry ORDER BY Count DESC LIMIT 10
        """).fetchdf()
        if len(df_top_ind) > 0:
            fig_top_ind = px.bar(df_top_ind, x='Count', y='industry', orientation='h',
                                 color='Count', color_continuous_scale='Teal')
            fig_top_ind.update_layout(yaxis={'categoryorder': 'total ascending'},
                                       showlegend=False, height=360)
            st.plotly_chart(fig_top_ind, use_container_width=True)
    with col_right:
        st.markdown("### Seniority Breakdown")
        df_sen = con.execute(f"""
            SELECT
                CASE
                    WHEN job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%'
                         OR job_title ILIKE '%CFO%' OR job_title ILIKE '%Founder%' THEN 'C-Level / Founders'
                    WHEN job_title ILIKE '%VP%' OR job_title ILIKE '%Vice President%' THEN 'VP Level'
                    WHEN job_title ILIKE '%Director%' THEN 'Directors'
                    WHEN job_title ILIKE '%Manager%' OR job_title ILIKE '%Head%' THEN 'Managers / Heads'
                    ELSE 'Individual Contributors'
                END as Seniority,
                COUNT(*) as Count
            FROM leads {base_where} AND job_title IS NOT NULL
            GROUP BY Seniority ORDER BY Count DESC
        """).fetchdf()
        if len(df_sen) > 0:
            fig_sen = px.pie(df_sen, names='Seniority', values='Count', hole=0.45,
                             color_discrete_sequence=px.colors.qualitative.Set2)
            fig_sen.update_layout(height=360)
            st.plotly_chart(fig_sen, use_container_width=True)

elif page == "Demographics & Geo":
    st.header("Demographics & Geographical Distribution")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Followers by Geo Region")
        df_geo = con.execute(f"SELECT geo_tag, COUNT(*) as Count FROM leads {base_where} GROUP BY geo_tag ORDER BY Count DESC").fetchdf()
        fig_geo = px.pie(df_geo, names='geo_tag', values='Count', color_discrete_sequence=px.colors.sequential.Teal)
        fig_geo.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_geo, use_container_width=True)
    with col2:
        st.subheader("Top 'Person Location's")
        df_loc = con.execute(f"SELECT person_s_location, COUNT(*) as Count FROM leads {base_where} GROUP BY person_s_location ORDER BY Count DESC LIMIT {chart_limit}").fetchdf()
        fig_loc = px.bar(df_loc, y='person_s_location', x='Count', orientation='h', color='Count', color_continuous_scale='Blues')
        fig_loc.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_loc, use_container_width=True)
        
    st.markdown("---")
    st.subheader("Profile Connectivity Potential & Cross-Matrix")
    colA, colB = st.columns(2)
    with colA:
        df_prem = con.execute(f"SELECT premium_linkedin_, COUNT(*) as Count FROM leads {base_where} GROUP BY premium_linkedin_").fetchdf()
        fig_prem = px.pie(df_prem, names='premium_linkedin_', values='Count', hole=0.4, title='Premium Users (Highly Active)')
        st.plotly_chart(fig_prem, use_container_width=True)
    with colB:
        df_conn = con.execute(f"""
            SELECT 
                CASE 
                    WHEN premium_linkedin_ = True AND open_profile_ = True THEN 'Super Connectors (Premium + Open)'
                    WHEN premium_linkedin_ = True THEN 'Premium Only'
                    WHEN open_profile_ = True THEN 'Open Only'
                    ELSE 'Standard Profiles'
                END as Profile_Type,
                COUNT(*) as Count
            FROM leads {base_where}
            GROUP BY Profile_Type
        """).fetchdf()
        fig_conn = px.pie(df_conn, names='Profile_Type', values='Count', hole=0.4, title='High-Conviction Audience Matrix', color_discrete_sequence=px.colors.sequential.Sunset)
        st.plotly_chart(fig_conn, use_container_width=True)

    st.markdown("---")
    st.subheader("Remote Workforce Analysis (HQ vs Local)")
    df_remote = con.execute(f"""
        SELECT 
            CASE 
                WHEN LOWER(person_s_location) LIKE '%' || LOWER(split_part(company_hq, ',', 1)) || '%' THEN 'Local to HQ'
                ELSE 'Remote / Distributed'
            END as Worker_Type,
            COUNT(*) as Count
        FROM leads {base_where} AND company_hq IS NOT NULL AND person_s_location IS NOT NULL
        GROUP BY Worker_Type
    """).fetchdf()
    fig_remote = px.pie(df_remote, names='Worker_Type', values='Count', hole=0.4, title='Distributed Workforce Proxy', color_discrete_sequence=['#ff7f0e', '#1f77b4'])
    st.plotly_chart(fig_remote, use_container_width=True)

elif page == "Companies & Roles":
    st.header("Companies & Roles Analysis")
    
    st.markdown("### 🎯 The Decision Maker Funnel")
    df_funnel = con.execute(f"""
        SELECT 
            CASE 
                WHEN job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%' OR job_title ILIKE '%Founder%' THEN '1. C-Level / Founders'
                WHEN job_title ILIKE '%VP%' OR job_title ILIKE '%Vice President%' THEN '2. VP Level'
                WHEN job_title ILIKE '%Director%' THEN '3. Directors'
                WHEN job_title ILIKE '%Manager%' OR job_title ILIKE '%Head%' THEN '4. Managers / Heads'
                ELSE '5. Individual Contributors'
            END as Seniority,
            COUNT(*) as Count
        FROM leads {base_where} AND job_title IS NOT NULL
        GROUP BY Seniority
        ORDER BY Seniority
    """).fetchdf()
    fig_funnel = px.funnel(df_funnel, x='Count', y='Seniority', color='Seniority', title="Audience Seniority Distribution")
    st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown("---")
    st.markdown("### Top Industries")
    df_ind = con.execute(f"SELECT industry, COUNT(*) as Count FROM leads {base_where} AND industry IS NOT NULL GROUP BY industry ORDER BY Count DESC LIMIT {chart_limit}").fetchdf()
    fig_ind = px.bar(df_ind, x='Count', y='industry', orientation='h', color='Count', color_continuous_scale='Mint')
    fig_ind.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_ind, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Top Companies Represented")
        df_comp = con.execute(f"SELECT company_name, COUNT(*) as Count FROM leads {base_where} AND company_name IS NOT NULL GROUP BY company_name ORDER BY Count DESC LIMIT {chart_limit}").fetchdf()
        fig_comp = px.bar(df_comp, x='Count', y='company_name', orientation='h', color_discrete_sequence=['#ff7f0e'])
        fig_comp.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_comp, use_container_width=True)
        
        st.markdown(f"### Account-Based Saturation (Top {chart_limit})")
        df_abm = con.execute(f"""
            SELECT company_name, COUNT(DISTINCT job_title) as Unique_Roles
            FROM leads {base_where} AND company_name IS NOT NULL
            GROUP BY company_name
            ORDER BY COUNT(*) DESC
            LIMIT {chart_limit}
        """).fetchdf()
        fig_abm = px.bar(df_abm, x='Unique_Roles', y='company_name', orientation='h', title='Distinct Titles per Account (Horizontal Coverage)', color='Unique_Roles', color_continuous_scale='Purples')
        fig_abm.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_abm, use_container_width=True)
    with col2:
        st.markdown("### Top Job Titles")
        df_title = con.execute(f"SELECT job_title, COUNT(*) as Count FROM leads {base_where} AND job_title IS NOT NULL GROUP BY job_title ORDER BY Count DESC LIMIT {chart_limit}").fetchdf()
        fig_title = px.bar(df_title, x='Count', y='job_title', orientation='h', color_discrete_sequence=['#2ca02c'])
        fig_title.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_title, use_container_width=True)

elif page == "C-Suite Strategy Deck 🎯":
    st.header("UK Market Outreach Intelligence")
    tab1, tab2 = st.tabs(["📊 Strategy & TAM Matrix", "🎙️ NotebookLM Podcast Source Data"])
    
    with tab1:
        # Check if briefing content is available in the db
        tables = con.execute("SHOW TABLES").fetchdf()
        if 'csuite_briefing' in tables['name'].values:
            briefing_text = con.execute("SELECT content FROM csuite_briefing").fetchone()[0]
            st.markdown(briefing_text)
        else:
            st.warning("C-Suite Briefing not found in database. Please run ingest.py to load the briefing.")
        
        st.markdown("---")
        
        # --- Key outreach metrics ---
        total = con.execute(f"SELECT COUNT(*) FROM leads {base_where}").fetchone()[0]
        open_leads_count = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND open_profile_=True").fetchone()[0]
        prem_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND premium_linkedin_=True").fetchone()[0]
        pct_open = (open_leads_count / total * 100) if total > 0 else 0
        pct_prem = (prem_leads / total * 100) if total > 0 else 0
        companies_count = con.execute(f"SELECT COUNT(DISTINCT company_name) FROM leads {base_where} AND company_name IS NOT NULL").fetchone()[0]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Followers (Filtered)", f"{total:,}")
        col2.metric("Reachable via Free InMail", f"{open_leads_count:,}", f"{pct_open:.1f}% of base")
        col3.metric("Premium Networkers", f"{prem_leads:,}", f"{pct_prem:.1f}% — highly active")
        col4.metric("Unique Companies", f"{companies_count:,}", "Targetable accounts")

        # --- Top Industries (respects global filters) ---
        st.markdown("---")
        col_ind, col_sen = st.columns(2)
        with col_ind:
            st.subheader("Top Industries")
            df_ind_cs = con.execute(f"""
                SELECT industry, COUNT(*) as Count
                FROM leads {base_where} AND industry IS NOT NULL
                GROUP BY industry ORDER BY Count DESC LIMIT {chart_limit}
            """).fetchdf()
            if len(df_ind_cs) > 0:
                fig_ind_cs = px.bar(df_ind_cs, x='Count', y='industry', orientation='h',
                                     color='Count', color_continuous_scale='Teal', text='Count')
                fig_ind_cs.update_layout(yaxis={'categoryorder': 'total ascending'},
                                          showlegend=False, height=max(360, len(df_ind_cs) * 26))
                fig_ind_cs.update_traces(texttemplate='%{text:,}', textposition='outside')
                st.plotly_chart(fig_ind_cs, use_container_width=True)

        with col_sen:
            st.subheader("Seniority Breakdown")
            df_sen_cs = con.execute(f"""
                SELECT
                    CASE
                        WHEN job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%'
                             OR job_title ILIKE '%CFO%' OR job_title ILIKE '%Founder%' THEN 'C-Level / Founders'
                        WHEN job_title ILIKE '%VP%' OR job_title ILIKE '%Vice President%' THEN 'VP Level'
                        WHEN job_title ILIKE '%Director%' THEN 'Directors'
                        WHEN job_title ILIKE '%Manager%' OR job_title ILIKE '%Head%' THEN 'Managers / Heads'
                        ELSE 'Individual Contributors'
                    END as Seniority,
                    COUNT(*) as Count
                FROM leads {base_where} AND job_title IS NOT NULL
                GROUP BY Seniority ORDER BY Count DESC
            """).fetchdf()
            if len(df_sen_cs) > 0:
                fig_sen_cs = px.pie(df_sen_cs, names='Seniority', values='Count', hole=0.45,
                                     color_discrete_sequence=px.colors.qualitative.Set2)
                fig_sen_cs.update_layout(height=420)
                st.plotly_chart(fig_sen_cs, use_container_width=True)

        # --- Decision Makers by Industry (TAM) — expanded view ---
        st.markdown("---")
        st.subheader("Decision Makers by Industry — Targeting Matrix")
        st.markdown("Identifies the intersection of **Industry × Seniority** for your outreach campaigns. Use the sidebar filters to drill into specific geo regions or industries.")
        
        cross_df = con.execute(f"""
            SELECT 
                industry,
                CASE
                    WHEN job_title ILIKE '%Chief%' OR job_title ILIKE '%CEO%' OR job_title ILIKE '%CTO%'
                         OR job_title ILIKE '%CFO%' OR job_title ILIKE '%Founder%' OR job_title ILIKE '%Co-Founder%'
                         THEN 'C-Level / Founders'
                    WHEN job_title ILIKE '%VP%' OR job_title ILIKE '%Vice President%' THEN 'VP Level'
                    WHEN job_title ILIKE '%Director%' OR job_title ILIKE '%Managing Director%' THEN 'Directors'
                    WHEN job_title ILIKE '%Manager%' OR job_title ILIKE '%Head%' THEN 'Managers / Heads'
                    ELSE 'Individual Contributors'
                END as Seniority,
                COUNT(*) as Count
            FROM leads {base_where} 
            AND industry IS NOT NULL AND job_title IS NOT NULL
            GROUP BY industry, Seniority
            ORDER BY Count DESC
        """).fetchdf()
        
        if len(cross_df) > 0:
            # Sunburst for better hierarchy visualisation
            fig_sun = px.sunburst(cross_df, path=['industry', 'Seniority'], values='Count',
                                   color='Count', color_continuous_scale='Sunset',
                                   title='Follower Base: Industry → Seniority (all levels)')
            fig_sun.update_layout(height=650, margin=dict(t=40, l=0, r=0, b=0))
            st.plotly_chart(fig_sun, use_container_width=True)
            
            # Heatmap for precise numbers
            top_ind = cross_df.groupby('industry')['Count'].sum().nlargest(chart_limit).index.tolist()
            cross_filtered = cross_df[cross_df['industry'].isin(top_ind)]
            pivot = cross_filtered.pivot_table(index='industry', columns='Seniority', values='Count', fill_value=0)
            fig_heat = px.imshow(pivot, color_continuous_scale='Blues', aspect='auto',
                                  labels=dict(x='Seniority', y='Industry', color='Followers'),
                                  title=f'Industry × Seniority Heatmap (Top {chart_limit} Industries)',
                                  text_auto=True)
            fig_heat.update_layout(height=max(400, len(top_ind) * 32))
            st.plotly_chart(fig_heat, use_container_width=True)

    with tab2:
        st.markdown("### Prepare Data for NotebookLM (Podcast & Blog Post Generation)")
        st.caption("Google's NotebookLM can ingest structured text to generate realistic podcasts and blog posts. This dynamic string converts your current live SQL filters into an analytical narrative ready for AI.")
        
        # Gather live data for the narrative
        d_total = con.execute(f"SELECT COUNT(*) FROM leads {base_where}").fetchone()[0]
        
        d_ind = con.execute(f"SELECT industry FROM leads {base_where} AND industry IS NOT NULL GROUP BY industry ORDER BY COUNT(*) DESC LIMIT 3").fetchdf()['industry'].tolist()
        ind_str = ", ".join(d_ind) if d_ind else "various sectors"
        
        d_loc = con.execute(f"SELECT person_s_location FROM leads {base_where} AND person_s_location IS NOT NULL GROUP BY person_s_location ORDER BY COUNT(*) DESC LIMIT 3").fetchdf()['person_s_location'].tolist()
        loc_str = ", ".join(d_loc) if d_loc else "global areas"
        
        d_acc = con.execute(f"SELECT company_name FROM leads {base_where} AND company_name IS NOT NULL GROUP BY company_name ORDER BY COUNT(*) DESC LIMIT 3").fetchdf()['company_name'].tolist()
        acc_str = ", ".join(d_acc) if d_acc else "various companies"
        
        open_ct = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND open_profile_=True").fetchone()[0]
        
        savings = open_ct * 2
        tables_nb = con.execute("SHOW TABLES").fetchdf()
        if 'notebooklm_template' in tables_nb['name'].values:
            nb_template = con.execute("SELECT content FROM notebooklm_template").fetchone()[0]
            notebooklm_source_text = nb_template.format(
                d_total=d_total, 
                ind_str=ind_str, 
                loc_str=loc_str, 
                acc_str=acc_str, 
                open_ct=open_ct, 
                savings=savings
            )
        else:
            notebooklm_source_text = "Error: NotebookLM template missing from database. Please run ingest.py to load 'notebooklm_template.md'."
            
        st.text_area("Live Data Script (Copy/Paste into NotebookLM)", value=notebooklm_source_text, height=400)
        
        st.download_button(
            label="📥 Download Data Narrative formatted for NotebookLM (.md)",
            data=notebooklm_source_text.encode('utf-8'),
            file_name="NotebookLM_Source_Document.md",
            mime="text/markdown",
            type="primary"
        )

elif page == "Spatial Maps 🌍":
    st.header("Geographic Distribution Maps")
    st.markdown("Explore where your LinkedIn followers are located across the globe.")

    # ---- Country extraction from person_s_location ----
    _METRO_TO_COUNTRY = {
        'Greater Paris Metropolitan Region': 'France', 'Arnhem-Nijmegen Region': 'Netherlands',
        'Ghent Metropolitan Area': 'Belgium', 'Brussels Metropolitan Area': 'Belgium',
        'Antwerp Metropolitan Area': 'Belgium', 'Greater Groningen Area': 'Netherlands',
        'Amsterdam Area': 'Netherlands', 'Utrecht Area': 'Netherlands',
        'Brabantine City Row': 'Netherlands', 'Greater Enschede Area': 'Netherlands',
        'Greater Montpellier Metropolitan Area': 'France', 'Greater Cambridge Area': 'United Kingdom',
        'Eindhoven Area': 'Netherlands', 'Greater Toulouse Metropolitan Area': 'France',
        'Washington DC-Baltimore Area': 'United States', 'Greater Cardiff Area': 'United Kingdom',
        'Berlin Metropolitan Area': 'Germany', 'Greater Lyon Area': 'France',
        'Rotterdam and The Hague': 'Netherlands', 'Greater Leeds Area': 'United Kingdom',
        'Greater Aberdeen Area': 'United Kingdom', 'Bruges Metropolitan Area': 'Belgium',
        'Greater Reading Area': 'United Kingdom', 'San Francisco Bay Area': 'United States',
        'Breda-Tilburg Area': 'Netherlands', 'Casablanca Metropolitan Area': 'Morocco',
        'Greater Nantes Metropolitan Area': 'France', 'Greater Malmö Metropolitan Area': 'Sweden',
        'Los Angeles Metropolitan Area': 'United States', 'Greater Edinburgh Area': 'United Kingdom',
        'Greater Chicago Area': 'United States', 'Greater Bordeaux Metropolitan Area': 'France',
        'Doha Metropolitan Area': 'Qatar', 'Greater Sydney Area': 'Australia',
        'Greater Tampa Bay Area': 'United States', 'Greater Swansea Area': 'United Kingdom',
        'Belfast Metropolitan Area': 'United Kingdom', 'Athens Metropolitan Area': 'Greece',
        'Greater Richmond Region': 'United States', 'Greater Melbourne Area': 'Australia',
        'Frankfurt Rhine-Main Metropolitan Area': 'Germany', 'Greater Granada Metropolitan Area': 'Spain',
        'Warsaw Metropolitan Area': 'Poland', 'Johannesburg Metropolitan Area': 'South Africa',
        'Greater Houston': 'United States', 'Greater Hyderabad Area': 'India',
        'Thessaloniki Metropolitan Area': 'Greece', 'Greater Brisbane Area': 'Australia',
        'Charlotte Metro': 'United States', 'Greater Madrid Metropolitan Area': 'Spain',
        'Greater Oxford Area': 'United Kingdom', 's-Hertogenbosch Area': 'Netherlands',
        'Greater Bilbao Metropolitan Area': 'Spain', 'Greater Seattle Area': 'United States',
        'Greater Brighton and Hove Area': 'United Kingdom', 'Greater Milan Metropolitan Area': 'Italy',
        'Porto Metropolitan Area': 'Portugal', 'Tulsa Metropolitan Area': 'United States',
        'Greater Nottingham': 'United Kingdom', 'Greater Stockholm Metropolitan Area': 'Sweden',
        'Pretoria Metropolitan Area': 'South Africa', 'Greater Perth Area': 'Australia',
        'Greater São Paulo Area': 'Brazil', 'Greater Ahmedabad Area': 'India',
        'Greater Munich Metropolitan Area': 'Germany', 'Greater Sevilla Metropolitan Area': 'Spain',
        'Greater Pamplona Area': 'Spain', 'Greater Chambery Area': 'France',
        'Nashville Metropolitan Area': 'United States', 'Greater Bergen Region': 'Norway',
        'Helsinki Metropolitan Area': 'Finland', 'Coquimbo-La Serena Metropolitan Area': 'Chile',
        'Mobile Metropolitan Area': 'United States', 'Huntsville-Decatur-Albertville Area': 'United States',
        'Dallas-Fort Worth Metroplex': 'United States', 'Atlanta Metropolitan Area': 'United States',
        'Charleroi Metropolitan Area': 'Belgium', 'Cologne Bonn Region': 'Germany',
        'South Africa Metropolitan Area': 'South Africa', 'Pune/Pimpri-Chinchwad Area': 'India',
        'Greater Buenos Aires': 'Argentina', 'Greater Exeter Area': 'United Kingdom',
        'Ruhr Region': 'Germany', 'El Jadida Metropolitan Area': 'Morocco',
        'Agadir Metropolitan Area': 'Morocco', 'South Bend-Mishawaka Region': 'United States',
        'Greater Colorado Springs Area': 'United States', 'Denver Metropolitan Area': 'United States',
        'Greater Sheffield Area': 'United Kingdom', 'Greater Barcelona Metropolitan Area': 'Spain',
        'Wollongong Area': 'Australia', 'Greater Bern Area': 'Switzerland',
        'Greater Nancy Area': 'France', 'Greater Rome Metropolitan Area': 'Italy',
        'Greater Valenciennes Area': 'France', 'Rabat Metropolitan Area': 'Morocco',
        'Lisbon Metropolitan Area': 'Portugal', 'Greater Portsmouth Area': 'United Kingdom',
        'Durban Metropolitan Area': 'South Africa', 'Greater Marseille Metropolitan Area': 'France',
        'Greater Brest Area': 'France', 'Greater Rennes Metropolitan Area': 'France',
        'Greater Bournemouth Area': 'United Kingdom', 'Greater Catania Metropolitan Area': 'Italy',
        'Greater Dublin': 'Ireland', 'Greater Turin Metropolitan Area': 'Italy',
        'Greater Lille Metropolitan Area': 'France', 'Cork Metropolitan Area': 'Ireland',
        'Zürich Metropolitan Area': 'Switzerland', 'Greater Madison Area': 'United States',
        'Raleigh-Durham-Chapel Hill Area': 'United States', 'Greater Nice Metropolitan Area': 'France',
        'Greater Clermont-Ferrand Area': 'France', 'Tangier Metropolitan Area': 'Morocco',
        'Ho Chi Minh City Metropolitan Area': 'Vietnam', 'Copenhagen Metropolitan Area': 'Denmark',
        'Greater Chennai Area': 'India', 'Greater Mulhouse Area': 'France',
        'Guayaquil Metropolitan Area': 'Ecuador', 'Greater Glasgow Area': 'United Kingdom',
        'Greater Cheshire West and Chester Area': 'United Kingdom', 'Greater Vancouver Metropolitan Area': 'Canada',
        'Appleton-Oshkosh-Neenah Area': 'United States',
    }

    _COUNTRY_ALIASES = {
        'Türkiye': 'Turkey', 'Reunion': 'France', 'Guernsey': 'United Kingdom',
    }

    _COUNTRY_TO_ISO3 = {
        'Netherlands': 'NLD', 'United Kingdom': 'GBR', 'France': 'FRA', 'India': 'IND',
        'United States': 'USA', 'Belgium': 'BEL', 'Germany': 'DEU', 'Morocco': 'MAR',
        'Canada': 'CAN', 'Brazil': 'BRA', 'Spain': 'ESP', 'Italy': 'ITA',
        'United Arab Emirates': 'ARE', 'Turkey': 'TUR', 'Greece': 'GRC',
        'New Zealand': 'NZL', 'Switzerland': 'CHE', 'Australia': 'AUS',
        'Portugal': 'PRT', 'Sweden': 'SWE', 'South Africa': 'ZAF', 'Norway': 'NOR',
        'Saudi Arabia': 'SAU', 'Egypt': 'EGY', 'Austria': 'AUT', 'Denmark': 'DNK',
        'Ireland': 'IRL', 'Ethiopia': 'ETH', 'Pakistan': 'PAK', 'Iran': 'IRN',
        'Tunisia': 'TUN', 'Oman': 'OMN', 'China': 'CHN', 'Poland': 'POL',
        'Mexico': 'MEX', 'Hungary': 'HUN', 'Argentina': 'ARG', 'Malaysia': 'MYS',
        'Chile': 'CHL', 'Bulgaria': 'BGR', 'Indonesia': 'IDN', 'Kenya': 'KEN',
        'Cyprus': 'CYP', 'Lebanon': 'LBN', 'Czechia': 'CZE', 'Ghana': 'GHA',
        'Senegal': 'SEN', 'Peru': 'PER', 'Kuwait': 'KWT', 'Slovenia': 'SVN',
        'North Macedonia': 'MKD', 'Uruguay': 'URY', 'Croatia': 'HRV',
        'Bangladesh': 'BGD', "Côte d'Ivoire": 'CIV', 'Colombia': 'COL',
        'Israel': 'ISR', 'Luxembourg': 'LUX', 'Azerbaijan': 'AZE', 'Venezuela': 'VEN',
        'Ukraine': 'UKR', 'Lithuania': 'LTU', 'Angola': 'AGO', 'Romania': 'ROU',
        'Singapore': 'SGP', 'Guatemala': 'GTM', 'Algeria': 'DZA', 'Latvia': 'LVA',
        'Taiwan': 'TWN', 'Kazakhstan': 'KAZ', 'Bosnia and Herzegovina': 'BIH',
        'Japan': 'JPN', 'Nigeria': 'NGA', 'Iraq': 'IRQ', 'Malta': 'MLT',
        'Finland': 'FIN', 'Costa Rica': 'CRI', 'Serbia': 'SRB', 'Philippines': 'PHL',
        'Vietnam': 'VNM', 'Ecuador': 'ECU', 'Tanzania': 'TZA', 'Mongolia': 'MNG',
        'Cameroon': 'CMR', 'Iceland': 'ISL', 'Madagascar': 'MDG', 'Jordan': 'JOR',
        'Malawi': 'MWI', 'South Sudan': 'SSD', 'Laos': 'LAO', 'Paraguay': 'PRY',
        'Qatar': 'QAT', 'Zimbabwe': 'ZWE', 'Benin': 'BEN', 'Bahrain': 'BHR',
        'Togo': 'TGO', 'Estonia': 'EST', 'Armenia': 'ARM', 'Slovakia': 'SVK',
        'Nepal': 'NPL', 'Syria': 'SYR', 'Democratic Republic of the Congo': 'COD',
        'Saint Vincent and the Grenadines': 'VCT',
    }

    def resolve_country(loc):
        """Extract country name from a person_s_location string."""
        if not isinstance(loc, str):
            return None
        raw = loc.strip()
        # 1. Check if the entire string is a known metro / region
        if raw in _METRO_TO_COUNTRY:
            return _METRO_TO_COUNTRY[raw]
        # 2. Take last comma-delimited segment
        segment = raw.split(',')[-1].strip()
        # 3. Check metro lookup
        if segment in _METRO_TO_COUNTRY:
            return _METRO_TO_COUNTRY[segment]
        # 4. Alias normalisation
        segment = _COUNTRY_ALIASES.get(segment, segment)
        # 5. If it maps to an ISO3 code it's a real country
        if segment in _COUNTRY_TO_ISO3:
            return segment
        return None  # unresolvable

    # --- Fetch follower locations ---
    df_locs = con.execute(f"""
        SELECT person_s_location, COUNT(*) as Count
        FROM leads {base_where}
        AND person_s_location IS NOT NULL
        GROUP BY person_s_location
    """).fetchdf()

    df_locs['Country'] = df_locs['person_s_location'].apply(resolve_country)
    df_resolved = df_locs.dropna(subset=['Country'])

    if len(df_resolved) == 0:
        st.info("No spatial data available for the current filters.")
    else:
        df_country = df_resolved.groupby('Country', as_index=False)['Count'].sum()
        df_country['ISO3'] = df_country['Country'].map(_COUNTRY_TO_ISO3)
        df_country = df_country.dropna(subset=['ISO3'])
        df_country = df_country.sort_values('Count', ascending=False)

        # ---------- 1. Global Choropleth (polygon fill) ----------
        st.subheader("Global Follower Footprint")
        fig_global = px.choropleth(
            df_country,
            locations='ISO3',
            color='Count',
            hover_name='Country',
            hover_data={'ISO3': False, 'Count': ':,'},
            color_continuous_scale='Blues',
            projection='natural earth',
            title='Follower Distribution by Country',
        )
        fig_global.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            coloraxis_colorbar=dict(title='Followers'),
            geo=dict(showframe=False, showcoastlines=True, coastlinecolor='#ccc'),
        )
        st.plotly_chart(fig_global, use_container_width=True)

        # ---------- 2. Top Countries bar ----------
        st.markdown("---")
        st.subheader("Top Countries by Follower Count")
        df_top = df_country.head(chart_limit)
        fig_bar = px.bar(
            df_top, x='Count', y='Country', orientation='h',
            color='Count', color_continuous_scale='Teal',
            text='Count',
        )
        fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=max(320, len(df_top)*28))
        fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

        # ---------- 3. Europe Focused Choropleth ----------
        df_europe = df_country[df_country['ISO3'].isin([
            'NLD','GBR','FRA','BEL','DEU','ESP','ITA','PRT','SWE','NOR','DNK',
            'FIN','AUT','CHE','IRL','POL','CZE','GRC','HUN','ROU','BGR','HRV',
            'SVN','SVK','LTU','LVA','EST','LUX','MLT','CYP','ISL','SRB',
            'BIH','MKD','UKR','TUR',
        ])]
        if len(df_europe) > 0:
            st.markdown("---")
            st.subheader("European Follower Concentration")
            fig_eu = px.choropleth(
                df_europe,
                locations='ISO3',
                color='Count',
                hover_name='Country',
                hover_data={'ISO3': False, 'Count': ':,'},
                color_continuous_scale='Sunset',
                title='Followers across Europe',
                scope='europe',
            )
            fig_eu.update_layout(
                margin=dict(l=0, r=0, t=40, b=0),
                coloraxis_colorbar=dict(title='Followers'),
                geo=dict(showframe=False, showcoastlines=True, coastlinecolor='#ccc'),
            )
            st.plotly_chart(fig_eu, use_container_width=True)

        # ---------- 4. Industry x Country Heatmap ----------
        st.markdown("---")
        st.subheader("Industry Concentration by Country")
        df_ind_geo = con.execute(f"""
            SELECT person_s_location, industry, COUNT(*) as Count
            FROM leads {base_where}
            AND person_s_location IS NOT NULL AND industry IS NOT NULL
            GROUP BY person_s_location, industry
        """).fetchdf()
        df_ind_geo['Country'] = df_ind_geo['person_s_location'].apply(resolve_country)
        df_ind_geo = df_ind_geo.dropna(subset=['Country'])
        df_cross = df_ind_geo.groupby(['Country', 'industry'], as_index=False)['Count'].sum()

        # Limit to top countries & industries for readability
        top_countries = df_cross.groupby('Country')['Count'].sum().nlargest(12).index.tolist()
        top_industries = df_cross.groupby('industry')['Count'].sum().nlargest(12).index.tolist()
        df_cross = df_cross[df_cross['Country'].isin(top_countries) & df_cross['industry'].isin(top_industries)]

        if len(df_cross) > 0:
            pivot = df_cross.pivot_table(index='Country', columns='industry', values='Count', fill_value=0)
            fig_heat = px.imshow(
                pivot,
                color_continuous_scale='Viridis',
                labels=dict(x='Industry', y='Country', color='Followers'),
                aspect='auto',
                title='Follower Industry Mix by Country (Top 12 x 12)',
            )
            fig_heat.update_layout(height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

        # ---------- 4b. Key Markets Industry Comparison ----------
        st.markdown("---")
        st.subheader("Industry Mix Comparison: UK, France, Belgium & Netherlands")
        st.markdown("Side-by-side view of industry composition across key European markets — highlighting similarities and differences in follower profiles.")

        focus_countries = ['United Kingdom', 'France', 'Belgium', 'Netherlands']
        df_focus = df_ind_geo[df_ind_geo['Country'].isin(focus_countries)]

        if len(df_focus) > 0:
            df_focus_agg = df_focus.groupby(['Country', 'industry'], as_index=False)['Count'].sum()
            # Calculate percentage share within each country
            country_totals = df_focus_agg.groupby('Country')['Count'].transform('sum')
            df_focus_agg['Pct'] = (df_focus_agg['Count'] / country_totals * 100).round(1)

            # Keep top industries across these 4 countries for readability
            top_focus_ind = df_focus_agg.groupby('industry')['Count'].sum().nlargest(15).index.tolist()
            df_focus_plot = df_focus_agg[df_focus_agg['industry'].isin(top_focus_ind)]

            # Grouped bar — absolute counts
            fig_compare = px.bar(
                df_focus_plot, x='industry', y='Count', color='Country',
                barmode='group', text='Count',
                title='Follower Count by Industry across Key Markets',
                color_discrete_map={
                    'United Kingdom': '#1f77b4', 'France': '#ff7f0e',
                    'Belgium': '#2ca02c', 'Netherlands': '#d62728',
                },
            )
            fig_compare.update_layout(
                xaxis_tickangle=-45, height=520,
                xaxis_title='Industry', yaxis_title='Followers',
                legend_title='Country',
            )
            fig_compare.update_traces(texttemplate='%{text:,}', textposition='outside')
            st.plotly_chart(fig_compare, use_container_width=True)

            # Percentage share stacked bar — normalised view
            fig_pct = px.bar(
                df_focus_plot, x='industry', y='Pct', color='Country',
                barmode='group', text='Pct',
                title='Industry Share (%) within Each Country — Normalised Comparison',
                color_discrete_map={
                    'United Kingdom': '#1f77b4', 'France': '#ff7f0e',
                    'Belgium': '#2ca02c', 'Netherlands': '#d62728',
                },
            )
            fig_pct.update_layout(
                xaxis_tickangle=-45, height=520,
                xaxis_title='Industry', yaxis_title='% of Country Followers',
                legend_title='Country',
            )
            fig_pct.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_pct, use_container_width=True)

            # Radar / polar chart for top 8 industries
            top8_ind = df_focus_agg.groupby('industry')['Count'].sum().nlargest(8).index.tolist()
            df_radar = df_focus_agg[df_focus_agg['industry'].isin(top8_ind)].copy()
            # Normalise to % within country for fair comparison
            df_radar['Pct'] = df_radar['Pct'].round(1)
            fig_radar = px.line_polar(
                df_radar, r='Pct', theta='industry', color='Country',
                line_close=True,
                title='Industry Profile Radar — Top 8 Industries (% share per country)',
                color_discrete_map={
                    'United Kingdom': '#1f77b4', 'France': '#ff7f0e',
                    'Belgium': '#2ca02c', 'Netherlands': '#d62728',
                },
            )
            fig_radar.update_traces(fill='toself', opacity=0.25)
            fig_radar.update_layout(height=550)
            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            st.info("Not enough data for the selected filters to compare these markets.")

        # ---------- 5. Country Drill-down ----------
        st.markdown("---")
        st.subheader("Country Drill-Down")
        countries_available = sorted(df_country['Country'].tolist())
        selected_country = st.selectbox("Select a country to drill into:", countries_available,
                                         index=countries_available.index('Netherlands') if 'Netherlands' in countries_available else 0)
        df_drill = df_resolved[df_resolved['Country'] == selected_country]
        df_drill_locs = df_drill.groupby('person_s_location', as_index=False)['Count'].sum().sort_values('Count', ascending=False).head(chart_limit)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"**Top Locations in {selected_country}**")
            fig_drill = px.bar(df_drill_locs, x='Count', y='person_s_location', orientation='h',
                               color='Count', color_continuous_scale='Purples', text='Count')
            fig_drill.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False,
                                     height=max(300, len(df_drill_locs)*26))
            fig_drill.update_traces(texttemplate='%{text:,}', textposition='outside')
            st.plotly_chart(fig_drill, use_container_width=True)

        with col_d2:
            st.markdown(f"**Industry Split in {selected_country}**")
            df_drill_ind = df_ind_geo[df_ind_geo['Country'] == selected_country].groupby('industry', as_index=False)['Count'].sum().sort_values('Count', ascending=False).head(10)
            if len(df_drill_ind) > 0:
                fig_drill_ind = px.pie(df_drill_ind, names='industry', values='Count', hole=0.4,
                                       color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_drill_ind.update_layout(height=400)
                st.plotly_chart(fig_drill_ind, use_container_width=True)
            else:
                st.info("No industry data available for this country.")

elif page == "Follower Database 🔗":
    st.header("Follower Search & Export")
    st.caption("Filter, search, and access LinkedIn follower profiles directly.")
    
    # Search inputs
    col1, col2 = st.columns(2)
    search_name = col1.text_input("🔍 Search Name:")
    search_title = col2.text_input("🏢 Search Title or Company:")
    
    query = f"""
    SELECT 
        full_name AS "Name",
        job_title AS "Title", 
        company_name AS "Company", 
        industry AS "Industry", 
        person_s_location AS "Location",
        open_profile_ AS "Free to Message",
        linkedin_profile_url AS "LinkedIn URL",
        linkedin_company_url AS "Company URL"
    FROM leads {base_where}
    """
    
    if search_name:
        safe_name = search_name.lower().replace("'", "''")
        query += f" AND LOWER(full_name) LIKE '%{safe_name}%'"
    if search_title:
        safe_title = search_title.lower().replace("'", "''")
        query += f" AND (LOWER(job_title) LIKE '%{safe_title}%' OR LOWER(company_name) LIKE '%{safe_title}%')"
        
    query += " LIMIT 500"
    
    results = con.execute(query).fetchdf()
    
    st.dataframe(
        results,
        column_config={
            "LinkedIn URL": st.column_config.LinkColumn(
                "🔗 LinkedIn Profile",
                help="Click to open LinkedIn profile",
                validate="^https://.*",
                max_chars=100,
            ),
            "Company URL": st.column_config.LinkColumn(
                "🏢 Company Page",
                help="Click to open LinkedIn company page",
                validate="^https://.*",
                max_chars=100,
            )
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    csv = results.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Database View (CSV)",
        data=csv,
        file_name="linkedin_followers_export.csv",
        mime="text/csv",
        type="primary"
    )
