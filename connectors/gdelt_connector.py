"""Isolated read-only connector for the GDELT DOC API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
TIMEOUT_SECONDS = 8
CACHE_PATH = Path(__file__).resolve().parents[1] / ".cache" / "gdelt_cache.json"
CACHE_TTL = timedelta(hours=6)


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
    cache_key = _build_cache_key(cleaned_query, limited_days, limited_max_records)
    cache = _read_cache()
    cached_articles = _get_cached_articles(cache, cache_key, require_fresh=True)
    if cached_articles is not None:
        return cached_articles

    query_params = urlencode(
        {
            "query": cleaned_query,
            "mode": "ArtList",
            "format": "json",
            "sort": "HybridRel",
            "maxrecords": limited_max_records,
            "timespan": f"{limited_days}d",
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
        stale_articles = _get_cached_articles(cache, cache_key, require_fresh=False)
        return stale_articles if stale_articles is not None else []

    articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(articles, list):
        stale_articles = _get_cached_articles(cache, cache_key, require_fresh=False)
        return stale_articles if stale_articles is not None else []

    normalized_articles = [
        _normalize_article(article)
        for article in articles
        if isinstance(article, dict)
    ]
    _write_cache_entry(cache, cache_key, normalized_articles)

    return normalized_articles


def _build_cache_key(query: str, days: int, max_records: int) -> str:
    return json.dumps(
        {
            "query": query,
            "days": days,
            "max_records": max_records,
        },
        sort_keys=True,
    )


def _read_cache() -> Dict:
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
            cache = json.load(cache_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return cache if isinstance(cache, dict) else {}


def _get_cached_articles(
    cache: Dict,
    cache_key: str,
    require_fresh: bool,
) -> List[Dict[str, str]] | None:
    entry = cache.get(cache_key)
    if not isinstance(entry, dict):
        return None

    articles = entry.get("articles")
    if not isinstance(articles, list):
        return None

    if require_fresh and _cache_entry_is_expired(entry):
        return None

    return [
        _normalize_article(article)
        for article in articles
        if isinstance(article, dict)
    ]


def _cache_entry_is_expired(entry: Dict) -> bool:
    cached_at = entry.get("cached_at")
    if not isinstance(cached_at, str):
        return True

    try:
        cached_datetime = datetime.fromisoformat(cached_at)
    except ValueError:
        return True

    if cached_datetime.tzinfo is None:
        cached_datetime = cached_datetime.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - cached_datetime > CACHE_TTL


def _write_cache_entry(
    cache: Dict,
    cache_key: str,
    articles: List[Dict[str, str]],
) -> None:
    cache[cache_key] = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }

    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_PATH.open("w", encoding="utf-8") as cache_file:
            json.dump(cache, cache_file, ensure_ascii=False, indent=2)
    except OSError:
        return


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
