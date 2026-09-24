# Rozvi Flood Model

Corridor-scale **flood susceptibility screening** for linear assets (roads and similar networks).

The model segments a road network, scores each segment with a weighted multi-criteria index, maps scores to a 0–100 risk category and band, attributes **which drivers contribute most at each location**, and writes CSV, GeoJSON, JSON, figure and Word report outputs.

This repository is intended for team use: clone, install dependencies, supply local inputs (or fetch CHIRPS / WorldCover), and reproduce runs without a Google Earth Engine project or other personal cloud credentials.

**Current version:** 1.4.1

---

## What this model is (and is not)

| In scope | Out of scope (reported as not assessed) |
|----------|------------------------------------------|
| Relative susceptibility score (1–10) | Return-period flood depths |
| Risk category (0–100) and bands | Defended / undefended hydraulics |
| Per-segment driver contributions | Climate SSP depth surfaces |
| Segment chainage and terrain attributes | Expected Annual Loss (EAL) / PML |
| Optional CHIRPS rainfall and ESA WorldCover LULC | Calibrated flood probability |
| Maps and charts in the Word report | Inundation extent polygons |

Treat outputs as a **screening ranking** to prioritise inspection and further study. Do not interpret scores as design water levels or insurance-grade probabilities.

---

## Repository layout

```text
rozvi-flood-model/
├── README.md
├── LICENSE
├── requirements.txt
├── environment.yml
├── .gitignore
├── rozvi_flood_model.py      # main CLI
├── fetch_climate_lulc.py     # optional CHIRPS + WorldCover download
├── config/
│   └── default.yaml
├── data/
│   ├── README.md
│   ├── roads.geojson         # your corridor (required)
│   ├── dem.tif               # elevation (strongly recommended)
│   ├── rainfall_chirps_*.tif # optional, from fetch script
│   ├── worldcover.tif        # optional, from fetch script
│   ├── cache/                # full CHIRPS annual downloads
│   └── sample/
├── outputs/                  # created at runtime (gitignored)
├── docs/
│   └── METHOD.md
└── tests/
    └── test_smoke.py
```

---

## Requirements

- Python 3.10 or newer (3.11 recommended; 3.12–3.14 work with current wheels)
- OS: Windows, macOS or Linux
- Internet only for optional CHIRPS / WorldCover fetch

Core stack: `geopandas`, `rasterio`, `numpy`, `pandas`, `shapely`, `scipy`, `pyproj`, `python-docx`, `matplotlib`

Optional for auto-fetch:

- CHIRPS: no extra packages beyond core
- WorldCover: `pystac-client`, `planetary-computer`, `stackstac`, `xarray`, `dask`

---

## Setup

### pip + venv

```bash
git clone <your-repo-url> rozvi-flood-model
cd rozvi-flood-model

python -m venv .venv

# Windows PowerShell
.venv\Scripts\activate
# If activation is blocked:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### conda

```bash
conda env create -f environment.yml
conda activate rozvi-flood
```

---

## Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--roads` | Yes | GeoJSON or Shapefile (LineString / MultiLineString) |
| `--dem` | Strongly recommended | Elevation GeoTIFF (metres). Without it the model uses a synthetic test surface |
| `--rain` | Recommended | Rainfall GeoTIFF (mm), e.g. CHIRPS annual clip |
| `--lulc` | Recommended | Land-cover GeoTIFF, e.g. ESA WorldCover |
| `--water` | Optional | Water-mask GeoTIFF (values > 0 = water) |
| `--outdir` | No | Output folder (default `./outputs`) |
| `--portfolio-name` | No | Name used in report metadata |
| `--seg-length` | No | Segment length in metres (default 100) |
| `--corridor` | No | Half-width of sampling buffer in metres (default 15) |
| `--max-segments` | No | Cap on number of segments (default 5000) |
| `--no-docx` | No | Skip Word report |

Road geometry should preferably be in **EPSG:4326**. Other CRS values are reprojected on load.

**Important:** files in `data/` are not picked up automatically. Pass them with `--dem`, `--rain`, and `--lulc`.

---

## Optional data fetch (CHIRPS + WorldCover)

`fetch_climate_lulc.py` downloads and clips products to the road corridor bounding box. No Google Earth Engine account is required.

```bash
# Both products (CHIRPS annual + ESA WorldCover)
python fetch_climate_lulc.py --roads data/roads.geojson --outdir data --chirps-year 2023

# CHIRPS only
python fetch_climate_lulc.py --roads data/roads.geojson --outdir data --chirps-year 2023 --no-worldcover

# WorldCover only
python fetch_climate_lulc.py --roads data/roads.geojson --outdir data --no-chirps
```

| Product | Source | Notes |
|---------|--------|--------|
| **CHIRPS v2.0 annual** | Climate Hazards Center (UCSB) HTTPS | mm/year for the chosen calendar year; global file cached under `data/cache/` |
| **ESA WorldCover** | Microsoft Planetary Computer STAC | 10 m classes; mapped to a 1–10 susceptibility surface in the model |

Choose `--chirps-year` to match your study period (2023 is only an example default).

Zimbabwe Meteorological Department (ZMD) station data can be used separately for **cross-check** (bias tables in the report narrative). They are not a second grid inside the weighted score unless you build a bias-corrected raster.

---

## Running the model

### Minimal (roads only — demo terrain)

```bash
python rozvi_flood_model.py --roads data/roads.geojson --outdir outputs
```

### Recommended (DEM + CHIRPS + WorldCover)

**Windows PowerShell:**

```powershell
python rozvi_flood_model.py --roads data\roads.geojson --dem data\dem.tif --rain data\rainfall_chirps_2023_mm.tif --lulc data\worldcover.tif --outdir outputs --portfolio-name "Harare-Beitbridge Road"
```

**bash:**

```bash
python rozvi_flood_model.py \
  --roads data/roads.geojson \
  --dem data/dem.tif \
  --rain data/rainfall_chirps_2023_mm.tif \
  --lulc data/worldcover.tif \
  --outdir outputs \
  --portfolio-name "Harare-Beitbridge Road"
```

Confirm in the log:

```text
Reading DEM: data\dem.tif
Rain resampled to DEM grid: ...
Reading LULC: data\worldcover.tif
```

If you see `synthetic (demo)` or `placeholder (80 mm uniform)`, the corresponding path was missing or incorrect.

### Sample smoke test

```bash
python rozvi_flood_model.py --roads data/sample/roads_sample.geojson --outdir outputs --portfolio-name "Sample corridor"
```

---

## Scoring method (summary)

**Fixed weights** (must sum to 1.0):

| Driver | Weight | Typical data |
|--------|--------|----------------|
| Precipitation | 0.30 | CHIRPS or other mm grid; else uniform 80 mm placeholder |
| Proximity to water / local low points | 0.25 | Water mask distance, or height above local DEM minimum |
| Land cover | 0.20 | ESA WorldCover classes; else neutral 5 |
| Slope | 0.15 | Derived from DEM |
| Elevation | 0.10 | DEM |

Each continuous driver is scaled to 1–10 with AOI percentile stretches (2nd–98th). Land-cover classes are mapped to fixed susceptibility values. Segment scores are corridor zonal means.

**Risk category:** `round((score - 1) / 9 * 100)` → bands Minimal / Low / Moderate / High / Extreme.

**Local attribution:** for each segment, `contribution = weight × scaled_driver`. The report lists primary and top drivers at that location. Global weights used for the score do not change.

Rain and LULC rasters that differ in resolution from the DEM are **resampled to the DEM grid** before combination (bilinear for rain, nearest for categorical LULC).

---

## Outputs

Written under `--outdir`:

| File | Content |
|------|---------|
| `Executive_Summary_*.csv` | Portfolio headline metrics |
| `Road_Section_Exposure_Register_*.csv` | Per-segment scores, chainage, contributions |
| `Rozvi_Asset_Scores_*.csv` | Ranked asset table |
| `Risk_Driver_Weights_*.csv` | Driver weights and data sources for the run |
| `Rozvi_Report_Payload_*.json` | Machine-readable payload |
| `Road_Segments_Scored_*.geojson` | Scored geometries for GIS |
| `Flood_Risk_Report_*.docx` | Word report (figures embedded) |
| `figures/` | PNG charts and corridor map |

### Figures

- Risk band distribution  
- Score histogram  
- Longitudinal risk profile along the network  
- Corridor map (segments by band)  
- Primary driver share  
- Stacked driver contributions for top segments  

For PDF: open the `.docx` and use **Save As → PDF**.

---

## DEM notes

- Prefer a GeoTIFF in metres covering the full corridor (e.g. SRTM ~30 m, project survey DEM).  
- On Windows, ensure you pass the large raster (hundreds of MB), not a small `.xml` sidecar.  
- Example: `--dem data/dem.tif`

---

## Interpreting empty elevation or slope values

If `elev_m` or `slope_deg` is empty, the corridor buffer did not intersect valid DEM pixels (extent mismatch, nodata, or geometry issues). Supply a DEM that fully covers the network.

---

## Tests

```bash
pip install pytest
pytest tests/test_smoke.py -q
```

---

## Reproducibility checklist

1. Record the git commit hash used for a published run.  
2. Record the exact CLI (including DEM, rain, LULC paths and CHIRPS year).  
3. Keep input roads and rasters under versioned storage or document source and date.  
4. Archive the full `outputs/` folder with the report.  
5. Do not commit large rasters to Git; use Git LFS or external storage.

---

## Publishing to GitHub

```bash
cd rozvi-flood-model
git init
git add .
git status   # confirm outputs/ and large rasters are not staged
git commit -m "Rozvi Flood Model initial release"
git branch -M main
git remote add origin https://github.com/<org-or-user>/rozvi-flood-model.git
git push -u origin main
```

---

## Licence

MIT — see [LICENSE](LICENSE).

Third-party data remain subject to their own terms:

- CHIRPS (Climate Hazards Center / UCSB)  
- ESA WorldCover  
- SRTM / other DEMs  
- Road centreline sources  

Cite them in project reports.

---

## Contact

Maintainers: update this section with the team lead and preferred issue tracker before the first public push.
