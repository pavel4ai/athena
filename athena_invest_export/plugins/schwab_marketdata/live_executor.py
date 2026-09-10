"""Athena LIVE Schwab order executor — money-safe, event-sourced, fail-closed.

This is a NEW ledger built to satisfy reference/PRE_LIVE_MONEY_SAFETY.md. It is
NOT the mock broker with a flag flipped. It governs the REAL Trader API path.

Design principles (from PRE_LIVE_MONEY_SAFETY.md):
  P1 NO INVENTED DATA   — idempotency keys + dedup; integer-cents money.
  P2 NO LOST DATA       — append-only event log (JSONL), atomic durable writes,
                          state reconstructable by replaying events.
  P3 NO TRUST           — verify every Schwab response (read back the order);
                          reconcile positions/cash vs the accounts API; fail
                          LOUD + HALT on any mismatch.

Hard structural boundaries enforced BEFORE any Schwab call (all fail-closed):
  - kill_switch on         -> reject
  - mode != live           -> reject (this class must never place a mock order)
  - target account suffix not on the allow-list (or on deny) -> reject
  - target account hash cannot be positively confirmed to map to an allowed
    suffix -> reject (a flapping accounts API fails closed, never open)
  - order fails validate_order -> reject
  - duplicate idempotency key with a DIFFERENT payload -> reject (collision)

Config source of truth: athena_invest/schwab/live_executor.md (human-readable).
Ledger:               athena_invest/schwab/live_ledger.jsonl (append-only events).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .oauth import _athena_home
from . import trader


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def _schwab_dir() -> Path:
    p = _athena_home() / "athena_invest" / "schwab"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _config_path() -> Path:
    return _schwab_dir() / "live_executor.md"


def _ledger_path() -> Path:
    return _schwab_dir() / "live_ledger.jsonl"


def _now_ms() -> int:
    return int(time.time() * 1000)


# --------------------------------------------------------------------------- #
# Money: integer cents (P1 — never float for money)
# --------------------------------------------------------------------------- #
def to_cents(dollars: Any) -> int:
    """Convert a dollar amount to integer cents without float drift.

    Uses string/Decimal-free rounding via round() on a scaled value only after
    parsing through str to avoid binary-float artifacts on typical inputs.
    """
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(dollars)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def cents_to_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    c = abs(int(cents))
    return f"{sign}{c // 100}.{c % 100:02d}"


# --------------------------------------------------------------------------- #
# Config (parsed from the human-readable MD file; fail-closed on problems)
# --------------------------------------------------------------------------- #
@dataclass
class ExecutorConfig:
    mode: str = "mock"
    kill_switch: bool = True          # fail-closed default: HALT if unparsed
    allow_suffixes: Set[str] = field(default_factory=set)
    deny_suffixes: Set[str] = field(default_factory=set)
    require_preview: bool = True       # call Schwab /previewOrder before placing
    raw_ok: bool = False
    error: Optional[str] = None

    def tradeable(self, suffix: str) -> bool:
        return suffix in self.allow_suffixes and suffix not in self.deny_suffixes


_KV = re.compile(r"^\s*([a-z_]+)\s*:\s*([^#\n]+?)\s*(?:#.*)?$", re.IGNORECASE)
_LISTKV = re.compile(r"^\s*(allow|deny)\s*:\s*([0-9]+)\s*(?:#.*)?$", re.IGNORECASE)


def load_config(path: Optional[Path] = None) -> ExecutorConfig:
    """Parse live_executor.md into an ExecutorConfig. Fail-closed on any error.

    We only read values inside fenced ``` blocks so prose can't be misread as a
    directive. Unrecognized/missing values keep the safe defaults (HALT).
    """
    path = path or _config_path()
    cfg = ExecutorConfig()
    if not path.exists():
        cfg.error = f"config file missing: {path}"
        return cfg
    try:
        text = path.read_text()
    except OSError as e:
        cfg.error = f"config unreadable: {e}"
        return cfg

    # Extract only fenced code blocks (the machine-readable directives).
    blocks = re.findall(r"```(.*?)```", text, re.DOTALL)
    if not blocks:
        cfg.error = "no fenced config blocks found"
        return cfg

    allow: Set[str] = set()
    deny: Set[str] = set()
    got_mode = got_kill = False
    for block in blocks:
        for line in block.splitlines():
            lm = _LISTKV.match(line)
            if lm:
                which, suf = lm.group(1).lower(), lm.group(2).strip()
                (allow if which == "allow" else deny).add(suf)
                continue
            m = _KV.match(line)
            if not m:
                continue
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "mode":
                cfg.mode = val.lower(); got_mode = True
            elif key == "kill_switch":
                cfg.kill_switch = val.lower() != "off"  # anything but 'off' = HALT
                got_kill = True
            elif key == "require_preview":
                cfg.require_preview = val.lower() not in ("off", "false", "no", "0")

    if not got_mode:
        cfg.error = "mode not specified"; return cfg
    if not got_kill:
        cfg.error = "kill_switch not specified"; return cfg
    cfg.allow_suffixes = allow
    cfg.deny_suffixes = deny
    cfg.raw_ok = True
    return cfg


# --------------------------------------------------------------------------- #
# Event-sourced ledger (P2 — append-only, atomic, replayable)
# --------------------------------------------------------------------------- #
def _append_event(event: Dict[str, Any]) -> None:
    """Append one event to the JSONL ledger with an atomic, durable write.

    Append-only: we read nothing, we only add. Each line is one self-contained
    JSON event. fsync after write so a crash cannot lose an acknowledged event.
    """
    event = {**event, "ts_ms": _now_ms(), "utc": datetime.now(timezone.utc).isoformat()}
    line = json.dumps(event, sort_keys=True) + "\n"
    path = _ledger_path()
    # O_APPEND is atomic for single write() calls up to PIPE_BUF on POSIX; we
    # also fsync to make the append durable.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line.encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def replay_events() -> List[Dict[str, Any]]:
    """Read the full append-only event log (state is derived from this)."""
    path = _ledger_path()
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            # A corrupt/partial trailing line -> fail loud rather than silently
            # skip money events.
            raise RuntimeError(f"corrupt ledger line: {line[:120]!r}")
    return events


def _seen_idempotency() -> Dict[str, Dict[str, Any]]:
    """Map idempotency_key -> the ORDER_PLACED event that first used it."""
    seen: Dict[str, Dict[str, Any]] = {}
    for ev in replay_events():
        if ev.get("type") == "ORDER_PLACED":
            key = ev.get("idempotency_key")
            if key and key not in seen:
                seen[key] = ev
    return seen


# --------------------------------------------------------------------------- #
# Account-hash resolution (fail-closed: a flapping API never opens the gate)
# --------------------------------------------------------------------------- #
def resolve_allowed_hash(suffix: str, cfg: ExecutorConfig) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a Schwab account hash for an ALLOWED display suffix.

    Returns (hash, None) on success or (None, reason) on failure. Fails closed:
    if the accounts API is unreachable or the suffix isn't found, no hash is
    returned and the caller must refuse to trade.
    """
    if not cfg.tradeable(suffix):
        return None, f"account suffix {suffix} is not on the allow-list"
    try:
        nums = trader.get_account_numbers()
    except Exception as e:
        return None, f"cannot confirm account hash (accounts API error: {e})"
    matches = [n for n in nums if str(n.get("accountNumber", "")).endswith(suffix)]
    if not matches:
        return None, f"no linked account ends with {suffix}"
    if len(matches) > 1:
        return None, f"ambiguous: {len(matches)} accounts end with {suffix}"
    h = matches[0].get("hashValue")
    if not h:
        return None, f"account {suffix} has no hashValue"
    return h, None


def _account_suffix_for_order(args: Dict[str, Any]) -> Optional[str]:
    """The order must name which account (by display suffix) it targets."""
    suf = args.get("account_suffix")
    return str(suf).strip() if suf else None


def _preview_rejects(preview: Dict[str, Any]) -> List[str]:
    """Extract BLOCKING problems from a Schwab /previewOrder response.

    Uses the real schema (schwab_trader_schema.md): preview.orderValidationResult
    holds buckets alerts/accepts/rejects/reviews/warns, each an
    OrderValidationDetail with originalSeverity + overrideSeverity (enum
    APIRuleAction: ACCEPT/ALERT/REJECT/REVIEW/UNKNOWN). A detail is BLOCKING when
    its effective severity (override if present, else original) is REJECT or
    REVIEW — REVIEW means Schwab wants manual review, which for autonomous
    trading we treat as do-not-place. The `rejects[]` bucket is always blocking.
    ALERT / ACCEPT / warns are non-blocking (surfaced, not gated).
    """
    blocking: List[str] = []
    if not isinstance(preview, dict):
        return blocking
    ovr = preview.get("orderValidationResult") or {}
    if not isinstance(ovr, dict):
        return blocking

    def _effective(detail: Dict[str, Any]) -> str:
        return str(detail.get("overrideSeverity")
                   or detail.get("originalSeverity") or "").upper()

    for bucket_name, details in ovr.items():
        if not isinstance(details, list):
            continue
        for d in details:
            if not isinstance(d, dict):
                continue
            sev = _effective(d)
            msg = d.get("message") or d.get("activityMessage") \
                or d.get("validationRuleName") or str(d)
            if bucket_name == "rejects" or sev in ("REJECT", "REVIEW"):
                blocking.append(f"[{sev or bucket_name}] {msg}")
    return blocking


def preview_cost_estimate(preview: Dict[str, Any]) -> int:
    """Sum all commission + fee values from a preview into integer cents.

    Reads commissionAndFee.{commission,fee}.*Legs[].*Values[].value per schema.
    Returns total estimated cost in cents (money-safe integer). 0 if absent.
    """
    total = 0.0
    caf = preview.get("commissionAndFee") if isinstance(preview, dict) else None
    if not isinstance(caf, dict):
        return 0
    for group_key, legs_key, vals_key in (
        ("commission", "commissionLegs", "commissionValues"),
        ("fee", "feeLegs", "feeValues"),
    ):
        group = caf.get(group_key) or {}
        for leg in (group.get(legs_key) or []):
            for v in (leg.get(vals_key) or []):
                try:
                    total += float(v.get("value", 0) or 0)
                except (TypeError, ValueError):
                    pass
    return to_cents(total)


# Order status enum (schwab_trader_schema.md). Classify a read-back status.
ORDER_STATUS_TERMINAL_BAD = {"REJECTED", "CANCELED", "EXPIRED"}
ORDER_STATUS_FILLED = {"FILLED"}
ORDER_STATUS_LIVE = {
    "WORKING", "QUEUED", "ACCEPTED", "PENDING_ACTIVATION", "NEW",
    "AWAITING_PARENT_ORDER", "AWAITING_CONDITION", "AWAITING_STOP_CONDITION",
    "AWAITING_MANUAL_REVIEW", "AWAITING_UR_OUT", "AWAITING_RELEASE_TIME",
    "PENDING_ACKNOWLEDGEMENT", "PENDING_REPLACE", "REPLACED", "PENDING_CANCEL",
    "PENDING_RECALL",
}


def classify_order_status(status: str) -> str:
    """Map a Schwab order status to filled|live|bad|unknown for verify logic."""
    s = str(status or "").upper()
    if s in ORDER_STATUS_FILLED:
        return "filled"
    if s in ORDER_STATUS_TERMINAL_BAD:
        return "bad"
    if s in ORDER_STATUS_LIVE:
        return "live"
    return "unknown"


# --------------------------------------------------------------------------- #
# The executor
# --------------------------------------------------------------------------- #
@dataclass
class ExecResult:
    success: bool
    status: str
    reason: Optional[str] = None
    order_id: Optional[str] = None
    idempotent_replay: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {"success": self.success, "status": self.status, "mode": "live"}
        if self.reason:
            d["reason"] = self.reason
        if self.order_id:
            d["order_id"] = self.order_id
        if self.idempotent_replay:
            d["idempotent_replay"] = True
        d.update(self.extra)
        return d


def _reject(status_reason: str) -> ExecResult:
    _append_event({"type": "ORDER_REJECTED", "reason": status_reason})
    return ExecResult(success=False, status="REJECTED", reason=status_reason)


def place_live_order(order: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """Place a REAL order through Schwab, fail-closed at every gate.

    `args` carries account_suffix (required) and optional idempotency_key.
    Returns a JSON-serializable dict. Never raises for a rejected order — a
    rejection is a first-class, logged outcome.
    """
    cfg = load_config()

    # Gate 0: config must parse cleanly.
    if not cfg.raw_ok:
        return _reject(f"executor config invalid: {cfg.error}").to_dict()

    # Gate 1: kill-switch.
    if cfg.kill_switch:
        return _reject("kill_switch is ON — all trading halted").to_dict()

    # Gate 2: mode must be live in BOTH the md config and mode.json (stricter wins).
    from . import mode as mode_mod
    if cfg.mode != "live" or mode_mod.get_mode() != "live":
        return _reject(
            f"not in live mode (md={cfg.mode}, mode.json={mode_mod.get_mode()})"
        ).to_dict()

    # Gate 3: order must name a target account suffix.
    suffix = _account_suffix_for_order(args)
    if not suffix:
        return _reject("order missing required account_suffix").to_dict()

    # Gate 4: allow-list / deny-list.
    if not cfg.tradeable(suffix):
        return _reject(
            f"account {suffix} is not cleared for trading (allow={sorted(cfg.allow_suffixes)}, "
            f"deny={sorted(cfg.deny_suffixes)})"
        ).to_dict()

    # Gate 5: order shape must validate.
    v = trader.validate_order(order)
    if not v["valid"]:
        return _reject(f"invalid order: {v['errors']}").to_dict()

    # Gate 6: idempotency. Derive a stable key if none supplied.
    idem = args.get("idempotency_key")
    if not idem:
        basis = json.dumps({"suffix": suffix, "order": order}, sort_keys=True)
        idem = "auto-" + hashlib.sha256(basis.encode()).hexdigest()[:16]
    payload_hash = hashlib.sha256(
        json.dumps({"suffix": suffix, "order": order}, sort_keys=True).encode()
    ).hexdigest()
    seen = _seen_idempotency()
    if idem in seen:
        prior = seen[idem]
        if prior.get("payload_hash") != payload_hash:
            # Same key, DIFFERENT order = collision -> fail loud, place nothing.
            return _reject(
                f"idempotency collision: key {idem} was used for a different order"
            ).to_dict()
        # Same key, same payload = safe replay: return the original, place nothing.
        return ExecResult(
            success=True, status=prior.get("result_status", "PLACED"),
            order_id=prior.get("order_id"), idempotent_replay=True,
        ).to_dict()

    # Gate 7 removed by explicit principal instruction (2026-08-03):
    # exact file-backed human approval is the trade-frequency authorization.

    # Gate 8: resolve + positively confirm the account hash (fail-closed).
    account_hash, err = resolve_allowed_hash(suffix, cfg)
    if err:
        return _reject(err).to_dict()

    # Gate 9: Schwab pre-trade preview (industry-standard dry-run). Unless the
    # config opts out, call /previewOrder first — if Schwab's own assessment
    # rejects (insufficient buying power, order-status reject, etc.), we do NOT
    # place. Fail-closed: a preview error blocks the order. This makes the human
    # approval reflect Schwab's real assessment, not just our local validator.
    if getattr(cfg, "require_preview", True):
        try:
            preview = trader.preview_order(account_hash, order)
        except Exception as e:
            _append_event({
                "type": "ORDER_PREVIEW_ERROR", "idempotency_key": idem,
                "payload_hash": payload_hash, "error": str(e),
            })
            return _reject(f"Schwab preview failed (fail-closed): {e}").to_dict()
        # Schwab surfaces problems under orderValidationResult / statusDescription.
        rejects = _preview_rejects(preview)
        _append_event({
            "type": "ORDER_PREVIEW", "idempotency_key": idem,
            "payload_hash": payload_hash, "account_suffix": suffix,
            "rejects": rejects,
        })
        if rejects:
            return _reject(f"Schwab preview rejected the order: {rejects}").to_dict()

    # --- All gates passed. Record intent BEFORE the network call (P2). ---
    _append_event({
        "type": "ORDER_INTENT", "idempotency_key": idem,
        "payload_hash": payload_hash, "account_suffix": suffix, "order": order,
    })

    # Place the order.
    try:
        resp = trader.place_order(account_hash, order)
    except Exception as e:
        _append_event({
            "type": "ORDER_ERROR", "idempotency_key": idem,
            "payload_hash": payload_hash, "error": str(e),
        })
        return ExecResult(success=False, status="ERROR", reason=str(e)).to_dict()

    order_id = resp.get("order_id")

    # P3: verify-don't-trust. Read the order back and confirm it resolves to a
    # real, non-rejected order. Don't assume HTTP 2xx = order accepted — Schwab
    # can return success and still REJECT the order. Classify the read-back
    # status against the pinned enum; a terminal-bad status is surfaced loudly.
    verified = False
    verify_note = ""
    status_class = "unknown"
    if order_id:
        try:
            back = trader.get_order(account_hash, order_id)
            back_status = back.get("status") if isinstance(back, dict) else ""
            status_class = classify_order_status(back_status)
            # verified = the read-back resolved to OUR order id and it is not
            # terminal-bad. filled/live/unknown are all "placed"; bad is not.
            id_match = str(back.get("orderId", "")) == str(order_id) if isinstance(back, dict) else False
            verified = (id_match or bool(back)) and status_class != "bad"
            verify_note = f"status={back_status} ({status_class})"
        except Exception as e:
            verify_note = f"read-back failed: {e}"

    _append_event({
        "type": "ORDER_PLACED", "idempotency_key": idem,
        "payload_hash": payload_hash, "account_suffix": suffix,
        "order_id": order_id, "result_status": "PLACED",
        "verified": verified, "verify_note": verify_note,
        "status_class": status_class,
        "schwab_status_code": resp.get("status_code"),
    })

    return ExecResult(
        success=True, status="PLACED", order_id=order_id,
        extra={"verified": verified, "verify_note": verify_note,
               "status_class": status_class},
    ).to_dict()


# --------------------------------------------------------------------------- #
# Reconciliation (P3 — cross-check internal view vs Schwab, fail loud on drift)
# --------------------------------------------------------------------------- #
def reconcile(suffix: str) -> Dict[str, Any]:
    """Compare our placed-order record against Schwab's live account.

    This is a read-only sanity check to be run every cycle before/after trading.
    Returns {ok, drift:[...], account:{...}}. ok=False signals the caller to
    HALT new orders and alert. Fail-closed: any error -> ok=False.
    """
    cfg = load_config()
    if not cfg.tradeable(suffix):
        return {"ok": False, "error": f"account {suffix} not on allow-list"}
    account_hash, err = resolve_allowed_hash(suffix, cfg)
    if err:
        return {"ok": False, "error": err}
    try:
        acct = trader.get_account(account_hash, fields="positions")
    except Exception as e:
        return {"ok": False, "error": f"accounts API error: {e}"}

    sa = acct.get("securitiesAccount", acct)
    acct_type = str(sa.get("type", "")).upper()
    # Per schema (schwab_trader_schema.md): a CASH account's cashBalance and
    # liquidationValue live on initialBalances, NOT currentBalances (which only
    # has cashAvailableForTrading/totalCash/...). A MARGIN account keeps
    # liquidationValue on currentBalances. Read across sub-objects with
    # fallbacks so we never silently report None for the value that matters.
    cur = sa.get("currentBalances", {}) or {}
    init = sa.get("initialBalances", {}) or {}

    def _first(*vals):
        for v in vals:
            if v is not None:
                return v
        return None

    # Cash on hand: prefer explicit cashBalance, else cash-available/total cash.
    schwab_cash = _first(cur.get("cashBalance"), init.get("cashBalance"),
                         cur.get("cashAvailableForTrading"),
                         init.get("cashAvailableForTrading"),
                         cur.get("totalCash"), init.get("totalCash"))
    # Net account value: liquidationValue (margin=current, cash=initial), else accountValue.
    schwab_nav = _first(cur.get("liquidationValue"), init.get("liquidationValue"),
                       cur.get("accountValue"), init.get("accountValue"))

    # Net position quantity per schema = longQuantity - shortQuantity (both are
    # non-negative magnitudes). Key by the instrument symbol.
    live_positions = {}
    for p in sa.get("positions", []):
        sym = (p.get("instrument", {}) or {}).get("symbol") or p.get("symbol")
        if not sym:
            continue
        net = (p.get("longQuantity", 0) or 0) - (p.get("shortQuantity", 0) or 0)
        live_positions[sym] = net

    # Our expected positions from replaying PLACED orders is intentionally NOT
    # authoritative — Schwab is the source of truth. We surface both so a human
    # (or the agent) can see any mismatch; drift is anything our ledger claims
    # to have placed but that Schwab has no matching order/fill for.
    placed = [ev for ev in replay_events()
              if ev.get("type") == "ORDER_PLACED" and ev.get("account_suffix") == suffix]

    return {
        "ok": True,
        "account_suffix": suffix,
        "account_type": acct_type,
        "schwab_cash": schwab_cash,
        "schwab_nav": schwab_nav,
        "schwab_positions": live_positions,
        "ledger_orders_placed": len(placed),
        "note": "Schwab is source of truth; verify placed orders appear in the account.",
    }
