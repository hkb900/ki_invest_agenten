"""Rule-based placeholder for future LLM news reviews."""

from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse


POSITIVE_KEYWORDS = (
    "growth",
    "profit",
    "upgrade",
    "partnership",
    "approval",
    "beat",
    "strong",
    "expansion",
)
NEGATIVE_KEYWORDS = (
    "lawsuit",
    "loss",
    "downgrade",
    "investigation",
    "warning",
    "decline",
    "weak",
    "recall",
)
MAX_ARTICLES = 3
MAX_COMMENT_LENGTH = 300
NO_ARTICLES_COMMENT = "Keine belastbaren aktuellen Nachrichten gefunden."


def build_news_review(company_name: str, articles: List[Dict]) -> Dict[str, object]:
    """Build a rule-based placeholder review for company news articles."""
    selected_articles = articles[:MAX_ARTICLES]
    if not selected_articles:
        return {
            "sentiment": "neutral",
            "comment": NO_ARTICLES_COMMENT,
            "article_count": 0,
            "sources": "",
        }

    positive_count = 0
    negative_count = 0
    for article in selected_articles:
        article_text = _article_text(article).lower()
        positive_count += _count_keyword_hits(article_text, POSITIVE_KEYWORDS)
        negative_count += _count_keyword_hits(article_text, NEGATIVE_KEYWORDS)

    sentiment = _determine_sentiment(positive_count, negative_count)
    comment = _build_comment(
        company_name=company_name,
        article_count=len(selected_articles),
        sentiment=sentiment,
        positive_count=positive_count,
        negative_count=negative_count,
    )

    return {
        "sentiment": sentiment,
        "comment": _limit_text(comment, MAX_COMMENT_LENGTH),
        "article_count": len(selected_articles),
        "sources": _build_sources(selected_articles),
    }


def _article_text(article: Dict) -> str:
    parts = []
    for key in ("title", "headline", "summary", "domain"):
        value = article.get(key)
        if value is not None and str(value).strip():
            parts.append(str(value))

    return " ".join(parts)


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _determine_sentiment(positive_count: int, negative_count: int) -> str:
    if positive_count > negative_count:
        return "positiv"
    if negative_count > positive_count:
        return "negativ"

    return "neutral"


def _build_comment(
    company_name: str,
    article_count: int,
    sentiment: str,
    positive_count: int,
    negative_count: int,
) -> str:
    cleaned_company_name = company_name.strip() or "das Unternehmen"
    base = f"Regelbasiert: {article_count} Artikel zu {cleaned_company_name} ausgewertet."

    if sentiment == "positiv":
        return (
            f"{base} Positive Signalwörter überwiegen "
            f"({positive_count} positiv, {negative_count} negativ)."
        )
    if sentiment == "negativ":
        return (
            f"{base} Negative Signalwörter überwiegen "
            f"({negative_count} negativ, {positive_count} positiv)."
        )

    return (
        f"{base} Keine klare Richtung aus den geprüften Signalwörtern "
        f"({positive_count} positiv, {negative_count} negativ)."
    )


def _build_sources(articles: List[Dict]) -> str:
    sources = []
    for article in articles:
        source = _extract_domain(article)
        if source and source not in sources:
            sources.append(source)

    return ", ".join(sources)


def _extract_domain(article: Dict) -> str:
    domain = article.get("domain")
    if domain is not None and str(domain).strip():
        return str(domain).strip()

    url = article.get("url")
    if url is None or not str(url).strip():
        return ""

    return urlparse(str(url)).netloc.strip()


def _limit_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value

    return value[: max_length - 3].rstrip() + "..."
