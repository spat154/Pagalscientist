"""Group related articles into story clusters and surface patterns.

This is how the desk finds "connecting angles": articles from different sources
about the same underlying event collapse into one cluster, and the count of
distinct sources becomes a corroboration signal for verification.

Pure standard-library logic (single-link agglomerative clustering on token
overlap), so it is fully testable offline.
"""
from __future__ import annotations

from collections import Counter

from .models import Article, Cluster, make_id, now_iso
from .text import jaccard, token_set, top_terms


def _build_signature(article: Article, min_len: int) -> set[str]:
    return token_set(article.text, min_len=min_len)


def cluster_articles(
    articles: list[Article],
    *,
    similarity_threshold: float = 0.18,
    min_token_length: int = 3,
) -> list[Cluster]:
    """Single-link clustering: an article joins a cluster if it is similar
    enough to ANY member. Returns clusters built from the given articles only.
    """
    sigs = {a.id: _build_signature(a, min_token_length) for a in articles}
    by_id = {a.id: a for a in articles}

    groups: list[list[str]] = []
    for art in articles:
        placed = False
        for group in groups:
            if any(
                jaccard(sigs[art.id], sigs[mid]) >= similarity_threshold
                for mid in group
            ):
                group.append(art.id)
                placed = True
                break
        if not placed:
            groups.append([art.id])

    clusters: list[Cluster] = []
    for group in groups:
        members = [by_id[i] for i in group]
        # Lead article = highest trust tier (tier 1 is best), tie-break newest.
        lead = sorted(members, key=lambda a: (a.source_tier, _neg_time(a)))[0]
        combined = " ".join(m.text for m in members)
        terms = top_terms(combined, n=8, min_len=min_token_length)
        sources = [m.source for m in members]
        cluster_id = make_id(*sorted(group))
        clusters.append(
            Cluster(
                id=cluster_id,
                article_ids=group,
                key_terms=terms,
                sources=sources,
                lead_article_id=lead.id,
                created_at=now_iso(),
            )
        )
    return clusters


def _neg_time(article: Article) -> str:
    # Sort helper: invert ISO timestamps so "newest first" works with min().
    return "".join(chr(255 - ord(c)) if c.isascii() else c for c in article.published)


def rank_clusters(clusters: list[Cluster], articles_by_id: dict[str, Article]) -> list[Cluster]:
    """Order clusters by newsworthiness for the Middle India desk.

    Score blends corroboration (distinct sources), source trust, and how
    strongly the contributing sources skew to our audience.
    """
    def score(cluster: Cluster) -> float:
        members = [articles_by_id[i] for i in cluster.article_ids if i in articles_by_id]
        if not members:
            return 0.0
        corroboration = cluster.corroboration
        best_tier = min(m.source_tier for m in members)          # 1 best
        tier_bonus = {1: 1.0, 2: 0.6, 3: 0.3}.get(best_tier, 0.3)
        audience = max(m.audience_weight for m in members)
        return corroboration * 2.0 + tier_bonus + audience

    return sorted(clusters, key=score, reverse=True)


def pattern_summary(clusters: list[Cluster]) -> list[dict]:
    """Cross-cluster pattern detection: which themes are bubbling up across
    multiple distinct stories right now. Feeds the editor's "what's trending"
    view and the generator's angle-finding.
    """
    term_counts: Counter[str] = Counter()
    term_clusters: dict[str, set[str]] = {}
    for c in clusters:
        for term in c.key_terms:
            term_counts[term] += 1
            term_clusters.setdefault(term, set()).add(c.id)
    patterns = []
    for term, count in term_counts.most_common(15):
        if len(term_clusters[term]) >= 2:  # appears across >=2 separate stories
            patterns.append({
                "term": term,
                "story_count": len(term_clusters[term]),
                "cluster_ids": sorted(term_clusters[term]),
            })
    return patterns
