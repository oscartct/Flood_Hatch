# Flood Analysis Pipeline

This repository contains a modular pipeline for post-event flood analysis using Sentinel-1 SAR, UK Environment Agency flood warnings, and road network data from OpenStreetMap. The workflow:

1. **Fetch flood warnings** from the UK Environment Agency API (`src/fetch_warnings.py`).  
2. **Fetch telemetry readings** for evaluation (`src/fetch_readings.py`).  
3. **Process satellite data** in Google Earth Engine to generate a binary flood mask (`src/process_satellite.py`).  
4. **Analyze flood extent & infrastructure** locally by overlaying the mask with OSM roads (`src/analyze_flood_and_infrastructure.py`).  
5. **Preview flood patches** via a quick zoomed-in script (`src/preview_flood_patch.py`).

---

## 📦 Repository Structure

```
├── data/
│   ├── raw/                   # Raw inputs: warnings_current.geojson, readings CSVs
│   └── processed/             # Processed outputs: flood_mask.tif, flood_analysis.json
├── src/
│   ├── fetch_warnings.py      # Download flood warning polygons
│   ├── fetch_readings.py      # Download telemetry CSV for gauge readings
│   ├── process_satellite.py   # EE batch export of Sentinel-1 flood mask
│   ├── analyze_flood_and_infrastructure.py  # Overlay mask with OSM roads
│   └── preview_flood_patch.py # Zoomed-in matplotlib preview of mask patch
├── .venv/                     # Python virtual environment
├── requirements.txt           # Python dependencies
└── README.md                  # Project overview and usage
```

---

## 🚀 Quick Start

### 1. Clone & Setup Virtual Environment

```bash
git clone <repo_url>
cd Hatch_flood
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Fetch Warning Polygons

```bash
python src/fetch_warnings.py
# Outputs `data/raw/warnings_current.geojson`
```

### 3. Fetch Telemetry Readings (Optional)

```bash
python src/fetch_readings.py
# Outputs `data/raw/readings_<DATE>.csv`
```

### 4. Generate Flood Mask in Earth Engine

1. Configure your GEE project:  
   ```bash
   earthengine set_project floodhatch
   ```
2. Run the export script:  
   ```bash
   python src/process_satellite.py
   ```
3. Monitor the export:  
   ```bash
   earthengine task list
   ```
4. Download `flood_mask.tif` from Drive → `FloodMasks` → save to `data/processed/`.

### 5. Analyze Flood & Roads

```bash
python src/analyze_flood_and_infrastructure.py
# Outputs metrics and saves `data/processed/flood_analysis.json`
```

### 6. Preview Flood Patch

```bash
python src/preview_flood_patch.py [half_window]
# Displays a zoomed-in view of the flood cluster
```

---

## 🔧 Configuration

- **Environment Variables**  
  - `EE_PROJECT`: Google Earth Engine project ID (e.g. `floodhatch`).

- **Script Parameters**  
  - Date ranges and thresholds in `process_satellite.py`:
    - `PRE_START`, `PRE_END`, `POST_START`, `POST_END`  
    - `DIFF_THRESHOLD`, `BASELINE_THRESHOLD`  
    - `HAND_MAX_ELEV`, `PERM_WATER_OCC`, `EXPORT_SCALE`
  - Patch size and buffer in `analyze_flood_and_infrastructure.py`:
    - `HALF_WINDOW_PX`, `BUFFER_DEG`, `OSM_FILTER`

---

## 📊 Results

- **Flood Extent**: binary GeoTIFF (`data/processed/flood_mask.tif`), masked by:
  - SAR change (pre/post & baseline)
  - HAND terrain mask (≤ 20 m)
  - JRC permanent water mask (≤ 80 % occurrence)

- **Analysis JSON** (`data/processed/flood_analysis.json`):
  ```json
  {
    "n_flooded_pixels": 396,
    "area_flooded_m2": 3937301.94,
    "total_road_length_m": 3589.67,
    "flooded_road_length_m": 99.71
  }
  ```

---

## 🛠️ Validation & Extension

- **Compare against**: JRC GSW Change, NASA ARIA, Copernicus EMS.  
- **Improve pipeline**: integrate Sentinel-2 optical, DEM refinements, ML/DL classifiers.  

---

## 📜 License & Credit

Provided under the MIT License.  
Developed by Oscar Canning-Thompson for the UK National Flood Forecasting Centre.

---

*For questions or contributions, please open an issue or pull request.*

