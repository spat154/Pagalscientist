"""House-style compliance linter for Made in India Magazine.

Enforces the editorial brief mechanically rather than trusting the model to
remember every rule: Australian English, the banned words/phrases list, the
em-dash ban, and the "it's not X, it's Y" structure ban. Also exposes helpers
for the hedge-trigger words and approved CTAs.

Standard-library only (regex). PyYAML is used only to load the rules file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import CONFIG_DIR


@dataclass
class Violation:
    kind: str          # au_spelling | banned_word | banned_phrase | em_dash | not_x_its_y
    term: str          # the offending text
    suggestion: str    # how to fix (may be empty)
    context: str = ""  # short snippet around the match

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=4)
def load_style_rules(path: str | None = None) -> dict[str, Any]:
    import yaml
    p = Path(path) if path else CONFIG_DIR / "style_rules.yaml"
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _context(text: str, start: int, end: int, pad: int = 25) -> str:
    snippet = text[max(0, start - pad):min(len(text), end + pad)].strip()
    return re.sub(r"\s+", " ", snippet)


# "it's not X, it's Y" and close variants ("it is not ... it is ...").
_NOT_X_ITS_Y = re.compile(
    r"\bit'?s?\s+not\b[^.,;]{0,60}?,?\s*\bit'?s?\b",
    re.IGNORECASE,
)


def lint_text(text: str, rules: dict[str, Any] | None = None) -> list[Violation]:
    rules = rules or load_style_rules()
    out: list[Violation] = []
    lower = text.lower()

    # 1) banned single words (word boundary)
    for word in rules.get("banned_words", []):
        for m in re.finditer(rf"\b{re.escape(word.lower())}\b", lower):
            out.append(Violation("banned_word", word, "remove / reword",
                                 _context(text, m.start(), m.end())))

    # 2) banned phrases (word-boundary match so we don't fire inside larger
    #    tokens, e.g. "key to" must not match "API_KEY to").
    for phrase in rules.get("banned_phrases", []):
        pat = r"\b" + r"\s+".join(re.escape(w) for w in phrase.lower().split()) + r"\b"
        for m in re.finditer(pat, lower):
            out.append(Violation("banned_phrase", phrase, "remove / reword",
                                 _context(text, m.start(), m.end())))

    # 3) em dash
    if rules.get("ban_em_dash") and "—" in text:
        i = text.find("—")
        out.append(Violation("em_dash", "—",
                             "use a comma, full stop, or rephrase",
                             _context(text, i, i + 1)))

    # 4) "it's not X, it's Y"
    if rules.get("ban_not_x_its_y"):
        for m in _NOT_X_ITS_Y.finditer(text):
            out.append(Violation("not_x_its_y", m.group(0).strip(),
                                 "rephrase without the not-X-its-Y structure",
                                 _context(text, m.start(), m.end())))

    # 5) Australian English
    for us, au in rules.get("au_spelling", {}).items():
        for m in re.finditer(rf"\b{re.escape(us)}\b", lower):
            out.append(Violation("au_spelling", us, f"use '{au}' (AU English)",
                                 _context(text, m.start(), m.end())))

    return out


def hedge_triggers(text: str, rules: dict[str, Any] | None = None) -> list[str]:
    """Words that require a named source or an [Unverified] label nearby."""
    rules = rules or load_style_rules()
    lower = text.lower()
    found = []
    for w in rules.get("hedge_trigger_words", []):
        if re.search(rf"\b{re.escape(w.lower())}\b", lower):
            found.append(w)
    return found


def approved_ctas(rules: dict[str, Any] | None = None) -> list[str]:
    rules = rules or load_style_rules()
    return list(rules.get("approved_ctas", ["Read the full article"]))


def compliance_report(text: str, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    rules = rules or load_style_rules()
    violations = lint_text(text, rules)
    by_kind: dict[str, int] = {}
    for v in violations:
        by_kind[v.kind] = by_kind.get(v.kind, 0) + 1
    return {
        "clean": not violations,
        "violation_count": len(violations),
        "by_kind": by_kind,
        "violations": [v.to_dict() for v in violations],
        "hedge_triggers": hedge_triggers(text, rules),
    }


def auto_fix_spellings(text: str, rules: dict[str, Any] | None = None) -> str:
    """Apply the unambiguous AU-spelling corrections in place.

    Only the spelling map is auto-applied; banned words/phrases are left for an
    editor because rewording needs judgement.
    """
    rules = rules or load_style_rules()
    fixed = text
    for us, au in rules.get("au_spelling", {}).items():
        fixed = re.sub(rf"\b{re.escape(us)}\b", au, fixed)
        fixed = re.sub(rf"\b{re.escape(us.capitalize())}\b", au.capitalize(), fixed)
    return fixed
