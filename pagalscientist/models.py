"""Core data models flowing through the pipeline.

Plain dataclasses with dict (de)serialization so the store can persist them as
JSON. No third-party dependencies.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(*parts: str) -> str:
    digest = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


class StoryStatus(str, Enum):
    DRAFTED = "drafted"            # AI wrote a draft
    NEEDS_REVIEW = "needs_review"  # waiting for a human editor
    APPROVED = "approved"          # editor approved; ready for the publish button
    PUBLISHED = "published"        # pushed to one or more targets
    REJECTED = "rejected"          # editor killed it


@dataclass
class Article:
    """A single item sensed from a source feed."""

    id: str
    source: str
    source_tier: int
    audience_weight: float
    title: str
    summary: str
    link: str
    published: str        # ISO8601, best-effort from the feed
    fetched_at: str
    language: str = "en"
    topics: list[str] = field(default_factory=list)
    cluster_id: str | None = None

    @classmethod
    def create(cls, *, source, source_tier, audience_weight, title, summary,
               link, published, language="en", topics=None) -> "Article":
        return cls(
            id=make_id(link or title),
            source=source,
            source_tier=source_tier,
            audience_weight=audience_weight,
            title=title.strip(),
            summary=summary.strip(),
            link=link,
            published=published or now_iso(),
            fetched_at=now_iso(),
            language=language,
            topics=list(topics or []),
        )

    @property
    def text(self) -> str:
        return f"{self.title}. {self.summary}".strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Article":
        return cls(**d)


@dataclass
class Cluster:
    """A group of articles that tell the same underlying story."""

    id: str
    article_ids: list[str]
    key_terms: list[str]
    sources: list[str]
    lead_article_id: str
    created_at: str
    # The "connecting angle" — what ties these reports together and why the
    # Middle India reader should care. Filled by the generator.
    angle: str = ""

    @property
    def corroboration(self) -> int:
        """Number of distinct sources reporting the story."""
        return len(set(self.sources))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cluster":
        return cls(**d)


@dataclass
class CredibilityReport:
    score: float                       # 0-100
    corroboration_count: int
    signals: list[dict[str, Any]]      # {name, weight, note}
    flags: list[str]                   # caution flags
    recommendation: str                # "fast_review" | "review" | "hold"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CredibilityReport":
        return cls(**d)


@dataclass
class Story:
    """A drafted, diaspora-customized article staged for review/publishing."""

    id: str
    cluster_id: str
    headline: str
    dek: str                           # standfirst / subheading
    body: str                          # markdown
    tags: list[str]
    status: str
    created_at: str
    updated_at: str
    credibility: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, str]] = field(default_factory=list)  # {name, link}
    editor_notes: str = ""
    published_targets: dict[str, str] = field(default_factory=dict)  # target -> url/id
    # --- editorial brief fields ---
    hook: str = ""                     # opening hook
    takeaway: str = ""                 # closing reflection
    pillar: str = ""                   # which of the 3 pillars it serves + why
    # Each quote/date must carry >= N reference URLs: {claim, type, urls:[...]}
    references: list[dict[str, Any]] = field(default_factory=list)
    unverified_notes: list[str] = field(default_factory=list)
    faq: list[dict[str, str]] = field(default_factory=list)   # {question, answer}
    schema: dict[str, Any] = field(default_factory=dict)       # JSON-LD structured data
    compliance: dict[str, Any] = field(default_factory=dict)   # style lint result
    seo: dict[str, Any] = field(default_factory=dict)          # step 2 output
    social: dict[str, Any] = field(default_factory=dict)       # step 3 output

    @classmethod
    def create(cls, *, cluster_id, headline, dek, body, tags,
               credibility, sources, hook="", takeaway="", pillar="",
               references=None, unverified_notes=None, faq=None) -> "Story":
        ts = now_iso()
        return cls(
            id=make_id(cluster_id, headline),
            cluster_id=cluster_id,
            headline=headline,
            dek=dek,
            body=body,
            tags=list(tags),
            status=StoryStatus.NEEDS_REVIEW.value,
            created_at=ts,
            updated_at=ts,
            credibility=credibility,
            sources=sources,
            hook=hook,
            takeaway=takeaway,
            pillar=pillar,
            references=list(references or []),
            unverified_notes=list(unverified_notes or []),
            faq=list(faq or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Story":
        return cls(**d)
