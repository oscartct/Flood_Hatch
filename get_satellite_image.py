# src/get_satellite_images.py

import os
import json
import requests
import ee
from shapely.geometry import shape
from shapely.ops import unary_union

# Initialize Earth Engine (uses EE_PROJECT env var if set)
project_id = os.getenv("EE_PROJECT")
if project_id:
    ee.Initialize(project=project_id)
else:
    ee.Initialize()


def load_aoi(geojson_fp: str) -> ee.Geometry:
    """
    Load GeoJSON of flood warning areas and return a unified EE Geometry.
    """
    with open(geojson_fp, 'r') as f:
        gj = json.load(f)
    geoms = [shape(feat['geometry']) for feat in gj.get('features', []) if feat.get('geometry')]
    unified = unary_union(geoms)
    return ee.Geometry(json.loads(json.dumps(unified.__geo_interface__)))


def fetch_and_save_thumbnails(aoi: ee.Geometry,
                              pre_start: str, pre_end: str,
                              post_start: str, post_end: str,
                              out_dir: str = 'data/processed/thumbnails'):
    """
    Fetch pre- and post-event Sentinel-1 VV thumbnails and save locally.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Build median composites
    coll = (ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(aoi)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .select('VV'))
    pre = coll.filterDate(pre_start, pre_end).median()
    post = coll.filterDate(post_start, post_end).median()

    # Thumbnail parameters
    thumb_params = {
        'dimensions': 1024,
        'region': aoi,
        'bands': ['VV'],
        'min': -25,
        'max': 0,
        'format': 'png'
    }

    # Get thumbnail URLs
    url_pre = pre.getThumbURL(thumb_params)
    url_post = post.getThumbURL(thumb_params)

    # Download and save
    for label, url in [('pre', url_pre), ('post', url_post)]:
        resp = requests.get(url)
        resp.raise_for_status()
        fname = os.path.join(out_dir, f"{label}_thumbnail.png")
        with open(fname, 'wb') as f:
            f.write(resp.content)
        print(f"Saved {label}-event thumbnail to {fname}")


if __name__ == '__main__':
    # Configuration
    warnings_fp = 'data/raw/warnings_current.geojson'
    # Define your event windows
    pre_start  = '2025-04-04'
    pre_end    = '2025-04-13'
    post_start = '2025-04-14'
    post_end   = '2025-04-16'

    # Load AOI
    aoi = load_aoi(warnings_fp)

    # Fetch and save thumbnails
    fetch_and_save_thumbnails(aoi, pre_start, pre_end, post_start, post_end)
