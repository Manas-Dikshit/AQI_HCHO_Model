#!/usr/bin/env python3
"""
run_pipeline.py
===============
Top-level CLI orchestrator for the ISRO AQI & HCHO pipeline.

Provides single-command access to every pipeline stage:

    python scripts/run_pipeline.py download_all  --start YYYY-MM-DD --end YYYY-MM-DD
    python scripts/run_pipeline.py build_datasets --synthetic
    python scripts/run_pipeline.py train_baseline
    python scripts/run_pipeline.py train_deep --synthetic
    python scripts/run_pipeline.py export_for_dashboard
    python scripts/run_pipeline.py run_all --synthetic   # full demo pipeline

Run with --help on any subcommand for available options:

    python scripts/run_pipeline.py train_baseline --help

Must be run from the isro-aqi-hcho project root:

    cd isro-aqi-hcho
    python scripts/run_pipeline.py <command> [options]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Ensure project root is on Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logging_utils import get_logger, setup_logging

logger = get_logger("run_pipeline")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _run(cmd: list[str], desc: str = "") -> int:
    """
    Run a subprocess command and stream its output.

    Returns
    -------
    int  Return code (0 = success).
    """
    label = desc or " ".join(cmd)
    logger.info("▶ %s", label)
    t0 = time.time()
    result = subprocess.run(cmd, check=False, cwd=PROJECT_ROOT)
    elapsed = time.time() - t0
    rc = result.returncode
    if rc == 0:
        logger.info("  ✓ Done (%.1fs)", elapsed)
    else:
        logger.error("  ✗ Failed (rc=%d, %.1fs): %s", rc, elapsed, label)
    return rc


def _python(module_or_script: str, *args: str) -> list[str]:
    """Build a `python -m module ...` or `python script.py ...` command."""
    # Filter out None arguments (some CLI flags may be optional)
    cleaned = [str(a) for a in args if a is not None]
    if module_or_script.endswith(".py"):
        return [sys.executable, module_or_script] + cleaned
    return [sys.executable, "-m", module_or_script] + cleaned


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline stage functions
# ──────────────────────────────────────────────────────────────────────────────

def cmd_download_all(args: argparse.Namespace) -> int:
    """Orchestrate all data downloads."""
    logger.info("=== Stage: Download All Data ===")
    start, end = args.start, args.end
    rc_total = 0

    steps = [
        (_python("src.data.download_cpcb",
                 "--start_date", start, "--end_date", end,
                 "--output_dir", "data/raw/cpcb"),
         "Download CPCB ground-station data"),

        (_python("src.data.download_tropomi",
                 "--start_date", start, "--end_date", end,
                 "--output_dir", "data/raw/tropomi"),
         "Download TROPOMI satellite columns"),

        (_python("src.data.download_insat_aod",
                 "--start_date", start, "--end_date", end,
                 "--output_dir", "data/raw/insat_aod"),
         "Download INSAT-3D AOD"),

        (_python("src.data.download_reanalysis",
                 "--start_date", start, "--end_date", end,
                 "--output_dir", "data/raw/reanalysis"),
         "Download ERA5 reanalysis"),

        (_python("src.data.download_firms_fire",
                 "--start_date", start, "--end_date", end,
                 "--output_dir", "data/raw/firms"),
         "Download FIRMS fire data"),
    ]

    if args.static:
        steps.append((
            _python("src.data.download_static_layers",
                    "--layers", "land_cover", "population"),
            "Download static layers (land cover, population)",
        ))

    for cmd, desc in steps:
        rc = _run(cmd, desc)
        if rc != 0 and not args.skip_errors:
            logger.error("Download step failed; stopping. Use --skip_errors to continue.")
            return rc
        rc_total += rc

    return 0 if rc_total == 0 else 1


def cmd_build_datasets(args: argparse.Namespace) -> int:
    """Build AQI and HCHO training datasets."""
    logger.info("=== Stage: Build Datasets ===")
    rc_total = 0

    synthetic_flag = ["--synthetic"] if args.synthetic else []

    # AQI dataset
    rc = _run(
        _python("src.data.build_dataset_aqi", *synthetic_flag),
        "Build AQI training dataset",
    )
    rc_total += rc
    if rc != 0 and not args.skip_errors:
        return rc

    # HCHO dataset
    rc = _run(
        _python("src.data.build_dataset_hcho", *synthetic_flag),
        "Build HCHO hotspot dataset",
    )
    rc_total += rc

    return 0 if rc_total == 0 else 1


def cmd_train_baseline(args: argparse.Namespace) -> int:
    """Train Random Forest and Gradient Boosting baseline models."""
    logger.info("=== Stage: Train Baseline Models ===")

    extra: list[str] = []
    if args.hparam_search:
        extra.append("--hparam_search")
    if args.igp_only:
        extra.append("--igp_only")
    # Build argument list, only include optional flags when values are present
    tb_args: list[str] = ["--input", args.input, "--output_dir", args.output_dir]
    if getattr(args, "train_end", None):
        tb_args += ["--train_end", args.train_end]
    if getattr(args, "test_start", None):
        tb_args += ["--test_start", args.test_start]
    tb_args += extra

    rc = _run(
        _python("src.models.baseline_ml", *tb_args),
        "Train baseline models (RF + GBM)",
    )
    return rc


def cmd_train_deep(args: argparse.Namespace) -> int:
    """Train the CNN-LSTM / ConvLSTM deep model."""
    logger.info("=== Stage: Train Deep Model ===")

    extra: list[str] = []
    if args.synthetic:
        extra.append("--synthetic")
    if args.hparam_sweep:
        extra.append("--hparam_sweep")

    rc = _run(
        _python("src.models.train_aqi",
                "--config", args.config,
                "--output_dir", args.output_dir,
                *extra),
        "Train CNN-LSTM model",
    )
    return rc


def cmd_export_for_dashboard(args: argparse.Namespace) -> int:
    """Run feature engineering pipelines to prepare dashboard-ready files."""
    logger.info("=== Stage: Export for Dashboard ===")
    rc_total = 0

    # AQI features
    rc = _run(
        _python("src.features.make_features_aqi",
                "--input",  "data/processed/aqi_training_dataset.csv",
                "--output", "data/processed/aqi_features.csv"),
        "AQI feature engineering",
    )
    rc_total += rc

    # HCHO features
    rc = _run(
        _python("src.features.make_features_hcho",
                "--input",  "data/processed/hcho_fire_daily_grid.csv",
                "--output", "data/processed/hcho_hotspot_features.csv",
                "--config", "config/hcho_hotspot.yaml"),
        "HCHO hotspot feature engineering",
    )
    rc_total += rc

    # Export full-grid model predictions for dashboard (if model checkpoint exists)
    try:
        from src.models.export_predictions_grid import predict_on_grid_and_export
        model_ckpt = "models/cnn_lstm/best_model_default.pt"
        if Path(model_ckpt).exists():
            logger.info("Exporting full-grid predictions for dashboard …")
            predict_on_grid_and_export(
                model_ckpt,
                "data/processed/grid_daily_features.csv",
                "data/processed/predicted_aqi_grids",
                export_geotiff=getattr(args, "export_geotiff", False),
            )
        else:
            logger.info("No deep-model checkpoint found at %s — skipping full-grid export.", model_ckpt)
    except Exception as exc:  # pragma: no cover - best-effort export
        logger.warning("Full-grid export failed: %s", exc)

    if rc_total == 0:
        logger.info("Dashboard files ready. Launch with:")
        logger.info("  streamlit run src/webapp/app.py")

    return 0 if rc_total == 0 else 1


def cmd_run_all(args: argparse.Namespace) -> int:
    """Run the complete pipeline end-to-end (demo or real data)."""
    logger.info("=== Full Pipeline ===")
    stages: list[tuple[str, argparse.Namespace]] = []

    if not args.synthetic:
        stages.append(("download_all", args))

    stages += [
        ("build_datasets", args),
        ("train_baseline", args),
        ("train_deep", args),
        ("export_for_dashboard", args),
    ]

    dispatch = {
        "download_all": cmd_download_all,
        "build_datasets": cmd_build_datasets,
        "train_baseline": cmd_train_baseline,
        "train_deep": cmd_train_deep,
        "export_for_dashboard": cmd_export_for_dashboard,
    }

    t0 = time.time()
    for stage_name, stage_args in stages:
        rc = dispatch[stage_name](stage_args)
        if rc != 0 and not args.skip_errors:
            logger.error("Pipeline aborted at stage '%s'.", stage_name)
            return rc

    logger.info("Full pipeline completed in %.1f min", (time.time() - t0) / 60)
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_pipeline.py",
        description=(
            "ISRO AQI & HCHO Pipeline Orchestrator\n\n"
            "Run from the isro-aqi-hcho directory:\n"
            "  cd isro-aqi-hcho && python scripts/run_pipeline.py <command>"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--log_file", default="logs/pipeline.log",
                        help="Path to log file (default: logs/pipeline.log)")
    parser.add_argument("--skip_errors", action="store_true",
                        help="Continue even if a stage fails (not recommended)")

    sub = parser.add_subparsers(dest="command", required=True)

    # ── download_all ─────────────────────────────────────────────────────────
    p_dl = sub.add_parser("download_all", help="Download all raw data sources")
    # Default start/end fall back to .env or config/paths.yaml when present
    p_dl.add_argument("--start", default=None, help="Start date (YYYY-MM-DD). If omitted, taken from .env START_DATE or config/paths.yaml")
    p_dl.add_argument("--end", default=None, help="End date (YYYY-MM-DD). If omitted, taken from .env END_DATE or config/paths.yaml")
    p_dl.add_argument("--static", action="store_true",
                      help="Also download static layers (land cover, population)")

    # ── build_datasets ───────────────────────────────────────────────────────
    p_bd = sub.add_parser("build_datasets", help="Build AQI and HCHO training datasets")
    p_bd.add_argument("--synthetic", action="store_true",
                      help="Generate synthetic data (no API keys required)")

    # ── train_baseline ───────────────────────────────────────────────────────
    p_tb = sub.add_parser("train_baseline", help="Train RF + GBM baseline models")
    p_tb.add_argument("--input", default="data/processed/aqi_training_dataset.csv")
    p_tb.add_argument("--output_dir", default="models/baseline")
    p_tb.add_argument("--train_end", default=None,
                        help="Train end date (YYYY-MM-DD). If omitted, uses config/paths.yaml or .env")
    p_tb.add_argument("--test_start", default=None,
                        help="Test start date (YYYY-MM-DD). If omitted, uses config/paths.yaml or .env")
    p_tb.add_argument("--hparam_search", action="store_true")
    p_tb.add_argument("--igp_only", action="store_true",
                      help="Restrict training to the Indo-Gangetic Plain")

    # ── train_deep ───────────────────────────────────────────────────────────
    p_td = sub.add_parser("train_deep", help="Train CNN-LSTM / ConvLSTM deep model")
    p_td.add_argument("--config", default="config/aqi_training.yaml")
    p_td.add_argument("--output_dir", default="models/cnn_lstm")
    p_td.add_argument("--synthetic", action="store_true")
    p_td.add_argument("--hparam_sweep", action="store_true")

    # ── export_for_dashboard ─────────────────────────────────────────────────
    p_exp = sub.add_parser("export_for_dashboard",
                   help="Run feature engineering to prepare Streamlit-ready files")
    p_exp.add_argument("--export-geotiff", action="store_true",
                       help="Also write per-day GeoTIFFs from NetCDF exports")

    # ── run_all ──────────────────────────────────────────────────────────────
    p_all = sub.add_parser("run_all", help="Run the full pipeline end-to-end")
    p_all.add_argument("--start", default=None, help="Start date (YYYY-MM-DD). If omitted, taken from .env START_DATE or config/paths.yaml")
    p_all.add_argument("--end", default=None, help="End date (YYYY-MM-DD). If omitted, taken from .env END_DATE or config/paths.yaml")
    p_all.add_argument("--synthetic", action="store_true",
                       help="Skip downloads; use synthetic data throughout")
    p_all.add_argument("--config", default="config/aqi_training.yaml")
    p_all.add_argument("--input", default="data/processed/aqi_training_dataset.csv")
    p_all.add_argument("--output_dir", default="models/baseline")
    p_all.add_argument("--train_end", default=None,
                        help="Train end date (YYYY-MM-DD). If omitted, uses config/paths.yaml or .env")
    p_all.add_argument("--test_start", default=None,
                        help="Test start date (YYYY-MM-DD). If omitted, uses config/paths.yaml or .env")
    p_all.add_argument("--hparam_search", action="store_true")
    p_all.add_argument("--igp_only", action="store_true")
    p_all.add_argument("--hparam_sweep", action="store_true")
    p_all.add_argument("--static", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Resolve start/end defaults from .env, then config/paths.yaml
    from pathlib import Path
    env_path = PROJECT_ROOT / ".env"
    def _resolve_date(val_name: str, cli_val: str | None) -> str | None:
        # CLI value takes precedence
        if cli_val:
            return cli_val
        # .env
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith(f"{val_name}="):
                    return line.split("=", 1)[1].strip()
        # config/paths.yaml fallback
        try:
            from src.utils.config_utils import load_yaml
            cfg = load_yaml(PROJECT_ROOT / "config" / "paths.yaml")
            dr = cfg.get("date_range", {})
            if cli_val is None and val_name == "START_DATE":
                return dr.get("default_start")
            if cli_val is None and val_name == "END_DATE":
                return dr.get("default_end")
        except Exception:
            return None
        return None

    # Only set these attributes if they exist on the args object
    if hasattr(args, "start"):
        args.start = _resolve_date("START_DATE", getattr(args, "start"))
    if hasattr(args, "end"):
        args.end = _resolve_date("END_DATE", getattr(args, "end"))

    setup_logging(log_file=args.log_file)
    logger.info("ISRO AQI & HCHO Pipeline  |  command: %s", args.command)

    dispatch = {
        "download_all": cmd_download_all,
        "build_datasets": cmd_build_datasets,
        "train_baseline": cmd_train_baseline,
        "train_deep": cmd_train_deep,
        "export_for_dashboard": cmd_export_for_dashboard,
        "run_all": cmd_run_all,
    }

    fn = dispatch.get(args.command)
    if fn is None:
        parser.print_help()
        sys.exit(1)

    rc = fn(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
