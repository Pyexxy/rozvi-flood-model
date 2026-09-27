# Data directory

## What is in the git repository

| Path | In git? | Notes |
|------|---------|--------|
| `sample/roads_sample.geojson` | **Yes** | Smoke tests and quick demo |
| `roads.geojson` | Optional | Your project corridor (may be private; not always published) |
| `dem.tif` / rainfall / worldcover | **No** | Large rasters; excluded by `*.tif` in `.gitignore` |
| `cache/` | **No** | Full CHIRPS annual downloads |

If you only see `dem.tfw` / `dem.tif.xml` without `dem.tif`, that is expected on a fresh clone: the elevation grid was never meant to be stored in git.

## Required local files for a production-style run

Place these under `data/` on your machine (paths are examples):

```text
data/
  roads.geojson                 # or pass any path via --roads
  dem.tif                       # elevation, metres (your SRTM or project DEM)
  rainfall_chirps_2023_mm.tif   # optional; from fetch_climate_lulc.py
  worldcover.tif                # optional; from fetch_climate_lulc.py
  sample/
    roads_sample.geojson        # shipped with the repo
```

### DEM

Copy your project DEM as `data/dem.tif` (or another name and pass `--dem`).

### Rainfall (CHIRPS) and land cover (WorldCover)

```bash
python fetch_climate_lulc.py --roads data/roads.geojson --outdir data --chirps-year 2023
```

Requires network. CHIRPS annual globals are cached under `data/cache/`.

### Run

```bash
python rozvi_flood_model.py \
  --roads data/roads.geojson \
  --dem data/dem.tif \
  --rain data/rainfall_chirps_2023_mm.tif \
  --lulc data/worldcover.tif \
  --outdir outputs \
  --portfolio-name "Harare-Beitbridge Road"
```

Without `--dem` / `--rain` / `--lulc` the model falls back to synthetic DEM, uniform rainfall placeholder, and neutral land cover — fine for pipeline tests only.
