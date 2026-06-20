"""
Validate presence and basic format of data download credentials and local fallbacks.

Usage:
    python scripts/validate_credentials.py

Checks:
 - .env keys: MOSDAC_USER, MOSDAC_PASS, FIRMS_MAP_KEY, GEE_PROJECT_ID
 - ~/.cdsapirc existence and `key: ...` line
 - Earth Engine config dir: ~/.config/earthengine (typical)
 - Local FIRMS CSVs in data/raw/firms/
 - CPCB raw directory exists

This script deliberately *does not* print secret values.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_env(env_path: Path) -> dict:
    if not env_path.exists():
        return {}
    out = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def check_cdsapirc() -> tuple[bool, str]:
    path = Path.home() / ".cdsapirc"
    if not path.exists():
        return False, f"Missing {path}"
    text = path.read_text()
    if "key:" not in text:
        return False, f"{path} found but no 'key:' line present"
    return True, f"Found {path}"


def check_earthengine() -> tuple[bool, str]:
    # Common EE credential directory
    ee_path = Path.home() / ".config" / "earthengine"
    if ee_path.exists() and any(ee_path.iterdir()):
        return True, f"Found {ee_path}"
    # Windows alternative
    alt = Path.home() / ".config" / "earthengine"
    if alt.exists() and any(alt.iterdir()):
        return True, f"Found {alt}"
    return False, f"No Earth Engine config under {ee_path}"


def check_local_firms(project_root: Path) -> tuple[bool, str]:
    p = project_root / "data" / "raw" / "firms"
    if not p.exists():
        return False, f"Directory not found: {p}"
    csvs = list(p.glob("*.csv"))
    if not csvs:
        return False, f"No CSV files in {p}"
    return True, f"Found {len(csvs)} FIRMS CSV(s) in {p}"


def check_cpcb(project_root: Path) -> tuple[bool, str]:
    p = project_root / "data" / "raw" / "cpcb"
    if not p.exists():
        return False, f"Directory not found: {p}"
    csvs = list(p.glob("*.csv"))
    if not csvs:
        return False, f"No CPCB CSVs in {p}"
    return True, f"Found {len(csvs)} CPCB CSV(s) in {p}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate credentials and local data fallbacks")
    parser.add_argument("--project_root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    project_root = Path(args.project_root)
    env_path = project_root / ".env"

    print("Checking .env →", env_path)
    env = read_env(env_path)

    checks_ok = True

    # MOSDAC
    mosdac_user = env.get("MOSDAC_USER")
    mosdac_pass = env.get("MOSDAC_PASS")
    if mosdac_user and mosdac_pass:
        print("[OK] MOSDAC credentials present (MOSDAC_USER set)")
    else:
        print("[MISSING] MOSDAC_USER / MOSDAC_PASS — required for INSAT-3D AOD downloads")
        checks_ok = False

    # FIRMS MAP_KEY or local CSVs
    firms_key = env.get("FIRMS_MAP_KEY")
    firms_ok = False
    if firms_key and firms_key.lower() not in ("", "your_firms_api_key", "none"):
        print("[OK] FIRMS_MAP_KEY appears set in .env")
        firms_ok = True
    else:
        ok, msg = check_local_firms(project_root)
        if ok:
            print(f"[OK] No FIRMS_MAP_KEY but local FIRMS CSVs found: {msg}")
            firms_ok = True
        else:
            print(f"[MISSING] FIRMS_MAP_KEY not set and no local FIRMS CSVs: {msg}")
            checks_ok = False

    # GEE
    gee_proj = env.get("GEE_PROJECT_ID")
    if gee_proj and gee_proj.lower() not in ("", "your_gcp_project_id", "none"):
        print("[OK] GEE_PROJECT_ID appears set in .env")
    else:
        ok, msg = check_earthengine()
        if ok:
            print(f"[OK] Earth Engine auth found: {msg}")
        else:
            print(f"[MISSING] Earth Engine not authenticated: {msg}")
            checks_ok = False

    # CDS API
    ok, msg = check_cdsapirc()
    if ok:
        print(f"[OK] CDS API credentials: {msg}")
    else:
        print(f"[MISSING] CDS API credentials: {msg}")
        checks_ok = False

    # CPCB CSVs
    ok, msg = check_cpcb(project_root)
    if ok:
        print(f"[OK] CPCB data: {msg}")
    else:
        print(f"[WARNING] CPCB data not present: {msg}")

    print("\nSummary:")
    if checks_ok:
        print("All required credentials / local fallbacks are present. You can run `scripts/run_pipeline.py download_all`.")
        return 0
    else:
        print("Some required credentials or local files are missing. See messages above to resolve.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
