"""Smoke tests for geometry helpers and sample road segmentation."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
    if not path.is_file():
        pytest.skip(
            f"Sample file missing: {path}. "
            "Ensure data/sample/roads_sample.geojson is committed to the repository."
        )
    import geopandas as gpd

    gdf = ensure_wgs84(gpd.read_file(path))
    segs = segment_roads(gdf, seg_len_m=100, max_segments=50)
    assert len(segs) >= 1
    assert segs.crs.to_epsg() == 4326
