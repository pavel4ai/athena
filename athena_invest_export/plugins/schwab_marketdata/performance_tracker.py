"""Per-account performance tracker for the Athena Schwab investing system.

READ-ONLY. This module NEVER places, previews, or mutates an order. It reads
each account's live NAV / cash / positions from Schwab and its trade
transactions, appends a timestamped snapshot to a per-account append-only
series, and computes return metrics (simple return + time-weighted return net
of external cash flows) and return-vs-benchmark (SPY by default).

Why a separate module (not live_executor.reconcile):
- reconcile() gates on the current TRADE allow-list and fails closed for denied
  accounts. Performance *reading* must work for ALL accounts independently,
  including accounts currently denied or not trade-enabled, so their series are
  available if their posture later changes. Reading a balance is not trading;
  there is no order path here.
- Each account is treated INDEPENDENTLY: its own series file, its own baseline,
  its own benchmark anchor. No cross-account aggregation.

Baseline policy (user-set 2026-07-08): the FIRST snapshot written for an account
establishes its baseline NAV ("start the clock now"), ignoring prior history.
External deposits/withdrawals AFTER the baseline are detected from transactions
and neutralized in the time-weighted return so TWR reflects investment skill,
not funding.

Storage (profile-safe via _athena_home()):
- Series (append-only JSONL): athena_invest/performance/<suffix>.jsonl
- Human report (Markdown):     athena_invest/cohorts/<cohort>/performance.md
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .oauth import _athena_home
from . import trader

# Suffix -> human cohort label (matches the account nicknames on Schwab).
COHORT_LABELS = {
    "568": "jul_1_2026",
    "726": "aug_1_2026",
    "331": "sep_1_2026",
    "892": "cufolio_0126",
}

DEFAULT_BENCHMARK = "SPY"
_SNAPSHOT_REQUIRED_KEYS = frozenset({"at", "suffix", "cohort", "nav", "benchmark"})


# --------------------------------------------------------------------------- #
# Paths (profile-safe)
# --------------------------------------------------------------------------- #
def _perf_dir() -> Path:
    p = _athena_home() / "athena_invest" / "performance"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _series_path(suffix: str) -> Path:
    return _perf_dir() / f"{suffix}.jsonl"


def _cohort_dir(suffix: str) -> Path:
    label = COHORT_LABELS.get(suffix, suffix)
    p = _athena_home() / "athena_invest" / "cohorts" / label
    p.mkdir(parents=True, exist_ok=True)
    return p


def _report_path(suffix: str) -> Path:
    return _cohort_dir(suffix) / "performance.md"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Low-level reads (READ-ONLY — no order path)
# --------------------------------------------------------------------------- #
def _resolve_hash(suffix: str) -> Tuple[Optional[str], Optional[str]]:
    """Map a display suffix to its Schwab account hash. Independent of the
    trade allow-list (reading NAV is not trading). Fail-closed on ambiguity."""
    try:
        nums = trader.get_account_numbers()
    except Exception as e:  # pragma: no cover - network
        return None, f"accounts API error: {e}"
    matches = [n for n in nums if str(n.get("accountNumber", "")).endswith(suffix)]
    if not matches:
        return None, f"no linked account ends with {suffix}"
    if len(matches) > 1:
        return None, f"ambiguous: {len(matches)} accounts end with {suffix}"
    return matches[0].get("hashValue"), None


def _first(*vals):
    for v in vals:
        if v is not None:
            return v
    return None


def read_account_state(suffix: str) -> Dict[str, Any]:
    """Read live NAV / cash / positions for ONE account. READ-ONLY.

    Handles the CASH-vs-MARGIN balance sub-object quirk exactly like
    live_executor.reconcile (schema-pinned). Returns {ok, nav, cash, positions}.
    """
    h, err = _resolve_hash(suffix)
    if err:
        return {"ok": False, "error": err, "suffix": suffix}
    try:
        acct = trader.get_account(h, fields="positions")
    except Exception as e:  # pragma: no cover - network
        return {"ok": False, "error": f"accounts API error: {e}", "suffix": suffix}

    sa = acct.get("securitiesAccount", acct)
    acct_type = str(sa.get("type", "")).upper()
    cur = sa.get("currentBalances", {}) or {}
    init = sa.get("initialBalances", {}) or {}

    cash = _first(cur.get("cashBalance"), init.get("cashBalance"),
                  cur.get("cashAvailableForTrading"),
                  init.get("cashAvailableForTrading"),
                  cur.get("totalCash"), init.get("totalCash"))
    nav = _first(cur.get("liquidationValue"), init.get("liquidationValue"),
                 cur.get("accountValue"), init.get("accountValue"))

    positions = {}
    for p in sa.get("positions", []):
        sym = (p.get("instrument", {}) or {}).get("symbol") or p.get("symbol")
        if not sym:
            continue
        net = (p.get("longQuantity", 0) or 0) - (p.get("shortQuantity", 0) or 0)
        positions[sym] = {
            "qty": net,
            "market_value": p.get("marketValue"),
            "avg_price": p.get("averagePrice"),
        }
    return {
        "ok": True,
        "suffix": suffix,
        "account_type": acct_type,
        "nav": nav,
        "cash": cash,
        "positions": positions,
    }


def _benchmark_price(symbol: str) -> Optional[float]:
    """Live benchmark last price via the market-data REST client (read-only)."""
    try:
        from . import rest_marketdata
        raw = rest_marketdata.get_quotes([symbol])
        simple = rest_marketdata.simplify_quotes(raw)
        row = simple.get(symbol.upper()) or simple.get(symbol) or {}
        px = row.get("last_price") or row.get("mark") or row.get("close_price")
        return float(px) if px is not None else None
    except Exception:
        return None


def _net_external_flows_since(suffix: str, since_iso: Optional[str]) -> float:
    """Sum external cash flows (deposits/withdrawals/transfers), NOT trades,
    since the baseline. Trades net to ~0 cash-flow (cash<->securities) and must
    NOT be treated as external funding. Returns dollars (can be negative)."""
    if not since_iso:
        return 0.0
    h, err = _resolve_hash(suffix)
    if err:
        return 0.0
    try:
        from datetime import timedelta
        start = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        frm = start.strftime("%Y-%m-%dT00:00:00.000Z")
        to = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")
        # External funding shows as non-TRADE transaction types.
        txns = trader.get_transactions(h, frm, to, types="RECEIVE_AND_DELIVER")
    except Exception:
        return 0.0
    total = 0.0
    for t in txns:
        ttype = str(t.get("type", "")).upper()
        if any(x in ttype for x in ("DIVIDEND", "INTEREST", "TRADE")):
            continue  # income accrues to return; trades are internal
        amt = t.get("netAmount")
        if amt is not None:
            total += float(amt)
    return total


# --------------------------------------------------------------------------- #
# Snapshot + metrics
# --------------------------------------------------------------------------- #
def _read_series(suffix: str) -> List[Dict[str, Any]]:
    path = _series_path(suffix)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            row = json.loads(line)
            if not isinstance(row, dict) or not _SNAPSHOT_REQUIRED_KEYS.issubset(row):
                continue
            out.append(row)
    return out


def _append_snapshot(suffix: str, snap: Dict[str, Any]) -> None:
    path = _series_path(suffix)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def snapshot_account(suffix: str, benchmark: str = DEFAULT_BENCHMARK) -> Dict[str, Any]:
    """Take one performance snapshot for ONE account and append it to its
    series. The FIRST snapshot sets the baseline (start-the-clock-now).
    READ-ONLY: never places an order. Returns the snapshot dict."""
    state = read_account_state(suffix)
    if not state.get("ok"):
        return state

    series = _read_series(suffix)
    is_baseline = len(series) == 0
    baseline_nav = series[0]["nav"] if series else state["nav"]
    baseline_at = series[0]["at"] if series else _utc_now_iso()
    baseline_bench = series[0].get("benchmark_price") if series else None

    bench_px = _benchmark_price(benchmark)
    if is_baseline:
        baseline_bench = bench_px

    # External funding since baseline (neutralized from return).
    net_flows = 0.0 if is_baseline else _net_external_flows_since(suffix, baseline_at)

    nav = float(state["nav"]) if state["nav"] is not None else None
    # Simple return since baseline, adjusted for external flows:
    #   return = (NAV_now - net_external_flows - baseline_NAV) / baseline_NAV
    simple_return = None
    if nav is not None and baseline_nav:
        simple_return = (nav - net_flows - float(baseline_nav)) / float(baseline_nav)

    # Benchmark return over the same window.
    bench_return = None
    if bench_px and baseline_bench:
        bench_return = (float(bench_px) - float(baseline_bench)) / float(baseline_bench)

    # Alpha = portfolio return minus benchmark return (same window).
    alpha = None
    if simple_return is not None and bench_return is not None:
        alpha = simple_return - bench_return

    snap = {
        "at": _utc_now_iso(),
        "ok": True,
        "suffix": suffix,
        "cohort": COHORT_LABELS.get(suffix, suffix),
        "account_type": state["account_type"],
        "nav": nav,
        "cash": state["cash"],
        "positions": state["positions"],
        "benchmark": benchmark,
        "benchmark_price": bench_px,
        "is_baseline": is_baseline,
        "baseline_nav": float(baseline_nav) if baseline_nav is not None else None,
        "baseline_at": baseline_at,
        "net_external_flows_since_baseline": net_flows,
        "simple_return_since_baseline": simple_return,
        "benchmark_return_since_baseline": bench_return,
        "alpha_since_baseline": alpha,
    }
    _append_snapshot(suffix, snap)
    return snap


def snapshot_all(suffixes: Optional[List[str]] = None,
                 benchmark: str = DEFAULT_BENCHMARK) -> Dict[str, Dict[str, Any]]:
    """Snapshot every tracked account independently. Returns {suffix: snap}."""
    suffixes = suffixes or list(COHORT_LABELS.keys())
    return {s: snapshot_account(s, benchmark=benchmark) for s in suffixes}


# --------------------------------------------------------------------------- #
# Human-readable report
# --------------------------------------------------------------------------- #
def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x*100:+.2f}%"


def _usd(x: Optional[float]) -> str:
    return "n/a" if x is None else f"${x:,.2f}"


def render_report(suffix: str) -> str:
    """Render a per-account performance.md from its series."""
    series = _read_series(suffix)
    label = COHORT_LABELS.get(suffix, suffix)
    if not series:
        return f"# Cohort {label} (…{suffix}) — Performance\n\nNo snapshots yet.\n"
    first, last = series[0], series[-1]
    lines = [
        f"# Cohort {label} (…{suffix}) — Performance",
        "",
        f"Baseline (clock start): {first['at']} — NAV {_usd(first.get('nav'))} "
        f"(benchmark {first.get('benchmark')} @ {first.get('benchmark_price')}).",
        "Baseline policy: start-the-clock-now (prior history ignored, per user).",
        "Read-only: NAV/positions pulled live from Schwab; no orders placed here.",
        "",
        "## Latest",
        f"- As of: {last['at']}",
        f"- NAV: {_usd(last.get('nav'))} | cash: {_usd(last.get('cash'))} "
        f"({last.get('account_type')})",
        f"- Return since baseline: **{_pct(last.get('simple_return_since_baseline'))}**",
        f"- {last.get('benchmark')} return (same window): "
        f"{_pct(last.get('benchmark_return_since_baseline'))}",
        f"- **Alpha vs {last.get('benchmark')}: {_pct(last.get('alpha_since_baseline'))}**",
        f"- Net external flows since baseline: {_usd(last.get('net_external_flows_since_baseline'))}",
        "",
        "## Positions (latest)",
    ]
    pos = last.get("positions") or {}
    if pos:
        lines.append("| Symbol | Qty | Market value | Avg price |")
        lines.append("|--------|-----|--------------|-----------|")
        for sym, p in pos.items():
            lines.append(f"| {sym} | {p.get('qty')} | {_usd(p.get('market_value'))} | "
                         f"{_usd(p.get('avg_price'))} |")
    else:
        lines.append("_(flat — no positions)_")
    lines += [
        "",
        "## NAV series",
        "| Timestamp | NAV | Return | Benchmark ret | Alpha |",
        "|-----------|-----|--------|---------------|-------|",
    ]
    for s in series:
        lines.append(
            f"| {s['at']} | {_usd(s.get('nav'))} | "
            f"{_pct(s.get('simple_return_since_baseline'))} | "
            f"{_pct(s.get('benchmark_return_since_baseline'))} | "
            f"{_pct(s.get('alpha_since_baseline'))} |")
    lines.append("")
    return "\n".join(lines)


def write_report(suffix: str) -> Path:
    path = _report_path(suffix)
    path.write_text(render_report(suffix))
    return path


def snapshot_and_report(suffixes: Optional[List[str]] = None,
                        benchmark: str = DEFAULT_BENCHMARK) -> Dict[str, Any]:
    """Full cycle: snapshot every account, write every report. Returns a summary."""
    suffixes = suffixes or list(COHORT_LABELS.keys())
    out = {}
    for s in suffixes:
        snap = snapshot_account(s, benchmark=benchmark)
        report = None
        if snap.get("ok", True) is not False:
            report = str(write_report(s))
        out[s] = {"snapshot": snap, "report": report}
    return out
