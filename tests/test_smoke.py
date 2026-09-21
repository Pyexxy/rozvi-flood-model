"""Smoke test: segment sample road and produce score fields."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import geopandas as gpd
from rozvi_flood_model import (
    ensure_wgs84,
    segment_roads,
    score_to_rozvi_category,
    rozvi_band,
)


def test_score_mapping():
    assert score_to_rozvi_category(1.0) == 0
    assert score_to_rozvi_category(10.0) == 100
    assert rozvi_band(5) == "Minimal"
    assert rozvi_band(50) == "Moderate"
    assert rozvi_band(90) == "Extreme"


def test_sample_segmentation():
    path = ROOT / "data" / "sample" / "roads_sample.geojson"
    gdf = ensure_wgs84(gpd.read_file(path))
    segs = segment_roads(gdf, seg_len_m=100, max_segments=50)
    assert len(segs) >= 1
    assert segs.crs.to_epsg() == 4326
