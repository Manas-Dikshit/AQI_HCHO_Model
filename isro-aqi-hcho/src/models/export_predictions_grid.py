"""export_predictions_grid.py
=============================
Utilities to run model inference over the full India grid and export
per-day gridded predictions as NetCDF / Parquet files and an index CSV.

Functions
- predict_on_grid_and_export(model_path, grid_csv, output_dir, config)

This module is called by the pipeline to create `predicted_aqi_grids/` files
for the dashboard and GIS tools.
"""

from __future__ import annotations

import json
from pathlib import Path
import logging
import yaml
import numpy as np
import pandas as pd
import torch

from src.models.cnn_lstm_aqi import build_grid_arrays, build_model
from src.visualization.export_geospatial_layers import grid_df_to_xarray, save_dataset_netcdf

logger = logging.getLogger(__name__)


def load_config(path: str = "config/aqi_training.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def predict_on_grid_and_export(
    model_checkpoint: str | Path,
    grid_csv: str | Path,
    output_dir: str | Path,
    config_path: str = "config/aqi_training.yaml",
    seq_len: int | None = None,
    device: str | None = None,
    export_geotiff: bool = False,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(config_path)
    if seq_len is None:
        seq_len = cfg.get("model", {}).get("sequence_length", 7)

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Build arrays from full grid CSV (no targets required)
    feature_cols = cfg.get("features", {}).get("satellite", []) + cfg.get("features", {}).get("meteorological", [])
    img_h = cfg.get("cnn_lstm", {}).get("spatial", {}).get("img_height", 30)
    img_w = cfg.get("cnn_lstm", {}).get("spatial", {}).get("img_width", 30)

    logger.info("Building grid arrays for full data …")
    X, y_dummy, dates = build_grid_arrays(grid_csv, None, feature_cols, img_h=img_h, img_w=img_w)

    # Load model
    model_cfg = cfg
    model = build_model(model_cfg)
    model.load_state_dict(torch.load(model_checkpoint, map_location=device))
    model.eval()

    # Run inference by tiling the full India grid so the exporter covers all cells.
    df_grid = pd.read_csv(grid_csv)
    lat_vals = np.sort(df_grid["lat"].unique())
    lon_vals = np.sort(df_grid["lon"].unique())
    n_lat = len(lat_vals)
    n_lon = len(lon_vals)

    T = len(X)
    # number of tiles in each dimension
    tiles_lat = int(np.ceil(n_lat / float(img_h)))
    tiles_lon = int(np.ceil(n_lon / float(img_w)))

    # container per-day
    preds_daily_map = {i: [] for i in range(seq_len, T)}
    resolution = cfg.get("grid", {}).get("resolution", 0.1)

    import tempfile

    # Precompute allowed coordinate set for filtering
    grid_coords = set((round(float(r["lat"]), 6), round(float(r["lon"]), 6)) for _, r in df_grid.iterrows())

    for ti in range(tiles_lat):
        lat_start = ti * img_h
        lat_end = min((ti + 1) * img_h, n_lat)
        tile_lats = lat_vals[lat_start:lat_end]
        if len(tile_lats) == 0:
            continue
        lat_min_tile = float(tile_lats[0] - resolution / 2.0)
        lat_max_tile = float(tile_lats[-1] + resolution / 2.0)

        for tj in range(tiles_lon):
            lon_start = tj * img_w
            lon_end = min((tj + 1) * img_w, n_lon)
            tile_lons = lon_vals[lon_start:lon_end]
            if len(tile_lons) == 0:
                continue
            lon_min_tile = float(tile_lons[0] - resolution / 2.0)
            lon_max_tile = float(tile_lons[-1] + resolution / 2.0)

            df_tile = df_grid[
                (df_grid["lat"] >= lat_min_tile) & (df_grid["lat"] <= lat_max_tile) &
                (df_grid["lon"] >= lon_min_tile) & (df_grid["lon"] <= lon_max_tile)
            ].copy()

            # write temp CSV for this tile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tf:
                tmp_path = tf.name
                df_tile.to_csv(tmp_path, index=False)

            try:
                X_tile, y_tile, dates_tile = build_grid_arrays(tmp_path, None, feature_cols, img_h=img_h, img_w=img_w)
            finally:
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass

            if len(dates_tile) != T:
                logger.warning("Tile (%d,%d) has %d dates (expected %d); skipping.", ti, tj, len(dates_tile), T)
                continue

            with torch.no_grad():
                for i in range(seq_len, T):
                    x = X_tile[i - seq_len: i]
                    x = np.expand_dims(x, axis=0)
                    xb = torch.tensor(x, dtype=torch.float32).to(device)
                    out_tile = model(xb).cpu().numpy()[0]

                    sub_lats = tile_lats
                    sub_lons = tile_lons

                    # pad/extend to img_h/img_w
                    if len(sub_lats) < img_h:
                        needed = img_h - len(sub_lats)
                        extra = sub_lats[-1] + np.arange(1, needed + 1) * resolution
                        sub_lats = np.concatenate([sub_lats, extra])
                    if len(sub_lons) < img_w:
                        needed = img_w - len(sub_lons)
                        extra = sub_lons[-1] + np.arange(1, needed + 1) * resolution
                        sub_lons = np.concatenate([sub_lons, extra])

                    sub_lats = np.round(np.array(sub_lats)[:img_h], 6)
                    sub_lons = np.round(np.array(sub_lons)[:img_w], 6)

                    for ii, lat in enumerate(sub_lats):
                        for jj, lon in enumerate(sub_lons):
                            key = (round(float(lat), 6), round(float(lon), 6))
                            if key not in grid_coords:
                                continue
                            preds_daily_map[i].append({
                                "date": pd.to_datetime(dates[i]),
                                "lat": float(lat),
                                "lon": float(lon),
                                "pm25_pred": float(out_tile[ii, jj]),
                            })

    preds_daily = [pd.DataFrame(preds_daily_map[i]) for i in sorted(preds_daily_map.keys())]

    # Concatenate and save a NetCDF dataset with dims (time, lat, lon)
    all_df = pd.concat(preds_daily, ignore_index=True)
    ds = grid_df_to_xarray(all_df, ["pm25_pred"], time_col="date")
    # Attach coordinate metadata for downstream GIS tools
    ds.attrs = ds.attrs or {}
    ds.attrs["crs"] = "EPSG:4326"
    ds.attrs["resolution"] = float(resolution)
    if "lat" in ds.coords:
        ds["lat"].attrs = {"units": "degrees_north", "standard_name": "latitude"}
    if "lon" in ds.coords:
        ds["lon"].attrs = {"units": "degrees_east", "standard_name": "longitude"}
    var_name = "pm25_pred"
    if var_name in ds.data_vars:
        ds[var_name].attrs = {"long_name": "Predicted PM2.5", "units": "ug m-3"}

    save_dataset_netcdf(ds, output_dir / "predicted_pm25.nc")

    # Also save a simple index CSV mapping dates to NetCDF path
    idx = pd.DataFrame({"date": ds["time"].values, "file": str(output_dir / "predicted_pm25.nc")})
    idx.to_csv(output_dir / "predictions_index.csv", index=False)

    logger.info("Exported predictions NetCDF → %s", output_dir)
    # Also export a coarse GeoJSON for fast dashboard choropleth (0.25°)
    try:
        from src.visualization.export_geospatial_layers import export_coarse_geojson
        # pick mean over time for coarse visualization
        mean_df = all_df.groupby(["lat", "lon"]).agg({"pm25_pred": "mean"}).reset_index()
        mean_df["date"] = pd.Timestamp("1970-01-01")
        export_coarse_geojson(mean_df, "pm25_pred", output_dir / "predicted_pm25_coarse.geojson", resolution=0.25)
    except Exception as exc:
        logger.warning("Failed to export coarse GeoJSON: %s", exc)
    # Optionally write per-day GeoTIFFs for GIS workflows
    if export_geotiff:
        try:
            from src.visualization.export_geospatial_layers import save_dataset_geotiff
            save_dataset_geotiff(ds, output_dir / "geotiffs", var_name="pm25_pred")
            logger.info("Exported GeoTIFFs → %s", output_dir / "geotiffs")
        except Exception as exc:  # pragma: no cover - best-effort
            logger.warning("Failed to export GeoTIFFs: %s", exc)
    return output_dir
