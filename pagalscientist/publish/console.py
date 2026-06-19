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
        return (
            f"# {story.headline}\n\n"
            f"_{story.dek}_\n\n"
            f"{story.body}\n\n"
            f"---\n"
            f"**Tags:** {', '.join(story.tags)}\n\n"
            f"**Credibility:** score {cred.get('score', 'n/a')} · "
            f"{cred.get('corroboration_count', 0)} source(s) · "
            f"flags: {', '.join(cred.get('flags', [])) or 'none'}\n\n"
            f"**Sources:**\n{src_lines}\n"
        )

    def publish(self, story: Story, *, as_draft: bool = True) -> PublishResult:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"{story.id}.md"
        path.write_text(self.render(story), encoding="utf-8")
        status = "DRAFT" if as_draft else "LIVE"
        print(f"[console:{status}] wrote {path}")
        return PublishResult(target=self.name, ok=True, ref=str(path),
                             detail=f"rendered as {status}")
