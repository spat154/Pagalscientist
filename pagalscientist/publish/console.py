"""Console / dry-run publisher.

Writes the rendered story to ./out as Markdown and prints a preview. Always
available, no credentials. Useful as the default target and for demos.
"""
from __future__ import annotations

from pathlib import Path

from ..models import Story
from .base import PublishResult


class ConsolePublisher:
    name = "console"

    def __init__(self, out_dir: str | Path = "out"):
        self.out_dir = Path(out_dir)

    def render(self, story: Story) -> str:
        cred = story.credibility or {}
        src_lines = "\n".join(
            f"- [{s['name']}]({s['link']})" for s in story.sources
        )
        parts = [f"# {story.headline}\n"]
        if story.pillar:
            parts.append(f"> **Pillar:** {story.pillar}\n")
        if story.hook:
            parts.append(f"**{story.hook}**\n")
        parts.append(f"_{story.dek}_\n")
        parts.append(f"{story.body}\n")
        if story.takeaway:
            parts.append(f"**Takeaway:** {story.takeaway}\n")
        parts.append("---")
        parts.append(f"**Tags:** {', '.join(story.tags)}")
        parts.append(
            f"**Credibility:** score {cred.get('score', 'n/a')} · "
            f"{cred.get('corroboration_count', 0)} source(s) · "
            f"flags: {', '.join(cred.get('flags', [])) or 'none'}"
        )
        comp = story.compliance or {}
        style = comp.get("style", {})
        refs = comp.get("references", {})
        if style:
            parts.append(
                f"**Style check:** "
                f"{'clean' if style.get('clean') else str(style.get('violation_count')) + ' issue(s): ' + str(style.get('by_kind'))}"
            )
        if refs:
            ub = refs.get("unbacked_claims", [])
            parts.append(f"**Reference check:** "
                         f"{'all quotes/dates backed' if refs.get('ok') else str(len(ub)) + ' unbacked: ' + str(ub)}")
        if story.unverified_notes:
            parts.append("**Unverified notes:** " + "; ".join(story.unverified_notes))
        if story.faq:
            parts.append("\n## FAQ")
            for qa in story.faq:
                parts.append(f"**{qa.get('question','')}**\n\n{qa.get('answer','')}\n")
        if story.schema:
            sch = story.compliance.get("schema", {}) if story.compliance else {}
            types = ", ".join(sch.get("types", [])) or "Article"
            parts.append(f"**Structured data (AEO):** {types}")
        if story.seo:
            seo = story.seo
            rm = seo.get("rankmath", {})
            parts.append(f"**SEO:** focus '{seo.get('focus_keyword')}' · "
                         f"RankMath {rm.get('score', '?')}/100 · slug `{seo.get('slug')}`")
            parts.append(f"  - title: {seo.get('seo_title')}")
            parts.append(f"  - meta: {seo.get('meta_description')}")
        if story.social:
            soc = story.social
            parts.append(f"**Social:** {soc.get('hook')}")
            parts.append(f"  caption: {soc.get('caption')}")
            parts.append(f"  CTA: {soc.get('cta')} · tags: {' '.join(soc.get('hashtags', []))}")
        parts.append(f"\n**Sources:**\n{src_lines}\n")
        return "\n".join(parts)

    def publish(self, story: Story, *, as_draft: bool = True) -> PublishResult:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"{story.id}.md"
        path.write_text(self.render(story), encoding="utf-8")
        status = "DRAFT" if as_draft else "LIVE"
        print(f"[console:{status}] wrote {path}")
        return PublishResult(target=self.name, ok=True, ref=str(path),
                             detail=f"rendered as {status}")
