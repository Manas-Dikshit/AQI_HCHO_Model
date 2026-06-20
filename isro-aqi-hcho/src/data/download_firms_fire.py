"""
download_firms_fire.py
======================
Download MODIS/VIIRS active fire data from NASA FIRMS
(Fire Information for Resource Management System) over India.

Portal: https://firms.modaps.eosdis.nasa.gov/active_fire/

API: https://firms.modaps.eosdis.nasa.gov/api/area/

To obtain a MAP_KEY:
    1. Register at https://firms.modaps.eosdis.nasa.gov/api/
    2. Copy your MAP_KEY from the API page.

Usage:
    python -m src.data.download_firms_fire \\
        --map_key YOUR_MAP_KEY \\
        --start YYYY-MM-DD --end YYYY-MM-DD \\
        --output_dir data/raw/firms \\
        --output_csv data/processed/firms_fire_daily.csv
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Local helpers
try:
    from src.utils.config_utils import resolve_date
except Exception:
    # resolve_date is optional at import-time; will be resolved at runtime when PYTHONPATH is set
    resolve_date = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INDIA_BBOX = "68.0,8.0,97.5,37.5"   # west,south,east,north
GRID_RESOLUTION = 0.1

# FIRMS API endpoint
FIRMS_API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def download_firms_csv(
    map_key: str,
    source: str,
    start_date: str,
    n_days: int,
    output_dir: str | Path,
) -> Path:
    """
    Download a chunk of FIRMS data for *n_days* starting at *start_date*.

    The FIRMS API allows a maximum of 10 days per request.

    Parameters
    ----------
    map_key : str
        Your FIRMS API key.
    source : str
        Data source, e.g. "MODIS_NRT", "VIIRS_SNPP_NRT", "MODIS_SP".
    start_date : str
        ISO date string.
    n_days : int
        Number of days (max 10).
    output_dir : str | Path

    Returns
    -------
    Path to saved CSV file.
    """
    import requests

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"firms_{source}_{start_date}_{n_days}d.csv"

    if out_file.exists():
        logger.info("  Cached: %s", out_file.name)
        return out_file

    url = f"{FIRMS_API_BASE}/{map_key}/{source}/{INDIA_BBOX}/{n_days}/{start_date}"
    logger.info("  GET %s", url)

    resp = requests.get(url, timeout=60)
    if resp.status_code == 200:
        out_file.write_text(resp.text)
    elif resp.status_code == 401:
        raise ValueError("Invalid FIRMS MAP_KEY. Register at https://firms.modaps.eosdis.nasa.gov/api/")
    else:
        raise RuntimeError(f"FIRMS API returned {resp.status_code}: {resp.text[:200]}")

    return out_file


def download_firms_range(
    map_key: str,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    source: str = "MODIS_SP",
    chunk_days: int = 10,
) -> list[Path]:
    """
    Download FIRMS data in chunks of *chunk_days* days for a date range.

    Parameters
    ----------
    map_key : str
    start_date, end_date : str
    output_dir : str | Path
    source : str
        "MODIS_SP" (standard processing, 2000–present),
        "VIIRS_SNPP_SP" (2012–present), or NRT alternatives.
    chunk_days : int
        Days per request (max 10).

    Returns
    -------
    List of downloaded CSV paths.
    """
    dates = pd.date_range(start_date, end_date, freq=f"{chunk_days}D")
    files: list[Path] = []

    for d in dates:
        remaining = (pd.Timestamp(end_date) - d).days + 1
        n = min(chunk_days, remaining)
        if n <= 0:
            break
        try:
            fpath = download_firms_csv(map_key, source, d.strftime("%Y-%m-%d"), n, output_dir)
            files.append(fpath)
            time.sleep(0.5)
        except Exception as exc:
            logger.error("  Failed %s +%dd: %s", d.strftime("%Y-%m-%d"), n, exc)

    return files


def read_and_aggregate_firms(
    csv_files: list[Path],
    resolution: float = GRID_RESOLUTION,
) -> pd.DataFrame:
    """
    Read FIRMS CSV files, grid fire detections to *resolution* degrees,
    and compute daily fire counts per grid cell.

    Parameters
    ----------
    csv_files : list[Path]
    resolution : float

    Returns
    -------
    pd.DataFrame with columns: lat, lon, date, fire_count, cell_id.
    """
    dfs: list[pd.DataFrame] = []
    for fpath in csv_files:
        try:
            df = pd.read_csv(fpath, low_memory=False)
            dfs.append(df)
        except Exception as exc:
            logger.error("  Cannot read %s: %s", fpath.name, exc)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    # FIRMS columns: latitude, longitude, acq_date, confidence, etc.
    lat_col = next((c for c in combined.columns if "lat" in c.lower()), None)
    lon_col = next((c for c in combined.columns if "lon" in c.lower()), None)
    date_col = next((c for c in combined.columns if "date" in c.lower()), None)

    if not (lat_col and lon_col and date_col):
        raise ValueError(f"Cannot identify required columns. Found: {list(combined.columns)}")

    combined = combined.rename(columns={lat_col: "lat", lon_col: "lon", date_col: "date"})
    combined["date"] = pd.to_datetime(combined["date"])

    # Filter confidence (MODIS: nominal = 'nominal', high; VIIRS: ≥ 30%)
    if "confidence" in combined.columns:
        confidence_vals = combined["confidence"].astype(str)
        # Keep nominal and high for MODIS; numeric ≥ 30 for VIIRS
        keep = (confidence_vals.str.lower().isin(["nominal", "high"])) | \
               (pd.to_numeric(confidence_vals, errors="coerce").fillna(0) >= 30)
        combined = combined[keep]

    # Snap to grid
    from src.data.grid_definition import assign_cell_id
    combined = assign_cell_id(combined, resolution=resolution)

    gridded = (
        combined.groupby(["cell_id", "cell_lat", "cell_lon", "date"], as_index=False)
        .size()
        .rename(columns={"cell_lat": "lat", "cell_lon": "lon", "size": "fire_count"})
    )

    return gridded


def process_firms(
    map_key: str,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    output_csv: str | Path,
    source: str = "MODIS_SP",
) -> pd.DataFrame:
    """
    Full pipeline: download → aggregate → save.

    Parameters
    ----------
    map_key : str
    start_date, end_date : str
    output_dir : str | Path
    output_csv : str | Path
    source : str

    Returns
    -------
    pd.DataFrame
    """
    files = download_firms_range(map_key, start_date, end_date, output_dir, source)
    if not files:
        logger.warning("No FIRMS files downloaded.")
        return pd.DataFrame()

    df = read_and_aggregate_firms(files)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    logger.info("Saved %d rows to %s", len(df), output_csv)
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Download FIRMS fire data")
    parser.add_argument("--map_key", required=False, help="FIRMS MAP_KEY from NASA (optional). If omitted, the script will look for local FIRMS CSVs in --output_dir and aggregate them.")
    parser.add_argument("--start", default=None, help="Start date (ISO). If omitted, resolved from config/.env")
    parser.add_argument("--end", default=None, help="End date (ISO). If omitted, resolved from config/.env")
    parser.add_argument("--source", default="MODIS_SP")
    parser.add_argument("--output_dir", default="data/raw/firms")
    parser.add_argument("--output_csv", default="data/processed/firms_fire_daily.csv")
    args = parser.parse_args()

    # Resolve start/end using resolve_date() (CLI -> .env -> config)
    start = args.start
    end = args.end
    if resolve_date is not None:
        start = resolve_date(start, "date_range.default_start") or start
        end = resolve_date(end, "date_range.default_end") or end

    # Dynamic fallback: end -> today; start -> one year before end
    end_dt = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()
    start_dt = pd.Timestamp(start) if start else (end_dt - pd.Timedelta(days=365))
    start = start_dt.strftime("%Y-%m-%d")
    end = end_dt.strftime("%Y-%m-%d")

    if args.map_key:
        process_firms(args.map_key, start, end, args.output_dir, args.output_csv, args.source)
    else:
        # No API key provided: attempt to process local FIRMS CSV files in output_dir
        logger.info("No FIRMS MAP_KEY provided — attempting to process local CSVs in %s", args.output_dir)
        p = Path(args.output_dir)
        csv_files = sorted(p.glob("*.csv"))
        if not csv_files:
            logger.error(
                "No FIRMS CSV files found in %s. Please download FIRMS CSVs from https://firms.modaps.eosdis.nasa.gov/active_fire/ and place them there, or provide --map_key.",
                args.output_dir,
            )
            return
        df = read_and_aggregate_firms(csv_files)
        if df.empty:
            logger.warning("Local FIRMS CSVs yielded no data.")
            return
        # filter by requested date range
        df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
        Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output_csv, index=False)
        logger.info("Saved %d rows to %s", len(df), args.output_csv)


if __name__ == "__main__":
    main()
