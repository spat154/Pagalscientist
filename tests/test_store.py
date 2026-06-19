from pagalscientist.cluster import cluster_articles
from pagalscientist.models import Story, StoryStatus
from pagalscientist.store import Store
from tests.conftest import make_article


def test_dedupes_articles_on_reingest():
    store = Store(":memory:")
    arts = [make_article("Same story", "same body", link="https://x/1")]
    assert len(store.add_new_articles(arts)) == 1
    assert len(store.add_new_articles(arts)) == 0  # already seen
    assert len(store.all_articles()) == 1


def test_cluster_backref_set_on_articles():
    store = Store(":memory:")
    arts = [
        make_article("MSME scheme launched for traders", "credit guarantee"),
        make_article("MSME scheme launched for traders today", "credit guarantee"),
    ]
    store.add_new_articles(arts)
    clusters = cluster_articles(store.unclustered_articles(), similarity_threshold=0.1)
    for c in clusters:
        store.upsert_cluster(c)
    assert store.unclustered_articles() == []  # all now have a cluster_id


def test_story_status_queries():
    store = Store(":memory:")
    story = Story.create(cluster_id="c1", headline="H", dek="d", body="b",
                         tags=["t"], credibility={"score": 80}, sources=[])
    store.upsert_story(story)
    assert len(store.stories_by_status(StoryStatus.NEEDS_REVIEW)) == 1
    story.status = StoryStatus.APPROVED.value
    store.upsert_story(story)
    assert store.stories_by_status(StoryStatus.NEEDS_REVIEW) == []
    assert len(store.stories_by_status(StoryStatus.APPROVED)) == 1
    assert store.cluster_has_story("c1") is True
