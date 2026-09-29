# Round 7 ISM Manufacturing — Frozen Stage-1 Plan

## Candidate

`R7ISM1`: unanimous ES/NQ/RTY post-release continuation after the ISM Manufacturing PMI release.

## Motivation

This is intentionally different from the prior 08:30 government-release tests. ISM Manufacturing is released at 10:00 ET, after the U.S. cash session has opened. The experiment asks whether a unanimous cross-index shock during the first five minutes after the release continues for the next 25 minutes.

## Frozen event rule

For every scheduled ISM Manufacturing release:

1. Measure ES, NQ and RTY from 10:00 open to 10:05 open.
2. If all three returns are positive, go long ES at 10:05 open.
3. If all three returns are negative, go short ES at 10:05 open.
4. Otherwise, no trade.
5. Exit at 10:30 open.
6. One trade maximum per release.

No magnitude threshold, stop, target, surprise data, weekday filter, volatility filter, or direction-specific rule is allowed in Stage 1.

## Data split

- Historical context: 2018–2020.
- Stage-1 scoring: 2021–2023.
- 2024–2026 remain protected and must not be loaded.

ISM states that Manufacturing PMI is released at 10:00 ET on the first business day of the month, with the January release occurring on the second business day. The frozen calendar is encoded offline in the backtester.

## Costs

Use the same event-test cost model as CPI/NFP/PPI:
- ES and MES
- 0, 1, 2 and 4 adverse ticks round-trip slippage scenarios
- Commission assumptions inherited from `round7_cpi_event.py`

Primary economics: ES +1 tick.

## Frozen Stage-1 gate

All must pass:

1. At least 20 trades in 2021–2023.
2. Primary ES +1 tick average net points > 0.
3. Primary PF >= 1.25.
4. At least 2 of 3 modern years positive after primary costs.
5. Average remains positive after deleting the single best trade.
6. Bootstrap P(positive mean return) >= 0.90.
7. ES +2 tick average net points > 0.
8. No one positive year contributes >75% of total positive-year profits.
9. Long-signal average net points >= 0.
10. Short-signal average net points >= 0.

No gate changes after seeing results.

## Anti-overfit rule

If R7ISM1 fails, retire this exact rule. Do not flip to reversal, alter 10:05/10:30, remove one side, or tune on 2021–2023. A failure does not unlock 2024.
