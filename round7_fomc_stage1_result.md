# Round 7 FOMC Stage-1 Result

Candidate: **R7FOMC1 — unanimous ES/NQ/RTY 14:00->14:05 FOMC statement shock continuation, enter 14:05 ET, exit 14:30 ET.**

Protected years 2024-2026 were not loaded.

## Data audit
- 47/47 frozen regular FOMC events complete across 2018-2023.
- Modern unanimous-signal trades: 21 total (2021: 7, 2022: 8, 2023: 6).

## Historical context 2018-2020
At ES +1 adverse tick: 18 trades, 55.56% win rate, avg net -0.1556 points, PF 0.9218, total -$140, bootstrap P(mean>0)=0.4308.

## Modern 2021-2023 primary result
At ES $5 round trip +1 adverse tick:
- trades: 21
- win rate: 38.10%
- avg gross: +1.0357 ES points
- avg net: +0.6857 ES points
- PF: 1.2439
- total: +$720
- Sharpe: 0.2244
- bootstrap P(mean>0): 0.6323

At +2 ticks the expectancy remained positive (+0.4357 points/trade), but at +4 ticks it turned slightly negative (-0.0643).

## Year by year
- 2021: 7 trades, avg net -1.3857, PF 0.2240, -$485
- 2022: 8 trades, avg net +3.2750, PF 1.9650, +$1,310
- 2023: 6 trades, avg net -0.3500, PF 0.8918, -$105

## Side diagnostics
- long signals: 13 trades, avg net -0.8692 points
- short signals: 8 trades, avg net +3.2125 points

## Tail robustness
Removing the single best trade: avg net -0.6250 points, PF 0.7883.

## Frozen Stage-1 gate
Passed:
- n >= 15
- avg net positive
- 2-tick avg positive
- short signal nonnegative

Failed:
- PF >= 1.25
- positive in 2 of 3 modern years
- tail avg positive
- bootstrap >= 0.90
- max positive-year share <= 0.75
- long signal nonnegative

`ROUND7_FOMC_STAGE1_SURVIVOR = False`

## Decision
Retire exact R7FOMC1. Do not rescue it by switching to short-only, changing the 14:05 entry, changing the 14:30 exit, or using press-conference windows based on these results. 2024 remains protected.
