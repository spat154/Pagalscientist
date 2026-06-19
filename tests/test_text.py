from pagalscientist.text import jaccard, token_set, tokens, top_terms


def test_tokens_drops_stopwords_and_short_words():
    out = tokens("The new MSME scheme is for small business owners")
    assert "the" not in out and "is" not in out and "for" not in out
    assert "msme" in out and "scheme" in out and "business" in out


def test_jaccard_identical_and_disjoint():
    a = token_set("MSME loan scheme launched for traders")
    b = token_set("MSME loan scheme launched for traders")
    assert jaccard(a, b) == 1.0
    c = token_set("cricket match rain delay mumbai")
    assert jaccard(a, c) == 0.0


def test_top_terms_orders_by_frequency():
    terms = top_terms("rupee rupee rupee dollar dollar euro", n=3)
    assert terms[0] == "rupee"
