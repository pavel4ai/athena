# Athena Score

Every recommendation receives a composite score from 0–100. Athena should
**generally avoid recommendations scoring below 70**. Below-70 recommendations
may only be surfaced with an explicit waiver note explaining why.

## Components & Weights

| Component        | Weight | Owner agent             | What it measures |
|------------------|--------|-------------------------|------------------|
| Macro            | 20%    | Athena Scout / Oracle   | Alignment with current regime & macro lens |
| Fundamentals     | 20%    | Athena Analyst          | Graham lens: value, quality, earnings |
| Quantitative     | 20%    | Athena Analyst          | Chan/Hull lens: momentum, factors, vol |
| News Flow        | 15%    | Athena Scout            | Event + breaking news support |
| Twitter/X Signals| 10%    | Athena Scout            | Information alpha: pre-pricing X velocity |
| Risk/Reward      | 15%    | Athena Sentinel         | Asymmetry, max-drawdown vs. expected upside |

Each component is scored 0–100, then weighted and summed:

```
athena_score = 0.20*macro + 0.20*fundamentals + 0.20*quant
             + 0.15*news + 0.10*twitter + 0.15*risk_reward
```

## Score Bands

- **85–100** — high conviction; multiple lenses + identifiable Information/Event alpha.
- **70–84**  — actionable; standard threshold for proposal.
- **50–69**  — watchlist only; do not propose without waiver.
- **<50**    — reject.

## Rules
- The score is **advisory, not mechanical** — Athena Sentinel can veto a
  high-scoring recommendation on risk grounds, and the human can reject any.
- Every published score must show its **component breakdown** so it is auditable.
- A high News/Twitter score with a low Risk/Reward score is a flag, not a
  green light — Information alpha still needs an exit thesis and acceptable
  asymmetry.
