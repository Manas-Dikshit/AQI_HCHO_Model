"""Plot a static map showing coarse PM2.5 predictions and HCHO hotspots.

Saves a PNG to `docs/aqi_hcho_map.png`.
"""
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parent.parent
    pm25_geo = root / "data" / "processed" / "predicted_aqi_grids" / "predicted_pm25_coarse.geojson"
    hcho_geo = root / "data" / "processed" / "hcho_hotspot_clusters.geojson"
    out_png = root / "docs" / "aqi_hcho_map.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if not pm25_geo.exists():
        print("PM2.5 coarse GeoJSON not found:", pm25_geo)
        return
    if not hcho_geo.exists():
        print("HCHO hotspots GeoJSON not found:", hcho_geo)

    gdf_pm25 = gpd.read_file(pm25_geo)
    gdf_hcho = gpd.read_file(hcho_geo) if hcho_geo.exists() else None

    # Compute color limits (clip at 2nd-98th percentile to avoid outliers)
    vals = gdf_pm25['pm25_pred'].dropna().astype(float)
    vmin = float(np.nanpercentile(vals, 2)) if len(vals) > 0 else 0.0
    vmax = float(np.nanpercentile(vals, 98)) if len(vals) > 0 else 100.0

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf_pm25.plot(column='pm25_pred', ax=ax, cmap='OrRd', linewidth=0, edgecolor='none', vmin=vmin, vmax=vmax)

    # Overlay hotspots
    if gdf_hcho is not None and not gdf_hcho.empty:
        # plot cluster polygons if present, otherwise centroids
        try:
            gdf_hcho.plot(ax=ax, facecolor='none', edgecolor='blue', linewidth=1.0)
        except Exception:
            centroids = gdf_hcho.geometry.centroid
            gpd.GeoSeries(centroids).plot(ax=ax, color='blue', markersize=10)

    ax.set_title('Coarse Surface PM2.5 Predictions (synthetic) and HCHO Hotspots')
    ax.set_axis_off()
    # Add a colorbar
    sm = plt.cm.ScalarMappable(cmap='OrRd', norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = fig.colorbar(sm, ax=ax, fraction=0.036, pad=0.04)
    cbar.set_label('PM2.5 (µg/m³)')

    fig.savefig(out_png, dpi=150, bbox_inches='tight')
    print('Wrote map:', out_png)


if __name__ == '__main__':
    main()
