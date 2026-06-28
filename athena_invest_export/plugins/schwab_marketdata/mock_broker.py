"""Mock Schwab broker — paper trading on REAL market data.

Pre-flight mode for Athena: uses live quotes from the Market Data Production
REST API (rest_marketdata.py) but SIMULATES accounts, fills, positions, cash,
and transactions. Mirrors the real trader.py surface so Athena's code path is
identical in mock and live — only `schwab.mode` in mock_config selects which.

Fill model (realistic):
  - MARKET buy  -> fills at live ask * (1 + slippage_bps)
  - MARKET sell -> fills at live bid * (1 - slippage_bps)
  - LIMIT buy   -> fills at limit if live ask <= limit, else stays WORKING
  - LIMIT sell  -> fills at limit if live bid >= limit, else stays WORKING
  - commission applied per order (default 0)
Working orders are re-checked against live quotes on each `process_working_orders`.

Any symbol the quote API returns is tradeable. State persists to
$ATHENA_HOME/athena_invest/mock/<cohort>.json so it survives restarts.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .oauth import _athena_home
from . import rest_marketdata as rmd

DEFAULT_SLIPPAGE_BPS = 2.0      # 0.02% slippage on market orders
DEFAULT_COMMISSION = 0.0        # per-order commission (Schwab equities = $0)


def _mock_dir() -> Path:
    p = _athena_home() / "athena_invest" / "mock"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now_ms() -> int:
    return int(time.time() * 1000)


def _live_quote(symbol: str) -> Dict[str, Any]:
    raw = rmd.get_quotes([symbol])
    q = rmd.simplify_quotes(raw).get(symbol.upper())
    if not q or q.get("last_price") is None:
        raise ValueError(f"No live quote available for {symbol}")
    return q


class MockBroker:
    """Paper-trading broker for one cohort, backed by live market data."""

    def __init__(self, cohort: str, slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
                 commission: float = DEFAULT_COMMISSION):
        self.cohort = cohort
        self.slippage_bps = slippage_bps
        self.commission = commission
        self.path = _mock_dir() / f"{cohort}.json"
        self.state = self._load()

    # -- state --------------------------------------------------------------
    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"cohort": self.cohort, "cash": 0.0, "positions": {},
                "orders": [], "transactions": [], "created": _now_ms()}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.state, indent=2))

    def fund(self, cash: float) -> None:
        """Set starting cash for a fresh mock cohort."""
        self.state["cash"] = float(cash)
        self.state.setdefault("initial_cash", float(cash))
        self._save()

    # -- read surface (mirrors trader.py) -----------------------------------
    def get_account(self, account_hash: str = None, fields: str = "positions") -> Dict[str, Any]:
        positions = []
        nav = self.state["cash"]
        for sym, pos in self.state["positions"].items():
            try:
                last = _live_quote(sym)["last_price"]
            except Exception:
                last = pos["avg_price"]
            mv = last * pos["qty"]
            nav += mv
            positions.append({
                "symbol": sym, "quantity": pos["qty"], "averagePrice": pos["avg_price"],
                "marketValue": round(mv, 2), "lastPrice": last,
                "unrealizedPL": round((last - pos["avg_price"]) * pos["qty"], 2),
            })
        return {
            "mock": True, "cohort": self.cohort,
            "securitiesAccount": {
                "type": "MOCK", "accountNumber": f"MOCK-{self.cohort}",
                "currentBalances": {"cashBalance": round(self.state["cash"], 2),
                                    "liquidationValue": round(nav, 2)},
                "positions": positions,
            },
        }

    def get_orders(self, *a, **k) -> List[Dict[str, Any]]:
        return self.state["orders"]

    def get_transactions(self, *a, **k) -> List[Dict[str, Any]]:
        return self.state["transactions"]

    # -- order placement (mirrors trader.place_order) -----------------------
    def place_order(self, account_hash: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate placing an order. Returns {order_id, status, fills:[...]}."""
        order_id = uuid.uuid4().hex[:12]
        legs = order.get("orderLegCollection", [])
        otype = order.get("orderType", "MARKET").upper()
        limit_price = float(order["price"]) if order.get("price") else None

        record = {"order_id": order_id, "placed_at": _now_ms(),
                  "orderType": otype, "price": limit_price,
                  "status": "WORKING", "legs": legs, "fills": []}

        filled = self._try_fill(record)
        record["status"] = "FILLED" if filled else "WORKING"
        self.state["orders"].append(record)
        self._save()
        return {"order_id": order_id, "status": record["status"],
                "fills": record["fills"], "mock": True}

    def _try_fill(self, record: Dict[str, Any]) -> bool:
        """Attempt to fill all legs against live quotes. All-or-nothing per order."""
        planned = []
        for leg in record["legs"]:
            sym = leg["instrument"]["symbol"]
            qty = int(leg["quantity"])
            instr = leg["instruction"].upper()
            side = "buy" if instr in ("BUY", "BUY_TO_OPEN", "BUY_TO_COVER", "BUY_TO_CLOSE") else "sell"
            q = _live_quote(sym)
            ask, bid, last = q.get("ask_price") or q["last_price"], q.get("bid_price") or q["last_price"], q["last_price"]
            slip = self.slippage_bps / 10000.0

            if record["orderType"] == "MARKET":
                price = ask * (1 + slip) if side == "buy" else bid * (1 - slip)
            else:  # LIMIT
                lim = record["price"]
                if side == "buy" and ask <= lim:
                    price = lim
                elif side == "sell" and bid >= lim:
                    price = lim
                else:
                    return False  # not crossable yet -> stays working
            planned.append((sym, qty, side, round(price, 4), instr))

        # apply
        for sym, qty, side, price, instr in planned:
            self._apply_fill(sym, qty, side, price, instr)
            record["fills"].append({"symbol": sym, "qty": qty, "side": side,
                                    "price": price, "filled_at": _now_ms()})
        return True

    def _apply_fill(self, sym: str, qty: int, side: str, price: float, instr: str) -> None:
        cost = price * qty + self.commission
        pos = self.state["positions"].get(sym, {"qty": 0, "avg_price": 0.0})
        if side == "buy":
            self.state["cash"] -= cost
            new_qty = pos["qty"] + qty
            pos["avg_price"] = ((pos["avg_price"] * pos["qty"]) + price * qty) / new_qty if new_qty else 0.0
            pos["qty"] = new_qty
        else:  # sell
            self.state["cash"] += price * qty - self.commission
            pos["qty"] -= qty
            if pos["qty"] <= 0:
                pos = {"qty": 0, "avg_price": 0.0}
        if pos["qty"] == 0:
            self.state["positions"].pop(sym, None)
        else:
            self.state["positions"][sym] = pos
        self.state["transactions"].append({
            "time": _now_ms(), "symbol": sym, "side": side, "qty": qty,
            "price": price, "commission": self.commission, "instruction": instr})

    def process_working_orders(self) -> List[str]:
        """Re-check WORKING limit orders against live quotes; fill if crossable."""
        filled_ids = []
        for rec in self.state["orders"]:
            if rec["status"] != "WORKING":
                continue
            if self._try_fill(rec):
                rec["status"] = "FILLED"
                filled_ids.append(rec["order_id"])
        if filled_ids:
            self._save()
        return filled_ids

    def cancel_order(self, account_hash: str, order_id: str) -> Dict[str, Any]:
        for rec in self.state["orders"]:
            if rec["order_id"] == order_id and rec["status"] == "WORKING":
                rec["status"] = "CANCELED"
                self._save()
                return {"order_id": order_id, "status": "CANCELED", "mock": True}
        return {"order_id": order_id, "status": "NOT_FOUND", "mock": True}
