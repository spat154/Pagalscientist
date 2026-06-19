"""WordPress publisher via the REST API.

Posts the story as a draft (default) or publishes it live. Auth uses a
WordPress Application Password (WP_USERNAME / WP_APP_PASSWORD) over HTTPS.
`requests` is imported lazily.

Body markdown is sent as-is; WordPress renders it acceptably for drafts, and
the editor does the final formatting pass in wp-admin before going live —
which matches the "have it ready, hit a button" workflow.
"""
from __future__ import annotations

import os

from ..models import Story
from .base import PublishResult


class WordPressPublisher:
    name = "wordpress"

    def __init__(self):
        self.base_url = (os.environ.get("WP_BASE_URL") or "").rstrip("/")
        self.username = os.environ.get("WP_USERNAME")
        self.app_password = os.environ.get("WP_APP_PASSWORD")

    def _configured(self) -> bool:
        return bool(self.base_url and self.username and self.app_password)

    def publish(self, story: Story, *, as_draft: bool = True) -> PublishResult:
        if not self._configured():
            return PublishResult(
                target=self.name, ok=False,
                detail="WordPress not configured (set WP_BASE_URL, WP_USERNAME, "
                       "WP_APP_PASSWORD).",
            )
        try:
            import requests
        except ImportError:
            return PublishResult(target=self.name, ok=False,
                                 detail="`requests` not installed.")

        endpoint = f"{self.base_url}/wp-json/wp/v2/posts"
        content = story.body
        # Append an FAQ section and the JSON-LD structured data so the page is
        # AEO-ready even if the theme/RankMath doesn't add it.
        if story.faq:
            content += "\n\n## FAQ\n" + "\n".join(
                f"\n### {qa.get('question','')}\n{qa.get('answer','')}"
                for qa in story.faq)
        if story.schema:
            from ..schema import to_script_tag
            content += "\n\n" + to_script_tag(story.schema)
        payload = {
            "title": story.headline,
            "excerpt": story.dek,
            "content": content,
            "status": "draft" if as_draft else "publish",
            "tags": [],  # tag IDs would be resolved here in a full integration
        }
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                auth=(self.username, self.app_password),
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001
            return PublishResult(target=self.name, ok=False, detail=str(exc))

        if resp.status_code in (200, 201):
            data = resp.json()
            return PublishResult(
                target=self.name, ok=True,
                ref=data.get("link", str(data.get("id", ""))),
                detail="draft created" if as_draft else "published",
            )
        return PublishResult(
            target=self.name, ok=False,
            detail=f"HTTP {resp.status_code}: {resp.text[:300]}",
        )
