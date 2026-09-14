"""Schwab Streamer (WebSocket) client.

Implements the Schwab Streamer API connection contract:
  1. Fetch streamer connection info + ids from GET User Preference (via the
     injected `CredentialProvider`).
  2. Open ONE WebSocket (Schwab allows a single streamer connection per user —
     response code 12 = CLOSE_CONNECTION if you exceed it).
  3. Send ADMIN/LOGIN and WAIT for a successful response before any SUBS
     (avoids the documented race -> codes 20/22).
  4. SUBS/ADD/UNSUBS/VIEW to services; decode numbered fields to named dicts.
  5. Handle heartbeats, response codes, and re-login on LOGIN_DENIED (code 3).

This module is transport + protocol only. It depends on a CredentialProvider
for the access token and the GET User Preference values; that provider is
supplied by the OAuth/REST layer (built when those specs are provided). The
client is therefore fully unit-testable with a fake provider and a fake socket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .fields import (
    RESPONSE_CODES,
    SERVICE_ALL_FIELDS,
    decode_data_message,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Credential / connection info contract (filled by the OAuth + REST layer)
# ---------------------------------------------------------------------------
@dataclass
class StreamerInfo:
    """Connection info sourced from GET User Preference + POST Token.

    All five non-token fields come straight from the GET User Preference
    response's `streamerInfo`/identifiers; `access_token` from POST Token.
    """
    websocket_url: str
    access_token: str
    schwab_client_customer_id: str
    schwab_client_correl_id: str
    schwab_client_channel: str
    schwab_client_function_id: str


class CredentialProvider:
    """Interface the streamer uses to obtain fresh connection info.

    The OAuth/REST layer implements this. Until then a stub raises a clear
    error so the agent operates preview-only rather than fabricating data.
    """

    async def get_streamer_info(self) -> StreamerInfo:  # pragma: no cover - interface
        raise NotImplementedError(
            "Schwab OAuth/REST layer not configured yet — cannot obtain a "
            "streamer access token or GET User Preference values. Market-data "
            "streaming is unavailable until credentials are provided."
        )

    def is_configured(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# The streamer client
# ---------------------------------------------------------------------------
@dataclass
class _Subscription:
    service: str
    keys: set
    fields: str


class SchwabStreamerClient:
    """Singleton-style async Schwab streamer client.

    Use one instance per user. Opening a second WebSocket will be rejected by
    Schwab (code 12). `connect()` is idempotent — calling it while already
    connected is a no-op.
    """

    def __init__(self, provider: CredentialProvider):
        self._provider = provider
        self._ws = None
        self._info: Optional[StreamerInfo] = None
        self._connected = False
        self._logged_in = False
        self._req_counter = 0
        self._subs: Dict[str, _Subscription] = {}
        self._login_event: Optional[asyncio.Event] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._data_handlers: List[Callable[[list], Awaitable[None]]] = []
        self._lock = asyncio.Lock()
        # injected for tests: a factory returning an async ws connection
        self._connect_factory: Optional[Callable[[str], Awaitable[Any]]] = None

    # -- handlers -----------------------------------------------------------
    def on_data(self, handler: Callable[[list], Awaitable[None]]) -> None:
        """Register an async handler called with decoded data rows."""
        self._data_handlers.append(handler)

    def _next_request_id(self) -> str:
        self._req_counter += 1
        return str(self._req_counter)

    def _admin_ids(self) -> Dict[str, str]:
        assert self._info is not None
        return {
            "SchwabClientCustomerId": self._info.schwab_client_customer_id,
            "SchwabClientCorrelId": self._info.schwab_client_correl_id,
        }

    # -- connection ---------------------------------------------------------
    async def connect(self) -> None:
        """Open the WebSocket and complete LOGIN. Idempotent."""
        async with self._lock:
            if self._connected and self._logged_in:
                return
            if not self._provider.is_configured():
                raise RuntimeError(
                    "Schwab credentials not configured — streaming unavailable."
                )
            self._info = await self._provider.get_streamer_info()
            self._ws = await self._open_socket(self._info.websocket_url)
            self._connected = True
            self._login_event = asyncio.Event()
            # start the read loop BEFORE login so we catch the login response
            asyncio.ensure_future(self._read_loop())
            await self._login()

    async def _open_socket(self, url: str):
        if self._connect_factory is not None:
            return await self._connect_factory(url)
        import websockets  # local import; dependency already pinned in pyproject
        return await websockets.connect(url, max_size=None)

    async def _login(self) -> None:
        assert self._info is not None
        req = {
            "service": "ADMIN",
            "command": "LOGIN",
            "requestid": self._next_request_id(),
            **self._admin_ids(),
            "parameters": {
                "Authorization": self._info.access_token,
                "SchwabClientChannel": self._info.schwab_client_channel,
                "SchwabClientFunctionId": self._info.schwab_client_function_id,
            },
        }
        await self._send(req)
        # Wait for a successful LOGIN response before allowing any SUBS.
        try:
            await asyncio.wait_for(self._login_event.wait(), timeout=15)
        except asyncio.TimeoutError:
            raise RuntimeError("Schwab streamer LOGIN timed out (no response).")
        if not self._logged_in:
            raise RuntimeError("Schwab streamer LOGIN denied.")

    async def _send(self, request: Dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError("Streamer socket not open.")
        await self._ws.send(json.dumps({"requests": [request]}))

    # -- subscriptions ------------------------------------------------------
    async def subscribe(self, service: str, keys: List[str],
                        fields: Optional[str] = None, command: str = "SUBS") -> str:
        """SUBS/ADD to a service. Returns the requestid used.

        `fields=None` subscribes to all known fields for the service.
        """
        if not self._logged_in:
            raise RuntimeError("Must LOGIN before subscribing.")
        flds = fields if fields is not None else SERVICE_ALL_FIELDS.get(service, "0")
        rid = self._next_request_id()
        req = {
            "service": service,
            "command": command,
            "requestid": rid,
            **self._admin_ids(),
            "parameters": {"keys": ",".join(k.upper() for k in keys), "fields": flds},
        }
        await self._send(req)
        sub = self._subs.get(service)
        if command == "SUBS" or sub is None:
            self._subs[service] = _Subscription(service, set(k.upper() for k in keys), flds)
        else:  # ADD
            sub.keys.update(k.upper() for k in keys)
        return rid

    async def unsubscribe(self, service: str, keys: List[str]) -> str:
        rid = self._next_request_id()
        req = {
            "service": service,
            "command": "UNSUBS",
            "requestid": rid,
            **self._admin_ids(),
            "parameters": {"keys": ",".join(k.upper() for k in keys)},
        }
        await self._send(req)
        if service in self._subs:
            for k in keys:
                self._subs[service].keys.discard(k.upper())
        return rid

    async def logout(self) -> None:
        if self._ws is None:
            return
        try:
            await self._send({
                "service": "ADMIN",
                "command": "LOGOUT",
                "requestid": self._next_request_id(),
                **self._admin_ids(),
                "parameters": {},
            })
        finally:
            await self._close()

    async def _close(self) -> None:
        self._connected = False
        self._logged_in = False
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    # -- read loop ----------------------------------------------------------
    async def _read_loop(self) -> None:
        ws = self._ws
        try:
            async for raw in ws:
                await self._handle_message(raw)
        except Exception as exc:  # connection dropped
            logger.warning("Schwab streamer read loop ended: %s", exc)
            await self._close()

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            logger.warning("Schwab streamer: non-JSON message dropped")
            return

        if "notify" in msg:
            # heartbeats — keepalive only
            return

        if "response" in msg:
            for resp in msg["response"]:
                self._handle_response(resp)
            return

        if "data" in msg:
            decoded = decode_data_message(msg)
            for handler in self._data_handlers:
                try:
                    await handler(decoded)
                except Exception:
                    logger.exception("Schwab streamer data handler error")
            return

    def _handle_response(self, resp: Dict[str, Any]) -> None:
        service = resp.get("service")
        command = resp.get("command")
        content = resp.get("content", {}) or {}
        code = content.get("code")
        name, severs = RESPONSE_CODES.get(code, ("UNKNOWN", None))

        if service == "ADMIN" and command == "LOGIN":
            self._logged_in = (code == 0)
            if self._login_event is not None:
                self._login_event.set()
            if code == 0:
                logger.info("Schwab streamer login OK: %s", content.get("msg"))
            else:
                logger.error("Schwab streamer login failed (%s): %s", name, content.get("msg"))
            return

        if code not in (0, 26, 27, 28, 29):
            logger.warning("Schwab streamer %s/%s -> code %s (%s): %s",
                           service, command, code, name, content.get("msg"))
        if severs:
            logger.error("Schwab streamer connection will sever (code %s = %s).", code, name)
