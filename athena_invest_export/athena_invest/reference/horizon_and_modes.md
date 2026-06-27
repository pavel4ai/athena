# Horizon Classes & Portfolio Modes

Athena Allocator classifies each cohort into a **horizon class** (set by the
mandate) and the portfolio into a **mode** (set dynamically by Allocator +
Sentinel based on regime, gains, and proximity to horizon end).

## Horizon Classes (from the mandate)

### Horizon Class A — 0–30 days
- **Objective:** maximize asymmetry
- **Focus:** momentum, events, news catalysts
- **Construction:** concentrated, catalyst-timed, Information/Event alpha led.

### Horizon Class B — 30–180 days
- **Objective:** capture trend
- **Focus:** sector rotation, earnings revisions, macro shifts
- **Construction:** thematic tilts, factor + macro lenses, moderate diversification.

### Horizon Class C — 180 days+
- **Objective:** compound capital
- **Focus:** quality, cash flow, valuation
- **Construction:** Graham lens led, diversified, low turnover.

**Construction rules change automatically by horizon class.** The mandate's
horizon maps to a class:
- intraday / swing / 30-day → A
- 90-day → A/B boundary; 6-month → B
- 1-year → B/C boundary; multi-year / retirement → C

## Time-Horizon Phases (Allocator)
- 12-month growth mode
- 6-month tactical mode
- 30-day defense/growth mode
- user-requested capital preservation mode

## Portfolio Modes (Allocator + Sentinel classify the book)

### Attack Mode
Maximize upside. Higher concentration, higher beta, full risk budget.

### Balanced Mode
Balanced return and risk. Diversified, moderate beta.

### Defense Mode
Protect gains. Reduced beta, raised cash, hedges on.

### Capital Preservation Mode
Primary objective: **avoid loss.** Minimal risk, high cash, only highest-
conviction asymmetric bets. The Timur 100K project entered this mode in its
final phase and successfully protected gains.

## Critical Rule — "Do Not Lose the Win"
**Never recommend full-risk exposure near horizon-end unless a catch-up is
required** (i.e. behind objective with time running out). As the cohort
approaches its horizon end with gains banked, Sentinel forces a shift toward
Defense / Capital Preservation.
