import os
import gdown
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from zipfile import ZipFile
import geopandas as gpd
from shapely import wkt

# --- 1. SETUP & DOWNLOAD ---
FOLDER_ID = '1rse8CPdingDraedGCma6iB0Wce55t1-z'
os.makedirs('./data', exist_ok=True)

print("Starting download from Google Drive...")
gdown.download_folder(id=FOLDER_ID, output='./data', quiet=False, use_cookies=False)

m = folium.Map(location=[35.86, -86.66], zoom_start=7, tiles='CartoDB positron')
marker_cluster = MarkerCluster(name="Work Area Points").add_to(m)

# --- 2. KMZ LAYERS ---
print("Processing KMZ files...")
for root, dirs, files in os.walk('./data'):
    for file in files:
        if file.endswith('.kmz'):
            print(f"Found KMZ: {file}")
            path = os.path.join(root, file)
            with ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(root)
                kml_file = [f for f in zip_ref.namelist() if f.endswith('.kml')][0]
                gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
                gdf_kmz = gpd.read_file(os.path.join(root, kml_file), driver='KML')
                folium.GeoJson(gdf_kmz, name=f"Layer: {file}").add_to(m)

# --- 3. PROCESS DAILY CSV ---
print("Processing CSV...")
csv_file = None
for root, dirs, files in os.walk('./data'):
    for f in files:
        if f.endswith('.csv'):
            csv_file = os.path.join(root, f)

if csv_file:
    print(f"Found CSV: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # Clean column names (removes extra spaces and makes lowercase)
    df.columns = df.columns.str.strip().str.lower()
    TARGET_COL = 'work area geometry'
    
    if TARGET_COL in df.columns:
        print(f"Found column '{TARGET_COL}'. Processing 12k rows...")
        # Convert text to shapes, skipping errors
        def safe_load_wkt(val):
            try:
                return wkt.loads(str(val))
            except:
                return None

        df['geometry'] = df[TARGET_COL].apply(safe_load_wkt)
        gdf = df.dropna(subset=['geometry'])
        
        for i, row in gdf.iterrows():
            geom = row['geometry']
            if geom.geom_type == 'Point':
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=5,
                    color='red',
                    fill=True
                ).add_to(marker_cluster)
    else:
        print(f"ERROR: Could not find column '{TARGET_COL}'. Available columns are: {list(df.columns)}")
        exit(1)

# --- 4. SAVE ---
folium.LayerControl().add_to(m)
m.save('index.html')
print("Map successfully built!")
