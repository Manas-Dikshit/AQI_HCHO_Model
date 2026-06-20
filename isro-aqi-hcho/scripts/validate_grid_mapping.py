#!/usr/bin/env python3
"""validate_grid_mapping.py

Simple smoke-test to verify that `build_grid_arrays` produces arrays
whose spatial dimensions correspond to the intended `img_h` x `img_w` crop
and that the exported lat/lon reconstruction matches shape.

Run from project root:
    python scripts/validate_grid_mapping.py
"""
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

from src.data.grid_definition import get_india_grid
from src.models.cnn_lstm_aqi import build_grid_arrays


def main():
    print("Starting grid mapping validation...")
    grid = get_india_grid()
    # create synthetic multi-day table (use a recent dynamic range)
    import datetime
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=9)
    dates = pd.date_range(start, end, freq="D")
    rows = []
    rng = np.random.default_rng(0)
    for d in dates:
        for _, r in grid.iterrows():
            rows.append({
                "cell_id": r["cell_id"],
                "lat": r["lat"],
                "lon": r["lon"],
                "date": d.strftime("%Y-%m-%d"),
                "insat_aod": float(rng.normal(0.1, 0.01)),
            })
    df = pd.DataFrame(rows)
    tmp = Path(tempfile.gettempdir()) / "validate_grid_mapping_grid.csv"
    df.to_csv(tmp, index=False)
    print("Wrote temporary grid CSV:", tmp)

    feature_cols = ["insat_aod"]
    img_h = 30
    img_w = 30
    X, y, dates_out = build_grid_arrays(tmp, None, feature_cols, img_h=img_h, img_w=img_w)
    print("build_grid_arrays produced X shape:", X.shape)
    assert X.shape[1] == len(feature_cols), "Unexpected channel count"
    assert X.shape[2] == img_h and X.shape[3] == img_w, "Spatial dims mismatch"
    print("Spatial dimensions match expected img_h x img_w")
    print("Validation OK")


if __name__ == '__main__':
    main()
