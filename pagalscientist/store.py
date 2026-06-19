"""SQLite persistence for articles, clusters and stories.

Keeps the pipeline idempotent: re-running ingest does not create duplicate
articles, and the review queue survives restarts. Standard library only.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Article, Cluster, Story, StoryStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    source TEXT,
    published TEXT,
    cluster_id TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clusters (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    cluster_id TEXT,
    status TEXT,
    updated_at TEXT,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_cluster ON articles(cluster_id);
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- articles --------------------------------------------------------
    def has_article(self, article_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM articles WHERE id = ?", (article_id,))
        return cur.fetchone() is not None

    def upsert_article(self, article: Article) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO articles (id, source, published, cluster_id, data) "
            "VALUES (?, ?, ?, ?, ?)",
            (article.id, article.source, article.published, article.cluster_id,
             json.dumps(article.to_dict())),
        )
        self.conn.commit()

    def add_new_articles(self, articles: Iterable[Article]) -> list[Article]:
        """Insert only articles we have not seen; return the freshly added ones."""
        added = []
        for art in articles:
            if not self.has_article(art.id):
                self.upsert_article(art)
                added.append(art)
        return added

    def get_article(self, article_id: str) -> Article | None:
        row = self.conn.execute(
            "SELECT data FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return Article.from_dict(json.loads(row["data"])) if row else None

    def unclustered_articles(self) -> list[Article]:
        rows = self.conn.execute(
            "SELECT data FROM articles WHERE cluster_id IS NULL"
        ).fetchall()
        return [Article.from_dict(json.loads(r["data"])) for r in rows]

    def all_articles(self) -> list[Article]:
        rows = self.conn.execute("SELECT data FROM articles").fetchall()
        return [Article.from_dict(json.loads(r["data"])) for r in rows]

    # --- clusters --------------------------------------------------------
    def upsert_cluster(self, cluster: Cluster) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO clusters (id, created_at, data) VALUES (?, ?, ?)",
            (cluster.id, cluster.created_at, json.dumps(cluster.to_dict())),
        )
        # keep the article -> cluster backref in sync
        for aid in cluster.article_ids:
            self.conn.execute(
                "UPDATE articles SET cluster_id = ? WHERE id = ?", (cluster.id, aid)
            )
        self.conn.commit()

    def get_cluster(self, cluster_id: str) -> Cluster | None:
        row = self.conn.execute(
            "SELECT data FROM clusters WHERE id = ?", (cluster_id,)
        ).fetchone()
        return Cluster.from_dict(json.loads(row["data"])) if row else None

    def all_clusters(self) -> list[Cluster]:
        rows = self.conn.execute("SELECT data FROM clusters").fetchall()
        return [Cluster.from_dict(json.loads(r["data"])) for r in rows]

    def cluster_has_story(self, cluster_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM stories WHERE cluster_id = ?", (cluster_id,)
        )
        return cur.fetchone() is not None

    # --- stories ---------------------------------------------------------
    def upsert_story(self, story: Story) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO stories (id, cluster_id, status, updated_at, data) "
            "VALUES (?, ?, ?, ?, ?)",
            (story.id, story.cluster_id, story.status, story.updated_at,
             json.dumps(story.to_dict())),
        )
        self.conn.commit()

    def get_story(self, story_id: str) -> Story | None:
        row = self.conn.execute(
            "SELECT data FROM stories WHERE id = ?", (story_id,)
        ).fetchone()
        return Story.from_dict(json.loads(row["data"])) if row else None

    def stories_by_status(self, status: str | StoryStatus) -> list[Story]:
        status = status.value if isinstance(status, StoryStatus) else status
        rows = self.conn.execute(
            "SELECT data FROM stories WHERE status = ? ORDER BY updated_at DESC",
            (status,),
        ).fetchall()
        return [Story.from_dict(json.loads(r["data"])) for r in rows]

    def all_stories(self) -> list[Story]:
        rows = self.conn.execute(
            "SELECT data FROM stories ORDER BY updated_at DESC"
        ).fetchall()
        return [Story.from_dict(json.loads(r["data"])) for r in rows]
