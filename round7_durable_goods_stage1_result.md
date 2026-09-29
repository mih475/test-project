# Round 7 Durable Goods — Stage-1 Result

Candidate: `R7DUR1`

Frozen rule: unanimous ES/NQ/RTY 08:30→08:35 shock continuation; enter ES at 08:35 ET; exit 09:00 ET; one trade maximum per Advance Durable Goods release.

## Data

- Stage-1 years: 2021–2023 only.
- 36/36 scheduled events had complete event data.
- Unanimous-signal trades: 29 total (2021: 9, 2022: 9, 2023: 11).
- 2024–2026 remained protected and were not loaded.

## Primary modern result — ES +1 tick

- Trades: 29
- Win rate: 34.48%
- Average gross: -2.5776 points/trade
- Average net: -2.9276 points/trade
- Profit factor: 0.2611
- Total: -$4,245
- Sharpe: -1.5358
- Bootstrap P(mean > 0): 0.0051

Year by year:
- 2021: 9 trades, -2.2667 pts/trade, PF 0.1570, -$1,020
- 2022: 9 trades, -4.1833 pts/trade, PF 0.1788, -$1,882.50
- 2023: 11 trades, -2.4409 pts/trade, PF 0.4013, -$1,342.50

Side diagnostics:
- Long: 17 trades, -1.0559 pts/trade
- Short: 12 trades, -5.5792 pts/trade

Tail robustness after removing the best trade:
- Average net: -3.3589 pts/trade
- PF: 0.1815

## Frozen Stage-1 gate

Passed only `n_ge_20`.

Failed:
- avg_net_positive
- PF_ge_1_25
- positive_2_of_3_years
- tail_avg_positive
- bootstrap_ge_0_90
- two_tick_avg_positive
- max_positive_year_share_le_0_75
- long_signal_nonnegative
- short_signal_nonnegative

`ROUND7_DURABLE_STAGE1_SURVIVOR = False`

## Decision

Retire exact R7DUR1. Do not flip to reversal, remove the short side, change the holding window, or otherwise tune it using 2021–2023. Keep 2024 protected.
