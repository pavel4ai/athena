# Athena Investment Intelligence — System Index

Agentic investment platform. Maximizes expected risk-adjusted return over a
user-specified horizon via macro analysis, quant reasoning, fundamental
research, alternative-information (X/news) gathering, disciplined risk control,
and continuous learning. **Proposes; never executes without explicit human
approval.**

## State Root
`~/.athena/athena_invest/`

## Directory Map
- `reference/` — the shared constitution (load these first; agents depend on them)
  - `philosophy.md` — mission, 8 principles, 7 lessons, operating posture
  - `lenses.md` — Graham / Fabozzi / Hull-McMillan / Chan / Macro
  - `alpha_taxonomy.md` — Beta / Factor / Event / Information
  - `athena_score.md` — 0–100 composite (Macro20/Fund20/Quant20/News15/X10/RR15)
  - `regime_engine.md` — 9 regimes; current/previous/P(change ≤30d)
  - `exit_schema.md` — mandatory exit-strategy gate
  - `horizon_and_modes.md` — Horizon Classes A/B/C; Attack/Balanced/Defense/Preservation
  - `metrics.md` — per-cohort performance + 3-way attribution
  - `blackboard_protocol.md` — how agents communicate via markdown
- `mandate/` — per-cohort mandates (`_TEMPLATE.yaml`); REQUIRED before allocation
- `cohorts/<name>/` — per-cohort portfolio.json, performance.md, decision_journal.jsonl
- `blackboard/` — shared agent outputs (scout/oracle/analyst/allocator/sentinel/regime)
- `schwab/` — token state, order previews, reconciliation (account-isolated)
- `reports/` — daily / weekly / monthly briefings
- `agents/` — agent system-prompt specs (the 8 Athena agents)

## The 8 Agents
1. **Athena** — orchestrator (this main session): cron, coordination, approval workflow, reconciliation, reporting, cohort isolation.
2. **Athena Scout** — market intel + X/Twitter news velocity (Information alpha).
3. **Athena Analyst** — fundamental + quantitative evaluation.
4. **Athena Allocator** — portfolio construction by horizon class + mode.
5. **Athena Sentinel** — risk, drawdown protection, "do not lose the win", veto.
6. **Athena Oracle** — thesis generation, scenarios, second-order effects, regime call.
7. **Athena Archivist** — memory, compliance, performance, attribution, post-mortems.
8. **Athena Schwab** — Charles Schwab API: reconcile, ticket prep, validation, execution (post-approval only).

## Hard Gates
- No allocation without a valid **mandate** (5 inputs).
- No position without a complete **exit strategy**.
- No recommendation without named **lenses** + **alpha source**.
- No trade without explicit **human approval**.
- **Cohort isolation** — never mix accounts.
- Recommendations **below Athena Score 70** avoided (waiver required).

## Build Status
- [x] Directory structure
- [x] Reference layer (constitution)
- [x] Mandate template
- [x] Agent system-prompt specs (8) — all 10-section template + MD/JSON schemas
- [x] Schwab plugin (token-gated) — 31 tests pass; LIVE market data verified:
  - [x] Market-data REST (`/marketdata/v1`): quotes LIVE-VERIFIED (AAPL/SPY/NVDA)
  - [x] OAuth: consent done, tokens minted/stored, refresh + token health working
  - [x] Streamer (WebSocket): built + tested (needs Trader API entitlement to run)
  - [x] Trader REST + validated order builder (built; needs trading app entitlement)
  - [x] Tools: schwab_quote (REST default), schwab_accounts, schwab_token_health
  - [ ] Trading app: separate Schwab app w/ Trader API for accounts + execution
- [ ] Skills (methodologies + Schwab playbook + blackboard protocol)
- [ ] Cron jobs (armed last, after review)
- [ ] First cohort mandate (needs your 5 inputs)

## Schwab integration (plugin at ~/.athena/plugins/schwab_marketdata/)
- `fields.py` — numbered→named decoders for all LEVELONE_* + CHART_* services, response codes
- `streamer.py` — SchwabStreamerClient (singleton WS, login→subscribe sequencing) + CredentialProvider
- `symbols.py` — Schwab symbol formatting (equity/option/future/future-option/forex)
- `oauth.py` — OAuth 2 3-legged flow, token storage/refresh (30min/7day), token_health, RealCredentialProvider
- `trader.py` — accounts/positions/transactions/orders REST + validated order builder (EQUITY/OPTION; futures propose-only)
- `__init__.py` — token-gated tools: schwab_quote, schwab_accounts, schwab_token_health (toolset: schwab)
- `README.md` — credential setup + one-time consent (CAG/LMS) instructions
- NEEDED NEXT: app credentials in ~/.athena/.env + one-time browser consent to go live.
