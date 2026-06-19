from pagalscientist.cluster import cluster_articles
from pagalscientist.verify import score_cluster
from tests.conftest import make_article


def _cluster_and_index(arts, threshold=0.1):
    clusters = cluster_articles(arts, similarity_threshold=threshold)
    by_id = {a.id: a for a in arts}
    return clusters[0], by_id


def test_corroborated_official_story_scores_high():
    arts = [
        make_article("Budget allocates funds for rural roads",
                     "Government allocates funds for rural road building",
                     source="PIB", tier=1, hours_old=1),
        make_article("Rural roads get budget allocation funds",
                     "Funds allocated for rural roads in budget",
                     source="The Hindu", tier=1, hours_old=2),
    ]
    cluster, by_id = _cluster_and_index(arts)
    report = score_cluster(cluster, by_id, corroboration_for_auto=2)
    assert report.score >= 70
    assert report.recommendation == "fast_review"
    assert report.corroboration_count == 2


def test_single_low_tier_sensational_story_flagged():
    arts = [
        make_article("SHOCKING: viral video exposes secret miracle cure",
                     "You won't believe this viral rumour, sources say allegedly",
                     source="Aggregator", tier=3, hours_old=40),
    ]
    cluster, by_id = _cluster_and_index(arts)
    report = score_cluster(cluster, by_id)
    assert "single_source" in report.flags
    assert "sensational_language" in report.flags
    assert "unverified_claim_markers" in report.flags
    assert report.recommendation in ("hold", "review")
    assert report.score < 70


def test_recency_penalizes_old_news():
    fresh = score_cluster(*_cluster_and_index([
        make_article("Petrol prices revised across India today",
                     "Fuel prices changed nationwide", source="PIB", tier=1,
                     hours_old=1),
    ]), recency_half_life_hours=18)
    stale = score_cluster(*_cluster_and_index([
        make_article("Petrol prices revised across India today",
                     "Fuel prices changed nationwide", source="PIB", tier=1,
                     hours_old=200),
    ]), recency_half_life_hours=18)
    assert fresh.score > stale.score
