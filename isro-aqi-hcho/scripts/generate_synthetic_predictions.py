#!/usr/bin/env python3
"""generate_synthetic_predictions.py

Create synthetic pm25 predictions for all dates in grid_daily_features.csv and
write NetCDF, coarse GeoJSON, and optional GeoTIFFs for dashboard testing.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from src.visualization.export_geospatial_layers import (
    grid_df_to_xarray,
    save_dataset_netcdf,
    export_coarse_geojson,
    save_dataset_geotiff,
    aggregate_to_resolution,
)


def main():
    root = Path(__file__).resolve().parent.parent
    grid_csv = root / "data" / "processed" / "grid_daily_features.csv"
    out_dir = root / "data" / "processed" / "predicted_aqi_grids"

    if not grid_csv.exists():
        print("grid_daily_features.csv not found at:", grid_csv)
        return

    df = pd.read_csv(grid_csv)
    if df.empty:
        print("Grid CSV is empty — nothing to do.")
        return

    df["date"] = pd.to_datetime(df["date"])
    df["doy"] = df["date"].dt.dayofyear

    rng = np.random.default_rng(1)

    def synth_val(row):
        base = 20.0
        # simple lat-based gradient and seasonal cycle
        lat_factor = (30.0 - float(row["lat"])) / 30.0 * 10.0
        seasonal = 10.0 * np.sin(2.0 * np.pi * float(row["doy"]) / 365.0)
        noise = float(rng.normal(0, 3.0))
        return max(0.0, base + lat_factor + seasonal + noise)

    df["pm25_pred"] = df.apply(synth_val, axis=1)

    # Convert to xarray and save NetCDF
    ds = grid_df_to_xarray(df[["date", "lat", "lon", "pm25_pred"]], ["pm25_pred"], time_col="date")
    ds.attrs = ds.attrs or {}
    ds.attrs["crs"] = "EPSG:4326"
    ds.attrs["resolution"] = 0.1

    out_dir.mkdir(parents=True, exist_ok=True)
    out_nc = out_dir / "predicted_pm25.nc"
    save_dataset_netcdf(ds, out_nc)
    print("Wrote NetCDF:", out_nc)

    # Coarse GeoJSON (try helper, fall back to manual creation on error)
    out_geo = out_dir / "predicted_pm25_coarse.geojson"
    try:
        export_coarse_geojson(df[["date", "lat", "lon", "pm25_pred"]], "pm25_pred", out_geo, resolution=0.25)
        print("Wrote coarse GeoJSON:", out_geo)
    except Exception as exc:
        print("export_coarse_geojson failed, falling back to manual export:", exc)
        try:
            import geopandas as gpd
            from shapely.geometry import box
            agg = aggregate_to_resolution(df[["date", "lat", "lon", "pm25_pred"]], 0.25)
            polys = []
            vals = []
            dates = []
            for _, row in agg.iterrows():
                lat = float(row["lat"])
                lon = float(row["lon"])
                half = 0.25 / 2.0
                geom = box(lon - half, lat - half, lon + half, lat + half)
                polys.append(geom)
                vals.append(float(row.get("pm25_pred", float("nan"))))
                dates.append(pd.to_datetime(row["date"]))
            gdf = gpd.GeoDataFrame({"date": dates, "pm25_pred": vals}, geometry=polys, crs="EPSG:4326")
            gdf.to_file(out_geo, driver="GeoJSON")
            print("Wrote coarse GeoJSON (fallback):", out_geo)
        except Exception as exc2:
            print("Fallback coarse GeoJSON export also failed:", exc2)

    # Optional GeoTIFFs
    try:
        save_dataset_geotiff(ds, out_dir, var_name="pm25_pred")
        print("Wrote GeoTIFFs into:", out_dir)
    except Exception as exc:
        print("GeoTIFF export skipped (rasterio may be missing):", exc)


if __name__ == "__main__":
    main()
