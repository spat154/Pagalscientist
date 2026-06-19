"""End-to-end pipeline + review/publish, fully offline (dry-run LLM, no feeds)."""
from pagalscientist.config import Settings
from pagalscientist.llm import LLMClient
from pagalscientist.models import StoryStatus
from pagalscientist.pipeline import Pipeline
from pagalscientist.review import approve, publish_story
from pagalscientist.store import Store
from tests.conftest import make_article


def _settings(tmp_out):
    return Settings(raw={
        "audience": {"description": "Middle India", "reading_level": "simple"},
        "clustering": {"similarity_threshold": 0.15, "min_token_length": 3},
        "verification": {"corroboration_for_auto": 2, "min_score_to_draft": 40,
                         "trust_recommend_threshold": 70, "recency_half_life_hours": 18},
        "generation": {"target_word_count": 400, "max_tokens": 500},
        "publishing": {"stage_as_draft": True, "default_targets": ["console"]},
    })


def test_full_pipeline_drafts_then_publishes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)            # console publisher writes to ./out
    store = Store(":memory:")
    settings = _settings(tmp_path)
    dry_llm = LLMClient("test-model", dry_run=True)

    # Seed corroborated articles directly (skip the network ingest stage).
    store.add_new_articles([
        make_article("MSME credit scheme launched for small traders",
                     "Government launches credit guarantee for MSME traders",
                     source="PIB", tier=1, hours_old=1),
        make_article("New MSME credit scheme announced for traders",
                     "Small traders to get loan guarantee under MSME scheme",
                     source="Mint", tier=2, hours_old=2),
    ])

    pipe = Pipeline(store, settings=settings, sources=[], llm=dry_llm)
    assert pipe.cluster() == 1
    drafts = pipe.draft_pending()
    assert len(drafts) == 1

    story = drafts[0]
    assert story.status == StoryStatus.NEEDS_REVIEW.value
    assert story.credibility["score"] >= 40
    assert len(story.sources) == 2

    # Cannot publish before approval.
    try:
        publish_story(store, story.id, settings)
        assert False, "should refuse to publish unapproved story"
    except ValueError:
        pass

    approve(store, story.id)
    results = publish_story(store, story.id, settings)
    assert all(r.ok for r in results)
    assert store.get_story(story.id).status == StoryStatus.PUBLISHED.value


def test_pipeline_skips_already_drafted_clusters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(":memory:")
    settings = _settings(tmp_path)
    dry_llm = LLMClient("test-model", dry_run=True)
    store.add_new_articles([
        make_article("Petrol price cut announced across India",
                     "Fuel prices reduced nationwide by government",
                     source="PIB", tier=1, hours_old=1),
        make_article("Petrol price cut announced nationwide today",
                     "Government reduces fuel prices across India",
                     source="The Hindu", tier=1, hours_old=2),
    ])
    pipe = Pipeline(store, settings=settings, sources=[], llm=dry_llm)
    pipe.cluster()
    assert len(pipe.draft_pending()) == 1
    assert len(pipe.draft_pending()) == 0  # idempotent: no duplicate drafts
