import json

from pagalscientist.config import Settings
from pagalscientist.models import Story
from pagalscientist.schema import build_jsonld, schema_summary, to_script_tag


def _settings():
    return Settings(raw={
        "publication": {"name": "Made in India Magazine", "author": "A. Editor"},
        "publishing": {"category": "Made in India Magazine",
                       "site_url": "https://madeinindiamagazine.com.au"},
    })


def _story(**kw):
    base = dict(cluster_id="c1", headline="Indian students face new visa rules",
                dek="What the changes mean.", body="Body text.", tags=["visa"],
                credibility={}, sources=[{"name": "DFAT", "link": "https://x.gov.au/1"}])
    base.update(kw)
    return Story.create(**base)


def test_build_jsonld_has_article_and_org():
    g = build_jsonld(_story(), _settings(), url="https://m.com.au/post")
    types = [n["@type"] for n in g["@graph"]]
    assert "NewsArticle" in types and "Organization" in types
    article = next(n for n in g["@graph"] if n["@type"] == "NewsArticle")
    assert article["inLanguage"] == "en-AU"
    assert article["author"]["name"] == "A. Editor"
    assert article["citation"] == ["https://x.gov.au/1"]


def test_faq_becomes_faqpage_schema():
    story = _story(faq=[{"question": "When?", "answer": "In July 2026."}])
    g = build_jsonld(story, _settings())
    faq = next((n for n in g["@graph"] if n["@type"] == "FAQPage"), None)
    assert faq is not None
    assert faq["mainEntity"][0]["acceptedAnswer"]["text"] == "In July 2026."
    assert schema_summary(g)["has_faq"] is True


def test_event_like_stories_are_flagged_not_auto_emitted():
    concert = _story(headline="Rahat Fateh Ali Khan live concert in Sydney")
    g = build_jsonld(concert, _settings())
    # We never auto-emit Event schema (needs verified date/venue)...
    assert "Event" not in [n["@type"] for n in g["@graph"]]
    # ...but we flag it so an editor can add verified details.
    assert schema_summary(g, concert)["event_candidate"] is True
    plain = _story(headline="What the visa changes mean for families")
    assert schema_summary(build_jsonld(plain, _settings()), plain)["event_candidate"] is False


def test_script_tag_is_valid_json():
    tag = to_script_tag(build_jsonld(_story(), _settings()))
    assert tag.startswith('<script type="application/ld+json">')
    inner = tag[len('<script type="application/ld+json">'):-len("</script>")]
    json.loads(inner)  # must parse
