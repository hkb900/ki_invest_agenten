"""Build a local HTML test report for the KI-Invest financial news agent."""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from connectors.ki_invest_connector import read_depot, read_top20
from connectors.gdelt_connector import fetch_gdelt_articles
from connectors.llm_review_connector import build_news_review
from connectors.news_connector import fetch_company_news


REPORT_PATH = REPO_ROOT / "reports" / "finanznews_test_report.html"
NO_TICKER_MESSAGE = "Kein Ticker vorhanden"
NO_NEWS_MESSAGE = "Keine aktuellen Nachrichten gefunden"
MAX_NEWS_HEADLINES = 3
MAX_NEWS_COMMENT_LENGTH = 300
MAX_GDELT_NEWS_COMMENT_LENGTH = 350
MAX_NEWS_SOURCES = 3

NAME_COLUMNS = ("name", "unternehmen", "titel", "wertpapier", "bezeichnung")
ISIN_COLUMNS = ("isin", "isin_code")
TICKER_COLUMNS = ("ticker", "symbol", "ticker_yahoo")
DEPOT_COLUMNS = ("depot", "depot_label", "quelle_depot", "depotname", "depot_name")
VALUE_COLUMNS = (
    "wert",
    "positionswert",
    "depotwert",
    "marktwert",
    "market_value",
    "betrag",
)
SCORE_COLUMNS = ("score", "gesamt_score", "scores_gesamt", "ki_score", "punkte")
DEPOT_LABELS = {
    "heribert_finet": "Hfi",
    "heribert_degiro": "Hde",
    "elena_degiro": "Ede",
}


def main() -> None:
    top20_rows = read_top20()
    depot_rows = read_depot()

    report_rows = build_report_rows(top20_rows, depot_rows)
    html_document = render_html(report_rows)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(html_document, encoding="utf-8")

    print(f"Finanznews-Testreport geschrieben: {REPORT_PATH}")
    print(f"Zeilen: {len(report_rows)}")


def build_report_rows(
    top20_rows: Iterable[Dict[str, str]],
    depot_rows: Iterable[Dict[str, str]],
) -> List[Dict[str, str]]:
    depot_by_isin = _index_by_isin(depot_rows)
    rows: List[Dict[str, str]] = []

    for top20_row in top20_rows:
        isin = _get_value(top20_row, ISIN_COLUMNS)
        depot_row = depot_by_isin.get(_normalize_isin(isin)) if isin else None

        name = _get_value(top20_row, NAME_COLUMNS)
        if not name and depot_row:
            name = _get_value(depot_row, NAME_COLUMNS)

        rows.append(
            {
                "name": name,
                "isin": isin,
                "depot": _get_depot_label(depot_row),
                "wert": _get_value(depot_row, VALUE_COLUMNS) if depot_row else "",
                "score": _get_value(top20_row, SCORE_COLUMNS),
                "nachrichten": _build_news_comment(top20_row, name),
            }
        )

    return rows


def render_html(rows: Iterable[Dict[str, str]]) -> str:
    table_rows = "\n".join(_render_table_row(row) for row in rows)

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Finanznews Testreport</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #1f2933;
      background: #f5f7fa;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px;
    }}
    h1 {{
      margin: 0 0 18px;
      font-size: 24px;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid #d9e2ec;
    }}
    th,
    td {{
      padding: 7px 8px;
      border-bottom: 1px solid #d9e2ec;
      text-align: left;
      vertical-align: top;
      font-size: 12px;
    }}
    th {{
      background: #eef2f6;
      font-weight: 700;
    }}
    .col-name {{
      width: 18%;
    }}
    .col-isin {{
      width: 9%;
    }}
    .col-depot {{
      width: 4ch;
    }}
    .col-wert {{
      width: 9%;
    }}
    .col-score {{
      width: 6%;
    }}
    .col-news {{
      width: auto;
    }}
    td:nth-child(3),
    th:nth-child(3),
    td:nth-child(4),
    th:nth-child(4),
    td:nth-child(5),
    th:nth-child(5) {{
      white-space: nowrap;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Finanznews Testreport</h1>
    <table>
      <colgroup>
        <col class="col-name">
        <col class="col-isin">
        <col class="col-depot">
        <col class="col-wert">
        <col class="col-score">
        <col class="col-news">
      </colgroup>
      <thead>
        <tr>
          <th>name</th>
          <th>isin</th>
          <th>depot</th>
          <th>wert</th>
          <th>score</th>
          <th>nachrichten</th>
        </tr>
      </thead>
      <tbody>
{table_rows}
      </tbody>
    </table>
  </main>
</body>
</html>
"""


def _render_table_row(row: Dict[str, str]) -> str:
    cells = "".join(
        f"<td>{html.escape(str(row.get(column, '')))}</td>"
        for column in ("name", "isin", "depot", "wert", "score", "nachrichten")
    )
    return f"        <tr>{cells}</tr>"


def _index_by_isin(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    indexed: Dict[str, Dict[str, str]] = {}

    for row in rows:
        isin = _normalize_isin(_get_value(row, ISIN_COLUMNS))
        if isin:
            indexed[isin] = row

    return indexed


def _get_depot_label(depot_row: Optional[Dict[str, str]]) -> str:
    if not depot_row:
        return "—"

    depot_label = _get_value(depot_row, DEPOT_COLUMNS)
    if not depot_label:
        return "im D"

    return DEPOT_LABELS.get(depot_label.lower(), depot_label[:4])


def _build_news_comment(top20_row: Dict[str, str], company_name: str) -> str:
    query = _build_gdelt_query(company_name, _get_value(top20_row, TICKER_COLUMNS))
    if not query:
        return _format_news_review(build_news_review(company_name, []))

    try:
        articles = fetch_gdelt_articles(query, days=7, max_records=10)
    except Exception:
        articles = []

    return _format_news_review(build_news_review(company_name, articles))


def _build_gdelt_query(company_name: str, ticker: str) -> str:
    query_parts = []
    if company_name.strip():
        query_parts.append(company_name.strip())
    if ticker.strip():
        query_parts.append(ticker.strip())

    return " ".join(query_parts)


def _format_news_review(review: Dict[str, object]) -> str:
    sentiment = str(review.get("sentiment", "neutral")).strip() or "neutral"
    comment = str(review.get("comment", "")).strip()
    sources = _limit_sources(str(review.get("sources", "")).strip())

    news_text = f"{sentiment}: {comment}"
    if sources:
        news_text = f"{news_text} | Quellen: {sources}"

    return _limit_text(news_text, MAX_GDELT_NEWS_COMMENT_LENGTH)


def _limit_sources(sources: str) -> str:
    if not sources:
        return ""

    source_parts = [
        source.strip()
        for source in sources.split(",")
        if source.strip()
    ]

    return ", ".join(source_parts[:MAX_NEWS_SOURCES])


def _build_finnhub_news_comment(top20_row: Dict[str, str]) -> str:
    ticker = _get_value(top20_row, TICKER_COLUMNS)
    if not ticker:
        return NO_TICKER_MESSAGE

    try:
        news_items = fetch_company_news(ticker)
    except Exception:
        return NO_NEWS_MESSAGE

    headlines = []
    for news_item in news_items:
        headline = _extract_headline(news_item)
        if headline:
            headlines.append(headline)
        if len(headlines) == MAX_NEWS_HEADLINES:
            break

    if not headlines:
        return NO_NEWS_MESSAGE

    return _limit_text(" | ".join(headlines), MAX_NEWS_COMMENT_LENGTH)


def _extract_headline(news_item: Dict) -> str:
    for key in ("headline", "title", "summary"):
        value = news_item.get(key)
        if value is not None and str(value).strip():
            return " ".join(str(value).split())

    return ""


def _limit_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value

    return value[: max_length - 3].rstrip() + "..."


def _get_value(row: Optional[Dict[str, str]], candidates: Iterable[str]) -> str:
    if not row:
        return ""

    normalized_row = {_normalize_column_name(key): value for key, value in row.items()}
    for candidate in candidates:
        value = normalized_row.get(_normalize_column_name(candidate))
        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


def _normalize_column_name(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _normalize_isin(value: str) -> str:
    return value.strip().upper().replace(" ", "")


if __name__ == "__main__":
    main()
