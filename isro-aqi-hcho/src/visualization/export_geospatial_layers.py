"""export_geospatial_layers.py
=================================
Utilities to convert gridded prediction DataFrames into spatial
products suitable for GIS and the Streamlit dashboard: NetCDF, GeoTIFF,
and downsampled GeoJSON for fast choropleth display.

Functions
- grid_df_to_xarray
- save_dataset_netcdf
- aggregate_to_resolution
- export_coarse_geojson

These utilities are intentionally lightweight and avoid external
dependencies beyond geopandas / xarray / rasterio which are listed in
requirements.txt.
"""

from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import xarray as xr

from shapely.geometry import box
import geopandas as gpd


def save_dataset_geotiff(ds: xr.Dataset, out_dir: str | Path, var_name: str | None = None) -> None:
    """Save an xarray Dataset variable as per-date single-band GeoTIFFs.

    Writes one GeoTIFF per time-step into *out_dir* with filenames
    ``{var_name}_YYYY-MM-DD.tif``. The function attempts to infer a
    regular lat/lon resolution from the coordinates.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        import rasterio
        from rasterio.transform import from_origin
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("rasterio is required to write GeoTIFFs") from exc

    if var_name is None:
        var_name = list(ds.data_vars.keys())[0]

    var = ds[var_name]
    lats = var.coords["lat"].values
    lons = var.coords["lon"].values
    if len(lats) < 1 or len(lons) < 1:
        raise ValueError("Dataset must contain non-empty 'lat' and 'lon' coordinates")

    # infer resolution (assume regular)
    res_lat = float(np.abs(lats[1] - lats[0])) if len(lats) > 1 else float(ds.attrs.get("resolution", 0.1))
    res_lon = float(np.abs(lons[1] - lons[0])) if len(lons) > 1 else float(ds.attrs.get("resolution", 0.1))

    # rasterio uses top-left origin; compute top-left corner (xleft, ytop)
    xleft = float(lons[0] - res_lon / 2.0)
    ytop = float(lats[-1] + res_lat / 2.0)

    for t in var.coords["time"].values:
        arr = var.sel(time=t).values
        arr = np.asarray(arr)
        # flip rows so first array row corresponds to top (north)
        arr_flipped = np.flipud(arr)

        out_path = out / f"{var_name}_{np.datetime_as_string(t, unit='D')}.tif"
        dtype = str(arr_flipped.dtype)
        transform = from_origin(xleft, ytop, res_lon, res_lat)

        with rasterio.open(
            out_path, "w",
            driver="GTiff",
            height=arr_flipped.shape[0],
            width=arr_flipped.shape[1],
            count=1,
            dtype=dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(arr_flipped, 1)




def grid_df_to_xarray(df: pd.DataFrame, value_cols: list[str],
                      time_col: str = "date", lat_col: str = "lat", lon_col: str = "lon") -> xr.Dataset:
    """Convert a flat gridded DataFrame into an xarray.Dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns for time, lat, lon and the listed value_cols.
    value_cols : list[str]
        Column names to include as data variables.

    Returns
    -------
    xr.Dataset
        Dataset with dims (time, lat, lon) and coordinates.
    """
    if df.empty:
        return xr.Dataset()

    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    times = np.sort(df[time_col].unique())
    lats = np.sort(df[lat_col].unique())
    lons = np.sort(df[lon_col].unique())

    times = pd.to_datetime(times)

    data_vars = {}
    for col in value_cols:
        arr = np.full((len(times), len(lats), len(lons)), np.nan, dtype=np.float32)
        # build index maps
        lat_idx = {float(v): i for i, v in enumerate(lats)}
        lon_idx = {float(v): j for j, v in enumerate(lons)}
        time_idx = {pd.Timestamp(t): k for k, t in enumerate(times)}

        # fill
        for _, row in df[[time_col, lat_col, lon_col, col]].dropna(subset=[col]).iterrows():
            t = pd.Timestamp(row[time_col])
            i = lat_idx.get(float(row[lat_col]))
            j = lon_idx.get(float(row[lon_col]))
            k = time_idx.get(t)
            if i is None or j is None or k is None:
                continue
            arr[k, i, j] = float(row[col])

        data_vars[col] = (("time", "lat", "lon"), arr)

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "time": times,
            "lat": lats,
            "lon": lons,
        },
    )
    return ds


def save_dataset_netcdf(ds: xr.Dataset, out_path: str | Path) -> None:
    """Save xarray Dataset to NetCDF (creates parent dir)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out)


def aggregate_to_resolution(df: pd.DataFrame, target_res: float, res_col: str = "resampled_cell") -> pd.DataFrame:
    """Aggregate a flat grid DataFrame to a coarser regular grid by
    snapping lat/lon to the target resolution and averaging numeric values.

    Returns aggregated DataFrame with columns ['lat', 'lon', ...].
    """
    df = df.copy()
    half = target_res / 2.0

    def snap(x: float) -> float:
        return float(round(round(x / target_res) * target_res, 6))

    df["lat_snap"] = df["lat"].apply(snap)
    df["lon_snap"] = df["lon"].apply(snap)

    agg = df.groupby(["date", "lat_snap", "lon_snap"]).mean().reset_index()
    # rename snapped coords to 'lat'/'lon'
    agg = agg.rename(columns={"lat_snap": "lat", "lon_snap": "lon"})

    # If duplicate column names (e.g., original 'lat'/'lon' present alongside
    # the renamed snapped coords), drop duplicates and keep the snapped coords
    # (they appear last after the rename). This avoids per-row Series values
    # when selecting agg['lat'] during iteration.
    if agg.columns.duplicated().any():
        agg = agg.loc[:, ~agg.columns.duplicated(keep='last')]

    return agg


def export_coarse_geojson(df: pd.DataFrame, value_col: str, out_geojson: str | Path,
                          resolution: float = 0.25) -> None:
    """Export a downsampled GeoJSON choropleth where each polygon is a
    grid-cell at the requested `resolution` (degrees). The property
    for styling is `value_col`.
    """
    out = Path(out_geojson)
    out.parent.mkdir(parents=True, exist_ok=True)

    agg = aggregate_to_resolution(df, resolution)

    # Ensure expected columns exist and are numeric
    if "lat" not in agg.columns or "lon" not in agg.columns:
        raise ValueError("Aggregated DataFrame missing 'lat'/'lon' columns")

    agg = agg.copy()
    agg["lat"] = pd.to_numeric(agg["lat"], errors="coerce")
    agg["lon"] = pd.to_numeric(agg["lon"], errors="coerce")
    if value_col not in agg.columns:
        agg[value_col] = np.nan
    else:
        agg[value_col] = pd.to_numeric(agg[value_col], errors="coerce")

    polys = []
    vals = []
    dates = []
    half = resolution / 2.0
    for idx in agg.index:
        lat = agg.at[idx, "lat"]
        lon = agg.at[idx, "lon"]
        if pd.isna(lat) or pd.isna(lon):
            continue
        try:
            latf = float(lat)
            lonf = float(lon)
        except Exception:
            continue

        geom = box(lonf - half, latf - half, lonf + half, latf + half)
        polys.append(geom)

        val = agg.at[idx, value_col]
        vals.append(float(val) if pd.notna(val) else math.nan)

        # date may be present or not depending on aggregation
        date_val = agg.at[idx, "date"] if "date" in agg.columns else None
        dates.append(pd.Timestamp(date_val) if pd.notna(date_val) else None)

    gdf = gpd.GeoDataFrame({"date": dates, value_col: vals}, geometry=polys, crs="EPSG:4326")
    gdf.to_file(out, driver="GeoJSON")


if __name__ == "__main__":
    print("export_geospatial_layers: utility module — import functions from Python")
