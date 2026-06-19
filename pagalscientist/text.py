"""Small text helpers shared across clustering and verification.

Standard library only. Deliberately lightweight (no NLP deps) so the core
logic stays portable and testable.
"""
from __future__ import annotations

import re
from collections import Counter

_WORD_RE = re.compile(r"[a-z0-9ऀ-ॿ]+")  # includes Devanagari range

# Common English + a few Hindi stopwords. Not exhaustive; just enough to keep
# clustering signal clean.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "at",
    "by", "with", "from", "as", "is", "are", "was", "were", "be", "been", "has",
    "have", "had", "will", "would", "can", "could", "should", "this", "that",
    "these", "those", "it", "its", "his", "her", "their", "our", "your", "you",
    "he", "she", "they", "we", "i", "not", "no", "yes", "new", "say", "says",
    "said", "after", "over", "into", "out", "up", "down", "more", "than",
    "ka", "ki", "ke", "ko", "se", "me", "mein", "hai", "ho", "par", "aur",
}


def tokens(text: str, min_len: int = 3) -> list[str]:
    out = []
    for w in _WORD_RE.findall(text.lower()):
        if len(w) >= min_len and w not in STOPWORDS:
            out.append(w)
    return out


def token_set(text: str, min_len: int = 3) -> set[str]:
    return set(tokens(text, min_len=min_len))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def top_terms(text: str, n: int = 8, min_len: int = 3) -> list[str]:
    counts = Counter(tokens(text, min_len=min_len))
    return [w for w, _ in counts.most_common(n)]
