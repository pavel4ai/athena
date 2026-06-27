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
