# Round 7 PPI Event Strategy — Frozen Plan

## Objective
Test whether a unanimous cross-index reaction to the U.S. Producer Price Index (PPI) release contains tradable continuation after the first five minutes.

This is an independent inflation-release check following CPI. No CPI parameters are changed and no PPI thresholds will be tuned after seeing 2021-2023 results.

## Official release schedule
Use only official U.S. Bureau of Labor Statistics PPI release dates. The BLS PPI detailed reports state that PPI news releases are issued at 08:30 AM Eastern Time.

Years:
- Historical context: 2018-2020
- Stage-1 scoring: 2021-2023
- Protected: 2024-2026 (must not be loaded)

## Frozen candidate R7PPI1
For each official PPI release date:
1. Measure ES, NQ and RTY returns from 08:30 open to 08:35 open.
2. If all three returns are positive, enter long ES at the 08:35 open.
3. If all three returns are negative, enter short ES at the 08:35 open.
4. Otherwise, no trade.
5. Exit at the 09:00 open.
6. Maximum one trade per release.

No magnitude threshold. No stop/target. No alternate exit. No reversal candidate. No filtering by reported PPI surprise, consensus, weekday, volatility, or any post-hoc variable.

## Costs
Use the same event-strategy cost model as CPI/NFP/PCE/Retail:
- ES commission/fees: $5 round trip converted to points
- MES commission/fees: $1.50 round trip converted to points
- Slippage stress: 0, 1, 2, 4 adverse ticks round trip
- Primary result: ES +1 adverse tick

## Frozen Stage-1 gate
All must pass on 2021-2023:
1. trades >= 20
2. avg net ES points/trade > 0 at +1 tick
3. PF >= 1.25 at +1 tick
4. positive net total in at least 2 of 3 years
5. avg net > 0 after deleting the single best trade
6. bootstrap P(positive mean return) >= 0.90
7. avg net > 0 at +2 ticks
8. no one positive year >75% of total positive-year profit
9. long-signal avg net >= 0
10. short-signal avg net >= 0

No gate changes after results.

## Validation rule
If and only if all Stage-1 conditions pass, create a separate untouched 2024 PPI validation using the exact frozen rule. Otherwise retire R7PPI1 and keep 2024 protected.
