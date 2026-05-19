"""Build placeholder finanzen.net external metrics from a title CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import quote_plus, urljoin


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
INTERNAL_FETCH_ARG = "--_fetch-one-json"
BROWSER_FETCH_TIMEOUT_SECONDS = 20
GLOBAL_LIMIT5_TIMEOUT_SECONDS = 60
MAX_ERROR_LENGTH = 300


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == INTERNAL_FETCH_ARG:
        print(json.dumps(fetch_finanzen_metrics_in_browser(sys.argv[2]), ensure_ascii=False))
        return

    args = parse_args()
    rows = read_input_rows(args.input_csv)
    if args.limit is not None:
        rows = rows[: max(0, args.limit)]
    max_runtime_seconds = GLOBAL_LIMIT5_TIMEOUT_SECONDS if args.limit and args.limit >= 5 else None
    metrics_rows = build_metrics(rows, max_runtime_seconds=max_runtime_seconds)
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
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N input rows.",
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


def build_metrics(rows: Iterable[Dict[str, str]], max_runtime_seconds: int | None = None) -> List[Dict[str, str]]:
    rows = list(rows)
    metrics_rows = build_placeholder_metrics(rows)
    if not metrics_rows:
        return metrics_rows

    deadline = time.monotonic() + max_runtime_seconds if max_runtime_seconds else None
    metrics_rows[0].update(fetch_finanzen_metrics(rows[0], deadline=deadline))
    return metrics_rows


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


def fetch_finanzen_metrics(row: Dict[str, str]) -> Dict[str, str]:
    fetched_at = datetime.now().isoformat(timespec="seconds")
    search_term = clean_value(row.get("isin")) or clean_value(row.get("ticker")) or clean_value(row.get("name"))
    if not search_term:
        return {
            "abrufzeit": fetched_at,
            "fehler": "Kein Suchbegriff vorhanden",
        }

    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), INTERNAL_FETCH_ARG, search_term],
            check=False,
            capture_output=True,
            text=True,
            timeout=BROWSER_FETCH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "finanzen_url": build_search_url(search_term),
            "abrufzeit": fetched_at,
            "fehler": "finanzen.net-Abfrage Timeout",
        }

    if result.returncode != 0:
        error_text = clean_value(result.stderr) or f"Exit-Code {result.returncode}"
        return {
            "finanzen_url": build_search_url(search_term),
            "abrufzeit": fetched_at,
            "fehler": compact_error(f"finanzen.net-Abfrage fehlgeschlagen: {error_text}"),
        }

    try:
        fetched = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "finanzen_url": build_search_url(search_term),
            "abrufzeit": fetched_at,
            "fehler": "finanzen.net-Abfrage lieferte keine lesbare Antwort",
        }

    fetched["abrufzeit"] = fetched_at
    return fetched


def fetch_finanzen_metrics_in_browser(search_term: str) -> Dict[str, str]:
    from playwright.sync_api import sync_playwright

    search_url = build_search_url(search_term)
    browser = None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            detail_url = find_first_stock_link(page)
            if detail_url:
                page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
            finanzen_url = page.url
            page_text = page.locator("body").inner_text(timeout=10000)
            extracted = extract_metrics_from_page(page)
            browser.close()
    except Exception as exc:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        return {
            "finanzen_url": search_url,
            "fehler": compact_error(f"finanzen.net-Abfrage fehlgeschlagen: {type(exc).__name__}: {exc}"),
        }

    text_extracted = extract_metrics_from_text(page_text)
    for key, value in text_extracted.items():
        if not extracted.get(key):
            extracted[key] = value

    has_data = any(
        extracted.get(column)
        for column in ("finanzen_kurs", "finanzen_kgv", "finanzen_dividende")
    )
    extracted.update(
        {
            "finanzen_url": finanzen_url,
            "fehler": "" if has_data else "Keine finanzen.net-Kennzahlen extrahiert",
        }
    )
    return extracted


def build_search_url(search_term: str) -> str:
    return f"https://www.finanzen.net/suchergebnis.asp?_search={quote_plus(search_term)}"


def compact_error(value: str) -> str:
    text = " ".join(str(value).split())
    if len(text) <= MAX_ERROR_LENGTH:
        return text
    return text[: MAX_ERROR_LENGTH - 3].rstrip() + "..."


def find_first_stock_link(page) -> str:
    selectors = [
        'a[href*="/aktien/"]',
        'a[href*="/aktie/"]',
        'a[href*="_aktie"]',
        'a[href*="-aktie"]',
    ]
    for selector in selectors:
        try:
            links = page.locator(selector)
            count = min(links.count(), 20)
        except Exception:
            continue

        for index in range(count):
            try:
                href = links.nth(index).get_attribute("href")
            except Exception:
                continue
            if is_stock_detail_href(href):
                return urljoin(page.url, href)

    return ""


def is_stock_detail_href(href: object) -> bool:
    text = clean_value(href).lower()
    if not text:
        return False
    blocked_parts = (
        "javascript:",
        "#",
        "/suche/",
        "suchergebnis",
        "/nachrichten/",
        "/news/",
        "/index/",
        "/fonds/",
        "/etf/",
        "/zertifikate/",
    )
    if any(part in text for part in blocked_parts):
        return False
    return "/aktien/" in text or "/aktie/" in text or "_aktie" in text or "-aktie" in text


def extract_metrics_from_page(page) -> Dict[str, str]:
    return {
        "finanzen_kurs": first_locator_text(
            page,
            [
                '[data-testid*="price"]',
                '[class*="price"]',
                '[class*="Price"]',
                '.snapshot__value',
                '.quote__price',
            ],
        ),
        "finanzen_kgv": metric_near_label(page, ["KGV", "Kurs-Gewinn-Verhältnis"]),
        "finanzen_dividende": metric_near_label(page, ["Dividendenrendite", "Dividende"]),
    }


def first_locator_text(page, selectors: Iterable[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 5)
        except Exception:
            continue
        for index in range(count):
            try:
                text = clean_metric_text(locator.nth(index).inner_text(timeout=1000))
            except Exception:
                continue
            if text:
                return text
    return ""


def metric_near_label(page, labels: Iterable[str]) -> str:
    for label in labels:
        selectors = [
            f'text="{label}"',
            f'text=/{re.escape(label)}/i',
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first()
                if locator.count() == 0:
                    continue
                nearby_text = locator.locator("xpath=ancestor-or-self::*[self::tr or self::li or self::div][1]").inner_text(timeout=1000)
                value = value_after_label(nearby_text, label)
                if value:
                    return value
            except Exception:
                continue
    return ""


def value_after_label(text: str, label: str) -> str:
    normalized = " ".join(clean_value(text).split())
    if not normalized:
        return ""
    pattern = rf"{re.escape(label)}\s*[:\-]?\s*([0-9][0-9.,% ]*)"
    match = re.search(pattern, normalized, flags=re.IGNORECASE)
    if match:
        return clean_metric_text(match.group(1))

    parts = normalized.split()
    if len(parts) >= 2 and parts[0].lower().startswith(label.lower()[:3]):
        return clean_metric_text(parts[-1])
    return ""


def clean_metric_text(value: object) -> str:
    text = " ".join(clean_value(value).split())
    return text[:80]


def extract_metrics_from_text(page_text: str) -> Dict[str, str]:
    normalized_text = "\n".join(line.strip() for line in page_text.splitlines() if line.strip())
    return {
        "finanzen_kurs": first_match(
            normalized_text,
            [
                r"(?:Kurs|Aktueller Kurs|Letzter Kurs)\s*[:\n]\s*([0-9][0-9.,]*)",
                r"([0-9][0-9.,]*)\s*(?:EUR|USD|CHF|GBX)\b",
            ],
        ),
        "finanzen_kgv": first_match(
            normalized_text,
            [
                r"(?:KGV|Kurs-Gewinn-Verhältnis)\s*[:\n]\s*([0-9][0-9.,]*)",
            ],
        ),
        "finanzen_dividende": first_match(
            normalized_text,
            [
                r"(?:Dividende|Dividendenrendite)\s*[:\n]\s*([0-9][0-9.,% ]*)",
            ],
        ),
    }


def first_match(text: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_value(match.group(1))
    return ""


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
