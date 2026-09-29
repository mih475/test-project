# Round 7 PPI Stage-1 Result

Candidate: R7PPI1 — unanimous ES/NQ/RTY 08:30->08:35 Producer Price Index shock continuation; enter ES 08:35 ET, exit 09:00 ET.

## Result

ROUND7_PPI_STAGE1_SURVIVOR = False. 2024 remains protected. Retire exact R7PPI1 and do not flip it to reversal or otherwise tune it using the 2021-2023 result.

## Data audit

- Official BLS PPI dates frozen offline, 2018-2023.
- 69 complete events out of 72.
- Unanimous-signal events: 2018 8, 2019 9, 2020 10, 2021 6, 2022 10, 2023 9.

## Historical context 2018-2020, ES +1 tick

- Trades: 27
- Win rate: 29.63%
- Avg gross: +0.8333 ES points/trade
- Avg net: +0.4833 ES points/trade
- PF: 1.2399
- Total: +$652.50
- Bootstrap P(mean > 0): 0.6612

Historical context was mildly positive but not strong enough to establish a robust edge.

## Modern 2021-2023, primary ES +1 tick

- Trades: 25
- Win rate: 48.0%
- Avg gross: -0.92 ES points/trade
- Avg net: -1.27 ES points/trade
- PF: 0.6058
- Total: -$1,587.50
- Bootstrap P(mean > 0): 0.1369

The strategy was negative even before slippage in the modern scoring block.

## Year-by-year, ES +1 tick

- 2021: 6 trades, +2.9417 points/trade, +$882.50, PF infinite (all six trades profitable)
- 2022: 10 trades, -3.8250 points/trade, -$1,912.50, PF 0.1462
- 2023: 9 trades, -1.2389 points/trade, -$557.50, PF 0.6881

This is a strong regime flip rather than stable continuation behavior.

## Side diagnostics, ES +1 tick

- Long: 9 trades, -1.8500 points/trade
- Short: 16 trades, -0.9437 points/trade

Both sides lost.

## Tail robustness

After dropping the best trade:
- Avg net: -1.9229 points/trade
- PF: 0.4271

## Frozen Stage-1 gate

Passed only the minimum-sample gate. Failed positive expectancy, PF >= 1.25, 2-of-3 positive years, tail robustness, bootstrap >= 0.90, two-tick profitability, profit-concentration test, and both-side nonnegative requirements.

## Interpretation

PPI does not independently confirm the strong CPI continuation result. The contrast — mildly positive 2018-2020, excellent 2021, then sharply negative 2022-2023 — argues against treating CPI's 2022 performance as evidence of a durable broad inflation-release continuation family.
