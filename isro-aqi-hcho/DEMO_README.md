# Demo README — ISRO AQI & HCHO (Demo + how to switch to real data)

This file documents running the repository in demo mode (no API keys required) and the exact steps to follow when you obtain real credentials.

## Quick demo (no keys)

From the project root:

```powershell
# Generate demo datasets, train baseline and run a small deep-model smoke test
python scripts/run_pipeline.py run_all --synthetic

# Or run stages individually
python scripts/run_pipeline.py build_datasets --synthetic
python scripts/run_pipeline.py train_baseline
python scripts/run_pipeline.py train_deep --synthetic
python scripts/run_pipeline.py export_for_dashboard
```

Outputs (demo):
- `data/processed/aqi_training_dataset.csv`
- `data/processed/grid_daily_features.csv`
- `data/processed/hcho_fire_daily_grid.csv`
- `models/baseline/*` (trained baseline models & metrics)
- `models/cnn_lstm/smoke_test_model.pt` (small smoke-test checkpoint)

Launch the Streamlit dashboard (reads processed files; generates synthetic data if none present):

```powershell
streamlit run src/webapp/app.py
```

---

## What to do when you have real data / keys

Required credentials for full downloads:

- **Copernicus CDS (ERA5):** add a `~/.cdsapirc` file containing `url:` and `key: <UID>:<API_KEY>` as described in `data/README.md`.
- **Google Earth Engine (TROPOMI via GEE):** run `earthengine authenticate` (one-time) and set `GEE_PROJECT_ID` in `.env` or pass `--gee_project`.
- **MOSDAC (INSAT-3D AOD):** set `MOSDAC_USER` / `MOSDAC_PASS` in `.env` or download INSAT files manually into `data/raw/insat_aod/`.
- **NASA FIRMS (MODIS/VIIRS fires):** either set `FIRMS_MAP_KEY` in `.env`/pass `--map_key`, or place pre-downloaded FIRMS CSVs into `data/raw/firms/` (the pipeline now supports local CSV aggregation if a MAP_KEY is not provided).
- **CPCB station CSVs:** drop CPCB CSV exports into `data/raw/cpcb/`.

Steps to run full downloads (once keys are configured):

```powershell
# Ensure .env exists and ~/.cdsapirc present
python scripts/validate_credentials.py

# Download everything (requires valid keys and network)
python scripts/run_pipeline.py download_all --start YYYY-MM-DD --end YYYY-MM-DD

# Build datasets from downloaded files
python scripts/run_pipeline.py build_datasets

# Train models on the full dataset
python scripts/run_pipeline.py train_baseline
python scripts/run_pipeline.py train_deep --config config/aqi_training.yaml
```

Notes:
- If you cannot provide `FIRMS_MAP_KEY`, the pipeline will aggregate any CSVs found in `data/raw/firms/`.
- For ERA5, ensure `~/.cdsapirc` exists with correct credentials; `cdsapi` must be installed.
- For TROPOMI downloads via GEE, ensure `earthengine authenticate` has been run on this machine and the GCP project is set.

---

## Next steps I can do for you

- Sweep the repo and remove remaining hardcoded years (I can do this and open PR-style patches).
- Add CI checks and small unit tests for data loaders and config utilities.
- Help run the full downloads and retrain models once you provide access to keys on this machine.

If you want me to proceed with any of the above, tell me which step to run next.