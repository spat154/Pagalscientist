"""Publisher interface + registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import Story


@dataclass
class PublishResult:
    target: str
    ok: bool
    ref: str = ""        # URL or remote id on success
    detail: str = ""     # error / status message


class Publisher(Protocol):
    name: str

    def publish(self, story: Story, *, as_draft: bool = True) -> PublishResult:
        ...


def get_publisher(name: str) -> Publisher:
    name = name.lower()
    if name == "console":
        from .console import ConsolePublisher
        return ConsolePublisher()
    if name == "wordpress":
        from .wordpress import WordPressPublisher
        return WordPressPublisher()
    raise ValueError(f"Unknown publish target: {name!r}")


def available_targets() -> list[str]:
    return ["console", "wordpress"]
