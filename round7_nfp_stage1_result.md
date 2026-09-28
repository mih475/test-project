# Round 7 NFP / Employment Situation — Stage-1 Result

Status: **FAIL / RETIRED**

Candidate: `R7NFP1` — unanimous ES/NQ/RTY 08:30→08:35 shock continuation, enter ES at 08:35 ET, exit 09:00 ET.

Development/context years: 2018–2020. Primary Stage-1 years: 2021–2023. Protected years 2024–2026 were not loaded.

## Data audit

- 71 of 72 scheduled releases had complete usable event data.
- Modern unanimous-signal events: 2021 = 7, 2022 = 12, 2023 = 11; total = 30 trades.

## Historical context, 2018–2020

At ES +1 adverse tick: 31 trades, 51.61% win rate, -0.4226 points/trade, PF 0.8008, -$655 total, bootstrap P(mean>0) 22.31%.

## Primary modern result, 2021–2023

At ES +1 adverse tick:

- Trades: 30
- Win rate: 33.33%
- Gross expectancy: -3.7667 ES points/trade
- Net expectancy: -4.1167 ES points/trade
- PF: 0.4269
- Total P/L: -$6,175
- Bootstrap P(mean>0): 5.81%

The rule was negative even at zero slippage: -3.8667 points/trade, PF 0.4489.

## Year by year

- 2021: 7 trades, -5.9214 points/trade, PF 0.0940, -$2,072.50
- 2022: 12 trades, -5.1208 points/trade, PF 0.4481, -$3,072.50
- 2023: 11 trades, -1.8727 points/trade, PF 0.6473, -$1,030.00

All three modern years were negative.

## Side diagnostics

- Long signals: 14 trades, -4.4393 points/trade
- Short signals: 16 trades, -3.8344 points/trade

Both sides were negative.

## Tail robustness

After removing the single best trade: -5.2552 points/trade, PF 0.2928.

## Frozen gate

Only the minimum-sample check passed. The candidate failed positive expectancy, PF >= 1.25, 2-of-3 positive years, tail robustness, bootstrap >= 90%, two-tick profitability, concentration, and both-side nonnegative checks.

`ROUND7_NFP_STAGE1_SURVIVOR = False`

## Decision

Retire exact `R7NFP1`. Do not flip the sign to reversal or tune entry/exit times using the 2021–2023 result. 2024 remains protected.
