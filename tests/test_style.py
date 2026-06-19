from pagalscientist.style import (auto_fix_spellings, compliance_report,
                                   hedge_triggers, lint_text)


def test_flags_banned_words_and_phrases():
    text = "This innovation will revolutionize the landscape, a real game changer."
    kinds = {v.kind for v in lint_text(text)}
    terms = {v.term for v in lint_text(text)}
    assert "banned_word" in kinds
    assert "innovation" in terms and "landscape" in terms


def test_flags_em_dash():
    v = lint_text("Migration is up — sharply.")
    assert any(x.kind == "em_dash" for x in v)


def test_flags_not_x_its_y_structure():
    v = lint_text("It's not about the visa, it's about belonging.")
    assert any(x.kind == "not_x_its_y" for x in v)


def test_flags_us_spelling_with_au_suggestion():
    v = [x for x in lint_text("They optimized the colorful organization.")
         if x.kind == "au_spelling"]
    terms = {x.term for x in v}
    assert {"optimized", "organization"}.issubset(terms)
    assert any("optimise" in x.suggestion for x in v)


def test_auto_fix_applies_au_spellings():
    fixed = auto_fix_spellings("We optimized and organized the center.")
    assert "optimised" in fixed and "organised" in fixed and "centre" in fixed
    assert "optimized" not in fixed


def test_clean_text_passes():
    report = compliance_report("Indian students in Australia welcomed the update.")
    assert report["clean"] is True
    assert report["violation_count"] == 0


def test_hedge_triggers_detected():
    assert "guarantee" in hedge_triggers("This will guarantee a better outcome.")
