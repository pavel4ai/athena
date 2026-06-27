"""Tests for the Schwab Market Data REST simplifier (no network)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schwab_marketdata import rest_marketdata as rmd  # noqa: E402


def test_simplify_quotes_equity():
    raw = {
        "AAPL": {
            "assetMainType": "EQUITY", "realtime": True,
            "quote": {"lastPrice": 282.64, "bidPrice": 282.51, "askPrice": 282.59,
                      "bidSize": 3, "askSize": 1, "totalVolume": 261775450,
                      "openPrice": 280.0, "highPrice": 284.0, "lowPrice": 279.5,
                      "closePrice": 275.1, "netChange": 7.5, "netPercentChange": 2.72,
                      "52WeekHigh": 300.1, "52WeekLow": 160.0, "peRatio": 31.2,
                      "mark": 282.6, "quoteTime": 1714949592301},
            "reference": {"description": "APPLE INC", "exchangeName": "NASDAQ"},
        }
    }
    out = rmd.simplify_quotes(raw)
    a = out["AAPL"]
    assert a["symbol"] == "AAPL"
    assert a["asset_type"] == "EQUITY"
    assert a["last_price"] == 282.64
    assert a["bid_price"] == 282.51
    assert a["ask_price"] == 282.59
    assert a["total_volume"] == 261775450
    assert a["week52_high"] == 300.1
    assert a["week52_low"] == 160.0
    assert a["pe_ratio"] == 31.2
    assert a["description"] == "APPLE INC"
    assert a["exchange"] == "NASDAQ"
    assert a["delayed"] is False


def test_simplify_quotes_handles_missing_fields():
    raw = {"XYZ": {"assetMainType": "EQUITY", "quote": {}, "reference": {}}}
    out = rmd.simplify_quotes(raw)
    assert out["XYZ"]["last_price"] is None
    assert out["XYZ"]["symbol"] == "XYZ"


def test_simplify_quotes_empty():
    assert rmd.simplify_quotes({}) == {}
