"""Account-isolated Schwab read/preview tools for the default investment profile.

The plugin exposes separate read-only and preview-only toolsets for suffixes 331,
568, and 726. It calls Schwab ``previewOrder`` but has no placement handler,
resolver, order-amendment surface, or arbitrary account parameter.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable
from zoneinfo import ZoneInfo

_SCOPES = {"331": "sep_1_2026", "568": "july1_568", "726": "aug_1_2026"}
_EXCLUDED_SUFFIXES = {"892"}
_MAX_ORDERS = 12
_TERMINAL_ORDER_STATES = {"FILLED", "CANCELED", "REJECTED", "EXPIRED", "REPLACED"}
_PENDING_MARKERS = ("PENDING_APPROVAL", '"status":"pending"', '"status": "pending"')
_ET = ZoneInfo("America/New_York")


def _athena_home() -> Path:
    return Path(os.environ.get("ATHENA_HOME", Path.home() / ".athena")).expanduser()


def _load_schwab() -> ModuleType:
    name = "_default_preview_schwab"
    if name in sys.modules:
        return sys.modules[name]
    package = _athena_home() / "plugins" / "schwab_marketdata"
    spec = importlib.util.spec_from_file_location(
        name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load scoped Schwab plugin")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_schwab = _load_schwab()
_trader = importlib.import_module(f"{_schwab.__name__}.trader")
_mode = importlib.import_module(f"{_schwab.__name__}.mode")
_oauth = importlib.import_module(f"{_schwab.__name__}.oauth")
_marketdata = importlib.import_module(f"{_schwab.__name__}.rest_marketdata")
_live_executor = importlib.import_module(f"{_schwab.__name__}.live_executor")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _preview_dir() -> Path:
    path = _athena_home() / "athena_invest" / "schwab" / "previews"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _journal_path(suffix: str) -> Path:
    path = _athena_home() / "athena_invest" / "cohorts" / _SCOPES[suffix] / "decision_journal.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(preview: Path) -> Path:
    return preview.with_suffix(".state.json")


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    data = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, text.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        tmp.unlink(missing_ok=True)


def _account_snapshot(suffix: str, account: dict[str, Any]) -> dict[str, Any]:
    sec = account.get("securitiesAccount", account)
    current = sec.get("currentBalances") or {}
    initial = sec.get("initialBalances") or {}

    def first(*values: Any) -> Any:
        return next((value for value in values if value is not None), None)

    positions = []
    for position in sec.get("positions") or []:
        instrument = position.get("instrument") or {}
        positions.append({
            "symbol": instrument.get("symbol"),
            "long_quantity": position.get("longQuantity", 0),
            "short_quantity": position.get("shortQuantity", 0),
        })
    positions.sort(key=lambda item: str(item.get("symbol") or ""))
    return {
        "account_suffix": suffix,
        "account_type": sec.get("type"),
        "liquidation_value": first(current.get("liquidationValue"), initial.get("liquidationValue")),
        "cash_available_for_trading": first(
            current.get("cashAvailableForTrading"), initial.get("cashAvailableForTrading"),
            current.get("cashBalance"), initial.get("cashBalance")
        ),
        "available_funds": first(current.get("availableFunds"), initial.get("availableFunds")),
        "positions": positions,
    }


def _resolve_hash(suffix: str) -> tuple[str | None, str | None]:
    if suffix not in _SCOPES or suffix in _EXCLUDED_SUFFIXES:
        return None, "Account scope is denied."
    cfg = _live_executor.load_config()
    if not cfg.raw_ok:
        return None, f"Executor config invalid: {cfg.error}"
    if not cfg.tradeable(suffix):
        return None, f"Account {suffix} is not on the live allow-list."
    return _live_executor.resolve_allowed_hash(suffix, cfg)


def _token_health(args: dict[str, Any], **_: Any) -> str:
    probe = args.get("probe", True)
    if not isinstance(probe, bool) or set(args) - {"probe"}:
        return json.dumps({"success": False, "error": "Only boolean probe is accepted."})
    try:
        health = _oauth.token_health(probe=probe, app=_oauth.TRADER_APP)
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Trader token probe failed closed: {exc}"})
    safe = ("app", "access_valid", "refresh_valid", "refresh_expires_in_days", "needs_consent",
            "probed", "probe_ok", "probe_error")
    return json.dumps({"success": True, **{key: health.get(key) for key in safe}})


def _read_account(suffix: str, args: dict[str, Any], **_: Any) -> str:
    if args:
        return json.dumps({"success": False, "error": "This account-scoped read accepts no arguments."})
    account_hash, error = _resolve_hash(suffix)
    if error or not account_hash:
        return json.dumps({"success": False, "error": error or "Could not resolve account."})
    try:
        account = _trader.get_account(account_hash, fields="positions")
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Account {suffix} read failed closed: {exc}"})
    return json.dumps({"success": True, "account": _account_snapshot(suffix, account)})


def _parse_order_time(order: dict[str, Any]) -> datetime | None:
    raw = str(order.get("enteredTime") or order.get("closeTime") or "")
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _read_orders(suffix: str, args: dict[str, Any], **_: Any) -> str:
    if args:
        return json.dumps({"success": False, "error": "This account-scoped order read accepts no arguments."})
    account_hash, error = _resolve_hash(suffix)
    if error or not account_hash:
        return json.dumps({"success": False, "error": error or "Could not resolve account."})
    now = _now_utc()
    try:
        orders = _trader.get_orders(
            account_hash, (now - timedelta(days=60)).isoformat().replace("+00:00", "Z"),
            (now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        )
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Account {suffix} order read failed closed: {exc}"})
    if not isinstance(orders, list):
        return json.dumps({"success": False, "error": "Broker order response was not a list."})
    relevant = []
    for order in orders:
        if not isinstance(order, dict):
            return json.dumps({"success": False, "error": "Malformed order record returned by broker."})
        status = str(order.get("status") or "UNKNOWN").upper()
        entered = _parse_order_time(order)
        is_today = entered is None or entered.astimezone(_ET).date() == now.astimezone(_ET).date()
        if not is_today and status in _TERMINAL_ORDER_STATES:
            continue
        legs = []
        for leg in order.get("orderLegCollection") or []:
            instrument = leg.get("instrument") or {}
            legs.append({"symbol": instrument.get("symbol"), "asset_type": instrument.get("assetType"),
                         "instruction": leg.get("instruction"), "quantity": leg.get("quantity")})
        relevant.append({"order_id": order.get("orderId"), "entered_time": order.get("enteredTime"),
                         "status": status, "order_type": order.get("orderType"),
                         "session": order.get("session"), "duration": order.get("duration"),
                         "price": order.get("price"), "legs": legs})
    return json.dumps({"success": True, "account_suffix": suffix, "lookback_days": 60,
                       "current_day_or_open_orders": relevant})


def _quotes(args: dict[str, Any], **_: Any) -> str:
    symbols = args.get("symbols")
    if set(args) != {"symbols"} or not isinstance(symbols, list) or not 1 <= len(symbols) <= 30:
        return json.dumps({"success": False, "error": "symbols must contain 1-30 entries."})
    clean = []
    for symbol in symbols:
        value = str(symbol).strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9./$ -]{0,31}", value):
            return json.dumps({"success": False, "error": f"Invalid symbol: {symbol!r}"})
        clean.append(value)
    try:
        result = _marketdata.get_quotes(clean)
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Quote read failed closed: {exc}"})
    return json.dumps({"success": True, "quotes": result})


def _symbol(order: dict[str, Any]) -> str:
    legs = order.get("orderLegCollection") or []
    return str(((legs[0].get("instrument") or {}).get("symbol") if len(legs) == 1 else None) or "UNKNOWN").upper()


def _side(order: dict[str, Any]) -> str:
    legs = order.get("orderLegCollection") or []
    return str((legs[0].get("instruction") if len(legs) == 1 else None) or "UNKNOWN").upper()


def _quantity(order: dict[str, Any]) -> Any:
    legs = order.get("orderLegCollection") or []
    return legs[0].get("quantity", "?") if len(legs) == 1 else "?"


def _structural_ticket_error(order: dict[str, Any]) -> str | None:
    if str(order.get("orderStrategyType") or "").upper() != "SINGLE":
        return "Only SINGLE orders are accepted."
    if str(order.get("session") or "").upper() != "NORMAL":
        return "Only NORMAL-session orders are accepted."
    if str(order.get("duration") or "").upper() != "DAY":
        return "Only DAY orders are accepted."
    legs = order.get("orderLegCollection") or []
    if len(legs) != 1 or not isinstance(legs[0], dict):
        return "Exactly one order leg is required."
    qty = legs[0].get("quantity")
    if isinstance(qty, bool) or not isinstance(qty, (int, float)) or qty <= 0 or int(qty) != qty:
        return "Quantity must be a positive whole number; fractional shares are prohibited."
    instrument = legs[0].get("instrument") or {}
    if str(instrument.get("assetType") or "").upper() != "EQUITY":
        return "This preview surface accepts EQUITY tickets only."
    return None


def _validation_summary(preview: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    validation = preview.get("orderValidationResult") or {}
    if not isinstance(validation, dict):
        return output
    for bucket, details in validation.items():
        if not isinstance(details, list):
            continue
        clean = []
        for detail in details:
            if isinstance(detail, dict):
                clean.append({"severity": detail.get("overrideSeverity") or detail.get("originalSeverity"),
                              "message": detail.get("message") or detail.get("activityMessage"),
                              "rule": detail.get("validationRuleName")})
        if clean:
            output[str(bucket)] = clean
    return output


def _preview_blockers(preview: Any) -> list[str]:
    if not isinstance(preview, dict) or not isinstance(preview.get("orderValidationResult"), dict):
        return ["[MALFORMED] missing valid orderValidationResult"]
    return _live_executor._preview_rejects(preview)


def _existing_preview(suffix: str, proposal_id: str) -> tuple[Path | None, str | None]:
    directory = _preview_dir()
    seen_previews: set[Path] = set()
    for state_path in sorted(directory.glob("*.state.json")):
        preview = state_path.with_name(state_path.name.removesuffix(".state.json") + ".md")
        try:
            state = json.loads(state_path.read_text())
        except (OSError, json.JSONDecodeError):
            if suffix in state_path.name:
                return preview, "corrupt"
            continue
        if not isinstance(state, dict) or str(state.get("account_suffix") or "") != suffix:
            continue
        seen_previews.add(preview)
        if not preview.is_file() or state.get("preview_id") != preview.stem:
            return preview, "corrupt"
        if state.get("preview_sha256") != hashlib.sha256(preview.read_bytes()).hexdigest():
            return preview, "corrupt"
        state_proposal = str(state.get("proposal_id") or "")
        if state.get("status") == "PENDING_APPROVAL":
            return preview, "pending_same" if state_proposal == proposal_id else "pending_conflict"
        if proposal_id and state_proposal == proposal_id:
            return preview, "already_previewed"
    for preview in sorted(directory.glob("*.md")):
        if preview in seen_previews or _state_path(preview).is_file():
            continue
        try:
            text = preview.read_text()
        except OSError:
            if suffix in preview.name:
                return preview, "corrupt"
            continue
        scoped = (f'"account_suffix":"{suffix}"' in text or f'"account_suffix": "{suffix}"' in text or
                  f"account_suffix:** {suffix}" in text or f"suffix {suffix}" in text)
        if scoped and any(marker in text for marker in _PENDING_MARKERS):
            return preview, "legacy_pending"
    return None, None


def _next_preview_id(suffix: str, now: datetime) -> str:
    prefix = f"RH-{now.astimezone(_ET):%Y%m%d}-{suffix}-"
    highest = 0
    for path in _preview_dir().glob(f"{prefix}*.md"):
        match = re.fullmatch(rf"{re.escape(prefix)}(\d{{2}})\.md", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    if highest >= 99:
        raise RuntimeError("Daily preview ID sequence exhausted at 99")
    return f"{prefix}{highest + 1:02d}"


def _render_preview(*, suffix: str, preview_id: str, proposal_id: str, now: datetime,
                    account: dict[str, Any], items: list[dict[str, Any]],
                    assessments: list[dict[str, Any]], summary: str,
                    release_conditions: list[str], source_artifacts: dict[str, str]) -> str:
    cohort = _SCOPES[suffix]
    snapshot = _account_snapshot(suffix, account)
    rows, immutable = [], []
    for index, item in enumerate(items, 1):
        order = item["order"]
        side = _side(order)
        quote = item.get("quote") or {}
        anchor = quote.get("ask") if side.startswith("BUY") else quote.get("bid")
        anchor_text = f"${float(anchor):,.4f}" if isinstance(anchor, (int, float)) else "n/a"
        rows.append(f"| {index} | {_symbol(order)} | {side} | {_quantity(order)} | "
                    f"{order.get('orderType', 'UNKNOWN')} | {order.get('duration', 'UNKNOWN')} | {anchor_text} |")
        immutable.append({"index": index, "idempotency_key": f"{preview_id}-{index:02d}",
                          "order": order, "quote": quote, "thesis": item.get("thesis")})
    machine = {"preview_id": preview_id, "proposal_id": proposal_id, "cohort": cohort,
               "mode": "live", "account_suffix": suffix, "created_at": now.isoformat(),
               "status": "pending", "orders_placed": False, "account_snapshot": snapshot,
               "orders": immutable, "broker_assessments": assessments,
               "release_conditions": release_conditions, "source_artifacts": source_artifacts,
               "human_action": {"approve": f"APPROVE {preview_id}", "deny": f"DENY {preview_id}"}}
    machine_json = json.dumps(machine, sort_keys=True, separators=(",", ":"))
    excluded = ", ".join(sorted((_SCOPES.keys() | _EXCLUDED_SUFFIXES) - {suffix}))
    controls = "\n".join(f"{i}. {c}" for i, c in enumerate(release_conditions, 1))
    return f"""# Schwab Order Preview — {preview_id}

- **preview_id:** {preview_id}
- **proposal_id:** {proposal_id}
- **cohort:** {cohort}
- **mode:** LIVE
- **account_suffix:** {suffix}
- **created:** {now.isoformat()}
- **status:** PENDING_APPROVAL
- **orders_placed:** false
- **scope:** Account suffix {suffix} only. Suffixes {excluded} are excluded.

## Fresh reconciliation

Account snapshot: liquidation value `{snapshot['liquidation_value']}`, cash available for trading `{snapshot['cash_available_for_trading']}`, available funds `{snapshot['available_funds']}`, positions `{snapshot['positions'] or 'none'}`.

## Research decision

{summary.strip()}

Source artifacts: `{json.dumps(source_artifacts, sort_keys=True)}`

## Exact immutable tickets

| # | Symbol | Side | Qty | Type | Duration | Quote anchor |
|---|---|---|---:|---|---|---:|
{chr(10).join(rows)}

Schwab previewOrder accepted every ticket with no effective REJECT or REVIEW. Estimated aggregate commissions and fees: `${sum(a['estimated_cost_cents'] for a in assessments) / 100:.2f}`.

## Immutable execution controls

Approval authorizes exactly the tickets above for account suffix {suffix}. No substitutions, quantity changes, account changes, added legs, or order-type changes are authorized. Before submission the interactive resolver must re-probe OAuth, reconcile the account and 60-day/current open-order ledger, verify this SHA-bound file, obtain fresh normal-session quotes, re-run Schwab previewOrder, atomically claim the decision, and persist every broker receipt. This scheduled workflow has no placement capability. HTTP acceptance is not a fill.

{controls}

## Approval decision

```
APPROVE {preview_id}
```

```
DENY {preview_id}
```

## Machine-readable record

```json
{machine_json}
```
"""


def _prepare_preview(suffix: str, args: dict[str, Any], **_: Any) -> str:
    lock_path = _preview_dir() / ".create.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return _prepare_preview_locked(suffix, args)
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def _prepare_preview_locked(suffix: str, args: dict[str, Any]) -> str:
    cohort = _SCOPES[suffix]
    if str(args.get("account_suffix") or "").strip() != suffix:
        return json.dumps({"success": False, "error": f"Preview tool is hard-scoped to suffix {suffix}."})
    if str(args.get("cohort") or "").strip() != cohort:
        return json.dumps({"success": False, "error": f"Preview tool is hard-scoped to cohort {cohort}."})
    proposal_id = str(args.get("proposal_id") or "").strip()
    summary = str(args.get("summary") or "").strip()
    items = args.get("items")
    conditions = args.get("release_conditions")
    sources = args.get("source_artifacts") or {}
    if not proposal_id or not summary:
        return json.dumps({"success": False, "error": "proposal_id and summary are required."})
    if not isinstance(items, list) or not items or len(items) > _MAX_ORDERS:
        return json.dumps({"success": False, "error": f"items must contain 1-{_MAX_ORDERS} exact tickets."})
    if not isinstance(conditions, list) or not conditions or not all(isinstance(c, str) and c.strip() for c in conditions):
        return json.dumps({"success": False, "error": "At least one explicit release condition is required."})
    if not isinstance(sources, dict):
        return json.dumps({"success": False, "error": "source_artifacts must be an object."})
    now = _now_utc()
    now_et = now.astimezone(_ET)
    if now_et.weekday() >= 5 or not (time(10, 5) <= now_et.time() <= time(12, 0)):
        return json.dumps({"success": False, "status": "OUTSIDE_ACTIVATION_WINDOW",
                           "error": "Preview creation is code-gated to weekdays 10:05-12:00 America/New_York.",
                           "orders_placed": False})
    existing, reason = _existing_preview(suffix, proposal_id)
    if existing:
        statuses = {"pending_same": "EXISTING_PENDING", "pending_conflict": "CONFLICTING_PENDING",
                    "already_previewed": "ALREADY_PREVIEWED", "corrupt": "CORRUPT_PREVIEW_STATE",
                    "legacy_pending": "LEGACY_PENDING_REQUIRES_MIGRATION"}
        errors = {"pending_same": None, "pending_conflict": "A different proposal already has a pending approval package.",
                  "already_previewed": "This proposal already has a durable preview.",
                  "corrupt": "A corrupt or orphan preview artifact requires manual quarantine.",
                  "legacy_pending": "A legacy pending preview lacks a SHA-bound state sidecar; migrate or resolve it first."}
        return json.dumps({"success": reason == "pending_same", "status": statuses.get(reason, "PREVIEW_STATE_ERROR"),
                           "preview_id": existing.stem, "preview_path": str(existing),
                           "orders_placed": False, "error": errors.get(reason, "Unknown preview conflict.")})
    cfg = _live_executor.load_config()
    if not cfg.raw_ok:
        return json.dumps({"success": False, "error": f"Executor config invalid: {cfg.error}"})
    if cfg.kill_switch:
        return json.dumps({"success": False, "error": "kill_switch is ON."})
    if cfg.mode != "live" or _mode.get_mode() != "live":
        return json.dumps({"success": False, "error": "Account is not consistently in LIVE mode."})
    if not cfg.tradeable(suffix):
        return json.dumps({"success": False, "error": f"Account {suffix} is not on the live allow-list."})
    account_hash, error = _live_executor.resolve_allowed_hash(suffix, cfg)
    if error or not account_hash:
        return json.dumps({"success": False, "error": error or "Could not resolve account hash."})
    try:
        account = _trader.get_account(account_hash, fields="positions")
        orders = _trader.get_orders(account_hash, (now - timedelta(days=60)).isoformat().replace("+00:00", "Z"),
                                    (now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"))
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Account/order reconciliation failed closed: {exc}"})
    if not isinstance(orders, list):
        return json.dumps({"success": False, "error": "Broker order response was not a list."})
    blocking = []
    for order in orders:
        if not isinstance(order, dict):
            return json.dumps({"success": False, "error": "Malformed broker order record."})
        status = str(order.get("status") or "UNKNOWN").upper()
        entered = _parse_order_time(order)
        is_today = entered is None or entered.astimezone(_ET).date() == now_et.date()
        if is_today or status not in _TERMINAL_ORDER_STATES:
            blocking.append(order)
    if blocking:
        statuses = sorted({str(order.get("status") or "UNKNOWN").upper() for order in blocking})
        return json.dumps({"success": False, "error": f"Current-day or older open broker orders exist: {statuses}"})
    assessments = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict) or not isinstance(item.get("order"), dict):
            return json.dumps({"success": False, "error": f"Item {index} has no exact order object."})
        order = item["order"]
        structural_error = _structural_ticket_error(order)
        if structural_error:
            return json.dumps({"success": False, "error": f"Item {index}: {structural_error}"})
        validation = _trader.validate_order(order)
        if not validation.get("valid"):
            return json.dumps({"success": False, "error": f"Item {index} is invalid.", "details": validation.get("errors")})
        try:
            broker_preview = _trader.preview_order(account_hash, order)
        except Exception as exc:
            return json.dumps({"success": False, "error": f"Schwab preview failed closed for item {index}: {exc}"})
        blockers = _preview_blockers(broker_preview)
        if blockers:
            return json.dumps({"success": False, "error": f"Schwab rejected/reviewed item {index}.", "details": blockers})
        assessments.append({"index": index, "symbol": _symbol(order), "accepted": True,
                            "estimated_cost_cents": _live_executor.preview_cost_estimate(broker_preview),
                            "validation": _validation_summary(broker_preview)})
    try:
        preview_id = _next_preview_id(suffix, now)
    except RuntimeError as exc:
        return json.dumps({"success": False, "error": str(exc), "orders_placed": False})
    path = _preview_dir() / f"{preview_id}.md"
    content = _render_preview(suffix=suffix, preview_id=preview_id, proposal_id=proposal_id, now=now,
                              account=account, items=items, assessments=assessments, summary=summary,
                              release_conditions=[c.strip() for c in conditions],
                              source_artifacts={str(k): str(v) for k, v in sources.items()})
    state_path = _state_path(path)
    try:
        _write_atomic(path, content)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _write_atomic(state_path, json.dumps({"preview_id": preview_id, "proposal_id": proposal_id,
                      "cohort": cohort, "account_suffix": suffix, "status": "PENDING_APPROVAL",
                      "orders_placed": False, "preview_sha256": digest, "created_at": now.isoformat(),
                      "updated_at": now.isoformat()}, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError as exc:
        path.unlink(missing_ok=True)
        state_path.unlink(missing_ok=True)
        return json.dumps({"success": False, "error": f"Could not persist preview package: {exc}"})
    _append_jsonl(_journal_path(suffix), {"event": "PREVIEW_CREATED", "preview_id": preview_id,
                  "proposal_id": proposal_id, "cohort": cohort, "account_suffix": suffix,
                  "status": "PENDING_APPROVAL", "orders_placed": False, "ticket_count": len(items),
                  "created_at": now.isoformat(), "preview_path": str(path), "state_path": str(state_path),
                  "preview_sha256": digest})
    return json.dumps({"success": True, "status": "PENDING_APPROVAL", "preview_id": preview_id,
                       "preview_path": str(path), "state_path": str(state_path), "preview_sha256": digest,
                       "ticket_count": len(items), "broker_preview_accepted": True, "orders_placed": False,
                       "approve": f"APPROVE {preview_id}", "deny": f"DENY {preview_id}"})


def _schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "description": description, "parameters": parameters}


def _register_read_tool(ctx: Any, *, name: str, toolset: str, schema: dict[str, Any],
                        handler: Callable[..., str], description: str, emoji: str) -> None:
    ctx.register_tool(name=name, toolset=toolset, schema=schema, handler=handler,
                      check_fn=_schwab._credentials_present,
                      requires_env=["SCHWAB_APP_KEY", "SCHWAB_APP_SECRET"],
                      description=description, emoji=emoji)


def _register_surface(ctx: Any, suffix: str, preview: bool) -> None:
    cohort = _SCOPES[suffix]
    toolset = f"account{suffix}_{'preview' if preview else 'readonly'}"
    prefix = f"account{suffix}_{'preview_' if preview else ''}"
    no_args = {"type": "object", "properties": {}, "additionalProperties": False}
    token_args = {"type": "object", "properties": {"probe": {"type": "boolean", "default": True}},
                  "additionalProperties": False}
    quote_args = {"type": "object", "properties": {"symbols": {"type": "array", "items": {"type": "string"},
                  "minItems": 1, "maxItems": 30}}, "required": ["symbols"], "additionalProperties": False}
    handlers = [
        (f"{prefix}token_health", _schema(f"{prefix}token_health", f"Safe Trader OAuth health for suffix {suffix}.", token_args),
         _token_health, f"Safe Trader OAuth health for suffix {suffix}.", "🔐"),
        (f"{prefix}read_account", _schema(f"{prefix}read_account", f"Read only suffix-{suffix} balances and positions.", no_args),
         lambda args, _s=suffix, **kw: _read_account(_s, args, **kw), f"Redacted account {suffix} balances and positions.", "📊"),
        (f"{prefix}read_orders", _schema(f"{prefix}read_orders", f"Read suffix-{suffix} current-day and open orders.", no_args),
         lambda args, _s=suffix, **kw: _read_orders(_s, args, **kw), f"Current-day and open orders for {suffix}.", "📖"),
        (f"{prefix}quote", _schema(f"{prefix}quote", "Read bounded market-data quotes; never places orders.", quote_args),
         _quotes, f"Read-only quotes for account {suffix} research.", "📈"),
    ]
    for name, schema, handler, description, emoji in handlers:
        _register_read_tool(ctx, name=name, toolset=toolset, schema=schema, handler=handler,
                            description=description, emoji=emoji)
    if preview:
        name = f"account{suffix}_prepare_preview"
        params = {"type": "object", "properties": {
            "account_suffix": {"type": "string", "enum": [suffix]},
            "cohort": {"type": "string", "enum": [cohort]},
            "proposal_id": {"type": "string"}, "summary": {"type": "string"},
            "source_artifacts": {"type": "object", "additionalProperties": {"type": "string"}},
            "release_conditions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "items": {"type": "array", "minItems": 1, "maxItems": _MAX_ORDERS,
                      "items": {"type": "object", "properties": {"order": {"type": "object"},
                                "quote": {"type": "object"}, "thesis": {"type": "string"}},
                                "required": ["order", "quote", "thesis"], "additionalProperties": False}},
        }, "required": ["account_suffix", "cohort", "proposal_id", "summary", "source_artifacts",
                         "release_conditions", "items"], "additionalProperties": False}
        schema = _schema(name, f"Preview-only suffix-{suffix} handoff. Reconciles the isolated account and orders, calls "
                         "Schwab previewOrder, and writes an immutable PENDING_APPROVAL package. Cannot place orders.", params)
        _register_read_tool(ctx, name=name, toolset=toolset, schema=schema,
                            handler=lambda args, _s=suffix, **kw: _prepare_preview(_s, args, **kw),
                            description=f"Preview-only file-backed Schwab approval package for suffix {suffix}.", emoji="📋")


def register(ctx: Any) -> None:
    for suffix in _SCOPES:
        _register_surface(ctx, suffix, preview=False)
        _register_surface(ctx, suffix, preview=True)
