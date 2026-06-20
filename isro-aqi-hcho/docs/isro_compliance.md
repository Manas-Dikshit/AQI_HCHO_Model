# ISRO Problem Statement Alignment — V4

This document maps the ISRO hackathon requirements to the repository V4 implementation.

## Objective 1 — Surface AQI
- India grid: regular lat/lon grid defined in `src/data/grid_definition.py` (default 0.1°; bbox 68–97.5E, 8–37.5N).
- Training data: `src/data/build_dataset_aqi.py` builds `data/processed/grid_daily_features.csv` and `data/processed/aqi_training_dataset.csv` which join satellite, INSAT AOD, ERA5 and CPCB ground station labels.
- Models: baseline RF/GBM in `src/models/baseline_ml.py`; CNN-LSTM and ConvLSTM in `src/models/cnn_lstm_aqi.py` and training script `src/models/train_aqi.py`.
- Full-grid predictions: new module `src/models/export_predictions_grid.py` performs inference over the full grid and exports `data/processed/predicted_aqi_grids/predicted_pm25.nc` and `predictions_index.csv`.
- GIS exports: `src/visualization/export_geospatial_layers.py` converts flat DataFrames to NetCDF and can export coarse GeoJSON for dashboard use.

## Objective 2 — HCHO Hotspots
- TROPOMI HCHO ingestion: `src/data/build_dataset_hcho.py` (V3) produces `data/processed/hcho_fire_daily_grid.csv`.
- Hotspot detection: `src/features/make_features_hcho.py` exports `data/processed/hcho_hotspot_features.csv` including percentile flags and cluster labels.
- Fire integration: FIRMS counts are joined in `build_dataset_hcho.py` / `build_dataset_aqi.py` and visualised in the dashboard HCHO page.
- Transport analysis: dashboard includes wind quivers (u10, v10) over seasonal means; features pipeline computes lagged correlations for cluster summary.

## Dashboard
- Streamlit app `src/webapp/app.py` provides:
  - AQI Maps: continuous gridded map (from `grid_daily_features.csv`) and coarse GeoJSON choropleth (`data/processed/predicted_aqi_grids/predicted_pm25_coarse.geojson`).
  - HCHO Hotspots: seasonal hotspot maps, cluster tables, fire correlation plots and wind transport quiver overlays.
- The `scripts/run_pipeline.py export_for_dashboard` step now exports full-grid NetCDF + coarse GeoJSON when model checkpoint exists.

## Data products
- `data/processed/grid_daily_features.csv` — gridded daily features (satellite + met + fire_count)
- `data/processed/aqi_training_dataset.csv` — CPCB stations joined with gridded features (training table)
- `data/processed/predicted_aqi_grids/predicted_pm25.nc` — NetCDF timeseries of predicted PM2.5 on India grid
- `data/processed/predicted_aqi_grids/predicted_pm25_coarse.geojson` — coarse (0.25°) GeoJSON for dashboard
- `data/processed/hcho_fire_daily_grid.csv` — HCHO + fire counts gridded
- `data/processed/hcho_hotspot_features.csv` — hotspot flags, clusters, persistence

## Notes & Gaps
- The deep model inference currently assumes the model was trained with the same grid window size as `cnn_lstm` settings. For very large grids, inference may need tiling.
- GeoTIFF export is not implemented in V4 but can be added via `rasterio` quickly from the NetCDF.
- Transport analysis for individual hotspot clusters can be expanded (backtrajectory modelling) if required.
