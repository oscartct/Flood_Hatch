# src/fetch_warnings.py

# src/fetch_warnings.py

import os
import requests
import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union


def get_flood_warnings(county: str = None) -> gpd.GeoDataFrame:
    """
    Fetch current flood warnings from the Environment Agency Flood Monitoring API.
    Optionally filter by county name.
    Returns a GeoDataFrame with geometry of warning areas.
    """
    base_url = "https://environment.data.gov.uk/flood-monitoring/id/floods"
    params = {}
    if county:
        params["county"] = county

    resp = requests.get(base_url, params=params, headers={"Accept": "application/json"})
    resp.raise_for_status()
    items = resp.json().get("items", [])

    records = []
    for item in items:
        flood_area = item.get("floodArea", {})
        poly_url = flood_area.get("polygon")
        geom = None
        if poly_url:
            try:
                # Fetch GeoJSON for the flood area polygon
                p_resp = requests.get(poly_url + ".json")
                p_resp.raise_for_status()
                p_geojson = p_resp.json()

                if p_geojson.get("type") == "FeatureCollection":
                    # Combine all feature geometries
                    geoms = [shape(feat.get("geometry")) for feat in p_geojson.get("features", [])]
                    geom = unary_union(geoms) if geoms else None
                elif p_geojson.get("type") == "Feature":
                    geom = shape(p_geojson.get("geometry"))
                else:
                    # Fallback: attempt to parse as geometry directly
                    geom = shape(p_geojson)
            except Exception as e:
                print(f"Warning: could not fetch or parse polygon from {poly_url}: {e}")
                geom = None

        records.append({
            "floodAreaID": item.get("floodAreaID"),
            "description": item.get("description"),
            "severity": item.get("severity"),
            "severityLevel": item.get("severityLevel"),
            "timeRaised": item.get("timeRaised"),
            "timeSeverityChanged": item.get("timeSeverityChanged"),
            "geometry": geom
        })

    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    return gdf


def main():
    # Optional: set COUNTY environment variable to filter by county name
    county = os.getenv("COUNTY")
    print(f"Fetching flood warnings{' for ' + county if county else ''}...")
    gdf = get_flood_warnings(county)

    os.makedirs("data/raw", exist_ok=True)
    out_fp = os.path.join("data/raw", "warnings_current.geojson")
    gdf.to_file(out_fp, driver="GeoJSON")
    print(f"Saved {len(gdf)} warning areas to {out_fp}")


if __name__ == "__main__":
    main()