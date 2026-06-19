"""Shared fixtures / helpers for the test suite."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the package importable when running `pytest` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pagalscientist.models import Article  # noqa: E402


def make_article(title, summary="", *, source="Src", tier=2, weight=0.7,
                 link=None, hours_old=1.0, language="en"):
    published = datetime.now(timezone.utc).timestamp() - hours_old * 3600
    iso = datetime.fromtimestamp(published, tz=timezone.utc).isoformat()
    return Article.create(
        source=source, source_tier=tier, audience_weight=weight,
        title=title, summary=summary,
        link=link or f"https://example.com/{abs(hash(title)) % 100000}",
        published=iso, language=language,
    )
