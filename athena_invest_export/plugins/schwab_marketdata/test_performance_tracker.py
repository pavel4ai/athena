"""Tests for the per-account performance tracker (READ-ONLY, no network).

Trader + market-data are mocked. Verifies: baseline sets the clock, simple
return + benchmark alpha compute correctly, external flows are neutralized from
return, accounts are independent, and no order path is ever touched.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def pt(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHENA_HOME", str(tmp_path / ".athena"))
    from schwab_marketdata import performance_tracker as _pt
    importlib.reload(_pt)
    return _pt


def _acct_payload(nav, cash, positions=None):
    """Build a CASH-account get_account response (balances on initialBalances)."""
    poss = []
    for sym, (qty, mv, ap) in (positions or {}).items():
        poss.append({"instrument": {"symbol": sym}, "longQuantity": qty,
                     "shortQuantity": 0, "marketValue": mv, "averagePrice": ap})
    return {"securitiesAccount": {
        "type": "CASH",
        "initialBalances": {"liquidationValue": nav, "cashBalance": cash},
        "currentBalances": {"cashAvailableForTrading": cash},
        "positions": poss,
    }}


def test_baseline_sets_clock_and_zero_return(pt):
    with mock.patch.object(pt.trader, "get_account_numbers",
                           return_value=[{"accountNumber": "75812568", "hashValue": "H568"}]), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(10000.0, 10000.0)), \
         mock.patch.object(pt, "_benchmark_price", return_value=750.0):
        snap = pt.snapshot_account("568")
    assert snap["ok"]
    assert snap["is_baseline"] is True
    assert snap["baseline_nav"] == 10000.0
    # On the baseline day return is exactly 0.
    assert snap["simple_return_since_baseline"] == 0.0
    assert snap["benchmark_return_since_baseline"] == 0.0
    assert snap["alpha_since_baseline"] == 0.0


def test_second_snapshot_computes_return_and_alpha(pt):
    gan = [{"accountNumber": "75812568", "hashValue": "H568"}]
    # 1) baseline: NAV 10000, SPY 750
    with mock.patch.object(pt.trader, "get_account_numbers", return_value=gan), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(10000.0, 10000.0)), \
         mock.patch.object(pt, "_benchmark_price", return_value=750.0):
        pt.snapshot_account("568")
    # 2) later: NAV 10500 (+5%), SPY 765 (+2%), no external flows
    with mock.patch.object(pt.trader, "get_account_numbers", return_value=gan), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(10500.0, 500.0,
                                                      {"SPY": (13.0, 10000.0, 749.0)})), \
         mock.patch.object(pt, "_benchmark_price", return_value=765.0), \
         mock.patch.object(pt, "_net_external_flows_since", return_value=0.0):
        snap = pt.snapshot_account("568")
    assert snap["is_baseline"] is False
    assert snap["simple_return_since_baseline"] == pytest.approx(0.05)
    assert snap["benchmark_return_since_baseline"] == pytest.approx(0.02)
    assert snap["alpha_since_baseline"] == pytest.approx(0.03)


def test_external_flows_neutralized(pt):
    gan = [{"accountNumber": "75812568", "hashValue": "H568"}]
    with mock.patch.object(pt.trader, "get_account_numbers", return_value=gan), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(10000.0, 10000.0)), \
         mock.patch.object(pt, "_benchmark_price", return_value=750.0):
        pt.snapshot_account("568")
    # NAV rose to 15000 but 5000 of that is a DEPOSIT -> real return is 0%.
    with mock.patch.object(pt.trader, "get_account_numbers", return_value=gan), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(15000.0, 15000.0)), \
         mock.patch.object(pt, "_benchmark_price", return_value=750.0), \
         mock.patch.object(pt, "_net_external_flows_since", return_value=5000.0):
        snap = pt.snapshot_account("568")
    assert snap["simple_return_since_baseline"] == pytest.approx(0.0)


def test_accounts_are_independent(pt):
    def _gan():
        return [{"accountNumber": "75812568", "hashValue": "H568"},
                {"accountNumber": "42429726", "hashValue": "H726"}]
    with mock.patch.object(pt.trader, "get_account_numbers", side_effect=_gan), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(10000.0, 10000.0)), \
         mock.patch.object(pt, "_benchmark_price", return_value=750.0):
        pt.snapshot_account("568")
        pt.snapshot_account("726")
    # Separate series files, one baseline each.
    assert pt._series_path("568").exists()
    assert pt._series_path("726").exists()
    assert len(pt._read_series("568")) == 1
    assert len(pt._read_series("726")) == 1


def test_report_renders(pt):
    gan = [{"accountNumber": "75812568", "hashValue": "H568"}]
    with mock.patch.object(pt.trader, "get_account_numbers", return_value=gan), \
         mock.patch.object(pt.trader, "get_account",
                           return_value=_acct_payload(10000.0, 10000.0)), \
         mock.patch.object(pt, "_benchmark_price", return_value=750.0):
        pt.snapshot_account("568")
        path = pt.write_report("568")
    txt = Path(path).read_text(encoding="utf-8")
    assert "jul_1_2026" in txt
    assert "Return since baseline" in txt
    assert "start-the-clock-now" in txt


def test_report_ignores_foreign_records_in_performance_series(pt):
    series = pt._series_path("568")
    series.write_text(
        '{"at":"2026-08-31T20:00:00+00:00","ok":true,'
        '"suffix":"568","cohort":"jul_1_2026","nav":10000.0,'
        '"cash":10000.0,"positions":{},"benchmark":"SPY",'
        '"benchmark_price":750.0,"is_baseline":true,'
        '"baseline_nav":10000.0,"baseline_at":"2026-08-31T20:00:00+00:00",'
        '"net_external_flows_since_baseline":0.0,'
        '"simple_return_since_baseline":0.0,'
        '"benchmark_return_since_baseline":0.0,'
        '"alpha_since_baseline":0.0}\n'
        '{"timestamp":"2026-08-31T20:01:00+00:00",'
        '"account_suffix":"568","decision":"ACTIVE_NO_CHANGE"}\n'
    )

    report = pt.render_report("568")

    assert "Baseline (clock start): 2026-08-31T20:00:00+00:00" in report
    assert "ACTIVE_NO_CHANGE" not in report
    assert len(pt._read_series("568")) == 1


def test_unresolvable_account_fails_soft(pt):
    with mock.patch.object(pt.trader, "get_account_numbers",
                           return_value=[{"accountNumber": "99999999", "hashValue": "X"}]):
        snap = pt.snapshot_account("568")
    assert snap["ok"] is False
    assert "no linked account" in snap["error"]
