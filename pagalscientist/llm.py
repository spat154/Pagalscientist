"""Thin wrapper around the Claude Messages API.

Falls back to a deterministic dry-run when no ANTHROPIC_API_KEY is set or the
`anthropic` package is missing, so the whole pipeline is demonstrable offline.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, model: str, *, max_tokens: int = 2000, dry_run: bool | None = None):
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if dry_run is None:
            dry_run = not self.api_key
        self.dry_run = dry_run
        self._client = None
        if not self.dry_run:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                log.warning("anthropic package not installed; using dry-run mode.")
                self.dry_run = True

    def complete(self, system: str, user: str) -> str:
        """Return raw text from the model (or a stub in dry-run)."""
        if self.dry_run:
            return _stub_response(system, user)
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def complete_json(self, system: str, user: str) -> dict:
        """Ask for JSON and parse it, tolerating code fences and stray prose."""
        raw = self.complete(system + "\n\nRespond with valid JSON only.", user)
        return _extract_json(raw)


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip("` \n")
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _stub_response(system: str, user: str) -> str:
    """Deterministic offline output so dry-run produces a usable draft."""
    # The generator asks for JSON; detect that and return a structured stub.
    if "JSON" in system or "json" in system:
        return json.dumps({
            "headline": "[DRY-RUN] India desk draft pending live model",
            "dek": "Set ANTHROPIC_API_KEY to generate the real, audience-tuned story.",
            "angle": "Connecting angle will be synthesized by the live model.",
            "body": (
                "_This is a deterministic dry-run draft._\n\n"
                "The pipeline successfully sensed, clustered and verified this "
                "story. With a live Claude key it would now be rewritten for the "
                "Middle India reader — plain language, the 'what this means for "
                "me' angle, and any connecting patterns across recent news.\n\n"
                "**Facts provided to the writer:**\n\n" + user[-1200:]
            ),
            "tags": ["made-in-india", "dry-run"],
        })
    return "[DRY-RUN] No live model configured."
