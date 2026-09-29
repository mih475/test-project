# Round 7 — ISM Services Event Plan (Frozen Before Performance)

## Candidate
**R7ISMS1 — ISM Services post-release cross-index continuation**

ISM states that the Services PMI is released at **10:00 a.m. ET on the third business day of the month**, with January released on the fourth business day. This experiment uses a frozen offline calendar for 2021–2023 only.

## Why this test
ISM Manufacturing showed attractive aggregate economics but failed the frozen robustness gate because profitability was concentrated in 2022 and the long side was negative. ISM Services is a distinct scheduled event released at the same 10:00 ET time, so it is a clean independent test of whether the 10:00 post-news continuation effect is broader than Manufacturing.

## Frozen trading rule
For each ISM Services release:
1. Measure ES, NQ and RTY from 10:00 ET open to 10:05 ET open.
2. If all three returns are strictly positive, go LONG ES at the 10:05 ET open.
3. If all three returns are strictly negative, go SHORT ES at the 10:05 ET open.
4. Otherwise, no trade.
5. Exit at the 10:30 ET open.
6. Maximum one trade per release.

No magnitude threshold, no surprise-value input, no stop/target optimization, no retiming, no reversal alternative, and no one-sided filter may be added after seeing Stage-1 results.

## Evaluation block
- Stage-1 only: 2021–2023.
- 2024–2026 remain protected and must not be loaded unless the frozen Stage-1 gate passes.
- Transaction-cost sensitivity: ES and MES at 0, 1, 2 and 4 ticks of slippage plus the same commission assumptions used elsewhere in Round 7.

## Frozen Stage-1 gate — all must pass
- At least 20 trades.
- ES +1 tick average net > 0.
- ES +1 tick PF >= 1.25.
- At least 2 of 3 years profitable.
- Average remains positive after dropping the single best trade.
- Bootstrap P(mean > 0) >= 0.90.
- ES +2 tick average net > 0.
- No one profitable year supplies >75% of total positive-year profit.
- Long-signal average >= 0.
- Short-signal average >= 0.

If the gate fails, retire exact R7ISMS1. Do not flip direction, keep only one side, or alter the time window based on the observed results.
