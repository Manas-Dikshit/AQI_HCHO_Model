"""Generate final high-resolution AQI and HCHO maps for submission.

Creates:
 - docs/final_aqi_map_<date>.png
 - docs/final_aqi_hcho_<date>.png

Requires: xarray, geopandas, matplotlib, src utilities (in-repo).
"""
from pathlib import Path
import xarray as xr
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from src.utils.aqi_calculator import compute_aqi_series
from src.visualization.plot_maps import AQI_CMAP, AQI_NORM, _add_india_boundary


def main():
    root = Path(__file__).resolve().parent.parent
    nc = root / "data" / "processed" / "predicted_aqi_grids" / "predicted_pm25.nc"
    hotspots = root / "data" / "processed" / "hcho_hotspot_clusters.geojson"
    out_dir = root / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not nc.exists():
        print("NetCDF not found:", nc)
        return

    ds = xr.open_dataset(nc)
    if "pm25_pred" not in ds.data_vars:
        print("Variable 'pm25_pred' not found in dataset")
        return

    times = pd.to_datetime(ds["time"].values)
    if len(times) == 0:
        print("No time dimension in dataset")
        return
    latest = times[-1]

    # extract latest time slice and convert to tidy DataFrame
    da = ds["pm25_pred"].sel(time=ds["time"][-1])
    df = da.to_dataframe().reset_index()
    df = df.rename(columns={"pm25_pred": "pm25"})
    df = df.dropna(subset=["pm25"]).copy()

    if df.empty:
        print("No PM2.5 values found in the latest slice")
        return

    # compute AQI from PM2.5 predictions
    aqi_series = compute_aqi_series(df[["pm25"]].rename(columns={"pm25": "pm25"}))
    df["aqi"] = aqi_series

    # Write high-resolution AQI map (using CPCB AQI colormap/norm)
    out_aqi = out_dir / f"final_aqi_map_{latest.strftime('%Y-%m-%d')}.png"
    fig, ax = plt.subplots(figsize=(14, 12))
    sc = ax.scatter(
        df["lon"], df["lat"],
        c=df["aqi"], cmap=AQI_CMAP, norm=AQI_NORM,
        s=8, marker="s", linewidths=0,
    )
    _add_india_boundary(ax)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"Predicted Surface AQI — {latest.strftime('%Y-%m-%d')}")
    cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("AQI")
    cbar.set_ticks([25, 75, 150, 250, 350, 450])
    cbar.set_ticklabels(["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"])
    plt.tight_layout()
    fig.savefig(out_aqi, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_aqi)

    # Combined AQI + HCHO hotspots
    out_comb = out_dir / f"final_aqi_hcho_{latest.strftime('%Y-%m-%d')}.png"
    fig, ax = plt.subplots(figsize=(14, 12))
    sc = ax.scatter(
        df["lon"], df["lat"],
        c=df["aqi"], cmap=AQI_CMAP, norm=AQI_NORM,
        s=8, marker="s", linewidths=0,
    )
    _add_india_boundary(ax)
    if hotspots.exists():
        try:
            gdf_h = gpd.read_file(hotspots)
            if not gdf_h.empty:
                try:
                    gdf_h.plot(ax=ax, facecolor="none", edgecolor="blue", linewidth=1.0)
                except Exception:
                    cent = gdf_h.geometry.centroid
                    gpd.GeoSeries(cent).plot(ax=ax, color="blue", markersize=10)
        except Exception as exc:
            print("Failed to read/plot HCHO hotspots:", exc)
    else:
        print("HCHO hotspots GeoJSON not found:", hotspots)

    cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("AQI")
    cbar.set_ticks([25, 75, 150, 250, 350, 450])
    cbar.set_ticklabels(["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"])
    plt.tight_layout()
    fig.savefig(out_comb, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Wrote:", out_comb)


if __name__ == '__main__':
    main()
