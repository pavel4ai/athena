# Performance Metrics & Attribution

Athena Archivist computes these per **cohort** (and for the aggregate book).
A cohort = an isolated account / strategy with its own mandate. Metrics are
written to `cohorts/<name>/performance.md` and rolled into reports.

## Return & Risk Metrics
- Total return
- CAGR
- Daily P/L
- Monthly P/L
- Max drawdown
- Sharpe ratio
- Sortino ratio
- Beta (vs SPY)

## Benchmark-Relative (Alpha)
- Alpha vs **SPY**
- Alpha vs **QQQ**
- Alpha vs **Berkshire Hathaway (BRK.B)**

## Activity & Quality
- Win rate
- Turnover
- Cash utilization

## Attribution (three cuts)
- **Position attribution** — which positions drove return.
- **Sector attribution** — which sectors drove return.
- **Decision attribution** — which decisions / which agents drove return, and
  **what was luck vs. repeatable process** (the core learning question).

## Decision-History Narrative (human-readable)
Archivist maintains a plain-language log of *why* each major decision was made,
e.g.:
- initial allocation
- a thematic add (e.g. "India add")
- a volatility hedge decision
- a risk-on rotation
- a liquidation / preservation phase

Each entry: date, decision, rationale, which agent(s) recommended it, the
lenses/alpha source cited, and — once resolved — the outcome and the luck-vs-
process verdict.
