"""Verification: score how trustworthy a clustered story is before we draft it.

This is a screening layer, not a truth oracle. It combines transparent signals
into a 0-100 score and a recommendation. A human still approves every story
before it publishes — verification just routes editor attention.

Signals:
  * source trust tier (official/paper-of-record vs aggregator)
  * corroboration (how many distinct sources report it)
  * recency (fresher is better, with a configurable half-life)
  * sensational-language flags (clickbait / unverified-claim markers)

Standard library only.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from .models import Article, Cluster, CredibilityReport

# Phrases that suggest hype or unverified virality rather than reported fact.
_SENSATIONAL = [
    r"\bshocking\b", r"\byou won'?t believe\b", r"\bgone viral\b", r"\bmiracle\b",
    r"\bsecret\b", r"\b100% (?:proven|guaranteed)\b", r"\bbreaking\b!{2,}",
    r"\bexposed\b", r"\bdestroyed\b", r"\bslams\b", r"\bblasts\b",
]
_UNVERIFIED = [
    r"\brumou?r\b", r"\bunconfirmed\b", r"\ballegedly\b", r"\bsources say\b",
    r"\bclaim(?:s|ed)?\b", r"\bviral (?:post|video|message)\b", r"\bforwarded\b",
]


def _hours_since(iso_ts: str) -> float:
    try:
        ts = datetime.fromisoformat(iso_ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 9999.0
    delta = datetime.now(timezone.utc) - ts
    return max(delta.total_seconds() / 3600.0, 0.0)


def _match_any(patterns: list[str], text: str) -> list[str]:
    found = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            found.append(pat.strip("\\b").replace("\\", ""))
    return found


def score_cluster(
    cluster: Cluster,
    articles_by_id: dict[str, Article],
    *,
    corroboration_for_auto: int = 2,
    trust_recommend_threshold: float = 70.0,
    recency_half_life_hours: float = 18.0,
) -> CredibilityReport:
    members = [articles_by_id[i] for i in cluster.article_ids if i in articles_by_id]
    signals: list[dict] = []
    flags: list[str] = []

    if not members:
        return CredibilityReport(0.0, 0, [], ["no_articles"], "hold")

    # --- source trust (0-40) ----------------------------------------------
    best_tier = min(m.source_tier for m in members)
    tier_points = {1: 40.0, 2: 28.0, 3: 16.0}.get(best_tier, 12.0)
    signals.append({
        "name": "source_trust",
        "weight": tier_points,
        "note": f"best source tier = {best_tier}",
    })

    # --- corroboration (0-35) ---------------------------------------------
    corroboration = cluster.corroboration
    corr_points = min(corroboration, 4) / 4.0 * 35.0
    signals.append({
        "name": "corroboration",
        "weight": round(corr_points, 1),
        "note": f"{corroboration} distinct source(s)",
    })
    if corroboration < corroboration_for_auto:
        flags.append("single_source" if corroboration <= 1 else "thin_corroboration")

    # --- recency (0-25) ---------------------------------------------------
    newest_age = min(_hours_since(m.published) for m in members)
    recency_points = 25.0 * math.exp(-newest_age / max(recency_half_life_hours, 1e-6))
    signals.append({
        "name": "recency",
        "weight": round(recency_points, 1),
        "note": f"freshest item ~{newest_age:.1f}h old",
    })

    # --- language flags (penalties) ---------------------------------------
    blob = " ".join(m.text for m in members)
    sensational = _match_any(_SENSATIONAL, blob)
    unverified = _match_any(_UNVERIFIED, blob)
    penalty = min(len(sensational) * 4 + len(unverified) * 5, 30)
    if sensational:
        flags.append("sensational_language")
    if unverified:
        flags.append("unverified_claim_markers")
    if penalty:
        signals.append({
            "name": "language_penalty",
            "weight": -float(penalty),
            "note": f"sensational={sensational} unverified={unverified}",
        })

    raw = tier_points + corr_points + recency_points - penalty
    score = max(0.0, min(100.0, raw))

    if score >= trust_recommend_threshold and corroboration >= corroboration_for_auto:
        recommendation = "fast_review"
    elif score >= 40.0:
        recommendation = "review"
    else:
        recommendation = "hold"

    return CredibilityReport(
        score=round(score, 1),
        corroboration_count=corroboration,
        signals=signals,
        flags=flags,
        recommendation=recommendation,
    )
