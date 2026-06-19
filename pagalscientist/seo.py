"""Step 2 — SEO package, aligned to RankMath's on-page "score 100" checks.

Produces a focus keyword, secondary keywords, an SEO title, a meta description
and a slug, then runs the RankMath-style checklist programmatically against the
article so the editor knows what still needs fixing before publishing.

The creative parts (keyword choice, meta copy) come from the model; the
checklist is computed here so it is deterministic and testable. Falls back to
sensible values in dry-run.

Live keyword volumes can be enriched separately via the SEO MCP tools
(keyword_metrics, keyword_suggestions, serp_analysis) operated by the editor.
"""
from __future__ import annotations

import re

from .config import Settings
from .llm import LLMClient
from .models import Story

SYSTEM = """You are an SEO editor for Made in India Magazine (Australian \
English). Given an article, choose the best SEO metadata to rank on Google.

Rules:
- Focus keyword: 1-4 words, the main search term a reader would type.
- SEO title: <= {title_max} chars, includes the focus keyword near the front.
- Meta description: {meta_min}-{meta_max} chars, includes the focus keyword, \
active voice, no clickbait, Australian English.
- Provide {secondary} secondary keywords.

Return JSON: focus_keyword, secondary_keywords (array), seo_title, \
meta_description, slug."""


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s-]+", "-", text).strip("-")[:75]


def rankmath_checklist(*, focus_keyword, seo_title, meta_description, slug,
                       body, title_max, meta_min, meta_max) -> dict:
    fk = (focus_keyword or "").lower().strip()
    body_l = body.lower()
    title_l = seo_title.lower()
    # First 10% of the body, where RankMath wants the focus keyword to appear.
    head = body_l[:max(120, len(body_l) // 10)]
    checks = {
        "focus_keyword_set": bool(fk),
        "focus_keyword_in_title": fk in title_l if fk else False,
        "focus_keyword_at_title_start": title_l.startswith(fk) if fk else False,
        "focus_keyword_in_meta": fk in meta_description.lower() if fk else False,
        "focus_keyword_in_slug": fk.replace(" ", "-") in (slug or "") if fk else False,
        "focus_keyword_in_intro": fk in head if fk else False,
        "title_length_ok": 0 < len(seo_title) <= title_max,
        "meta_length_ok": meta_min <= len(meta_description) <= meta_max,
        "slug_set": bool(slug),
        "content_length_ok": len(body.split()) >= 600,
    }
    passed = sum(1 for v in checks.values() if v)
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "score": round(passed / len(checks) * 100),
    }


def generate_seo(story: Story, settings: Settings, *, llm: LLMClient | None = None) -> dict:
    cfg = settings.seo
    title_max = cfg.get("seo_title_max", 60)
    meta_min = cfg.get("meta_description_min", 120)
    meta_max = cfg.get("meta_description_max", 160)
    secondary = cfg.get("secondary_keyword_count", 4)

    llm = llm or LLMClient(settings.verify_model, max_tokens=600)
    system = SYSTEM.format(title_max=title_max, meta_min=meta_min,
                           meta_max=meta_max, secondary=secondary)
    user = (f"Headline: {story.headline}\nDek: {story.dek}\n\n"
            f"Article:\n{story.body[:3000]}")
    data = llm.complete_json(system, user)

    # Deterministic fallbacks so dry-run still yields a usable, checkable package.
    focus_keyword = data.get("focus_keyword") or _first_keywords(story.headline)
    seo_title = (data.get("seo_title") or story.headline)[:title_max]
    meta = data.get("meta_description") or (story.dek or story.headline)
    meta = meta[:meta_max]
    slug = data.get("slug") or _slugify(story.headline)

    checklist = rankmath_checklist(
        focus_keyword=focus_keyword, seo_title=seo_title,
        meta_description=meta, slug=slug, body=story.body,
        title_max=title_max, meta_min=meta_min, meta_max=meta_max,
    )
    return {
        "focus_keyword": focus_keyword,
        "secondary_keywords": data.get("secondary_keywords", []),
        "seo_title": seo_title,
        "meta_description": meta,
        "slug": slug,
        "rankmath": checklist,
    }


def _first_keywords(headline: str, n: int = 3) -> str:
    from .text import tokens
    toks = tokens(headline)
    return " ".join(toks[:n]) if toks else headline.lower()[:40]
