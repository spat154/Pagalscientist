"""Configuration loading for sources and settings.

YAML files hold the defaults; environment variables (PAGAL_*, WP_*,
ANTHROPIC_API_KEY) override the bits that are secret or deployment-specific.
PyYAML is imported lazily so the pure-logic modules and tests do not require it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without PyYAML
        raise RuntimeError(
            "PyYAML is required to read config files. Install it with "
            "`pip install -r requirements.txt`."
        ) from exc
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class Source:
    name: str
    url: str
    language: str = "en"
    trust_tier: int = 3
    audience_weight: float = 0.5
    topics: list[str] = field(default_factory=list)


@dataclass
class Settings:
    raw: dict[str, Any]

    # --- convenience accessors -------------------------------------------
    @property
    def audience(self) -> dict[str, Any]:
        return self.raw.get("audience", {})

    @property
    def clustering(self) -> dict[str, Any]:
        return self.raw.get("clustering", {})

    @property
    def verification(self) -> dict[str, Any]:
        return self.raw.get("verification", {})

    @property
    def generation(self) -> dict[str, Any]:
        return self.raw.get("generation", {})

    @property
    def publishing(self) -> dict[str, Any]:
        return self.raw.get("publishing", {})

    @property
    def db_path(self) -> str:
        return os.environ.get("PAGAL_DB", "data/pagalscientist.db")

    @property
    def generation_model(self) -> str:
        return os.environ.get(
            "PAGAL_GENERATION_MODEL",
            self.generation.get("generation_model", "claude-opus-4-8"),
        )

    @property
    def verify_model(self) -> str:
        return os.environ.get(
            "PAGAL_VERIFY_MODEL",
            self.generation.get("verify_model", "claude-sonnet-4-6"),
        )


def load_sources(path: Path | str | None = None) -> list[Source]:
    path = Path(path) if path else CONFIG_DIR / "sources.yaml"
    data = _load_yaml(path)
    sources = []
    for entry in data.get("feeds", []):
        sources.append(
            Source(
                name=entry["name"],
                url=entry["url"],
                language=entry.get("language", "en"),
                trust_tier=int(entry.get("trust_tier", 3)),
                audience_weight=float(entry.get("audience_weight", 0.5)),
                topics=list(entry.get("topics", [])),
            )
        )
    return sources


def load_settings(path: Path | str | None = None) -> Settings:
    path = Path(path) if path else CONFIG_DIR / "settings.yaml"
    return Settings(raw=_load_yaml(path))
