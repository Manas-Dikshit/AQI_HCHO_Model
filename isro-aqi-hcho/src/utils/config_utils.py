"""
config_utils.py
===============
YAML config loading, validation, and default-value helpers.

Usage::

    from src.utils.config_utils import load_and_validate, get_nested, validate_date_range

    config = load_and_validate("config/aqi_training.yaml", REQUIRED_KEYS)
    lr = get_nested(config, "cnn_lstm", "training", "learning_rate", default=1e-3)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Core helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_nested(config: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely retrieve a nested value from a dict using dot-path keys.

    Parameters
    ----------
    config : dict
    *keys : str
        Sequence of keys, e.g. ``get_nested(cfg, "cnn_lstm", "training", "lr")``.
    default : Any
        Returned when any key is missing.

    Returns
    -------
    Any  The value at the key path, or *default*.
    """
    curr = config
    for key in keys:
        if not isinstance(curr, dict) or key not in curr:
            return default
        curr = curr[key]
    return curr


def set_nested(config: dict, *keys_and_value: Any) -> dict:
    """
    Set a nested value in a dict, creating intermediate dicts as needed.

    Parameters
    ----------
    config : dict
    *keys_and_value
        All arguments except the last are keys; the last is the value.

    Example
    -------
    >>> cfg = {}
    >>> set_nested(cfg, "a", "b", 42)
    {'a': {'b': 42}}
    """
    keys = keys_and_value[:-1]
    value = keys_and_value[-1]
    curr = config
    for key in keys[:-1]:
        curr = curr.setdefault(key, {})
    curr[keys[-1]] = value
    return config


def merge_defaults(config: dict, defaults: dict) -> dict:
    """
    Recursively fill in missing keys from *defaults* into *config*.

    Parameters
    ----------
    config : dict
        User-provided configuration (may be incomplete).
    defaults : dict
        Default values to fill in where missing.

    Returns
    -------
    dict  Merged config (copy — *config* is not mutated).
    """
    merged = defaults.copy()
    for key, val in config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = merge_defaults(val, merged[key])
        else:
            merged[key] = val
    return merged


# ──────────────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_config(
    config: dict,
    required_keys: dict[str, type | None] | None = None,
) -> None:
    """
    Validate that a config dict contains all required keys with correct types.

    Parameters
    ----------
    config : dict
    required_keys : dict[str, type | None]
        Mapping of ``"dot.separated.key" → expected_type``.
        Use ``None`` as the type to skip type-checking (only existence is verified).

    Raises
    ------
    ValueError
        If any required key is missing or has the wrong type.
    """
    if required_keys is None:
        return

    errors: list[str] = []
    for key_path, expected_type in required_keys.items():
        keys = key_path.split(".")
        val = get_nested(config, *keys)
        if val is None:
            errors.append(f"Missing required key: '{key_path}'")
        elif expected_type is not None and not isinstance(val, expected_type):
            errors.append(
                f"Key '{key_path}' has wrong type: "
                f"expected {expected_type.__name__}, got {type(val).__name__} ({val!r})"
            )

    if errors:
        raise ValueError(
            "Config validation failed:\n"
            + "\n".join(f"  ✗ {e}" for e in errors)
        )
    logger.debug("Config validation passed (%d required keys checked)", len(required_keys))


def validate_date_range(start: str, end: str, key_name: str = "date_range") -> None:
    """
    Validate that *start* ≤ *end* and both are parseable ISO-8601 date strings.

    Raises
    ------
    ValueError
    """
    import pandas as pd

    try:
        ts_start = pd.Timestamp(start)
        ts_end = pd.Timestamp(end)
    except Exception as exc:
        raise ValueError(f"[{key_name}] Could not parse dates '{start}' / '{end}': {exc}") from exc

    if ts_start > ts_end:
        raise ValueError(
            f"[{key_name}] start date '{start}' must be ≤ end date '{end}'."
        )


def validate_numeric_range(
    value: float | int,
    lo: float,
    hi: float,
    name: str = "value",
) -> None:
    """Raise ValueError if *value* is outside [*lo*, *hi*]."""
    if not (lo <= value <= hi):
        raise ValueError(f"'{name}' must be in [{lo}, {hi}]; got {value}.")


# ──────────────────────────────────────────────────────────────────────────────
# Load + validate
# ──────────────────────────────────────────────────────────────────────────────

def load_yaml(path: str | Path) -> dict:
    """
    Load a YAML file and return its contents as a dict.

    Raises
    ------
    FileNotFoundError
    yaml.YAMLError
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path.resolve()}")
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    logger.debug("Loaded config: %s (%d top-level keys)", path.name, len(data))
    return data


def load_and_validate(
    yaml_path: str | Path,
    required_keys: dict[str, type | None] | None = None,
    defaults: dict | None = None,
) -> dict:
    """
    Load a YAML config, optionally merge defaults, and validate required keys.

    Parameters
    ----------
    yaml_path : str | Path
    required_keys : dict[str, type | None] | None
        Passed to :func:`validate_config`.
    defaults : dict | None
        If provided, missing keys are filled from *defaults* before validation.

    Returns
    -------
    dict  The fully resolved config.

    Raises
    ------
    FileNotFoundError, ValueError
    """
    config = load_yaml(yaml_path)
    if defaults:
        config = merge_defaults(config, defaults)
    validate_config(config, required_keys)
    return config


def resolve_date(cli_val: str | None, config_key: str) -> str | None:
    """
    Resolve a date string preference order: CLI value, .env override, config/paths.yaml.

    Parameters
    ----------
    cli_val : str | None
        Explicit CLI-provided value (highest precedence).
    config_key : str
        Dot-separated key within `config/paths.yaml`, e.g. 'date_range.default_end'.

    Returns
    -------
    str | None
        Resolved ISO date string or None if not found.
    """
    from pathlib import Path

    # CLI override
    if cli_val:
        return cli_val

    # Locate project root (two levels up from this file: src/utils -> isro-aqi-hcho)
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"

    # Check .env for START_DATE / END_DATE / TRAIN_END / TEST_START overrides
    if env_path.exists():
        try:
            for line in env_path.read_text().splitlines():
                if not line or line.strip().startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if not v:
                    continue
                # If config_key mentions 'start' prefer START_DATE
                if "start" in config_key and k == "START_DATE":
                    return v
                if "end" in config_key and k == "END_DATE":
                    return v
                # Allow explicit overrides like TRAIN_END / TEST_START
                if k.replace("_", "").lower() in config_key.replace(".", "").lower():
                    return v
        except Exception:
            # Fall through to config file lookup
            pass

    # Fallback to config/paths.yaml
    try:
        cfg = load_yaml(project_root / "config" / "paths.yaml")
        val = get_nested(cfg, *config_key.split("."))
        if val:
            return val
    except Exception:
        pass

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Project-specific required-key schemas
# ──────────────────────────────────────────────────────────────────────────────

AQI_TRAINING_REQUIRED: dict[str, type | None] = {
    "features.satellite": list,
    "features.meteorological": list,
    "model.sequence_length": int,
    "cnn_lstm.architecture.lstm_hidden": int,
    "cnn_lstm.training.epochs": int,
    "cnn_lstm.training.learning_rate": float,
    "baseline.train_end": str,
    "baseline.test_start": str,
}

HCHO_HOTSPOT_REQUIRED: dict[str, type | None] = {
    "hotspot.percentile": (int, float),
    "hotspot.cluster_method": str,
}

PATHS_REQUIRED: dict[str, type | None] = {
    "data.root": str,
    "india_bbox.lon_min": (int, float),
    "india_bbox.lat_min": (int, float),
    "grid_resolution": (int, float),
}


if __name__ == "__main__":
    # Quick self-test
    import json

    sample = {
        "features": {
            "satellite": ["no2_column", "hcho_column"],
            "meteorological": ["t2m", "rh2m"],
        },
        "model": {"sequence_length": 7},
        "cnn_lstm": {
            "architecture": {"lstm_hidden": 128},
            "training": {"epochs": 50, "learning_rate": 0.001},
        },
        # Defaults left intentionally blank to encourage dynamic resolution
        "baseline": {"train_end": None, "test_start": None},
    }

    try:
        validate_config(sample, AQI_TRAINING_REQUIRED)
        print("✓ Validation passed")
    except ValueError as e:
        print(f"✗ Validation failed:\n{e}")

    # Test nested get/set
    val = get_nested(sample, "cnn_lstm", "training", "learning_rate", default=1e-4)
    print(f"get_nested learning_rate = {val}")

    # Test date validation with a dynamic recent range
    today = pd.Timestamp.today().normalize()
    validate_date_range((today - pd.Timedelta(days=365)).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
    print("✓ Date range valid (dynamic recent-year check)")
