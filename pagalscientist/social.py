"""Step 3 — the social story post.

Builds a ready-to-post hook + caption for social, with an approved CTA. Enforces
the brief's caption rules: at most N lines, the word "sibling" is banned, and
the house-style linter still applies (no banned words, em dash, etc.).
"""
from __future__ import annotations

from .config import Settings
from .llm import LLMClient
from .models import Story
from .style import approved_ctas, compliance_report, load_style_rules

SYSTEM = """You write social media story posts for Made in India Magazine \
(Australian English). Given an article, produce a scroll-stopping but \
professional post. It may be intriguing, but must not feel like clickbait, and \
must read like a human wrote it.

Rules:
- Caption: at most {max_lines} lines, punchy, Australian English.
- Do not use the word "sibling".
- Do not use an em dash or any banned house-style words.
- Provide {hashtags} relevant hashtags.

Return JSON: hook (one line), caption, hashtags (array)."""


def _truncate_lines(text: str, max_lines: int) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[:max_lines])


def generate_social(story: Story, settings: Settings, *,
                    llm: LLMClient | None = None) -> dict:
    cfg = settings.social
    max_lines = cfg.get("caption_max_lines", 3)
    n_tags = cfg.get("hashtag_count", 5)
    rules = load_style_rules()

    llm = llm or LLMClient(settings.verify_model, max_tokens=500)
    system = SYSTEM.format(max_lines=max_lines, hashtags=n_tags)
    user = f"Headline: {story.headline}\nHook: {story.hook}\nDek: {story.dek}"
    data = llm.complete_json(system, user)

    hook = data.get("hook") or story.hook or story.headline
    caption = _truncate_lines(data.get("caption") or story.dek or story.headline,
                              max_lines)

    # Enforce the caption-specific bans.
    caption_flags = []
    for w in rules.get("caption_banned_words", []):
        if w.lower() in caption.lower():
            caption_flags.append(f"contains banned caption word '{w}'")
    line_count = len([ln for ln in caption.splitlines() if ln.strip()])
    if line_count > max_lines:
        caption_flags.append(f"caption has {line_count} lines (max {max_lines})")

    ctas = approved_ctas(rules)
    return {
        "hook": hook,
        "caption": caption,
        "hashtags": data.get("hashtags", []),
        "cta": ctas[0],
        "cta_options": ctas,
        "caption_flags": caption_flags,
        "style": compliance_report(f"{hook}\n{caption}", rules),
    }
