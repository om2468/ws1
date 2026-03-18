import duckdb
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

DB_FILE = '/Users/cherrytian/Documents/GitHub/ws1/leads.duckdb'
print("Connecting to DuckDB...")
con = duckdb.connect(DB_FILE)

print("Fetching top 150 unique locations...")
df_locs = con.execute("""
    SELECT person_s_location, COUNT(*) as Count 
    FROM leads 
    WHERE person_s_location IS NOT NULL 
    GROUP BY person_s_location 
    ORDER BY Count DESC 
    LIMIT 150
""").fetchdf()

print(f"Geocoding {len(df_locs)} locations (this might take 2 minutes to respect rate limits)...")
geolocator = Nominatim(user_agent="workspacegroup_leads_v1")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

lats, lons = [], []
for loc in df_locs['person_s_location']:
    try:
        # Simplify common locations for better matching
        search_loc = loc
        if search_loc == "London Area, United Kingdom":
            search_loc = "London, United Kingdom"
        elif search_loc == "Greater London, England, United Kingdom":
            search_loc = "London, United Kingdom"
            
        location = geocode(search_loc)
        if location:
            lats.append(location.latitude)
            lons.append(location.longitude)
        else:
            lats.append(None)
            lons.append(None)
    except Exception as e:
        print(f"Error geocoding {loc}: {e}")
        lats.append(None)
        lons.append(None)

df_locs['lat'] = lats
df_locs['lon'] = lons
df_locs = df_locs.dropna(subset=['lat', 'lon'])

print(f"Successfully geocoded {len(df_locs)} locations.")
con.execute("DROP TABLE IF EXISTS meta_geo")
con.register('df_geo_view', df_locs)
con.execute("CREATE TABLE meta_geo AS SELECT person_s_location, lat, lon FROM df_geo_view")
print("Geocoding complete and saved to 'meta_geo' table.")

con.close()
