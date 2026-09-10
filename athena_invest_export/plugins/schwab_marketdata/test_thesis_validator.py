"""Tests for the thesis-completeness validator (form-only; no scoring logic)."""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from schwab_marketdata import thesis_validator as V  # noqa: E402


def _full_lenses():
    return {l: {"stance": "neutral", "rationale": "addressed"} for l in V.LENSES}


def _good_thesis():
    return {
        "ticker": "MU",
        "athena_score": 78,
        "score_rationale": "strong memory cycle vs macro headwind",
        "alpha_source": "information: memory decouple",
        "lenses": _full_lenses(),
    }


def test_complete_thesis_passes():
    r = V.validate_thesis(_good_thesis())
    assert r["complete"] is True and r["issues"] == []


def test_missing_lens_flagged():
    t = _good_thesis(); del t["lenses"]["macro"]
    r = V.validate_thesis(t)
    assert not r["complete"]
    assert any("macro" in i and "not addressed" in i for i in r["issues"])


def test_silent_lens_rationale_flagged():
    t = _good_thesis(); t["lenses"]["chan"] = {"stance": "supporting", "rationale": ""}
    r = V.validate_thesis(t)
    assert not r["complete"]
    assert any("chan" in i and "rationale" in i for i in r["issues"])


def test_missing_score_flagged_but_value_not_judged():
    t = _good_thesis(); t["athena_score"] = None
    r = V.validate_thesis(t)
    assert not r["complete"] and any("missing athena_score" in i for i in r["issues"])


def test_low_score_is_NOT_a_failure():
    # The validator must NOT reject a low score — value is the model's call.
    t = _good_thesis(); t["athena_score"] = 12
    r = V.validate_thesis(t)
    assert r["complete"] is True  # complete; no floor enforced


def test_missing_alpha_source_flagged():
    t = _good_thesis(); t["alpha_source"] = ""
    r = V.validate_thesis(t)
    assert not r["complete"] and any("alpha_source" in i for i in r["issues"])


def test_bad_stance_flagged():
    t = _good_thesis(); t["lenses"]["graham"] = {"stance": "bullish", "rationale": "x"}
    r = V.validate_thesis(t)
    assert not r["complete"] and any("stance" in i for i in r["issues"])


def test_na_stance_allowed_with_reason():
    t = _good_thesis(); t["lenses"]["graham"] = {"stance": "n/a", "rationale": "no earnings; gold"}
    r = V.validate_thesis(t)
    assert r["complete"] is True


def test_validate_book_reports_incomplete():
    good = _good_thesis()
    bad = _good_thesis(); bad["ticker"] = "XYZ"; del bad["lenses"]["fabozzi"]
    out = V.validate_book([good, bad])
    assert out["all_complete"] is False and out["n"] == 2
    assert out["incomplete"][0]["ticker"] == "XYZ"


def test_supporting_lenses_reported_not_scored():
    t = _good_thesis()
    t["lenses"]["chan"]["stance"] = "supporting"
    t["lenses"]["macro"]["stance"] = "supporting"
    r = V.validate_thesis(t)
    assert set(r["supporting_lenses"]) == {"chan", "macro"}
