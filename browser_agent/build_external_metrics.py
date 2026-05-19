"""Build placeholder finanzen.net external metrics from a title CSV."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = Path.home() / "ki_invest_next" / "output" / "candidates_top60.csv"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "external_metrics.csv"
REQUIRED_INPUT_COLUMNS = ("isin", "ticker", "name")
OUTPUT_COLUMNS = (
    "isin",
    "ticker",
    "name",
    "quelle",
    "finanzen_url",
    "finanzen_kurs",
    "finanzen_kgv",
    "finanzen_dividende",
    "finanzen_analystensignal",
    "finanzen_news_signal",
    "abrufzeit",
    "fehler",
)


def main() -> None:
    args = parse_args()
    rows = read_input_rows(args.input_csv)
    metrics_rows = build_placeholder_metrics(rows)
    write_metrics(metrics_rows, args.output_csv)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build placeholder finanzen.net external metrics CSV rows."
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input CSV with at least isin, ticker and name columns. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def read_input_rows(input_csv: Path) -> List[Dict[str, str]]:
    input_csv = input_csv.expanduser()
    with input_csv.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"Eingabe-CSV hat keine Kopfzeile: {input_csv}")

        missing_columns = [
            column
            for column in REQUIRED_INPUT_COLUMNS
            if column not in reader.fieldnames
        ]
        if missing_columns:
            raise ValueError(
                f"Eingabe-CSV fehlt Spalte(n): {', '.join(missing_columns)}"
            )

        return list(reader)


def build_placeholder_metrics(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    fetched_at = datetime.now().isoformat(timespec="seconds")
    return [
        {
            "isin": clean_value(row.get("isin")),
            "ticker": clean_value(row.get("ticker")),
            "name": clean_value(row.get("name")),
            "quelle": "finanzen.net",
            "finanzen_url": "",
            "finanzen_kurs": "",
            "finanzen_kgv": "",
            "finanzen_dividende": "",
            "finanzen_analystensignal": "",
            "finanzen_news_signal": "",
            "abrufzeit": fetched_at,
            "fehler": "Noch keine echte finanzen.net-Abfrage",
        }
        for row in rows
    ]


def write_metrics(rows: Iterable[Dict[str, str]], output_csv: Path) -> None:
    output_csv = output_csv.expanduser()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def clean_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


if __name__ == "__main__":
    main()
