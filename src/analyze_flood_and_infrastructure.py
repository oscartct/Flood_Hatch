# src/analyze_flood_and_infrastructure.py

import os
import json
import rasterio
import numpy as np
from rasterio.windows import Window
from rasterio.features import shapes, rasterize
from shapely.geometry import shape, LineString
from shapely.ops import unary_union
import osmnx as ox

# Paths
FLOOD_MASK_TIF    = 'data/processed/flood_mask.tif'
OUTPUT_JSON       = 'data/processed/flood_analysis.json'

# Parameters
HALF_WINDOW_PX = 500    # pixels around flood centroid to analyze
BUFFER_DEG     = 0.005  # deg (~500m) buffer for roads
OSM_FILTER     = '["highway"~"motorway|trunk|primary|secondary"]'
METERS_PER_DEG = 111000.0  # approx

# ---------------------------------------------------------
# 1. Load mask and extract patch around flood centroid
# ---------------------------------------------------------
with rasterio.open(FLOOD_MASK_TIF) as src:
    mask_full = src.read(1)
    h_full, w_full = mask_full.shape

# Find flooded pixels
ys, xs = np.where(mask_full == 1)
if len(xs) == 0:
    raise RuntimeError("No flooded pixels found in mask.")
row_c, col_c = int(np.mean(ys)), int(np.mean(xs))

# Define window
r0 = max(row_c - HALF_WINDOW_PX, 0)
r1 = min(row_c + HALF_WINDOW_PX, h_full)
c0 = max(col_c - HALF_WINDOW_PX, 0)
c1 = min(col_c + HALF_WINDOW_PX, w_full)
window = Window(col_off=c0, row_off=r0,
                width=c1 - c0, height=r1 - r0)

# Read patch and transform
with rasterio.open(FLOOD_MASK_TIF) as src:
    mask_patch = src.read(1, window=window)
    tf_patch = src.window_transform(window)

# Compute pixel area (m2)
px_w, px_h = abs(tf_patch.a), abs(tf_patch.e)
pixel_area_m2 = (px_w * METERS_PER_DEG) * (px_h * METERS_PER_DEG)

# Flood stats
n_flooded_pixels = int((mask_patch == 1).sum())
area_flooded_m2 = n_flooded_pixels * pixel_area_m2

# Vectorize flood area
geoms = [shape(geom) for geom, val in shapes(mask_patch, transform=tf_patch) if val == 1]
flood_extent = unary_union(geoms)
if flood_extent.is_empty:
    raise RuntimeError("Flood extent polygon empty.")

# ---------------------------------------------------------
# 2. Fetch roads via OSMnx within flood_extent+buffer
# ---------------------------------------------------------
# Buffer extent
flood_poly = flood_extent.buffer(BUFFER_DEG)
# Download road network for polygon
G = ox.graph_from_polygon(
    flood_poly,
    network_type='drive',
    custom_filter=OSM_FILTER
)
# Convert to GeoDataFrame of edges
edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
roads = list(edges.geometry)

# ---------------------------------------------------------
# 3. Rasterize roads and compute flooded road length
# ---------------------------------------------------------
road_raster = rasterize(
    [(geom, 1) for geom in roads],
    out_shape=mask_patch.shape,
    transform=tf_patch,
    fill=0,
    all_touched=True,
    dtype='uint8'
)

n_road_pixels = int((road_raster == 1).sum())
n_flooded_road_pixels = int(((mask_patch == 1) & (road_raster == 1)).sum())

pixel_length_m = pixel_area_m2 ** 0.5
total_road_length_m = n_road_pixels * pixel_length_m
flooded_road_length_m = n_flooded_road_pixels * pixel_length_m

# ---------------------------------------------------------
# 4. Save results
# ---------------------------------------------------------
analysis = {
    'n_flooded_pixels': n_flooded_pixels,
    'area_flooded_m2': area_flooded_m2,
    'total_road_length_m': total_road_length_m,
    'flooded_road_length_m': flooded_road_length_m
}

os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
with open(OUTPUT_JSON, 'w') as f:
    json.dump(analysis, f, indent=2)

print("Flood analysis complete:")
print(json.dumps(analysis, indent=2))

