# Round 7 Retail Sales — Stage-1 Result

## Frozen candidate
R7RETAIL1: unanimous ES/NQ/RTY 08:30->08:35 shock continuation on U.S. Advance Retail Sales release days; enter ES at 08:35 ET in the shock direction and exit at 09:00 ET. One trade maximum per release.

## Stage-1 data
- Years: 2021-2023 only
- 36 official release dates, all complete
- 29 unanimous-signal trades
- 2024-2026 remained protected and were not loaded

## Primary ES +1 tick result
- Trades: 29
- Win rate: 62.07%
- Avg gross: -0.2069 ES points/trade
- Avg net: -0.5569 ES points/trade
- PF: 0.8460
- Total: -$807.50
- Bootstrap P(mean > 0): 0.4068

## Year-by-year
- 2021: 8 trades, +0.6813 points/trade, PF 1.6089, +$272.50
- 2022: 10 trades, +1.1250 points/trade, PF 1.2193, +$562.50
- 2023: 11 trades, -2.9864 points/trade, PF 0.2635, -$1,642.50

## Side diagnostics
- Long: 9 trades, +2.0667 points/trade
- Short: 20 trades, -1.7375 points/trade

## Tail robustness
After removing the single best trade:
- Avg net: -1.7696 points/trade
- PF: 0.5274

## Frozen gate
Passed:
- n >= 20
- positive 2 of 3 years
- max positive-year share <= 75%
- long signal nonnegative

Failed:
- avg net positive
- PF >= 1.25
- tail avg positive
- bootstrap >= 0.90
- two-tick avg positive
- short signal nonnegative

## Decision
ROUND7_RETAIL_STAGE1_SURVIVOR = False

Retire exact R7RETAIL1. Do not rescue it by changing to long-only, changing the exit, changing the signal window, or flipping to reversal after seeing these results. 2024 remains protected.
