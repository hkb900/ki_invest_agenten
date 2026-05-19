"""Isolated read-only connector for the GDELT DOC API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
TIMEOUT_SECONDS = 10


def fetch_gdelt_articles(
    query: str,
    days: int = 7,
    max_records: int = 10,
) -> List[Dict[str, str]]:
    """Fetch recent GDELT articles for a query without storing data."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    limited_days = max(1, min(days, 30))
    limited_max_records = max(1, min(max_records, 50))
    end_datetime = datetime.now(timezone.utc)
    start_datetime = end_datetime - timedelta(days=limited_days)

    query_params = urlencode(
        {
            "query": cleaned_query,
            "mode": "ArtList",
            "format": "json",
            "sort": "HybridRel",
            "maxrecords": limited_max_records,
            "startdatetime": _format_gdelt_datetime(start_datetime),
            "enddatetime": _format_gdelt_datetime(end_datetime),
        }
    )
    request = Request(
        f"{GDELT_DOC_API_URL}?{query_params}",
        headers={"User-Agent": "ki-invest-agent"},
    )

    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []

    articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(articles, list):
        return []

    return [_normalize_article(article) for article in articles if isinstance(article, dict)]


def _format_gdelt_datetime(value: datetime) -> str:
    return value.strftime("%Y%m%d%H%M%S")


def _normalize_article(article: Dict) -> Dict[str, str]:
    return {
        "title": _clean_value(article.get("title")),
        "url": _clean_value(article.get("url")),
        "domain": _clean_value(article.get("domain")),
        "seendate": _clean_value(article.get("seendate")),
        "sourcecountry": _clean_value(article.get("sourcecountry")),
        "language": _clean_value(article.get("language")),
    }


def _clean_value(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()
