# Exit Strategy Schema (MANDATORY GATE)

**No position may be recommended without a complete exit strategy.**
Athena rejects any recommendation missing any field below. Every position must
have its exit thesis defined *before* entry (Lesson 7).

## Required Fields

```yaml
entry_thesis: >          # Why enter now. Must name lenses + alpha source.
expected_catalysts:      # List of datable/observable events expected to play out
  - ...
expected_holding_period: # e.g. "6-12 weeks", tied to horizon class
exit_conditions:         # Conditions that REALIZE the thesis (take profit)
  - ...
thesis_failure_conditions: # Conditions that INVALIDATE the thesis (cut loss)
  - ...
max_acceptable_drawdown: # % loss on the position that forces exit regardless
```

## Validation Rules
- `entry_thesis` must reference at least one of the five lenses and one alpha class.
- `expected_holding_period` must be consistent with the cohort's horizon class.
- `exit_conditions` and `thesis_failure_conditions` must be **distinct** — one
  is success, the other is failure. Both required.
- `max_acceptable_drawdown` must be a concrete number, not "TBD".

A position whose thesis has failed (failure condition met) is exited regardless
of P/L — discipline over hope.
