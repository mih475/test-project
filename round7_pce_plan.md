# Round 7 PCE / Personal Income and Outlays — Frozen Stage-1 Plan

## Candidate
**R7PCE1 — unanimous ES/NQ/RTY 08:30->08:35 shock continuation on BEA Personal Income and Outlays (PCE) release days.**

## Why this is a separate hypothesis
PCE is a distinct scheduled inflation/consumption release from CPI, NFP, and FOMC. To keep event-type comparisons clean, R7PCE1 uses the same post-release continuation structure already frozen for CPI/NFP rather than inventing a PCE-specific threshold or exit.

## Event universe
- Official BEA Personal Income and Outlays release dates.
- Stage-1 years: **2021, 2022, 2023 only**.
- 2024-2026 remain protected and are not loaded.
- We intentionally omit 2018-2020 from this exact candidate because BEA Personal Income and Outlays release times were not uniform in those years (some releases occurred at 10:00 ET). R7PCE1 is defined specifically as an 08:30 ET event strategy.

## Frozen trading rule
For each frozen 08:30 ET PCE release:
1. Measure ES, NQ, and RTY from 08:30 open to 08:35 open.
2. If all three returns are positive, go **long ES** at the 08:35 open.
3. If all three returns are negative, go **short ES** at the 08:35 open.
4. Otherwise, no trade.
5. Exit at the 09:00 ES open.
6. Maximum one trade per release.

No magnitude threshold. No stop-loss or profit-target optimization. No alternate exit. No switching to reversal after results are observed.

## Costs
Use the same cost assumptions as the CPI/NFP event tests:
- ES round-trip commission: $5 = 0.10 ES points
- MES round-trip commission: $1.50 = 0.30 MES points
- Slippage diagnostics: 0, 1, 2, 4 adverse ticks round trip
- Primary: ES +1 adverse tick

## Stage-1 gate (all required)
- >=20 trades
- positive average net points at ES +1 tick
- PF >=1.25
- profitable in at least 2 of 3 years
- positive expectancy after removing the single best trade
- bootstrap P(mean return > 0) >=0.90
- positive expectancy at ES +2 ticks
- no one profitable year >75% of positive-year profits
- long-signal average nonnegative
- short-signal average nonnegative

Only R7PCE1 can unlock a separate protected 2024 PCE validation. No Stage-1 tuning is allowed after seeing 2021-2023 results.
