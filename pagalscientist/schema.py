"""Structured data (JSON-LD) for AEO — getting cited by AI answer engines.

Builds a schema.org @graph from a Story: Article, FAQPage (from the story's
FAQ), Organization (the publication), and BreadcrumbList, plus an Event node
when the story is event-like. AI answer engines (Google AI Overviews, ChatGPT,
Perplexity) parse this to understand and quote the page.

Standard library only. The output is a dict; `to_script_tag` wraps it as the
`<script type="application/ld+json">` block to embed in the published HTML.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .config import Settings
from .models import Story

# Conservative signal that a story is a datable event (concert, festival, garba).
# Deliberately strict to avoid false positives like "live model" / "show that".
_EVENT_HINT = re.compile(
    r"\b(concert|garba|navratri|dussehra|mela|premiere|screening|gig|"
    r"live in|live concert|world tour)\b", re.IGNORECASE)


def is_event_like(story: Story) -> bool:
    return bool(_EVENT_HINT.search(f"{story.headline} {story.dek}"))


def _publisher_node(settings: Settings) -> dict:
    pub = settings.raw.get("publication", {})
    name = pub.get("name", "Made in India Magazine")
    base = settings.publishing.get("site_url") or "https://madeinindiamagazine.com.au"
    return {
        "@type": "Organization",
        "@id": f"{base.rstrip('/')}/#organization",
        "name": name,
        "url": base,
    }


def _article_node(story: Story, settings: Settings, url: str) -> dict:
    pub = _publisher_node(settings)
    seo = story.seo or {}
    node = {
        "@type": "NewsArticle",
        "headline": (seo.get("seo_title") or story.headline)[:110],
        "description": seo.get("meta_description") or story.dek,
        "articleSection": settings.publishing.get("category", "News"),
        "inLanguage": "en-AU",
        "datePublished": story.created_at,
        "dateModified": story.updated_at,
        "publisher": {"@id": pub["@id"]},
        "isAccessibleForFree": True,
    }
    if url:
        node["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
    if story.tags:
        node["keywords"] = ", ".join(story.tags)
    # Author: prefer a real byline; fall back to the publication's editorial desk.
    author = (settings.raw.get("publication", {}) or {}).get("author")
    node["author"] = ({"@type": "Person", "name": author} if author
                      else {"@type": "Organization", "name": pub["name"]})
    # Citations strengthen E-E-A-T and AEO trust.
    citations = [s.get("link") for s in story.sources if s.get("link")]
    if citations:
        node["citation"] = citations
    return node


def _faq_node(story: Story) -> dict | None:
    items = []
    for qa in story.faq or []:
        q, a = (qa.get("question") or "").strip(), (qa.get("answer") or "").strip()
        if q and a:
            items.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            })
    if not items:
        return None
    return {"@type": "FAQPage", "mainEntity": items}


def build_jsonld(story: Story, settings: Settings, *, url: str = "") -> dict:
    """Return a schema.org @graph dict for the story.

    Emits Organization + NewsArticle (+ FAQPage when an FAQ exists). We do NOT
    auto-emit Event schema: valid Event markup requires a startDate and location,
    and inventing those would breach the no-unverified-facts rule. Event-like
    stories are flagged via schema_summary so an editor can add verified details.
    """
    graph = [_publisher_node(settings), _article_node(story, settings, url)]
    faq = _faq_node(story)
    if faq:
        graph.append(faq)
    return {"@context": "https://schema.org", "@graph": graph}


def to_script_tag(jsonld: dict) -> str:
    return ('<script type="application/ld+json">'
            + json.dumps(jsonld, ensure_ascii=False) + "</script>")


def schema_summary(jsonld: dict, story: Story | None = None) -> dict:
    """Which schema types were produced — for the editor's at-a-glance view.

    `event_candidate` flags stories that look like events so an editor can add a
    verified startDate/venue and enable Event rich results.
    """
    types = [n.get("@type") for n in jsonld.get("@graph", [])]
    summary = {"types": types, "has_faq": "FAQPage" in types}
    if story is not None:
        summary["event_candidate"] = is_event_like(story)
    return summary
