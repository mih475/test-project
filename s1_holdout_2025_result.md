# S1 — Frozen 2025 Holdout Result

Date: 2026-09-24

Strategy: S1 — 15-minute ORB close-confirmation, long-only.

This is an untouched holdout test. The implementation was frozen after 2021-2023 development and 2024 validation. No S1 parameter or rule was changed before this run. 2026 remains unrevealed.

## Frozen holdout gate

Same as the 2024 validation gate:
- n >= 100
- ES, $5 RT + 1 tick total adverse slippage: avgR > 0
- ES1 PF >= 1.10
- after removing five best trades: avgR > 0
- ES with 4 ticks total adverse slippage: avgR > 0

## 2025 result

Implementation audit:
- 166 trades
- 154 sessions with trade
- max 2 trades/day
- zero overlapping trades
- zero entries at/after noon
- median risk 21.375 ES points
- min risk 8.0 points
- max risk 324.25 points
- exit reasons: 68 stop, 59 EOD, 39 target

Raw:
- win rate 49.3976%
- avgR +0.0546
- PF 1.1240
- total +9.0697R
- DD -12.0662R

Primary ES $5 RT + 1 tick total adverse slippage:
- n 166
- win 49.3976%
- avgR +0.0363
- PF 1.0805
- total +6.0216R
- max DD -13.7679R

Tail robustness at ES1:
- drop best 1: avgR +0.0274, PF 1.0605, total +4.5241R
- drop best 3: avgR +0.0094, PF 1.0206, total +1.5390R
- drop best 5: avgR -0.0090, PF 0.9807, total -1.4427R

Cost sensitivity:
- ES 0 ticks: avgR +0.0494, PF 1.1114
- ES 1 tick: avgR +0.0363, PF 1.0805
- ES 2 ticks: avgR +0.0232, PF 1.0506
- ES 4 ticks: avgR -0.0031, PF 0.9935
- MES 1 tick: avgR +0.0258, PF 1.0565

## Frozen decision

`FROZEN_2025_HOLDOUT_GATE = False`

Reasons for failure:
1. ES1 PF 1.0805 < 1.10.
2. Drop-best-5 expectancy turns negative (-0.0090R) with PF 0.9807.
3. ES 4-tick stress turns negative (-0.0031R) with PF 0.9935.

Interpretation: S1 does not pass the untouched 2025 holdout. Do not tune or repair S1 using 2025, and do not reveal 2026 as a rescue attempt under this frozen research protocol.
