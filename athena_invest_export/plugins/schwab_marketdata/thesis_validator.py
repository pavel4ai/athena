"""Athena thesis-completeness validator (NOT a scorer).

Design principle (per user, 2026-06-27): the LLM is the decider. Investment
judgment — the lens reads, the 0-100 Athena Score, the stock/ETF mix, rebalance
yes/no, sizing — is made by the main model reasoning over each agent's system
prompt + past state + current state + performance history. This module does NOT
compute scores, does NOT enforce numeric floors, and does NOT decide anything.

It only checks COMPLETENESS of what the LLM produced, so the audit trail is
trustworthy: did the model address all five lenses, give each a rationale, state
a score with reasoning, and name an alpha source. Code validates the FORM of the
judgment; the model owns the SUBSTANCE.

The five lenses (reference/lenses.md) and the Athena Score weighting
(reference/athena_score.md) live in the agent PROMPTS as guidance the model
weighs — not as arithmetic here.
"""

from __future__ import annotations

from typing import Dict, List

# The five lenses every thesis must ADDRESS (guidance lives in the prompt;
# here we only check each was spoken to with a rationale).
LENSES = ("graham", "fabozzi", "hull_mcmillan", "chan", "macro")

# Stances the model may assign a lens. 'n/a' is allowed but still needs a reason
# (why this lens doesn't apply) — silence is not allowed; abstention must be stated.
_VALID_STANCE = {"supporting", "neutral", "against", "n/a"}


def validate_thesis(thesis: dict) -> dict:
    """Check an LLM-produced thesis for COMPLETENESS only. No scoring, no floor.

    Expected shape (all values are the MODEL's judgment, not computed here):
      {
        "ticker": "MU",
        "athena_score": 78,            # the LLM's score (0-100), its call
        "score_rationale": "...",      # why the model landed there
        "alpha_source": "information", # information|event|factor|beta + the model's words
        "lenses": {
           "graham":        {"stance": "supporting", "rationale": "..."},
           "fabozzi":       {"stance": "neutral",     "rationale": "..."},
           "hull_mcmillan": {"stance": "supporting", "rationale": "..."},
           "chan":          {"stance": "supporting", "rationale": "..."},
           "macro":         {"stance": "against",    "rationale": "..."}
        }
      }

    Returns {"complete": bool, "issues": [...]}. A True result means the model
    answered fully and auditably — NOT that the thesis is good (that's the
    model's and Sentinel's judgment) and NOT that it clears any threshold.
    """
    issues: List[str] = []
    tk = thesis.get("ticker", "<no-ticker>")

    if not thesis.get("ticker"):
        issues.append("missing ticker")

    # Score must be PRESENT (the model's number) and in range — but its VALUE is
    # the model's decision; we do not judge or floor it.
    score = thesis.get("athena_score")
    if score is None:
        issues.append(f"{tk}: missing athena_score (the model must state its score)")
    elif not isinstance(score, (int, float)) or not (0 <= score <= 100):
        issues.append(f"{tk}: athena_score must be a number 0-100, got {score!r}")
    if not (thesis.get("score_rationale") or "").strip():
        issues.append(f"{tk}: missing score_rationale (why the model chose that score)")

    if not (thesis.get("alpha_source") or "").strip():
        issues.append(f"{tk}: missing alpha_source (information|event|factor|beta + reasoning)")

    # All five lenses must be ADDRESSED with a stated stance + rationale.
    lenses = thesis.get("lenses") or {}
    for lens in LENSES:
        la = lenses.get(lens)
        if not la:
            issues.append(f"{tk}: lens '{lens}' not addressed (all five lenses must be spoken to)")
            continue
        stance = la.get("stance")
        if stance not in _VALID_STANCE:
            issues.append(f"{tk}: lens '{lens}' stance must be one of {sorted(_VALID_STANCE)}, got {stance!r}")
        if not (la.get("rationale") or "").strip():
            issues.append(f"{tk}: lens '{lens}' missing rationale (no silent lens — state the read or why n/a)")
    extra = [l for l in lenses if l not in LENSES]
    if extra:
        issues.append(f"{tk}: unknown lens key(s) {extra}; valid: {list(LENSES)}")

    return {
        "complete": not issues,
        "ticker": tk,
        "athena_score": score,
        "supporting_lenses": [l for l in LENSES
                              if (lenses.get(l) or {}).get("stance") == "supporting"],
        "issues": issues,
    }


def validate_book(theses: List[dict]) -> dict:
    """Run validate_thesis over a proposed book. Reports completeness per name.

    Does NOT pass/fail on scores or instrument mix — those are the model's call
    (and Sentinel's judgment). This only confirms every thesis is fully argued.
    """
    results = [validate_thesis(t) for t in theses]
    incomplete = [r for r in results if not r["complete"]]
    return {
        "all_complete": not incomplete,
        "n": len(results),
        "incomplete": [{"ticker": r["ticker"], "issues": r["issues"]} for r in incomplete],
        "results": results,
    }
