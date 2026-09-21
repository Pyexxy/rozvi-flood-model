# Data directory

## Required input

| File | Format | Description |
|------|--------|-------------|
| Road network | GeoJSON or Shapefile | LineString / MultiLineString geometries in WGS84 (EPSG:4326) preferred |

Place project roads under `data/` (or pass any path via `--roads`).

## Optional rasters

| File | Format | Description |
|------|--------|-------------|
| DEM | GeoTIFF | Elevation (m). Strongly recommended for production runs |
| Water mask | GeoTIFF | Pixels > 0 treated as water |
| Rainfall | GeoTIFF | Precipitation (mm) for the analysis window |

Without a DEM the model falls back to a coarse synthetic surface for pipeline testing only. Do not use synthetic results for design or investment decisions.

## Sample data

`sample/roads_sample.geojson` is a short test line for smoke tests and CI. It is not the Harare–Beitbridge corridor.
