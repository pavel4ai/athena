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
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"cohort": self.cohort, "cash": 0.0, "positions": {},
                "orders": [], "transactions": [], "created": _now_ms()}

    def _save(self) -> None:
        # Atomic durable write: temp file in the same dir -> fsync -> os.replace.
        # Prevents a crash mid-write from truncating/corrupting the cohort state.
        import os
        tmp = self.path.with_suffix(self.path.suffix + f".tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)  # atomic on POSIX + Windows

    def fund(self, cash: float, allow_after_trades: bool = False) -> None:
        """Set starting cash for a fresh cohort. Pre-trade only by default.

        Funding after trades have occurred would arbitrarily rewrite the balance
        (invented money). Refused unless explicitly modeling a deposit via
        `deposit()`. Use this only to initialize a fresh cohort.
        """
        if self.state.get("transactions") and not allow_after_trades:
            raise ValueError(
                f"fund() refused: cohort '{self.cohort}' already has "
                f"{len(self.state['transactions'])} trade(s). Funding now would "
                f"arbitrarily rewrite the balance. Use deposit() to model an "
                f"explicit cash deposit, or reset the cohort first.")
        self.state["cash"] = float(cash)
        self.state.setdefault("initial_cash", float(cash))
        self._save()

    def deposit(self, amount: float) -> None:
        """Model an explicit additive cash deposit/withdrawal (event-like).

        Unlike fund(), this is additive and recorded as a transaction, so the
        balance is never silently overwritten — a deposit is a tracked event.
        """
        amount = float(amount)
        self.state["cash"] = self.state.get("cash", 0.0) + amount
        self.state.setdefault("transactions", []).append({
            "time": _now_ms(), "type": "deposit" if amount >= 0 else "withdrawal",
            "amount": amount})
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
    def place_order(self, account_hash: str, order: Dict[str, Any],
                    idempotency_key: str = None) -> Dict[str, Any]:
        """Simulate placing an order. Returns {order_id, status, fills:[...]}.

        idempotency_key: if provided, a repeat call with the same key returns the
        ORIGINAL result without placing/filling again (retries & double-fired
        crons cannot double-fill). Mirrors the live requirement.
        """
        if idempotency_key:
            for rec in self.state["orders"]:
                if rec.get("idempotency_key") == idempotency_key:
                    return {"order_id": rec["order_id"], "status": rec["status"],
                            "fills": rec["fills"], "mock": True, "idempotent_replay": True}

        order_id = uuid.uuid4().hex[:12]
        legs = order.get("orderLegCollection", [])
        otype = order.get("orderType", "MARKET").upper()
        limit_price = float(order["price"]) if order.get("price") else None

        record = {"order_id": order_id, "placed_at": _now_ms(),
                  "idempotency_key": idempotency_key,
                  "orderType": otype, "price": limit_price,
                  "status": "WORKING", "legs": legs, "fills": []}

        try:
            filled = self._try_fill(record)
        except ValueError as exc:
            # Fail loud: a rejected order (e.g. oversell) is recorded as REJECTED,
            # not silently dropped, and the reason is surfaced.
            record["status"] = "REJECTED"
            record["reject_reason"] = str(exc)
            self.state["orders"].append(record)
            self._save()
            return {"order_id": order_id, "status": "REJECTED",
                    "reason": str(exc), "fills": [], "mock": True}
        record["status"] = "FILLED" if filled else "WORKING"
        self.state["orders"].append(record)
        self._save()
        return {"order_id": order_id, "status": record["status"],
                "fills": record["fills"], "mock": True}

    def _try_fill(self, record: Dict[str, Any]) -> bool:
        """Attempt to fill all legs against live quotes. All-or-nothing per order.

        Raises ValueError if a sell exceeds held quantity (no shorting modeled) —
        prevents inventing positions / phantom cash. Validation happens in the
        planning phase BEFORE any leg is applied, so a reject leaves state clean.
        """
        planned = []
        # track holdings as we plan, so multi-leg orders can't oversell either
        proj_qty = {s: p["qty"] for s, p in self.state["positions"].items()}
        for leg in record["legs"]:
            sym = leg["instrument"]["symbol"]
            qty = int(leg["quantity"])
            instr = leg["instruction"].upper()
            side = "buy" if instr in ("BUY", "BUY_TO_OPEN", "BUY_TO_COVER", "BUY_TO_CLOSE") else "sell"
            # Oversell guard: a closing sell cannot exceed what is held. Shorting
            # (SELL_SHORT) is NOT modeled in the mock -> also rejected for now.
            if side == "sell":
                if instr == "SELL_SHORT":
                    raise ValueError(f"short selling not modeled in mock ({sym})")
                held = proj_qty.get(sym, 0)
                if qty > held:
                    raise ValueError(
                        f"oversell rejected: {instr} {qty} {sym} but only {held} held")
                proj_qty[sym] = held - qty
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
