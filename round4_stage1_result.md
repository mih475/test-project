# Round 4 Stage 1 — Cross-Market / Regime Model Result

Date: 2026-09-24
Primary candidate: R4M1 cross-market regime OLS
Protected years: 2024-2026 remain unrevealed.

## Data integrity

The first run was invalid because NQ 2023 was missing. After downloading NQ.v.0 2023, the audit showed complete modern cross-market coverage:

- 2021: 237 complete feature sessions
- 2022: 233
- 2023: 231

The exact same frozen model was rerun; no model, feature, threshold, cost, or gate changes were made.

## R4M1 modern 2021-2023

Primary economics: ES $5 round-trip commission + 1 adverse tick.

- Trades: 648
- Average net points/trade: +0.0238
- Profit factor: 1.0019
- Total dollars: +$772.50
- Sharpe: 0.0320

Year by year:

- 2021: 220 trades, +1.0250 pts/trade, PF 1.1272, +$11,275, Sharpe 0.7242
- 2022: 215 trades, -1.3070 pts/trade, PF 0.9281, -$14,050, Sharpe -0.4381
- 2023: 213 trades, +0.3331 pts/trade, PF 1.0310, +$3,547.50, Sharpe 0.2161

## Cost sensitivity

ES:

- 0 ticks: +0.2738 pts/trade, PF 1.0225, +$8,872.50, Sharpe 0.1452
- 1 tick: +0.0238, PF 1.0019, +$772.50, Sharpe 0.0320
- 2 ticks: -0.2262, PF 0.9818, -$7,327.50, Sharpe -0.0813
- 4 ticks: -0.7262, PF 0.9428, -$23,527.50, Sharpe -0.3078

MES:

- 0 ticks: +0.0738 pts/trade, PF 1.0060
- 1 tick: -0.1762, PF 0.9858
- 2 ticks: -0.4262, PF 0.9660
- 4 ticks: -0.9262, PF 0.9276

## Tail robustness

Dropping the best 1% / seven trades:

- average net points/trade: -1.1226
- PF: 0.9098

## Frozen Stage-1 gate

Pass:

- n >= 150
- primary average net > 0
- positive in at least 2 of 3 years
- max positive-year share <= 80%

Fail:

- PF >= 1.10
- tail average > 0
- bootstrap P(mean > 0) >= 90%
- 2-tick average >= -0.05

`ROUND4_STAGE1_SURVIVOR = False`

## Conclusion

R4M1 does not earn 2024 validation. Its small raw/low-friction effect is economically negligible, disappears under modest additional execution friction, and is strongly dependent on a small number of large winners. Do not tune R4M1 using 2021-2023 and do not expose 2024 as a rescue attempt.

A separate reporting-only bug caused the printed primary-economics table to appear empty (`results.product` collided with pandas `DataFrame.product`). The gate and strategy metrics were computed directly and were unaffected. The display bug was fixed after the frozen result without changing model logic.
