from pagalscientist.config import Settings
from pagalscientist.llm import LLMClient
from pagalscientist.models import Story
from pagalscientist.seo import generate_seo, rankmath_checklist
from pagalscientist.social import generate_social


def _settings():
    return Settings(raw={
        "seo": {"seo_title_max": 60, "meta_description_min": 120,
                "meta_description_max": 160, "secondary_keyword_count": 4},
        "social": {"caption_max_lines": 3, "hashtag_count": 5},
    })


def _story():
    body = ("Indian students in Australia are weighing new visa rules. " * 80)
    return Story.create(
        cluster_id="c1",
        headline="Indian students in Australia face new visa rules",
        dek="What the changes mean for the diaspora and universities.",
        body=body, tags=["visa"], credibility={}, sources=[],
        hook="A big change is coming for Indian students.",
    )


def test_rankmath_checklist_scores_a_well_formed_page():
    rm = rankmath_checklist(
        focus_keyword="indian students",
        seo_title="Indian students in Australia face new visa rules",
        meta_description="Indian students in Australia face new visa rules. "
                         "Here is what the changes mean for the diaspora today.",
        slug="indian-students-australia-visa-rules",
        body="Indian students in Australia " + ("word " * 700),
        title_max=60, meta_min=120, meta_max=160,
    )
    assert rm["checks"]["focus_keyword_in_title"]
    assert rm["checks"]["focus_keyword_in_intro"]
    assert rm["score"] >= 80


def test_generate_seo_produces_checkable_package_in_dry_run():
    seo = generate_seo(_story(), _settings(), llm=LLMClient("x", dry_run=True))
    assert seo["focus_keyword"]
    assert seo["slug"]
    assert "rankmath" in seo and seo["rankmath"]["total"] > 0
    assert len(seo["seo_title"]) <= 60


def test_social_caption_respects_line_limit_and_bans():
    soc = generate_social(_story(), _settings(), llm=LLMClient("x", dry_run=True))
    assert soc["cta"] in ("Explore the full story", "Discover what happened next",
                          "Read the full article")
    assert len([l for l in soc["caption"].splitlines() if l.strip()]) <= 3
    assert "sibling" not in soc["caption"].lower()
