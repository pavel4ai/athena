# Schwab Market-Data + Trader Plugin

Token-gated Schwab integration for Athena Schwab. Provides read-only market
data + accounts, and a validated order layer (placement is **post-approval
only**, driven by the orchestrator — this plugin never auto-places).

## Modules
- `fields.py`  — Streamer numbered→named field decoders + response codes.
- `streamer.py`— WebSocket client (singleton; login→subscribe sequencing).
- `symbols.py` — Schwab symbol formatting (equity/option/future/fut-opt/forex).
- `oauth.py`   — OAuth 2 3-legged flow, token storage/refresh, token health,
                 RealCredentialProvider (GET User Preference for the streamer).
- `trader.py`  — REST: accounts/positions/transactions/orders + order builder
                 with instruction validation (EQUITY/OPTION only; futures
                 propose-only).
- `__init__.py`— token-gated tools: `schwab_quote`, `schwab_accounts`,
                 `schwab_token_health`.

## Credentials (secrets → ~/.athena/.env)
```
SCHWAB_APP_KEY=<client_id>
SCHWAB_APP_SECRET=<client_secret>
SCHWAB_CALLBACK_URL=https://127.0.0.1   # must match the app's registered callback
```
Tools stay hidden (zero footprint) until SCHWAB_APP_KEY + SCHWAB_APP_SECRET exist.

## One-time consent (CAG/LMS) — establishes the 7-day refresh token
```python
from schwab_marketdata import oauth
print(oauth.build_authorization_url())     # 1. open in browser, log in, consent
# 2. you'll land on a 404 at the callback; copy the ?code=... from the address bar
oauth.exchange_code_for_tokens("<code>")   # 3. mints + stores access+refresh tokens
```
Tokens are saved to `$ATHENA_HOME/athena_invest/schwab/tokens.json` (chmod 600).

## Token lifecycle
- Access token: 30 min — auto-refreshed (300s skew) on demand.
- Refresh token: 7 days — on expiry (or password reset) the consent flow above
  must be repeated. The token-health cron watches this and alerts before expiry.

## What works now vs. pending
- LIVE-VERIFIED: OAuth consent → token mint/refresh → REST market-data quotes
  (`/marketdata/v1/quotes`). Real AAPL/SPY/NVDA quotes confirmed via the
  `schwab_quote` tool.
- Built + unit-tested (31 tests, no network): field decode, symbol formatting,
  streamer protocol, token math, order builder/validator, REST simplifier, gate.

## Entitlement note (important)
The `schwab_quote` tool defaults to `transport="rest"` (Market Data Production
REST), which is what a data-only app is entitled to. The WebSocket **Streamer**
(`transport="stream"`) needs the GET User Preference endpoint, which lives under
the **Trader API** — a data-only app gets 401 there. Likewise `schwab_accounts`
and order placement need Trader API entitlement. Those light up with the
separate trading app. The streamer code is built + tested and ready for that app.

## Tests
```
python -m pytest ~/.athena/plugins/schwab_marketdata/ -q --asyncio-mode=auto
```
