"""Step 1 — write the article.

Encodes the Made in India Magazine editorial brief into the system prompt, asks
Claude for a structured article, then runs mechanical checks:
  * house-style compliance (banned words/phrases, em dash, AU English)
  * a reference check: every quote or date in the body needs N source URLs

The model is told the rules, but we verify them ourselves and attach the
results to the Story so the editor sees exactly what to fix.
"""
from __future__ import annotations

import re

from .config import Settings
from .llm import LLMClient
from .models import Article, Cluster, Story
from .style import auto_fix_spellings, compliance_report, load_style_rules

SYSTEM_TEMPLATE = """You are a senior journalist and editor at Made in India \
Magazine, a daily publication based in Australia for the Indian-Australian \
community.

AUDIENCE: {audience_desc}

THREE PILLARS — every article must clearly serve at least one. Name the pillar \
you are serving and why:
{pillars}

LANGUAGE: Australian English only (e.g. "organised", "optimised", "centre", \
"colour"). Never American spellings.

TONE & STRUCTURE:
- Journalistic and analytical. Not blog-like, not casual. No fluff; every \
sentence must add real value.
- Open with a strong hook (emotional, surprising, or a sharp question).
- Use clear subheadings so the piece is easy to skim and flows logically.
- Give depth: every person, organisation or case study you mention gets at \
least {min_lines} lines. No throwaway mentions.
- End with a thoughtful takeaway or broader reflection, handled with extra \
care for sensitive topics (immigration, religion, conflict): stay neutral and \
give context.
- Aim for about {word_count} words.

ANSWER ENGINE OPTIMISATION (so AI answer engines can cite us):
- Write answer-first: open each section with a short, direct, quotable answer, \
then expand. Phrase subheadings as the questions a reader would actually ask.
- Provide a "faq" array of 3-5 genuine question/answer pairs. Each answer must \
be self-contained, factual, and 1-3 sentences. Only include answers the sources \
support.

FACT STANDARDS (strict):
- Never invent facts, examples, names, quotes, numbers or dates.
- Do not include a statistic or claim unless a named, verifiable source backs \
it. If you are unsure, say so plainly.
- For EVERY quote and EVERY date you state, supply at least {refs} reference \
URLs in the "references" array so a human can confirm them. If you cannot find \
{refs} references, do not state the quote/date as fact: instead add a note to \
"unverified_notes" beginning with "I cannot verify".
- If anything is inferred or unconfirmed, label it inline with [Inference], \
[Speculation], or [Unverified].

STYLE BANS (do not use):
- The em dash character.
- The structure "It's not X, it's Y" (or any variation).
- These words: {banned_words}.
- These phrases: {banned_phrases}.
- Write like a human; avoid tell-tale signs of AI writing.

Return JSON with keys: pillar (string: which pillar + one line why), headline, \
dek, hook, body (markdown with subheadings; do NOT repeat the hook line), \
takeaway, tags (array), faq (array of {{question, answer}}), references (array \
of {{claim, type:"quote"|"date", urls:[...]}}), unverified_notes (array of \
strings)."""

# Detect dates and direct quotes in prose, for the reference check.
_DATE_RE = re.compile(
    r"\b("
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}"
    r"|(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r")\b",
    re.IGNORECASE,
)
_QUOTE_RE = re.compile(r"[\"“]([^\"“”]{12,})[\"”]")


def _facts_block(cluster: Cluster, articles_by_id: dict[str, Article]) -> str:
    lines = [f"Key terms: {', '.join(cluster.key_terms)}",
             f"Distinct sources: {cluster.corroboration}", ""]
    for aid in cluster.article_ids:
        art = articles_by_id.get(aid)
        if not art:
            continue
        lines.append(f"- [{art.source} | tier {art.source_tier}] {art.title}")
        if art.summary:
            lines.append(f"  {art.summary}")
        lines.append(f"  source URL: {art.link}")
    return "\n".join(lines)


def _format_pillars(settings: Settings) -> str:
    rows = []
    for p in settings.raw.get("pillars", []):
        rows.append(f"  {p['id']}. {p['name']} — {p['test']}")
    return "\n".join(rows) or "  1. Value to the Indian-Australian community."


def build_brief(cluster, articles_by_id, *, direction="", references=None,
                patterns=None) -> str:
    parts = ["Write an article for Made in India Magazine from these supplied "
             "sources. Use only what they support.\n",
             _facts_block(cluster, articles_by_id)]
    if direction:
        parts.append(f"\nEditor's direction / angle: {direction}")
    if references:
        parts.append("\nAdditional references supplied:\n" +
                     "\n".join(f"- {r}" for r in references))
    if patterns:
        trending = ", ".join(
            f"{p['term']} ({p['story_count']} stories)" for p in patterns[:6]
        )
        parts.append(f"\nThemes trending across the news now: {trending}. "
                     "If this story connects to any, draw out that angle.")
    return "\n".join(parts)


def check_references(body: str, references: list[dict], refs_required: int) -> dict:
    """Flag any quote or date in the body that lacks the required references."""
    covered = []
    for r in references or []:
        if len(r.get("urls", [])) >= refs_required:
            covered.append((r.get("claim", "") or "").lower())

    def is_covered(text: str) -> bool:
        t = text.lower()
        return any(t in c or c in t for c in covered if c)

    unbacked = []
    for m in _DATE_RE.finditer(body):
        if not is_covered(m.group(0)):
            unbacked.append({"type": "date", "text": m.group(0)})
    for m in _QUOTE_RE.finditer(body):
        if not is_covered(m.group(1)):
            unbacked.append({"type": "quote", "text": m.group(1)[:60]})
    return {
        "refs_required": refs_required,
        "claims_with_enough_refs": len(covered),
        "unbacked_claims": unbacked,
        "ok": not unbacked,
    }


def generate_story(cluster, articles_by_id, credibility, settings, *,
                   llm=None, patterns=None, direction="", references=None) -> Story:
    audience = settings.audience
    gen = settings.generation
    rules = load_style_rules()
    system = SYSTEM_TEMPLATE.format(
        audience_desc=audience.get("description", "The Indian-Australian community."),
        pillars=_format_pillars(settings),
        min_lines=gen.get("min_lines_per_entity", 5),
        word_count=gen.get("target_word_count", 700),
        refs=settings.verification.get("references_per_claim", 3),
        banned_words=", ".join(rules.get("banned_words", [])),
        banned_phrases=", ".join(rules.get("banned_phrases", [])),
    )
    brief = build_brief(cluster, articles_by_id, direction=direction,
                        references=references, patterns=patterns)

    llm = llm or LLMClient(settings.generation_model,
                           max_tokens=gen.get("max_tokens", 3000))
    data = llm.complete_json(system, brief)

    body = auto_fix_spellings(data.get("body", ""), rules)
    fallback_headline = (f"India-Australia update: {cluster.key_terms[0]}"
                         if cluster.key_terms else "Untitled story")

    story_sources = []
    for aid in cluster.article_ids:
        art = articles_by_id.get(aid)
        if art:
            story_sources.append({"name": art.source, "link": art.link})

    story = Story.create(
        cluster_id=cluster.id,
        headline=data.get("headline") or fallback_headline,
        dek=data.get("dek", ""),
        body=body,
        tags=data.get("tags", ["made-in-india"]),
        credibility=credibility,
        sources=story_sources,
        hook=data.get("hook", ""),
        takeaway=data.get("takeaway", ""),
        pillar=data.get("pillar", ""),
        references=data.get("references", []),
        unverified_notes=data.get("unverified_notes", []),
        faq=data.get("faq", []),
    )

    # Mechanical checks attached for the editor.
    refs_required = settings.verification.get("references_per_claim", 3)
    full_text = "\n".join([story.hook, story.dek, body, story.takeaway])
    story.compliance = {
        "style": compliance_report(full_text, rules),
        "references": check_references(body, story.references, refs_required),
    }
    # Structured data for AEO (Article + FAQPage + Event where relevant).
    from .schema import build_jsonld, schema_summary
    story.schema = build_jsonld(story, settings)
    story.compliance["schema"] = schema_summary(story.schema, story)
    cluster.angle = data.get("pillar", "")
    return story
