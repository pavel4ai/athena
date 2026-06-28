# Athena Investment Intelligence — Build Progress & TODO

Last updated: 2026-06-27. Pick up from "REMAINING TO-DOS" below.

## WHERE THINGS LIVE
- System state + reference + agents: `~/.athena/athena_invest/`
- Schwab plugin: `~/.athena/plugins/schwab_marketdata/`
- Token-health script: `~/.athena/scripts/schwab_token_health_check.py`
- Secrets (Schwab creds): `~/.athena/.env` (chmod 600)
- Schwab tokens: `~/.athena/athena_invest/schwab/tokens.json` (chmod 600)

## DECIDED PROFILE (from instruction intake)
- Broker: Charles Schwab API. Execution: EVERY order requires explicit human approval.
- Assets: equities/ETFs + options + futures (FUTURES = propose-only; Schwab API
  has no futures order entry — confirmed by both specs).
- Horizon/cadence: position/core, weeks–months, weekly rebalance.
- Delivery: Telegram (briefings + approvals) — GATEWAY NOT YET CONFIGURED.
- Risk limits: portfolio value from Schwab + standard limits.
- Universe: Athena proposes macro-driven universe; user approves.

## COMPLETED ✓

### Reference layer (the constitution) — `reference/`
philosophy, lenses (Graham/Fabozzi/Hull-McMillan/Chan/Macro), alpha_taxonomy
(Beta/Factor/Event/Information), athena_score (Macro20/Fund20/Quant20/News15/
X10/RR15, avoid <70), regime_engine (9 regimes), exit_schema (mandatory gate),
horizon_and_modes (classes A/B/C + Attack/Balanced/Defense/Preservation +
"do not lose the win"), metrics (3 benchmarks SPY/QQQ/BRK + 3 attribution cuts),
blackboard_protocol (+ runtime model).

### Mandate gate — `mandate/_TEMPLATE.yaml`
5 required inputs (horizon, objective, risk tolerance, tax jurisdiction, account
type). Validated: rejects empty, accepts complete, derives horizon class.

### 8 agent specs — `agents/` (all 10-section template + MD + JSON schemas)
00 Athena (orchestrator), 01 Scout, 02 Oracle, 03 Analyst, 04 Allocator,
05 Sentinel, 06 Archivist, 07 Schwab.
Runtime model: Scout/Oracle/Analyst = delegated; Allocator/Sentinel/Archivist =
inline; Schwab execution + approval = orchestrator-owned, never delegated.

### Schwab integration — `plugins/schwab_marketdata/` (31 tests pass)
- fields.py — Streamer numbered→named decoders (all LEVELONE_*/CHART_*) + codes.
- streamer.py — WebSocket client (singleton, login→subscribe sequencing). BUILT
  + tested; needs Trader API entitlement to actually run (uses User Preference).
- symbols.py — Schwab symbol formatting (equity/option/future/fut-opt/forex).
- oauth.py — OAuth 3-legged, token mint/refresh (30min/7day), token_health,
  RealCredentialProvider. CONSENT DONE, TOKENS LIVE.
- trader.py — accounts/positions/transactions/orders REST + validated order
  builder (EQUITY/OPTION instruction matrix enforced; futures rejected). BUILT;
  needs trading-app entitlement.
- rest_marketdata.py — Market Data Production REST (/marketdata/v1). LIVE.
- __init__.py — tools: schwab_quote (REST default, LIVE), schwab_accounts,
  schwab_token_health. All token-gated.

### Schwab app: athena-market-data (PRODUCTION, live)
- Entitled to Market Data Production REST only (NOT Trader API).
- LIVE-VERIFIED: real quotes for AAPL/SPY/NVDA through schwab_quote.
- Callback https://127.0.0.1, order limit 0.
- NOTE: Client ID/Secret were shared in plaintext chat → consider rotating
  the secret in the Schwab portal (just update ~/.athena/.env after).

### Token-health cron — job_id 776d75e000df
- Schedule: 0 8,20 * * * (twice daily). no_agent (zero tokens).
- Script: schwab_token_health_check.py — alerts only within 36h of refresh
  expiry / expired / unconfigured; silent when healthy. Both alert paths tested.
- DELIVERY: currently "local" (gateway/Telegram not set up). NEEDS RETARGET to
  Telegram once gateway is configured (see TODO).

## PRE-FLIGHT / MOCK MODE (live data, simulated fills) — READY ✓

Run Athena hands-off for days with REAL market data but SIMULATED trades, then
flip to live cleanly.

- `mode.py` — broker mode switch (mock|live); default mock (safe). Stored in
  athena_invest/schwab/mode.json.
- `mock_broker.py` — paper broker on live quotes. Market fills at ask/bid (+2bps
  slippage), limit orders fill only when live price crosses; per-cohort cash/
  positions/transactions persisted to athena_invest/mock/<cohort>.json.
- Tools: `schwab_place_order` (routes mock|live per mode; needs human approval
  upstream), `schwab_mock_admin` (get/set mode, fund cohort, read account,
  process working orders, reset).
- 43 tests pass. LIVE-VERIFIED end to end: funded two cohorts, bought NVDA/SPY at
  live prices, limit order stayed WORKING, NAV tracked, cohort isolation held.
- Go-live: `python ~/.athena/scripts/schwab_go_live.py` archives mock state +
  flips mode to live (--dry-run / --purge options).

Pre-flight usage:
  1. `schwab_mock_admin set_mode mock` (default)
  2. `schwab_mock_admin fund cohort=<name> cash=<amt>` per cohort
  3. Run Athena loop; approved orders fill via mock broker on live prices
  4. `schwab_mock_admin account cohort=<name>` to see NAV/positions anytime
  5. When done: `schwab_go_live.py` → add trading-app creds → live

## BLOOMBERG-STYLE LIVE TICKER BAR (CLI) — DONE ✓

A fitted, single-line market ticker pinned above the CLI status bar, showing
mega-cap last price + % change (green ▲ / red ▼), refreshed every 15s from the
Schwab Market Data REST API and repainted ~1s (display.cli_refresh_interval=1.0).

- Core (cli.py, +44 lines, generic + opt-in): a "supplemental status line"
  registry — `AthenaCLI.register_supplemental_status_line(provider)` +
  `_build_supplemental_status_widgets()`, wired into the layout above status_bar.
  Any plugin can supply a 1-line fragment provider; bar auto-hides when it
  returns []. Exceptions in a provider are swallowed (can never break the prompt).
- Plugin (ticker.py): background daemon poller updates a price cache; render path
  reads cache only (never blocks). Gated on Schwab creds + live data — invisible
  if the API is down/unconfigured. Symbols: AAPL/MSFT/NVDA/GOOGL/AMZN/META/SPY/QQQ.
- Verified: live line renders e.g. " MKT AAPL 282.65 ▲2.72% │ MSFT 372.79 ▲5.66% ...".
- NOTE: cli.py is a CORE file edit (the user confirmed this is their own Athena).
  The change is generic (not Schwab-specific) so it's reusable by any plugin.

## REMAINING TO-DOS (in suggested order)

1. [ ] TRADING APP (Schwab #2 with Trader API entitlement)
   - Create separate Schwab app subscribed to Trader API - Individual.
   - Order limit ~10/min. Callback https://127.0.0.1.
   - Add its creds to ~/.athena/.env as SCHWAB_TRADER_APP_KEY/SECRET (plan: the
     plugin should support TWO credential sets — data app vs trading app — so the
     data app can never place orders). Currently the plugin uses one cred set;
     extend oauth.py + __init__.py to route order/accounts/streamer through the
     trading creds and quotes through the data creds.
   - This unlocks: schwab_accounts, order placement, AND the WebSocket streamer
     (transport="stream"), since User Preference is Trader-gated.
   - Re-run consent for the trading app.

2. [ ] GATEWAY / TELEGRAM SETUP
   - Configure the gateway so briefings + approval prompts + token-health alerts
     reach Telegram. Token already in .env; need chat wiring + gateway.enabled.
   - Then retarget cron 776d75e000df delivery from "local" to the Telegram chat
     (cronjob action=update, deliver=telegram:<chat_id>:<thread_id>).

3. [ ] SKILLS LAYER — `~/.athena/skills/` (athena-invest category)
   - Per-agent methodology skills (how Scout/Oracle/Analyst/etc. actually work).
   - Schwab API playbook skill (consent flow, refresh, quote/account/order recipes).
   - Blackboard protocol skill (read upstream → write own file, append-only).
   - X/news-velocity skill (xurl Athena-Investor app, horizon-scoped windows).
   - Follow the HARDLINE skill standards in AGENTS.md (≤60-char description, etc.).

4. [ ] ORCHESTRATION WIRING
   - The actual run sequence (Scout→Oracle→Analyst→Allocator→Sentinel→Schwab
     preview→approval→Archivist) as a runnable flow (likely a skill the
     orchestrator follows + the blackboard files).
   - The 7-step approval handshake on Telegram/terminal (preview_id → APPROVE).

5. [ ] CRON SCHEDULE (arm LAST, after review)
   - Daily pre-market brief; intraday risk watch (market hours); weekly research
     + rebalance proposal; weekly learning/post-mortem. (Token-health already done.)

6. [ ] FIRST COHORT MANDATE
   - Collect the 5 inputs, write mandate/<cohort>.yaml, derive horizon class.
   - Then Athena can run its first (paper/preview) cycle.

## QUICK VERIFY COMMANDS
- Tests: `cd ~/Code/athena && source .venv/bin/activate && python -m pytest ~/.athena/plugins/schwab_marketdata/ -q --asyncio-mode=auto`
- Live quote: load .env, then `from schwab_marketdata import rest_marketdata; rest_marketdata.get_quotes(["AAPL"])`
- Token health: `python ~/.athena/scripts/schwab_token_health_check.py` (silent = healthy)
- Cron list: `athena cron list`
