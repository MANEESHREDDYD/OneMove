import os
import json
import hashlib
import subprocess
from datetime import datetime
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import h3
import networkx as nx

DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
OSM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osm")
GOLD_DIR = os.path.join(DATA_ROOT, "private", "official", "gold")
MANIFESTS_DIR = os.path.join(DATA_ROOT, "private", "official", "manifests")
OSMIUM_IMAGE = "stefda/osmium-tool@sha256:d2321d0e926f77ead7547b4b35f5cf98d9fd74043673cecc4fc2bb7cce06ff63"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def get_git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"

def generate_gold_dataset():
    ensure_dir(GOLD_DIR)
    ensure_dir(MANIFESTS_DIR)
    
    roads_pbf = os.path.join(OSM_DIR, "pilot_roads.osm.pbf")
    pois_geojson = os.path.join(OSM_DIR, "silver_pois.geojson")
    roads_geojson = os.path.join(OSM_DIR, "pilot_roads.geojson")
    
    if not os.path.exists(roads_pbf):
        print("Missing pilot_roads.osm.pbf. Run OSM pipeline first.")
        return
        
    print("Converting roads PBF to GeoJSON for Gold Generation...")
    subprocess.run([
        "docker", "run", "--rm", "-v", f"{OSM_DIR}:/data", OSMIUM_IMAGE,
        "osmium", "export", "/data/pilot_roads.osm.pbf", "-o", "/data/pilot_roads.geojson", "--overwrite"
    ], check=True)
    
    with open(roads_pbf, "rb") as f:
        pbf_sha = hashlib.sha256(f.read()).hexdigest()

    # Load Geometries
    roads_gdf = gpd.read_file(roads_geojson)
    # Filter to only LineStrings to prevent mixed geometry overlay errors
    roads_gdf = roads_gdf[roads_gdf.geometry.type.isin(['LineString', 'MultiLineString'])]
    
    # 1. Canonical Graph Module
    G = nx.DiGraph()
    for _, row in roads_gdf.iterrows():
        geom = row.geometry
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            oneway = row.get("oneway", "no")
            # Basic oneway handling
            is_oneway = oneway in ("yes", "true", "1", "-1")
            reverse = oneway == "-1"
            
            for i in range(len(coords) - 1):
                p1 = coords[i]
                p2 = coords[i+1]
                # Edge Length in meters approximately using pseudo projection or exact metric. 
                # For this pilot, use pyproj for true distance or simple haversine.
                # Geopandas length on EPSG:4326 is in degrees. Let's project to 3857 for metric distance
                seg_geom = LineString([p1, p2])
                
                if not reverse:
                    G.add_edge(p1, p2, geometry=seg_geom)
                if not is_oneway or reverse:
                    G.add_edge(p2, p1, geometry=seg_geom)

    undirected_G = G.to_undirected()
    degrees = dict(undirected_G.degree())
    intersections_nodes = {v for v, d in degrees.items() if d >= 3}
    
    graph_vertices = G.number_of_nodes()
    graph_directed_edges = G.number_of_edges()
    intersections_count = len(intersections_nodes)
    connected_components = nx.number_weakly_connected_components(G)
    largest_cc = len(max(nx.weakly_connected_components(G), key=len)) if graph_vertices > 0 else 0

    # 2. H3 Features Extraction
    BBOX = "77.58,12.90,77.65,12.98"
    min_lon, min_lat, max_lon, max_lat = map(float, BBOX.split(","))
    boundary_hash = hashlib.sha256(BBOX.encode('utf-8')).hexdigest()

    try:
        from h3 import LatLngPoly
        poly = LatLngPoly([(max_lat, min_lon), (max_lat, max_lon), (min_lat, max_lon), (min_lat, min_lon)])
        cells_8 = h3.polygon_to_cells(poly, 8)
    except AttributeError:
        poly = {'type': 'Polygon', 'coordinates': [[[min_lat, min_lon], [min_lat, max_lon], [max_lat, max_lon], [max_lat, min_lon]]]}
        cells_8 = h3.polyfill(poly, 8)
        
    cells_list = sorted(list(cells_8))

    # Convert cells to polygons in Geopandas
    cell_polys = []
    for cell in cells_list:
        boundary = h3.cell_to_boundary(cell)
        # H3 returns (lat, lon), shapely needs (lon, lat)
        lon_lat = [(lon, lat) for lat, lon in boundary]
        cell_polys.append(Polygon(lon_lat))
        
    cells_gdf = gpd.GeoDataFrame({"h3_index": cells_list}, geometry=cell_polys, crs="EPSG:4326")
    
    # Project to metric CRS (EPSG:32643 - UTM zone 43N for Bengaluru) for accurate lengths and areas
    cells_gdf_metric = cells_gdf.to_crs(epsg=32643)
    cells_gdf['cell_area_km2'] = cells_gdf_metric.geometry.area / 1e6
    
    # Intersections Points
    if intersections_nodes:
        ix_gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lon, lat in intersections_nodes], crs="EPSG:4326")
        ix_joined = gpd.sjoin(ix_gdf, cells_gdf, how="inner", predicate="intersects")
        ix_counts = ix_joined.groupby("h3_index").size().to_dict()
    else:
        ix_counts = {}

    # Roads Metric Length
    roads_metric = roads_gdf.to_crs(epsg=32643)
    # Intersect roads with cells
    # We do a spatial overlay to split roads precisely at H3 boundaries
    intersection_roads = gpd.overlay(roads_metric, cells_gdf_metric, how='intersection')
    intersection_roads['road_length_km'] = intersection_roads.geometry.length / 1000.0
    road_lengths = intersection_roads.groupby("h3_index")['road_length_km'].sum().to_dict()

    # POIs Classification
    if os.path.exists(pois_geojson):
        pois_gdf = gpd.read_file(pois_geojson)
        # Categories
        def classify_poi(row):
            amenity = str(row.get("amenity", "")).lower()
            shop = str(row.get("shop", "")).lower()
            
            is_rest = amenity in ["restaurant", "fast_food", "cafe"]
            is_groc = shop in ["supermarket", "convenience", "greengrocer"]
            is_comm = is_rest or is_groc or (shop != "none" and shop != "")
            return pd.Series([is_rest, is_groc, is_comm])
            
        pois_gdf[['is_restaurant', 'is_grocery', 'is_commercial']] = pois_gdf.apply(classify_poi, axis=1)
        
        # Spatial join POIs to cells
        pois_joined = gpd.sjoin(pois_gdf, cells_gdf, how="inner", predicate="intersects")
        rest_counts = pois_joined[pois_joined['is_restaurant']].groupby("h3_index").size().to_dict()
        groc_counts = pois_joined[pois_joined['is_grocery']].groupby("h3_index").size().to_dict()
        comm_counts = pois_joined[pois_joined['is_commercial']].groupby("h3_index").size().to_dict()
    else:
        rest_counts, groc_counts, comm_counts = {}, {}, {}

    # Build Gold Rows
    gold_rows = []
    for _, row in cells_gdf.iterrows():
        cell = row['h3_index']
        area = row['cell_area_km2']
        rd_len = road_lengths.get(cell, 0.0)
        ix_cnt = ix_counts.get(cell, 0)
        
        gold_rows.append({
            "h3_index": cell,
            "h3_resolution": 8,
            "cell_area_km2": area,
            "road_length_km": rd_len,
            "intersection_count": ix_cnt,
            "restaurant_count": rest_counts.get(cell, 0),
            "grocery_count": groc_counts.get(cell, 0),
            "commercial_poi_count": comm_counts.get(cell, 0),
            "road_density_km_per_sqkm": rd_len / area if area > 0 else 0,
            "intersection_density_per_sqkm": ix_cnt / area if area > 0 else 0
        })
        
    df = pd.DataFrame(gold_rows)
    
    # Store Parquet
    parquet_path = os.path.join(GOLD_DIR, "gold_network_h3_8.parquet")
    df.to_parquet(parquet_path)
    
    # Create Small Manifest
    with open(parquet_path, "rb") as f:
        parquet_sha256 = hashlib.sha256(f.read()).hexdigest()
        
    cells_hash = hashlib.sha256(json.dumps(cells_list).encode('utf-8')).hexdigest()
    
    manifest = {
        "dataset_id": "gold_network_bengaluru",
        "rows": len(df),
        "columns": list(df.columns),
        "h3_resolution": 8,
        "osm_source": "southern-zone-latest.osm.pbf",
        "osm_input_hash": pbf_sha,
        "graph_version": "1.1",
        "pilot_boundary_hash": boundary_hash,
        "code_sha": get_git_sha(),
        "parquet_sha256": parquet_sha256,
        "sorted_cell_list_sha256": cells_hash,
        "h3_library_version": h3.__version__,
        "generated_at": datetime.now().isoformat(),
        "graph_metrics": {
            "graph_vertices": graph_vertices,
            "graph_directed_edges": graph_directed_edges,
            "intersections": intersections_count,
            "connected_components": connected_components,
            "largest_component_vertices": largest_cc
        }
    }
    
    manifest_path = os.path.join(MANIFESTS_DIR, "gold_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Gold Static Dataset Generated Successfully.")
    print(f"Cells (Res 8): {len(cells_list)}")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    generate_gold_dataset()
