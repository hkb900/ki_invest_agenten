"""Isolated read-only news connector layer."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FINNHUB_API_URL = "https://finnhub.io/api/v1/company-news"
TIMEOUT_SECONDS = 10


def fetch_company_news(ticker: str, days: int = 7) -> List[Dict]:
    """Fetch recent Finnhub company news for a ticker without storing data."""
    cleaned_ticker = ticker.strip()
    if not cleaned_ticker:
        return []

    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []

    limited_days = max(1, min(days, 30))
    to_date = date.today()
    from_date = to_date - timedelta(days=limited_days)

    query = urlencode(
        {
            "symbol": cleaned_ticker,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "token": api_key,
        }
    )
    request = Request(f"{FINNHUB_API_URL}?{query}", headers={"User-Agent": "ki-invest-agent"})

    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []

    if not isinstance(payload, list):
        return []

    return payload
