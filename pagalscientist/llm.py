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
            "pillar": "1. Value to Indians living in Australia (dry-run placeholder).",
            "headline": "[DRY-RUN] Draft pending live model",
            "dek": "Set ANTHROPIC_API_KEY to generate the real, audience-tuned story.",
            "hook": "A quick note before the real writer takes over.",
            "body": (
                "_This is a deterministic dry-run draft._\n\n"
                "## What happened\n\n"
                "The pipeline sensed, clustered and verified this story. With a "
                "live Claude key it would be written for the Indian-Australian "
                "reader in Australian English, journalistic and analytical, with "
                "a strong hook, clear subheadings and proper depth.\n\n"
                "## Facts provided to the writer\n\n" + user[-1200:]
            ),
            "takeaway": "Add your API key to turn this into a finished, sourced article.",
            "tags": ["made-in-india", "dry-run"],
            "faq": [
                {"question": "Is this a real article?",
                 "answer": "No. This is a dry-run placeholder produced without a "
                           "live model; set ANTHROPIC_API_KEY for real content."},
                {"question": "What will the live version include?",
                 "answer": "An answer-first article in Australian English with a "
                           "hook, subheadings, sourced facts, and this FAQ block."},
            ],
            "references": [],
            "unverified_notes": ["I cannot verify any specifics in dry-run mode."],
        })
    return "[DRY-RUN] No live model configured."
