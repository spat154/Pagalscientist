"""Editorial review + the one-button "publish everywhere" step.

Stories arrive in NEEDS_REVIEW. An editor edits, approves, or rejects them.
Only APPROVED stories can be published, and publishing fans out to every
enabled target at once.
"""
from __future__ import annotations

import logging

from .config import Settings
from .models import Story, StoryStatus, now_iso
from .publish import PublishResult, get_publisher
from .store import Store

log = logging.getLogger(__name__)


def edit_story(store: Store, story_id: str, *, headline=None, dek=None,
               body=None, tags=None, editor_notes=None) -> Story:
    story = store.get_story(story_id)
    if not story:
        raise KeyError(f"No story {story_id}")
    if headline is not None:
        story.headline = headline
    if dek is not None:
        story.dek = dek
    if body is not None:
        story.body = body
    if tags is not None:
        story.tags = tags
    if editor_notes is not None:
        story.editor_notes = editor_notes
    story.updated_at = now_iso()
    store.upsert_story(story)
    return story


def set_status(store: Store, story_id: str, status: StoryStatus) -> Story:
    story = store.get_story(story_id)
    if not story:
        raise KeyError(f"No story {story_id}")
    story.status = status.value
    story.updated_at = now_iso()
    store.upsert_story(story)
    return story


def approve(store: Store, story_id: str) -> Story:
    return set_status(store, story_id, StoryStatus.APPROVED)


def reject(store: Store, story_id: str) -> Story:
    return set_status(store, story_id, StoryStatus.REJECTED)


def publish_story(
    store: Store,
    story_id: str,
    settings: Settings,
    *,
    targets: list[str] | None = None,
    force: bool = False,
) -> list[PublishResult]:
    """The publish button. Fans the story out to every enabled target.

    Refuses unless the story is APPROVED, unless `force=True` (for testing/demo).
    """
    story = store.get_story(story_id)
    if not story:
        raise KeyError(f"No story {story_id}")
    if story.status != StoryStatus.APPROVED.value and not force:
        raise ValueError(
            f"Story {story_id} is '{story.status}', not approved. "
            f"Approve it first (or pass force=True)."
        )

    pub_cfg = settings.publishing
    targets = targets or pub_cfg.get("default_targets", ["console"])
    as_draft = pub_cfg.get("stage_as_draft", True)

    results: list[PublishResult] = []
    for target in targets:
        try:
            publisher = get_publisher(target)
            result = publisher.publish(story, as_draft=as_draft)
        except Exception as exc:  # noqa: BLE001 - one bad target shouldn't block others
            result = PublishResult(target=target, ok=False, detail=str(exc))
        results.append(result)
        if result.ok:
            story.published_targets[target] = result.ref

    if any(r.ok for r in results):
        story.status = StoryStatus.PUBLISHED.value
        story.updated_at = now_iso()
        store.upsert_story(story)
    return results
