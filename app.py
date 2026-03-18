import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="LinkedIn Leads Analytics Dashboard", page_icon="📊", layout="wide")

import os
import tempfile

st.markdown("""
<style>
    .reportview-container { background: #f0f2f6 }
    .stMetric { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

st.title("📊 LinkedIn Leads Deep Dive")

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
    "Lead Database 🔗"
])

# Global Filters
st.sidebar.markdown('---')
st.sidebar.markdown("**Global Filters**")

geo_tags = con.execute("SELECT DISTINCT geo_tag FROM leads WHERE geo_tag IS NOT NULL").fetchdf()
selected_geo = st.sidebar.multiselect("Select Geo Region:", geo_tags['geo_tag'].tolist(), default=geo_tags['geo_tag'].tolist())

geo_list = tuple(selected_geo) if len(selected_geo) > 1 else f"('{selected_geo[0]}')" if len(selected_geo) == 1 else "('')"
base_where = f"WHERE geo_tag IN {geo_list}"

if page == "Overview & KPIs":
    st.header("Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where}").fetchone()[0]
    prem_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND premium_linkedin_=True").fetchone()[0]
    open_leads = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND open_profile_=True").fetchone()[0]
    companies = con.execute(f"SELECT COUNT(DISTINCT company_name) FROM leads {base_where}").fetchone()[0]
    
    col1.metric("Total Leads", f"{total_leads:,}")
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

elif page == "Demographics & Geo":
    st.header("Demographics & Geographical Distribution")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Leads by Geo Region")
        df_geo = con.execute(f"SELECT geo_tag, COUNT(*) as Count FROM leads {base_where} GROUP BY geo_tag ORDER BY Count DESC").fetchdf()
        fig_geo = px.pie(df_geo, names='geo_tag', values='Count', color_discrete_sequence=px.colors.sequential.Teal)
        fig_geo.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_geo, use_container_width=True)
    with col2:
        st.subheader("Top 'Person Location's")
        df_loc = con.execute(f"SELECT person_s_location, COUNT(*) as Count FROM leads {base_where} GROUP BY person_s_location ORDER BY Count DESC LIMIT 15").fetchdf()
        fig_loc = px.bar(df_loc, y='person_s_location', x='Count', orientation='h', color='Count', color_continuous_scale='Blues')
        fig_loc.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_loc, use_container_width=True)
        
    st.markdown("---")
    st.subheader("Profile Connectivity Potential")
    colA, colB = st.columns(2)
    with colA:
        df_prem = con.execute(f"SELECT premium_linkedin_, COUNT(*) as Count FROM leads {base_where} GROUP BY premium_linkedin_").fetchdf()
        fig_prem = px.pie(df_prem, names='premium_linkedin_', values='Count', hole=0.4, title='Premium Users (Highly Active)')
        st.plotly_chart(fig_prem, use_container_width=True)
    with colB:
        df_open = con.execute(f"SELECT open_profile_, COUNT(*) as Count FROM leads {base_where} GROUP BY open_profile_").fetchdf()
        fig_open = px.pie(df_open, names='open_profile_', values='Count', hole=0.4, title='Open Profiles (Free InMail)')
        st.plotly_chart(fig_open, use_container_width=True)

elif page == "Companies & Roles":
    st.header("Companies & Roles Analysis")
    st.markdown("### Top Industries")
    df_ind = con.execute(f"SELECT industry, COUNT(*) as Count FROM leads {base_where} AND industry IS NOT NULL GROUP BY industry ORDER BY Count DESC LIMIT 20").fetchdf()
    fig_ind = px.bar(df_ind, x='Count', y='industry', orientation='h', color='Count', color_continuous_scale='Mint')
    fig_ind.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_ind, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Top Companies Represented")
        df_comp = con.execute(f"SELECT company_name, COUNT(*) as Count FROM leads {base_where} AND company_name IS NOT NULL GROUP BY company_name ORDER BY Count DESC LIMIT 15").fetchdf()
        fig_comp = px.bar(df_comp, x='Count', y='company_name', orientation='h', color_discrete_sequence=['#ff7f0e'])
        fig_comp.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_comp, use_container_width=True)
    with col2:
        st.markdown("### Top Job Titles")
        df_title = con.execute(f"SELECT job_title, COUNT(*) as Count FROM leads {base_where} AND job_title IS NOT NULL GROUP BY job_title ORDER BY Count DESC LIMIT 15").fetchdf()
        fig_title = px.bar(df_title, x='Count', y='job_title', orientation='h', color_discrete_sequence=['#2ca02c'])
        fig_title.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_title, use_container_width=True)

elif page == "C-Suite Strategy Deck 🎯":
    # Check if briefing content is available in the db
    tables = con.execute("SHOW TABLES").fetchdf()
    if 'csuite_briefing' in tables['name'].values:
        briefing_text = con.execute("SELECT content FROM csuite_briefing").fetchone()[0]
        st.markdown(briefing_text)
    else:
        st.warning("C-Suite Briefing not found in database. Please run ingest.py to load the briefing.")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    inmail_cost = 2.0  # Assumed cost of a paid InMail message
    open_leads_count = con.execute(f"SELECT COUNT(*) FROM leads {base_where} AND open_profile_=True").fetchone()[0]
    total_savings = open_leads_count * inmail_cost
    
    col1.metric("Total Free InMail Leads", f"{open_leads_count:,} Leads")
    col2.metric("Acquisition Cost Saved", f"${total_savings:,.2f}", "via Open Profiles")
    col3.metric("Premium Networkers", "18.9%", "High Conversion Proxy")

    st.markdown("---")
    st.subheader("Cross-Tab Analysis: Highest ROI Targeting Matrix")
    st.markdown("This matrix identifies the precise intersection of Industry and Seniority, revealing where marketing dollars should be allocated first. Target these cross-sections on LinkedIn Ads.")
    
    cross_df = con.execute(f"""
        SELECT industry, job_title, COUNT(*) as Count 
        FROM leads {base_where} 
        AND industry IS NOT NULL 
        AND job_title IN ('Director', 'Managing Director', 'Founder', 'Chief Executive Officer', 'Partner', 'Co-Founder', 'Owner')
        GROUP BY industry, job_title
        ORDER BY Count DESC
        LIMIT 20
    """).fetchdf()
    
    fig_cross = px.treemap(cross_df, path=['industry', 'job_title'], values='Count', color='Count', color_continuous_scale='Sunset', title='Decision Makers by Industry (TAM)')
    st.plotly_chart(fig_cross, use_container_width=True)

elif page == "Spatial Maps 🌍":
    st.header("Geographic Distribution Maps")
    st.markdown("Visualize the density of high-value leads across global markets.")
    
    # Check if geo table exists
    tables = con.execute("SHOW TABLES").fetchdf()
    if 'meta_geo' not in tables['name'].values:
        st.warning("Geocoding in progress. Please wait a moment and refresh.")
    else:
        df_map = con.execute(f"""
            SELECT l.person_s_location, COUNT(*) as Count
            FROM leads l
            {base_where}
            GROUP BY l.person_s_location
        """).fetchdf()

        if len(df_map) > 0:
            # Extract simple country from location string
            def extract_country(loc):
                if not isinstance(loc, str): return 'Unknown'
                parts = loc.split(',')
                country = parts[-1].strip()
                # Handle special cases / manual mappings
                if country in ['England', 'Scotland', 'Wales', 'Northern Ireland', 'Greater Oxford Area']:
                    return 'United Kingdom'
                if country == 'UAE':
                    return 'United Arab Emirates'
                if 'United States' in country:
                    return 'United States'
                return country

            df_map['Country'] = df_map['person_s_location'].apply(extract_country)
            df_country = df_map.groupby('Country', as_index=False)['Count'].sum()
            
            st.subheader("Global Footprint (Choropleth)")
            fig_global = px.choropleth(
                df_country, 
                locations="Country", 
                locationmode="country names", 
                color="Count",
                hover_name="Country",
                color_continuous_scale="Blues",
                title="Global Lead Distribution"
            )
            fig_global.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig_global, use_container_width=True)

            # Keep a closer look at Europe if applicable
            st.subheader("European Footprint")
            fig_europe = px.choropleth(
                df_country, 
                locations="Country", 
                locationmode="country names", 
                color="Count",
                hover_name="Country",
                color_continuous_scale="Oranges",
                scope="europe",
                title="European Lead Distribution"
            )
            fig_europe.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig_europe, use_container_width=True)
            
        else:
            st.info("No spatial data available for current geo filters.")

elif page == "Lead Database 🔗":
    st.header("Search & Export Master List")
    st.markdown("Filter, search, and access LinkedIn profiles directly.")
    
    # Search inputs
    col1, col2 = st.columns(2)
    search_name = col1.text_input("Search Name:")
    search_title = col2.text_input("Search Title or Company:")
    
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
        query += f" AND LOWER(full_name) LIKE '%{search_name.lower()}%'"
    if search_title:
        query += f" AND (LOWER(job_title) LIKE '%{search_title.lower()}%' OR LOWER(company_name) LIKE '%{search_title.lower()}%')"
        
    query += " LIMIT 500"
    
    results = con.execute(query).fetchdf()
    
    st.dataframe(
        results,
        column_config={
            "LinkedIn URL": st.column_config.LinkColumn(
                "LinkedIn Profile",
                help="Click to open LinkedIn profile",
                validate="^https://.*",
                max_chars=100,
            ),
            "Company URL": st.column_config.LinkColumn(
                "Company Page",
                help="Click to open LinkedIn company page",
                validate="^https://.*",
                max_chars=100,
            )
        },
        use_container_width=True,
        hide_index=True
    )
