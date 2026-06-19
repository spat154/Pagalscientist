"""Orchestrates the desk: ingest -> cluster -> verify -> generate.

Publishing is deliberately a separate, human-triggered step (see review.py).
The pipeline only ever produces drafts in the NEEDS_REVIEW state.
"""
from __future__ import annotations

import logging

from .cluster import cluster_articles, pattern_summary, rank_clusters
from .config import Settings, load_settings, load_sources
from .generate import generate_story
from .ingest import fetch_all
from .llm import LLMClient
from .store import Store
from .verify import score_cluster

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, store: Store, settings: Settings | None = None,
                 sources=None, llm: LLMClient | None = None):
        self.store = store
        self.settings = settings or load_settings()
        self.sources = sources if sources is not None else load_sources()
        self.llm = llm

    # --- stage 1: sense --------------------------------------------------
    def ingest(self, limit_per_source: int = 25) -> int:
        articles = fetch_all(self.sources, limit_per_source=limit_per_source)
        added = self.store.add_new_articles(articles)
        log.info("Ingest: %d fetched, %d new", len(articles), len(added))
        return len(added)

    # --- stage 2: cluster + patterns ------------------------------------
    def cluster(self) -> int:
        cfg = self.settings.clustering
        pending = self.store.unclustered_articles()
        if not pending:
            return 0
        clusters = cluster_articles(
            pending,
            similarity_threshold=cfg.get("similarity_threshold", 0.18),
            min_token_length=cfg.get("min_token_length", 3),
        )
        for c in clusters:
            self.store.upsert_cluster(c)
        log.info("Cluster: %d articles -> %d clusters", len(pending), len(clusters))
        return len(clusters)

    # --- stage 3 + 4: verify + draft ------------------------------------
    def draft_pending(self, max_stories: int | None = None) -> list:
        vcfg = self.settings.verification
        articles_by_id = {a.id: a for a in self.store.all_articles()}
        clusters = self.store.all_clusters()
        patterns = pattern_summary(clusters)
        ranked = rank_clusters(clusters, articles_by_id)

        min_draft = vcfg.get("min_score_to_draft", 45)
        created = []
        for cluster in ranked:
            if max_stories is not None and len(created) >= max_stories:
                break
            if self.store.cluster_has_story(cluster.id):
                continue
            report = score_cluster(
                cluster, articles_by_id,
                corroboration_for_auto=vcfg.get("corroboration_for_auto", 2),
                trust_recommend_threshold=vcfg.get("trust_recommend_threshold", 70),
                recency_half_life_hours=vcfg.get("recency_half_life_hours", 18),
            )
            if report.score < min_draft:
                log.info("Skip cluster %s: score %.1f < %.1f",
                         cluster.id, report.score, min_draft)
                continue
            story = generate_story(
                cluster, articles_by_id, report.to_dict(), self.settings,
                llm=self.llm, patterns=patterns,
            )
            self.store.upsert_cluster(cluster)   # persist the angle
            self.store.upsert_story(story)
            created.append(story)
            log.info("Drafted story %s (score %.1f) for cluster %s",
                     story.id, report.score, cluster.id)
        return created

    # --- commission: editor supplies sources + a direction --------------
    def commission(self, sources: list[dict], *, direction: str = "",
                   references: list[str] | None = None):
        """Create a draft from supplied sources instead of sensed feeds.

        `sources` is a list of dicts: {source, title, summary, link, tier?}.
        This is the "Create Article" function from the brief: hand it material
        and a direction, get back a draft scored and compliance-checked.
        """
        from .cluster import cluster_articles
        from .models import Article

        articles = []
        for s in sources:
            articles.append(Article.create(
                source=s.get("source", "supplied"),
                source_tier=int(s.get("tier", 2)),
                audience_weight=float(s.get("audience_weight", 0.9)),
                title=s.get("title", ""),
                summary=s.get("summary", ""),
                link=s.get("link", ""),
                published=s.get("published", ""),
            ))
        self.store.add_new_articles(articles)
        clusters = cluster_articles(
            articles,
            similarity_threshold=self.settings.clustering.get("similarity_threshold", 0.18),
            min_token_length=self.settings.clustering.get("min_token_length", 3),
        )
        # Treat all supplied material as one commissioned story.
        merged = clusters[0]
        merged.article_ids = [a.id for a in articles]
        merged.sources = [a.source for a in articles]
        articles_by_id = {a.id: a for a in articles}

        report = score_cluster(
            merged, articles_by_id,
            corroboration_for_auto=self.settings.verification.get("corroboration_for_auto", 2),
            recency_half_life_hours=self.settings.verification.get("recency_half_life_hours", 18),
        )
        story = generate_story(
            merged, articles_by_id, report.to_dict(), self.settings,
            llm=self.llm, direction=direction, references=references,
        )
        self.store.upsert_cluster(merged)
        self.store.upsert_story(story)
        return story

    # --- convenience: run everything up to drafting ---------------------
    def run(self, limit_per_source: int = 25, max_stories: int | None = None) -> dict:
        n_new = self.ingest(limit_per_source=limit_per_source)
        n_clusters = self.cluster()
        drafts = self.draft_pending(max_stories=max_stories)
        return {
            "new_articles": n_new,
            "clusters_built": n_clusters,
            "drafts_created": len(drafts),
            "draft_ids": [s.id for s in drafts],
        }
