"""Sense the news: pull items from free public RSS/Atom feeds.

No paid wire. `feedparser` is imported lazily so the rest of the package and the
test suite work without a network connection or the dependency installed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import mktime

from .config import Source
from .models import Article

log = logging.getLogger(__name__)


def _published_iso(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None) or entry.get(key) if hasattr(entry, "get") else None
        if val:
            try:
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc).isoformat()
            except (TypeError, ValueError, OverflowError):
                pass
    return datetime.now(timezone.utc).isoformat()


def _clean(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", text or "")          # strip HTML tags
    return re.sub(r"\s+", " ", text).strip()


def fetch_source(source: Source, limit: int = 25) -> list[Article]:
    """Fetch and normalize one feed into Articles. Errors are logged, not raised."""
    try:
        import feedparser
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "feedparser is required for ingestion. "
            "Install it with `pip install -r requirements.txt`."
        ) from exc

    try:
        parsed = feedparser.parse(source.url)
    except Exception as exc:  # noqa: BLE001 - never let one bad feed stop the desk
        log.warning("Failed to fetch %s: %s", source.name, exc)
        return []

    articles: list[Article] = []
    for entry in parsed.entries[:limit]:
        title = _clean(getattr(entry, "title", ""))
        if not title:
            continue
        summary = _clean(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        link = getattr(entry, "link", "")
        articles.append(
            Article.create(
                source=source.name,
                source_tier=source.trust_tier,
                audience_weight=source.audience_weight,
                title=title,
                summary=summary,
                link=link,
                published=_published_iso(entry),
                language=source.language,
                topics=source.topics,
            )
        )
    log.info("Fetched %d items from %s", len(articles), source.name)
    return articles


def fetch_all(sources: list[Source], limit_per_source: int = 25) -> list[Article]:
    out: list[Article] = []
    for src in sources:
        out.extend(fetch_source(src, limit=limit_per_source))
    return out
