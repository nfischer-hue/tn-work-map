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

print("Downloading files from Google Drive...")
gdown.download_folder(id=FOLDER_ID, output='./data', quiet=False, use_cookies=False)

# Center map on Tennessee
m = folium.Map(location=[35.86, -86.66], zoom_start=7, tiles='CartoDB positron')
marker_cluster = MarkerCluster(name="Daily Work Areas").add_to(m)

# --- 2. PROCESS KMZ LAYERS ---
print("Checking for KMZ layers...")
for root, dirs, files in os.walk('./data'):
    for file in files:
        if file.endswith('.kmz'):
            try:
                path = os.path.join(root, file)
                with ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(root)
                    kml_file = [f for f in zip_ref.namelist() if f.endswith('.kml')][0]
                    gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
                    gdf_kmz = gpd.read_file(os.path.join(root, kml_file), driver='KML')
                    folium.GeoJson(gdf_kmz, name=f"Layer: {file}").add_to(m)
                print(f"Successfully added KMZ: {file}")
            except Exception as e:
                print(f"Could not process KMZ {file}: {e}")

# --- 3. PROCESS DAILY CSV ---
print("Looking for CSV data...")
csv_file = None
for root, dirs, files in os.walk('./data'):
    for f in files:
        if f.endswith('.csv'):
            csv_file = os.path.join(root, f)

if csv_file:
    print(f"Processing CSV: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # Case-insensitive column search for "Work Area Geometry"
    df.columns = df.columns.str.strip()
    target_col = next((c for c in df.columns if c.lower() == 'work area geometry'), None)
    
    if target_col:
        print(f"Found geometry column: {target_col}")
        
        # Function to safely load geometry
        def load_geom(x):
            try: return wkt.loads(str(x))
            except: return None

        df['geometry'] = df[target_col].apply(load_geom)
        # Filter out rows that failed to parse
        gdf = df.dropna(subset=['geometry'])
        
        print(f"Plotting {len(gdf)} points...")
        for row in gdf.itertuples():
            geom = row.geometry
            if geom.geom_type == 'Point':
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=5,
                    color='red',
                    fill=True,
                    popup=f"Record: {row.Index}"
                ).add_to(marker_cluster)
            elif geom.geom_type in ['Polygon', 'MultiPolygon']:
                folium.GeoJson(geom, style_function=lambda x: {'color': 'red', 'weight': 2}).add_to(m)
    else:
        print(f"ERROR: Column 'Work Area Geometry' not found. Available: {list(df.columns)}")
else:
    print("ERROR: No CSV file found in the data folder.")

# --- 4. SAVE ---
folium.LayerControl().add_to(m)
m.save('index.html')
print("index.html successfully created.")
