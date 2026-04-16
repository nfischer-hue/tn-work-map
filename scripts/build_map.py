import os
import gdown
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from zipfile import ZipFile
import geopandas as gpd
from shapely import wkt

# --- 1. SETUP & DOWNLOAD ---
# Your specific Google Drive Folder ID
FOLDER_ID = '1rse8CPdingDraedGCma6iB0Wce55t1-z'
os.makedirs('./data', exist_ok=True)

# Download everything from Drive (Ensure folder is "Anyone with link can view")
try:
    gdown.download_folder(id=FOLDER_ID, output='./data', quiet=False, use_cookies=False)
except Exception as e:
    print(f"Error downloading from Drive: {e}")

# Center map on Tennessee
m = folium.Map(location=[35.86, -86.66], zoom_start=7, tiles='CartoDB positron')
marker_cluster = MarkerCluster(name="Work Area Points").add_to(m)

# --- 2. PROCESS KMZ LAYERS ---
for root, dirs, files in os.walk('./data'):
    for file in files:
        if file.endswith('.kmz'):
            path = os.path.join(root, file)
            with ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(root)
                kml_file = [f for f in zip_ref.namelist() if f.endswith('.kml')][0]
                gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
                gdf_kmz = gpd.read_file(os.path.join(root, kml_file), driver='KML')
                folium.GeoJson(gdf_kmz, name=f"Layer: {file}").add_to(m)

# --- 3. PROCESS DAILY CSV (12k Rows) ---
csv_file = None
for root, dirs, files in os.walk('./data'):
    for f in files:
        if f.endswith('.csv'):
            csv_file = os.path.join(root, f)

if csv_file:
    df = pd.read_csv(csv_file)
    
    # Check for your specific column
    GEOM_COL = 'Work Area Geometry'
    
    if GEOM_COL in df.columns:
        # Convert text geometry to actual map shapes
        # This handles formats like "POINT (-86.7 36.1)"
        df['geometry'] = df[GEOM_COL].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(df, geometry='geometry')
        
        for i, row in gdf.iterrows():
            geom = row.geometry
            if geom.geom_type == 'Point':
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=5,
                    color='red',
                    fill=True,
                    popup=f"Record: {i}"
                ).add_to(marker_cluster)
            elif geom.geom_type in ['Polygon', 'MultiPolygon']:
                folium.GeoJson(geom, style_function=lambda x: {'color': 'red'}).add_to(m)

# --- 4. SAVE ---
folium.LayerControl().add_to(m)
m.save('index.html')
