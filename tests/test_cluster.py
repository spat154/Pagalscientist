from pagalscientist.cluster import cluster_articles, pattern_summary, rank_clusters
from tests.conftest import make_article


def test_similar_articles_cluster_together():
    arts = [
        make_article("MSME loan scheme launched for small traders",
                     "Government announces credit guarantee for MSME traders",
                     source="PIB", tier=1),
        make_article("New MSME credit scheme for traders announced",
                     "Small traders get loan guarantee under new MSME scheme",
                     source="Mint", tier=2),
        make_article("Mumbai rains disrupt local trains today",
                     "Heavy rainfall floods tracks across Mumbai",
                     source="NDTV", tier=2),
    ]
    clusters = cluster_articles(arts, similarity_threshold=0.18)
    sizes = sorted(len(c.article_ids) for c in clusters)
    assert sizes == [1, 2]  # MSME pair clusters, rain story alone


def test_lead_article_prefers_higher_trust_tier():
    arts = [
        make_article("Scheme launched for traders", "credit guarantee msme",
                     source="Aggregator", tier=3),
        make_article("Scheme launched for traders today", "credit guarantee msme",
                     source="PIB", tier=1),
    ]
    clusters = cluster_articles(arts, similarity_threshold=0.18)
    assert len(clusters) == 1
    lead = clusters[0].lead_article_id
    lead_art = next(a for a in arts if a.id == lead)
    assert lead_art.source_tier == 1


def test_corroboration_counts_distinct_sources():
    arts = [
        make_article("MSME scheme for traders launched", "credit guarantee",
                     source="PIB", tier=1),
        make_article("MSME scheme for traders launched now", "credit guarantee",
                     source="Mint", tier=2),
    ]
    clusters = cluster_articles(arts, similarity_threshold=0.1)
    assert clusters[0].corroboration == 2


def test_pattern_summary_finds_cross_story_themes():
    arts = [
        make_article("MSME scheme one", "msme credit traders", source="A", tier=1),
        make_article("Totally different cricket story", "cricket match", source="B"),
        make_article("MSME factory news", "msme manufacturing jobs", source="C"),
    ]
    clusters = cluster_articles(arts, similarity_threshold=0.5)
    patterns = pattern_summary(clusters)
    terms = {p["term"] for p in patterns}
    assert "msme" in terms  # appears across the two separate msme clusters
