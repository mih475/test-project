# Round 7 Retail Sales Event Strategy — Frozen Plan

## Objective
Test whether the first five-minute cross-index reaction to the U.S. Census Bureau Advance Monthly Sales for Retail and Food Services release continues through 09:00 ET.

## Data / protection
- Stage-1 years: 2021–2023 only.
- 2024–2026 remain protected and must not be loaded.
- Official U.S. Census Bureau release dates are frozen offline before performance is observed.
- Exactly 12 releases per year, all scheduled for 08:30 ET.
- Reuse existing ES, NQ, and RTY minute data and the same event engine/cost model used by the CPI/PCE tests.

## Candidate R7RETAIL1
For each official Retail Sales release day:
1. Measure ES, NQ, RTY from 08:30 open to 08:35 open.
2. If all three returns are positive, go LONG ES at 08:35 open.
3. If all three returns are negative, go SHORT ES at 08:35 open.
4. Otherwise, no trade.
5. Exit at 09:00 open.
6. At most one trade per release.

No magnitude threshold, no stop/target, no consensus-surprise variable, no reversal alternative, and no post-result parameter changes.

## Costs
Use the same cost model as the earlier Round-7 event tests:
- ES: $5 round trip plus adverse slippage of 0, 1, 2, and 4 ticks.
- MES: $1.50 round trip plus adverse slippage of 0, 1, 2, and 4 ticks.
- Primary = ES +1 tick.

## Frozen Stage-1 gate
All must pass:
1. At least 20 trades.
2. Primary average net points > 0.
3. Primary PF >= 1.25.
4. Positive total dollars in at least 2 of 3 years.
5. After removing the single best trade, average net points > 0.
6. Bootstrap P(positive mean return) >= 0.90.
7. ES +2 tick average net points > 0.
8. No one positive year contributes >75% of positive-year profits.
9. Long-signal average net points >= 0.
10. Short-signal average net points >= 0.

If any criterion fails, R7RETAIL1 is retired and 2024 stays protected. Do not flip to reversal, alter the 08:35 entry/09:00 exit, or introduce surprise thresholds using 2021–2023 results.
