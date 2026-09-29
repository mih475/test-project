# Round 7 ISM Manufacturing — Stage-1 Result

## Frozen candidate
R7ISM1: unanimous ES/NQ/RTY 10:00→10:05 shock continuation on ISM Manufacturing release days; enter ES at 10:05 ET and exit at 10:30 ET; maximum one trade per release.

## Data audit
- 72/72 scheduled events complete across 2018–2023.
- Historical context 2018–2020: 29 trades, ES +1 tick avg +0.0897 points, PF 1.0387, total +$130, bootstrap P(mean>0)=0.5178.
- Modern Stage-1 2021–2023: 25 trades.

## Primary modern result — ES +1 tick
- Win rate: 52.0%
- Avg gross: +2.87 points/trade
- Avg net: +2.52 points/trade
- PF: 1.6778
- Total: +$3,150
- Max drawdown: -$1,772.50
- Sharpe: 0.6735
- Bootstrap P(mean>0): 0.8377

## Cost robustness
- ES 0 ticks: +2.77 points/trade, PF 1.7699
- ES 1 tick: +2.52, PF 1.6778
- ES 2 ticks: +2.27, PF 1.5915
- ES 4 ticks: +1.77, PF 1.4311

## Year-by-year — ES +1 tick
- 2021: 5 trades, avg -4.05 points, PF 0.0711, total -$1,012.50
- 2022: 11 trades, avg +8.7864 points, PF 3.3573, total +$4,832.50
- 2023: 9 trades, avg -1.4889 points, PF 0.5556, total -$670

## Side diagnostics
- Long: 11 trades, avg -0.3955 points, total -4.35 points
- Short: 14 trades, avg +4.8107 points, total +67.35 points

## Tail robustness
Drop best trade: avg +1.025 points, PF 1.2647.

## Frozen Stage-1 gate
- n >= 20: PASS
- avg net positive: PASS
- PF >= 1.25: PASS
- positive in at least 2 of 3 modern years: FAIL
- drop-best-trade avg positive: PASS
- bootstrap >= 0.90: FAIL
- +2 tick avg positive: PASS
- no positive year >75% of positive-year profit: FAIL
- long signal nonnegative: FAIL
- short signal nonnegative: PASS

`ROUND7_ISM_STAGE1_SURVIVOR = False`

## Decision
Retire exact R7ISM1. Do not convert it to short-only, retime the window, or otherwise rescue it using the observed 2021–2023 results. 2024–2026 remain protected.

The economically interesting feature is that transaction-cost and tail robustness were respectable, but essentially all modern profitability came from 2022 and the long side was negative. This reinforces the Round-7 pattern that several macro-event continuation effects were concentrated in the unusual 2022 regime rather than stable across years.
