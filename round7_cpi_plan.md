# Round 7 CPI Event Strategy — Frozen Stage-1 Plan

## Research question
On scheduled U.S. CPI release days, after the first five minutes of price discovery, does a unanimous ES/NQ/RTY directional shock continue over the next 25 minutes?

## Event source
Official U.S. Bureau of Labor Statistics (BLS) historical release calendars only.
- Years used: 2018-2023.
- CPI release time must parse as 08:30 AM Eastern.
- The backtester must find exactly 12 CPI releases per calendar year or stop with an error.
- 2017 is excluded because RTY history is partial.
- 2024-2026 must not be loaded.

## Data
- ES: existing 1-minute continuous/raw source already used in prior rounds.
- NQ.v.0 and RTY.v.0: existing Databento 1-minute files in `round4_crossmarket_data`.
- No new paid data.

## Frozen candidate: R7CPI1
For each CPI event date:
1. Read the 08:30, 08:35, and 09:00 Eastern opens for ES, NQ, and RTY.
2. ES must use the same underlying contract symbol at all three timestamps; otherwise skip the event.
3. Define each market's initial CPI shock as 08:30 open -> 08:35 open.
4. Trade only if ES, NQ, and RTY shock signs are all strictly positive or all strictly negative.
5. Direction = that unanimous shock direction.
6. Enter ES at the 08:35 open.
7. Exit ES at the 09:00 open.
8. One trade maximum per CPI event.
9. No magnitude filter, stop, target, volatility filter, CPI-surprise data, weekday filter, or alternate time window.

This is a continuation hypothesis only. A reversal version is NOT a rescue candidate if R7CPI1 fails.

## Evaluation
Historical context: 2018-2020.
Stage-1 decision block: 2021-2023 only.
2024 remains protected.

Primary execution assumption:
- ES
- $5.00 round-trip commission
- 1 adverse tick round-trip slippage
Diagnostics/stress:
- ES 0, 1, 2, and 4 adverse ticks
- MES 0, 1, 2, and 4 adverse ticks

## Frozen Stage-1 gate
R7CPI1 must pass ALL:
1. >= 20 trades in 2021-2023.
2. Positive average net points at ES +1 tick.
3. Profit factor >= 1.25 at ES +1 tick.
4. Positive total dollars in at least 2 of 3 years.
5. Positive average net points after removing the single best trade.
6. Bootstrap P(mean trade return > 0) >= 0.90.
7. Positive average net points at ES +2 ticks.
8. No one profitable year contributes > 75% of total positive-year profits.
9. Long-signal trades have non-negative average net points.
10. Short-signal trades have non-negative average net points.

Only R7CPI1 can unlock a later 2024 CPI validation. Historical/context diagnostics cannot rescue it.

## Anti-overfit rule
If R7CPI1 fails, do not change:
- 5-minute reaction window,
- 09:00 exit,
- unanimity rule,
- direction,
- cost assumption,
- or any threshold based on 2021-2023 results.

Retire CPI R7CPI1 and move to the next independently pre-registered macro event (NFP).
