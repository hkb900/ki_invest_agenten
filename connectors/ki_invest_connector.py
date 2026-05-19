"""Read-only connector for the external KI-Invest core project."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


KI_INVEST_ROOT = Path("/home/burgeragent/ki_invest_next")

SCORES_RELATIVE_PATH = Path("output/scores_gesamt.csv")
TOP20_RELATIVE_PATH = Path("output/scores_top20.csv")
DEPOT_RELATIVE_PATH = Path("input/depot_gesamt.csv")


def get_scores_path() -> Path:
    """Return the external scores CSV path."""
    return KI_INVEST_ROOT / SCORES_RELATIVE_PATH


def get_top20_path() -> Path:
    """Return the external top-20 scores CSV path."""
    return KI_INVEST_ROOT / TOP20_RELATIVE_PATH


def get_depot_path() -> Path:
    """Return the external depot CSV path."""
    return KI_INVEST_ROOT / DEPOT_RELATIVE_PATH


def read_scores() -> List[Dict[str, str]]:
    """Read the external scores CSV."""
    return _read_csv(get_scores_path(), "scores")


def read_top20() -> List[Dict[str, str]]:
    """Read the external top-20 scores CSV."""
    return _read_csv(get_top20_path(), "top20")


def read_depot() -> List[Dict[str, str]]:
    """Read the external depot CSV."""
    return _read_csv(get_depot_path(), "depot")


def _read_csv(path: Path, label: str) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"KI-Invest {label} CSV not found: {path}. "
            "The connector is read-only and expects the external core project "
            "to provide this file."
        )

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))
