# Rozvi Flood Model

Corridor-scale **flood susceptibility screening** for linear assets (roads and similar networks).

The model segments a road network, scores each segment with a weighted multi-criteria index (precipitation, water proximity, land cover, slope, elevation), maps scores to a 0–100 risk category and band, and writes CSV, GeoJSON, JSON and Word report outputs.

This repository is intended for team use: clone, install dependencies, supply local inputs, and reproduce runs without a Google Earth Engine project or other personal cloud credentials.

---

## What this model is (and is not)

| In scope | Out of scope (reported as not assessed) |
|----------|------------------------------------------|
| Relative susceptibility score (1–10) | Return-period flood depths |
| Risk category (0–100) and bands | Defended / undefended hydraulics |
| Segment chainage and terrain attributes | Climate SSP depth surfaces |
| Portfolio screening summary | Expected Annual Loss (EAL) / PML |
| Reproducible local / offline workflow | Calibrated flood probability |

Treat outputs as a **screening ranking** to prioritise inspection and further study. Do not interpret scores as design water levels or insurance-grade probabilities.

---

## Repository layout

```text
rozvi-flood-model/
├── README.md                 # this file
├── LICENSE                   # MIT
├── requirements.txt          # pip dependencies
├── environment.yml           # optional conda environment
├── .gitignore
├── rozvi_flood_model.py      # main entry point (CLI)
├── config/
│   └── default.yaml          # default weights and parameters
├── data/
│   ├── README.md             # input data conventions
│   └── sample/
│       └── roads_sample.geojson
├── outputs/                  # created at runtime (gitignored)
└── tests/
    └── test_smoke.py
```

---

## Requirements

- Python 3.10 or newer (3.11 recommended)
- OS: Windows, macOS or Linux
- Optional but strongly recommended for production runs: a local DEM GeoTIFF covering the study corridor

No Google account, Earth Engine project ID or paid API key is required for the core workflow.

---

## Setup

### Option A — pip + venv

```bash
git clone <your-repo-url> rozvi-flood-model
cd rozvi-flood-model

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Option B — conda

```bash
conda env create -f environment.yml
conda activate rozvi-flood
```

---

## Quick start (sample data)

```bash
python rozvi_flood_model.py \
  --roads data/sample/roads_sample.geojson \
  --outdir outputs \
  --portfolio-name "Sample corridor"
```

On Windows PowerShell (one line):

```powershell
python rozvi_flood_model.py --roads data\sample\roads_sample.geojson --outdir outputs --portfolio-name "Sample corridor"
```

### Production run (recommended)

```bash
python rozvi_flood_model.py \
  --roads data/roads.geojson \
  --dem data/dem.tif \
  --outdir outputs \
  --portfolio-name "Harare-Beitbridge Road"
```

Optional:

```text
--water data/water_mask.tif
--rain  data/rainfall_mm.tif
--seg-length 100
--corridor 15
--max-segments 5000
--no-docx
```

---

## Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--roads` | Yes | GeoJSON or Shapefile of LineString / MultiLineString features |
| `--dem` | No* | Elevation GeoTIFF (metres). *Required for credible results |
| `--water` | No | Water mask GeoTIFF (values > 0 = water) |
| `--rain` | No | Rainfall GeoTIFF (mm) |
| `--outdir` | No | Output folder (default `./outputs`) |
| `--portfolio-name` | No | Name used in report metadata |

Road geometry should preferably be in **EPSG:4326**. Other CRS values are reprojected on load.

Without `--dem`, the model may attempt a public SRTM download (optional `elevation` package) or fall back to a synthetic surface for pipeline testing only.

---

## Outputs

Written under `--outdir`:

| File | Content |
|------|---------|
| `Executive_Summary_*.csv` | Portfolio headline metrics |
| `Road_Section_Exposure_Register_*.csv` | Per-segment scores, chainage, terrain |
| `Rozvi_Asset_Scores_*.csv` | Ranked asset table (report matrix) |
| `Rozvi_Report_Payload_*.json` | Machine-readable payload for templates |
| `Road_Segments_Scored_*.geojson` | Scored geometries for GIS |
| `Flood_Risk_Report_*.docx` | Word report (requires `python-docx`) |

For PDF, open the `.docx` and use **Save As → PDF**.

---

## Method summary

1. Load and reproject the road network.
2. Cut lines into fixed-length segments (default 100 m) in a local metric CRS.
3. Build driver rasters over the corridor bounding box:
   - elevation and derived slope
   - distance to water, or height above local DEM minima when no water mask is supplied
   - rainfall (or a uniform placeholder)
   - land cover held neutral when no LULC raster is supplied
4. Scale each driver to 1–10 with AOI percentile stretches; invert elevation, slope and water-distance so that higher physical values imply lower susceptibility where appropriate.
5. Combine drivers with fixed weights (see `config/default.yaml`).
6. Sample the composite surface under a corridor buffer; assign chainage and section IDs.
7. Map susceptibility to risk category  
   `category = round((score - 1) / 9 * 100)`  
   and to bands Minimal / Low / Moderate / High / Extreme.
8. Export tables, GeoJSON and the Word report.

Default weights:

| Driver | Weight |
|--------|--------|
| Precipitation | 0.30 |
| Distance to water / local low | 0.25 |
| Land cover | 0.20 |
| Slope | 0.15 |
| Elevation | 0.10 |

---

## Interpreting empty elevation or slope values

If `elev_m` or `slope_deg` is empty for a segment, the corridor buffer did not intersect any valid DEM pixels. Common causes:

- No DEM supplied (synthetic demo grid is coarse relative to a narrow buffer)
- Segment lies outside the DEM extent
- Very coarse raster resolution

Supply a DEM that covers the full network. Empty terrain samples often coincide with a neutral default score of 5.0 and should not be read as a strong moderate-risk finding.

---

## Tests

```bash
pip install pytest
pytest tests/test_smoke.py -q
```

---

## Reproducibility checklist for the team

1. Pin the repository commit hash used for a published run.
2. Record the exact CLI command (including DEM path and version).
3. Keep input roads and DEM under versioned storage or document their source and date.
4. Archive the full `outputs/` folder for that run with the report.
5. Do not commit large rasters to Git; use Git LFS or external storage and document the path in the run note.

---

## Publishing this repository to GitHub

```bash
cd rozvi-flood-model
git init
git add .
git status   # confirm outputs/ and large rasters are not staged
git commit -m "Initial Rozvi Flood Model release"
```

Create an empty repository on GitHub, then:

```bash
git branch -M main
git remote add origin https://github.com/<org-or-user>/rozvi-flood-model.git
git push -u origin main
```

Recommended repository settings:

- Add a short repository description: “Corridor flood susceptibility screening for linear assets”
- Protect `main` if the team uses pull requests
- Store large DEM/road datasets outside the repo or with Git LFS

---

## Licence

MIT — see [LICENSE](LICENSE).

Third-party data (SRTM, project DEMs, road centreline sources) remain subject to their own licences; cite them in project reports.

---

## Contact

Maintainers: update this section with the team lead and preferred issue tracker before the first public push.
