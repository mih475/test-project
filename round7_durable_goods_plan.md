# Round 7 — Durable Goods Event Strategy (Frozen Before Results)

## Objective
Test whether a unanimous cross-index reaction to the U.S. Census Bureau Advance Report on Durable Goods contains tradable continuation after the first five minutes.

## Candidate
R7DUR1 only.

## Event source
Official U.S. Census Bureau Economic Indicator release calendars. Stage-1 years are hard-frozen to 2021-2023. All listed Advance Report on Durable Goods releases used here were scheduled for 08:30 ET.

## Frozen dates

### 2021
2021-01-27, 2021-02-25, 2021-03-24, 2021-04-26, 2021-05-27, 2021-06-24, 2021-07-27, 2021-08-25, 2021-09-27, 2021-10-27, 2021-11-24, 2021-12-23

### 2022
2022-01-27, 2022-02-25, 2022-03-24, 2022-04-26, 2022-05-25, 2022-06-27, 2022-07-27, 2022-08-24, 2022-09-27, 2022-10-27, 2022-11-23, 2022-12-23

### 2023
2023-01-26, 2023-02-27, 2023-03-24, 2023-04-26, 2023-05-26, 2023-06-27, 2023-07-27, 2023-08-24, 2023-09-27, 2023-10-26, 2023-11-22, 2023-12-22

## Frozen trade rule
1. Measure ES, NQ and RTY from the 08:30 open to the 08:35 open.
2. If all three returns are positive, go LONG ES at the 08:35 open.
3. If all three returns are negative, go SHORT ES at the 08:35 open.
4. If signs disagree or any return is exactly zero, do not trade.
5. Exit at the 09:00 open.
6. One trade maximum per release.
7. No stop, target, magnitude threshold, surprise filter, weekday filter, or post-result direction flip.

## Costs
Same event-engine assumptions used for CPI/NFP/PCE/Retail/PPI:
- ES commission/fees: $5 round trip equivalent in point accounting.
- MES commission/fees: $1.50 round trip equivalent.
- Slippage diagnostics: 0, 1, 2 and 4 adverse ticks round trip.
- Primary test: ES +1 adverse tick.

## Stage-1 years
2021-2023 only. 2024-2026 remain protected and must not be loaded.

## Frozen Stage-1 gate
All must pass:
1. >=20 trades
2. ES +1 tick avg net points > 0
3. ES +1 tick PF >= 1.25
4. positive net total in >=2 of 3 years
5. after deleting the single best trade, avg net points > 0
6. bootstrap P(positive mean return) >= 0.90
7. ES +2 tick avg net points > 0
8. no one positive year >75% of total positive-year profits
9. long-signal avg net points >=0
10. short-signal avg net points >=0

If any gate fails, R7DUR1 is retired and 2024 stays protected. Do not optimize the rule using Stage-1 results.
