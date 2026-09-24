# Round 7 NFP — Frozen Stage-1 Plan

## Candidate
**R7NFP1: unanimous ES/NQ/RTY 08:30→08:35 Employment Situation shock continuation**

This is intentionally the same event-trading rule used for CPI, applied to a different scheduled macro event. The goal is to isolate event type rather than change parameters after seeing CPI results.

## Event source
- U.S. Bureau of Labor Statistics Employment Situation release calendar.
- Release time: 08:30 ET.
- Frozen event years: 2018–2023 only.
- 2024–2026 remain protected and are not loaded.
- Historical context: 2018–2020.
- Modern Stage-1 score block: 2021–2023.

## Frozen signal
For each official Employment Situation release date:
1. Measure ES, NQ, RTY return from 08:30 open to 08:35 open.
2. If all three are positive: LONG ES at 08:35.
3. If all three are negative: SHORT ES at 08:35.
4. Otherwise: NO TRADE.
5. Exit at 09:00 ET.
6. Maximum one trade per release.

No magnitude threshold, consensus-surprise variable, alternate exit, stop/target optimization, or reversal rescue is allowed.

## Cost model
Same as CPI Round 7:
- ES commission: $5 round trip = 0.10 ES points.
- MES commission: $1.50 round trip = 0.30 MES points.
- Slippage stress: 0, 1, 2, 4 adverse ticks.
- Primary: ES +1 adverse tick.

## Frozen Stage-1 gate
R7NFP1 must pass **all**:
1. At least 20 modern trades.
2. Positive average net points at ES +1 tick.
3. PF >= 1.25 at ES +1 tick.
4. Positive in at least 2 of 3 modern years.
5. Positive average after removing the single best trade.
6. Bootstrap P(mean return > 0) >= 0.90.
7. Positive average at ES +2 ticks.
8. No one profitable year may contribute >75% of total positive-year profit.
9. Long signals must have nonnegative average at ES +1 tick.
10. Short signals must have nonnegative average at ES +1 tick.

## Protection / anti-overfit
- Only the exact frozen R7NFP1 candidate can unlock 2024.
- If it fails, do not flip continuation to reversal based on 2021–2023.
- Do not alter 08:35 entry, 09:00 exit, unanimity rule, side selection, or costs after seeing results.
- CPI results do not count as NFP development data; the same rule is reused intentionally for cross-event comparability.
