# src/process_satellite.py

import os
import json
import ee
from shapely.geometry import shape
from shapely.ops import unary_union

# Initialize Earth Engine using the user’s project
project_id = os.getenv("EE_PROJECT")
if project_id:
    ee.Initialize(project=project_id)
else:
    ee.Initialize()

# ---------------------- Configuration ----------------------
WARNINGS_FP = 'data/raw/warnings_current.geojson'
OUT_TIF       = 'data/processed/flood_mask.tif'

PRE_START  = '2025-04-04'
PRE_END    = '2025-04-13'
POST_START = '2025-04-14'
POST_END   = '2025-04-16'

BASELINE_THRESHOLD = 2.5  # dB
DIFF_THRESHOLD     = 2.0  # dB

HAND_MAX_ELEV    = 20    # meters
PERM_WATER_OCC   = 80    # percent occurrence threshold for JRC water

EXPORT_SCALE = 100  # meters per pixel

# ---------------------- Helper Functions ----------------------
def load_aoi(geojson_fp: str) -> ee.Geometry:
    """Load and unify warning polygons into one EE Geometry."""
    with open(geojson_fp) as f:
        gj = json.load(f)
    geoms = [shape(feat['geometry']) for feat in gj.get('features', []) if feat.get('geometry')]
    unified = unary_union(geoms)
    return ee.Geometry(json.loads(json.dumps(unified.__geo_interface__)))


def get_median_composite(aoi: ee.Geometry, start: str, end: str) -> ee.Image:
    """Return median VV composite for a date range."""
    coll = (ee.ImageCollection('COPERNICUS/S1_GRD')
            .filterBounds(aoi)
            .filterDate(start, end)
            .filter(ee.Filter.eq('instrumentMode', 'IW'))
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
            .select('VV'))
    return coll.median()


def apply_hand_mask(img: ee.Image, aoi: ee.Geometry, max_elev: float) -> ee.Image:
    """Mask out areas above HAND threshold to restrict to flood-prone terrain."""
    dem = ee.Image('USGS/SRTMGL1_003')
    hand = dem.subtract(
        dem.reduceNeighborhood(
            reducer=ee.Reducer.min(),
            kernel=ee.Kernel.circle(radius=500, units='meters')
        )
    )
    mask_h = hand.lte(max_elev)
    return img.updateMask(mask_h).clip(aoi)


def apply_water_history_mask(img: ee.Image, aoi: ee.Geometry, occ_thresh: float) -> ee.Image:
    """Mask out permanent water using JRC Global Surface Water Occurrence."""
    # Use the Global Surface Water dataset's 'occurrence' band
    water = ee.Image('JRC/GSW1_3/GlobalSurfaceWater').select('occurrence')
    mask_w = water.lte(occ_thresh)
    return img.updateMask(mask_w).clip(aoi)


def compute_flood_mask(aoi: ee.Geometry) -> ee.Image:
    """Generate final flood mask combining change detection, terrain and water-history masks."""
    # Build composites
    baseline = get_median_composite(aoi, '2016-01-01', PRE_END)
    pre      = get_median_composite(aoi, PRE_START, PRE_END)
    post     = get_median_composite(aoi, POST_START, POST_END)

    # Change detection masks
    diff_mask     = pre.subtract(post).abs().gt(DIFF_THRESHOLD)
    baseline_mask = baseline.subtract(post).abs().gt(BASELINE_THRESHOLD)
    change_mask   = diff_mask.Or(baseline_mask)

    # Apply auxiliary masks
    mask_h = apply_hand_mask(change_mask, aoi, HAND_MAX_ELEV)
    mask_w = apply_water_history_mask(mask_h, aoi, PERM_WATER_OCC)

    # Single-band binary flood mask
    return mask_w.rename('flood_mask').uint8()


def export_mask_to_drive(mask: ee.Image, aoi: ee.Geometry, out_fp: str):
    """Batch export the mask to Google Drive."""
    prefix = os.path.splitext(os.path.basename(out_fp))[0]
    task = ee.batch.Export.image.toDrive(
        image=mask,
        description=f'Export_{prefix}',
        folder='FloodMasks',
        fileNamePrefix=prefix,
        region=aoi,
        scale=EXPORT_SCALE,
        crs='EPSG:4326',
        maxPixels=1e13
    )
    task.start()
    if project_id:
        print(f'Export started. Run "earthengine task list --project={project_id}" to monitor.')
    else:
        print('Export started. Run "earthengine task list" to monitor.')
    print(f"When done, download '{prefix}.tif' from Drive and place at '{out_fp}'")

# ---------------------- Main Execution ----------------------
if __name__ == '__main__':
    os.makedirs(os.path.dirname(OUT_TIF), exist_ok=True)
    aoi  = load_aoi(WARNINGS_FP)
    mask = compute_flood_mask(aoi)
    export_mask_to_drive(mask, aoi, OUT_TIF)



