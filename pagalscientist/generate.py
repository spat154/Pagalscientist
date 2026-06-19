"""Turn a verified story cluster into a Middle-India-customized draft.

Builds the editorial brief (audience persona + the corroborated facts + the
detected connecting angle), asks Claude for a structured story, and returns a
Story object staged for human review. Never publishes on its own.
"""
from __future__ import annotations

from .config import Settings
from .llm import LLMClient
from .models import Article, Cluster, Story

SYSTEM_TEMPLATE = """You are the senior editor of "Made in India", a magazine \
for the Middle India audience.

Audience: {audience_desc}
Reading level: {reading_level}

Editorial rules:
- Write for the reader who asks "what does this mean for me and my family?".
- Plain, warm, conversational English; you may use a few everyday Hindi words \
naturally, but stay accessible.
- Lead with the human/local impact, not Delhi/Mumbai elite framing.
- Be accurate. Only state what the provided sources support. If something is \
unconfirmed, say so plainly. Do NOT invent facts, numbers, names or quotes.
- Surface the connecting angle: how this links to wider patterns the audience \
cares about (jobs, schemes, small business, prices, India building things).
- No hype, no clickbait. Respect the reader's intelligence.
- Target about {word_count} words.

Return JSON with keys: headline, dek, angle, body (markdown), tags (array)."""


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
        lines.append(f"  ({art.link})")
    return "\n".join(lines)


def build_brief(
    cluster: Cluster,
    articles_by_id: dict[str, Article],
    patterns: list[dict] | None = None,
) -> str:
    parts = ["Write a story for the Made in India audience from these "
             "corroborated reports:\n", _facts_block(cluster, articles_by_id)]
    if patterns:
        trending = ", ".join(
            f"{p['term']} ({p['story_count']} stories)" for p in patterns[:6]
        )
        parts.append(f"\nThemes trending across the news right now: {trending}.")
        parts.append("If this story connects to any of those themes, draw that "
                     "angle out for the reader.")
    return "\n".join(parts)


def generate_story(
    cluster: Cluster,
    articles_by_id: dict[str, Article],
    credibility: dict,
    settings: Settings,
    *,
    llm: LLMClient | None = None,
    patterns: list[dict] | None = None,
) -> Story:
    audience = settings.audience
    gen = settings.generation
    system = SYSTEM_TEMPLATE.format(
        audience_desc=audience.get("description", "Middle India readers."),
        reading_level=audience.get("reading_level", "simple, grade 8"),
        word_count=gen.get("target_word_count", 550),
    )
    brief = build_brief(cluster, articles_by_id, patterns=patterns)

    llm = llm or LLMClient(
        settings.generation_model,
        max_tokens=gen.get("max_tokens", 2000),
    )
    data = llm.complete_json(system, brief)

    sources = []
    for aid in cluster.article_ids:
        art = articles_by_id.get(aid)
        if art:
            sources.append({"name": art.source, "link": art.link})

    fallback_headline = (
        f"India update: {cluster.key_terms[0]}"
        if cluster.key_terms else "Untitled India story"
    )
    story = Story.create(
        cluster_id=cluster.id,
        headline=data.get("headline") or fallback_headline,
        dek=data.get("dek", ""),
        body=data.get("body", ""),
        tags=data.get("tags", ["made-in-india"]),
        credibility=credibility,
        sources=sources,
    )
    # Persist the connecting angle back onto the cluster narrative.
    cluster.angle = data.get("angle", "")
    return story
