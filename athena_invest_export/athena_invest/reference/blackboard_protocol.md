# Blackboard Protocol — How Agents Communicate

Athena's subagents are **persistent via durable state**: they do not run as
resident processes between invocations, but they coordinate through a shared
set of **human-readable markdown files** (the "blackboard") that each
invocation reloads, reads upstream sections from, and appends its own output to.
Every file is auditable by a human at any time.

## Runtime Model (how each agent actually executes)

- **Delegated (isolated context via `delegate_task`):** Athena Scout, Athena
  Analyst, Athena Oracle. These pull large volumes (X feeds, filings, price
  history) that would flood the orchestrator and break prompt caching. Each
  runs in its own context, writes its blackboard file, and returns only a
  compact summary.
- **Inline (sequential phases in the orchestrator session):** Athena Allocator,
  Athena Sentinel, Athena Archivist, and Schwab order-preview prep. These are
  decision-logic agents — cheap, need the orchestrator's full picture, and
  benefit from cache reuse. They read the blackboard, apply rules, write a file.
- **Never delegated — orchestrator-owned:** the human-approval handshake and
  Athena Schwab order *execution*. A leaf subagent cannot run the approval
  workflow and must not hold broker authority. Execution always happens in the
  main Athena session after explicit human approval.

## Information Flow (one direction, top to bottom)

```
Athena Scout      → blackboard/scout_narratives.md   (intel, X velocity, regime signals)
Athena Oracle     → blackboard/oracle_theses.md      (theses, scenarios, regime call)
Athena Analyst    → blackboard/analyst_rankings.md   (fundamental + quant scores)
Athena Allocator  → blackboard/allocator_target.md   (target portfolio + trade list)
Athena Sentinel   → blackboard/sentinel_risk.md      (risk validation, vetoes, dashboard)
Athena Schwab     → schwab/previews/<ts>.md          (order preview for approval)
Athena Archivist  → cohorts/<name>/decision_journal.jsonl + performance.md
Regime (Scout+Oracle joint) → blackboard/regime.md
```

## Rules
1. **Each agent owns exactly one primary output file** and only writes there.
   It may READ any upstream file but must not overwrite another agent's file.
2. **Append, don't clobber.** Blackboard files keep a dated history; the latest
   section is at the top with a `## <ISO timestamp> — <cohort>` header.
3. **Every entry is timestamped and cohort-tagged.** No untagged writes.
4. **Schemas are enforced.** Each output carries both a human-readable markdown
   block AND a fenced ```json block matching that agent's required schema
   (so downstream agents and tooling can parse it).
5. **Cohort isolation is sacred.** An agent working a cohort reads/writes only
   that cohort's files plus the shared blackboard sections tagged for it.
   Never mix positions, cash, or theses across cohorts.

## Standard Entry Header
```
## 2026-06-24T13:00:00Z — cohort: <name> — agent: Athena <Role>
```
Followed by the human-readable analysis, then the ```json schema block.
