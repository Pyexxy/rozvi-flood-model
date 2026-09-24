#!/usr/bin/env python3
"""
Remote data helpers for Rozvi Flood Model
========================================

Optional download of:

* CHIRPS v2.0 precipitation (Climate Hazards Group) — used as the rainfall grid
* ESA WorldCover land cover — used as the land-use / land-cover driver

Both products are retrieved over HTTPS, clipped to the study bounding box, and
written as local GeoTIFFs so subsequent model runs can stay offline and
reproducible.

These helpers do not require Google Earth Engine. Internet access is required
only for the download step.

Typical usage
-------------
    from fetch_climate_lulc import fetch_chirps_annual, fetch_worldcover, bounds_from_vector

    bounds = bounds_from_vector("data/roads.geojson")
    fetch_chirps_annual(2023, bounds, "data/rainfall_chirps_mm.tif")
    fetch_worldcover(bounds, "data/worldcover.tif")
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds
    from rasterio.warp import calculate_default_transform, reproject, transform_bounds
except ImportError as exc:
    sys.exit("rasterio is required for data fetch helpers\n" + str(exc))

try:
    import geopandas as gpd
except ImportError:
    gpd = None


# CHIRPS annual global GeoTIFFs (mm/year), Climate Hazards Center / UCSB
CHIRPS_ANNUAL_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_annual/tifs/"
    "chirps-v2.0.{year}.tif"
)

# ESA WorldCover 2021 10 m — AWS Open Data (COG tiles are preferred in production;
# here we use the Planetary Computer STAC item when available, with a simple
# HTTPS fallback documentation path).
WORLDCOVER_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def bounds_from_vector(
    path: str | Path,
    pad_deg: float = 0.05,
) -> Tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) in EPSG:4326 with a small pad."""
    if gpd is None:
        raise RuntimeError("geopandas is required to read vector bounds")
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    minx, miny, maxx, maxy = gdf.total_bounds
    return (minx - pad_deg, miny - pad_deg, maxx + pad_deg, maxy + pad_deg)


def _download(url: str, dest: Path, timeout: int = 600) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading:\n    {url}")
    print(f"  -> {dest}")

    def _report(block: int, block_size: int, total: int) -> None:
        if total <= 0:
            return
        done = block * block_size
        pct = min(100.0, 100.0 * done / total)
        if block % 50 == 0 or pct >= 100:
            print(f"\r  {pct:5.1f}%", end="", flush=True)

    urllib.request.urlretrieve(url, str(dest), reporthook=_report)
    print()
    if not dest.exists() or dest.stat().st_size < 1000:
        raise RuntimeError(f"Download failed or file too small: {dest}")
    return dest


def _window_to_geotiff(
    src_path: Path,
    bounds: Tuple[float, float, float, float],
    out_path: Path,
    dst_crs: str = "EPSG:4326",
) -> Path:
    """Clip a (possibly global) raster to bounds and write a local GeoTIFF."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    minx, miny, maxx, maxy = bounds

    with rasterio.open(src_path) as src:
        # Transform bounds into the source CRS if needed
        if src.crs and src.crs.to_string() not in (dst_crs, "EPSG:4326"):
            rb = transform_bounds(dst_crs, src.crs, minx, miny, maxx, maxy, densify_pts=21)
        else:
            rb = (minx, miny, maxx, maxy)

        window = from_bounds(*rb, transform=src.transform)
        data = src.read(1, window=window, boundless=True, fill_value=src.nodata)
        win_transform = src.window_transform(window)

        # Strip layout avoids BLOCKYSIZE multiple-of-16 errors on small clips
        profile = {
            "driver": "GTiff",
            "height": int(data.shape[0]),
            "width": int(data.shape[1]),
            "count": 1,
            "dtype": data.dtype,
            "crs": src.crs or "EPSG:4326",
            "transform": win_transform,
            "compress": "lzw",
            "tiled": False,
            "interleave": "band",
        }
        if src.nodata is not None:
            profile["nodata"] = src.nodata
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(data, 1)

    print(f"  Wrote clip: {out_path}  shape={data.shape}")
    return out_path


def fetch_chirps_annual(
    year: int,
    bounds: Tuple[float, float, float, float],
    out_path: str | Path,
    cache_dir: str | Path = "data/cache",
) -> Path:
    """
    Download CHIRPS v2.0 annual precipitation (mm/year) and clip to bounds.

    Parameters
    ----------
    year : int
        Calendar year (CHIRPS archive availability depends on product release).
    bounds : tuple
        (minx, miny, maxx, maxy) in EPSG:4326.
    out_path : path
        Output GeoTIFF (mm/year over the AOI).
    cache_dir : path
        Directory for the full global annual file (reused across runs).

    Returns
    -------
    Path to the clipped GeoTIFF.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    global_tif = cache_dir / f"chirps-v2.0.{year}.tif"
    url = CHIRPS_ANNUAL_URL.format(year=year)

    if not global_tif.exists():
        try:
            _download(url, global_tif)
        except Exception as exc:
            raise RuntimeError(
                f"CHIRPS download failed for year {year}. "
                f"Check network access and that the year exists on the CHC server.\n{exc}"
            ) from exc
    else:
        print(f"  Using cached CHIRPS: {global_tif}")

    return _window_to_geotiff(global_tif, bounds, Path(out_path))


def fetch_worldcover(
    bounds: Tuple[float, float, float, float],
    out_path: str | Path,
    year: int = 2021,
) -> Path:
    """
    Fetch ESA WorldCover land cover for the bounding box.

    Prefers Microsoft Planetary Computer STAC (COG, no manual tile hunting).
    Falls back with a clear error if the stack is unavailable so the user can
    place a manual WorldCover GeoTIFF at out_path instead.

    Class values follow ESA WorldCover (10, 20, ..., 100).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    minx, miny, maxx, maxy = bounds

    try:
        import pystac_client
        import stackstac
        import planetary_computer
    except ImportError as exc:
        raise RuntimeError(
            "WorldCover auto-fetch requires: pystac-client, stackstac, planetary-computer.\n"
            "  pip install pystac-client stackstac planetary-computer\n"
            "Alternatively download ESA WorldCover manually and pass --lulc path/to/file.tif\n"
            f"Import error: {exc}"
        ) from exc

    print("  Querying Planetary Computer STAC for ESA WorldCover ...")
    catalog = pystac_client.Client.open(
        WORLDCOVER_STAC,
        modifier=planetary_computer.sign_inplace,
    )
    search = catalog.search(
        collections=["esa-worldcover"],
        bbox=[minx, miny, maxx, maxy],
        query={"esa_worldcover:product_version": {"eq": "2.0.0"}} if year >= 2021 else None,
    )
    items = list(search.items())
    if not items:
        # retry without version filter
        search = catalog.search(
            collections=["esa-worldcover"],
            bbox=[minx, miny, maxx, maxy],
        )
        items = list(search.items())
    if not items:
        raise RuntimeError(
            "No WorldCover items found for this bbox. "
            "Download a tile from https://esa-worldcover.org/ and use --lulc."
        )

    print(f"  Found {len(items)} item(s); stacking and clipping ...")
    # stackstac returns xarray; take map asset
    stack = stackstac.stack(
        items,
        assets=["map"],
        bounds_latlon=(minx, miny, maxx, maxy),
        epsg=4326,
        resolution=0.0001,  # ~10 m at equator; adequate for corridor screening
        chunksize=2048,
    )
    # WorldCover is categorical — nearest
    data = stack.isel(time=0).squeeze().values if "time" in stack.dims else stack.squeeze().values
    if data.ndim > 2:
        data = data[0]

    height, width = data.shape
    transform = rasterio.transform.from_bounds(minx, miny, maxx, maxy, width, height)
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "lzw",
        "tiled": False,
        "nodata": 0,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(np.asarray(data, dtype=np.uint8), 1)
    print(f"  Wrote WorldCover clip: {out_path}  shape={data.shape}")
    return out_path


# ESA WorldCover class → flood susceptibility score on 1–10 scale (screening)
# Higher = more susceptible in this formulation (runoff / water presence).
WORLDCOVER_TO_SUSCEPTIBILITY = {
    10: 3.0,   # Tree cover
    20: 4.0,   # Shrubland
    30: 5.0,   # Grassland
    40: 6.0,   # Cropland
    50: 7.5,   # Built-up
    60: 5.5,   # Bare / sparse vegetation
    70: 2.0,   # Snow and ice
    80: 9.5,   # Permanent water bodies
    90: 8.5,   # Herbaceous wetland
    95: 8.0,   # Mangroves
    100: 4.0,  # Moss and lichen
}


def worldcover_to_risk_array(lulc: np.ndarray) -> np.ndarray:
    """Map WorldCover class codes to a 1–10 susceptibility surface."""
    out = np.full(lulc.shape, 5.0, dtype=np.float64)
    for code, score in WORLDCOVER_TO_SUSCEPTIBILITY.items():
        out[lulc == code] = score
    out[~np.isfinite(lulc)] = 5.0
    out[lulc == 0] = 5.0
    return np.clip(out, 1.0, 10.0)


def fetch_for_roads(
    roads_path: str | Path,
    out_dir: str | Path = "data",
    chirps_year: int = 2023,
    do_chirps: bool = True,
    do_worldcover: bool = True,
) -> dict:
    """
    Convenience: derive bounds from a road network and fetch both products.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bounds = bounds_from_vector(roads_path)
    print(f"AOI bounds (padded): {bounds}")

    result = {"bounds": bounds, "chirps": None, "worldcover": None}
    if do_chirps:
        result["chirps"] = fetch_chirps_annual(
            chirps_year, bounds, out_dir / f"rainfall_chirps_{chirps_year}_mm.tif"
        )
    if do_worldcover:
        result["worldcover"] = fetch_worldcover(bounds, out_dir / "worldcover.tif")
    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Fetch CHIRPS and/or ESA WorldCover for an AOI")
    p.add_argument("--roads", required=True, help="Road GeoJSON/Shapefile used to set bounds")
    p.add_argument("--outdir", default="data", help="Output directory for clipped GeoTIFFs")
    p.add_argument("--chirps-year", type=int, default=2023,
                   help="CHIRPS calendar year (mm/year). Choose the year that matches your study period.")
    p.add_argument("--no-chirps", action="store_true")
    p.add_argument("--no-worldcover", action="store_true")
    args = p.parse_args()

    fetch_for_roads(
        args.roads,
        out_dir=args.outdir,
        chirps_year=args.chirps_year,
        do_chirps=not args.no_chirps,
        do_worldcover=not args.no_worldcover,
    )
    print("Done.")
