"""Tests for the Schwab market-data streamer layer (no network, no credentials).

Run: python -m pytest ~/.athena/plugins/schwab_marketdata/test_streamer.py -q
(or via the repo's scripts/run_tests.sh pointed at this path).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schwab_marketdata import fields as F  # noqa: E402
from schwab_marketdata import symbols as S  # noqa: E402
from schwab_marketdata.streamer import (  # noqa: E402
    CredentialProvider,
    SchwabStreamerClient,
    StreamerInfo,
)


# --------------------------------------------------------------------------- #
# Field decoding
# --------------------------------------------------------------------------- #
def test_decode_equity_row_named_fields():
    row = {"key": "AAPL", "delayed": False, "assetMainType": "EQUITY",
           "cusip": "037833100", "1": 183.75, "2": 183.8, "3": 183.8,
           "8": 163224109, "10": 187}
    out = F.decode_row("LEVELONE_EQUITIES", row)
    assert out["key"] == "AAPL"
    assert out["bid_price"] == 183.75
    assert out["ask_price"] == 183.8
    assert out["last_price"] == 183.8
    assert out["total_volume"] == 163224109
    assert out["high_price"] == 187
    assert out["cusip"] == "037833100"
    assert out["delayed"] is False


def test_decode_options_greeks():
    row = {"key": "AAPL  251219C00200000", "28": 0.55, "29": 0.02, "30": -0.03,
           "31": 0.12, "32": 0.01, "10": 0.31}
    out = F.decode_row("LEVELONE_OPTIONS", row)
    assert out["delta"] == 0.55
    assert out["gamma"] == 0.02
    assert out["theta"] == -0.03
    assert out["vega"] == 0.12
    assert out["rho"] == 0.01
    assert out["volatility"] == 0.31


def test_unknown_field_preserved():
    out = F.decode_row("LEVELONE_EQUITIES", {"999": "x"})
    assert out["field_999"] == "x"


def test_decode_full_data_message():
    msg = {"data": [{"service": "LEVELONE_EQUITIES", "timestamp": 1,
                     "command": "SUBS",
                     "content": [{"key": "SPY", "1": 512.3, "2": 512.32}]}]}
    decoded = F.decode_data_message(msg)
    assert decoded[0]["service"] == "LEVELONE_EQUITIES"
    assert decoded[0]["rows"][0]["bid_price"] == 512.3


def test_all_fields_lists_built():
    assert F.SERVICE_ALL_FIELDS["LEVELONE_EQUITIES"].startswith("0,1,2,3")
    assert F.SERVICE_ALL_FIELDS["CHART_FUTURES"] == "0,1,2,3,4,5,6"


def test_response_code_severs_flags():
    assert F.RESPONSE_CODES[0] == ("SUCCESS", False)
    assert F.RESPONSE_CODES[3][1] is True       # LOGIN_DENIED severs
    assert F.RESPONSE_CODES[12][1] is True       # CLOSE_CONNECTION severs
    assert F.RESPONSE_CODES[30][1] is True       # STOP_STREAMING severs


# --------------------------------------------------------------------------- #
# Symbol formatting
# --------------------------------------------------------------------------- #
def test_option_symbol_format():
    assert S.format_option_symbol("AAPL", 2025, 12, 19, "C", 200.0) == "AAPL  251219C00200000"


def test_futures_symbol_format():
    assert S.format_futures_symbol("ES", 12, 2025) == "/ESZ25"
    assert S.format_futures_symbol("CL", 1, 2026) == "/CLF26"


def test_service_inference():
    assert S.service_for_symbol("AAPL") == "LEVELONE_EQUITIES"
    assert S.service_for_symbol("/ESZ25") == "LEVELONE_FUTURES"
    assert S.service_for_symbol("./OZCZ23C565") == "LEVELONE_FUTURES_OPTIONS"
    assert S.service_for_symbol("EUR/USD") == "LEVELONE_FOREX"
    assert S.service_for_symbol("AAPL  251219C00200000") == "LEVELONE_OPTIONS"


# --------------------------------------------------------------------------- #
# Streamer protocol against a fake socket
# --------------------------------------------------------------------------- #
class FakeSocket:
    """Minimal async ws double: queues outbound, feeds scripted inbound."""

    def __init__(self):
        self.sent = []
        self._inbound = asyncio.Queue()
        self._closed = False

    async def send(self, data):
        self.sent.append(json.loads(data))

    def feed(self, msg: dict):
        self._inbound.put_nowait(json.dumps(msg))

    async def __aiter__(self):
        while not self._closed:
            item = await self._inbound.get()
            if item is None:
                break
            yield item

    async def close(self):
        self._closed = True
        self._inbound.put_nowait(None)


class FakeProvider(CredentialProvider):
    def is_configured(self) -> bool:
        return True

    async def get_streamer_info(self) -> StreamerInfo:
        return StreamerInfo(
            websocket_url="wss://fake", access_token="TOKEN",
            schwab_client_customer_id="CUST", schwab_client_correl_id="CORR",
            schwab_client_channel="N9", schwab_client_function_id="APIAPP",
        )


@pytest.mark.asyncio
async def test_login_then_subscribe_and_decode():
    sock = FakeSocket()
    client = SchwabStreamerClient(FakeProvider())
    client._connect_factory = lambda url: _ret(sock)

    got = []
    async def handler(decoded):
        got.extend(decoded)
    client.on_data(handler)

    # Feed a successful login response shortly after connect sends LOGIN
    async def respond():
        await asyncio.sleep(0.05)
        sock.feed({"response": [{"service": "ADMIN", "command": "LOGIN",
                                 "requestid": "1", "content": {"code": 0, "msg": "ok"}}]})
    asyncio.ensure_future(respond())

    await client.connect()
    assert client._logged_in is True
    # First outbound must be the LOGIN
    assert sock.sent[0]["requests"][0]["command"] == "LOGIN"
    assert sock.sent[0]["requests"][0]["service"] == "ADMIN"

    await client.subscribe("LEVELONE_EQUITIES", ["aapl"])
    sub = sock.sent[1]["requests"][0]
    assert sub["command"] == "SUBS"
    assert sub["parameters"]["keys"] == "AAPL"          # uppercased
    assert "1" in sub["parameters"]["fields"]            # all-fields default

    # Now push a data message and confirm decode reaches the handler
    sock.feed({"data": [{"service": "LEVELONE_EQUITIES", "timestamp": 2,
                         "command": "SUBS",
                         "content": [{"key": "AAPL", "1": 183.7, "3": 183.8}]}]})
    await asyncio.sleep(0.05)
    assert got and got[-1]["rows"][0]["bid_price"] == 183.7
    await client.logout()


@pytest.mark.asyncio
async def test_subscribe_before_login_rejected():
    client = SchwabStreamerClient(FakeProvider())
    with pytest.raises(RuntimeError, match="LOGIN"):
        await client.subscribe("LEVELONE_EQUITIES", ["AAPL"])


@pytest.mark.asyncio
async def test_login_denied_raises():
    sock = FakeSocket()
    client = SchwabStreamerClient(FakeProvider())
    client._connect_factory = lambda url: _ret(sock)

    async def respond():
        await asyncio.sleep(0.05)
        sock.feed({"response": [{"service": "ADMIN", "command": "LOGIN",
                                 "requestid": "1",
                                 "content": {"code": 3, "msg": "denied"}}]})
    asyncio.ensure_future(respond())
    with pytest.raises(RuntimeError, match="denied"):
        await client.connect()


def test_unconfigured_provider_blocks():
    p = CredentialProvider()
    assert p.is_configured() is False


async def _ret(x):
    return x
