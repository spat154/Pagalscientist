from pagalscientist.config import Settings
from pagalscientist.llm import LLMClient
from pagalscientist.pipeline import Pipeline
from pagalscientist.store import Store


def _settings():
    return Settings(raw={
        "audience": {"description": "Indian-Australian community", "reading_level": "x"},
        "clustering": {"similarity_threshold": 0.15, "min_token_length": 3},
        "verification": {"corroboration_for_auto": 2, "references_per_claim": 3,
                         "recency_half_life_hours": 18},
        "generation": {"target_word_count": 400, "max_tokens": 500,
                       "min_lines_per_entity": 5},
    })


def test_commission_from_supplied_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = Store(":memory:")
    pipe = Pipeline(store, settings=_settings(), sources=[],
                    llm=LLMClient("x", dry_run=True))
    sources = [
        {"source": "DFAT", "title": "India Australia trade deal expands",
         "summary": "New tariff cuts announced for goods.", "tier": 1,
         "link": "https://example.gov.au/1"},
        {"source": "The Hindu", "title": "ECTA expansion details",
         "summary": "More sectors covered under the trade agreement.", "tier": 1,
         "link": "https://thehindu.com/2"},
    ]
    story = pipe.commission(sources, direction="Focus on what it means for "
                            "Indian-owned small businesses in Australia.")
    assert story.headline
    assert len(story.sources) == 2
    # Compliance + reference checks must be attached.
    assert "style" in story.compliance
    assert "references" in story.compliance
    # The story is persisted and retrievable.
    assert store.get_story(story.id) is not None
