# S1 Frozen 2024 Validation Result

Date: 2026-09-24

Frozen implementation: 15-minute ORB close-confirmation, long-only, as selected in Round 1 using 2021-2023 only.
No tuning was performed before this validation. 2025 remains untouched at the time of this record.

## 2024 result — ES, $5 RT + 1 tick total adverse slippage

- Trades: 184
- Win rate: 46.20%
- Net average R/trade: +0.0596R
- Net PF: 1.1212
- Net total R: +10.9653R
- Max drawdown: -10.1153R

## Raw

- Win rate: 46.74%
- Average R/trade: +0.0859R
- PF: 1.1794
- Total R: +15.7969R

## Tail robustness — ES 1 tick

- Remove best 1: avg +0.0518R, PF 1.1047
- Remove best 3: avg +0.0359R, PF 1.0718
- Remove best 5: avg +0.0197R, PF 1.0390
- Largest winner / positive gross R: 1.47%

## Cost sensitivity

- ES 0 tick: +0.0784R, PF 1.1625
- ES 1 tick: +0.0596R, PF 1.1212
- ES 2 tick: +0.0408R, PF 1.0814
- ES 4 tick: +0.0033R, PF 1.0064
- MES 1 tick: +0.0446R, PF 1.0892
- MES 4 tick: -0.0117R, PF 0.9779

## Implementation audit

- 184 trades across 151 sessions
- Max 4 trades/day
- Zero overlapping trades
- Zero entries at/after noon
- Median risk 14.375 ES points
- Minimum risk 3.25 points
- Maximum risk 74.5 points
- Exit reasons: 84 stop, 60 target, 40 EOD

## Frozen validation gate

PASS.

Pre-specified gate before reveal:
1. >=100 trades
2. ES 1-tick net avgR > 0
3. ES 1-tick PF >= 1.10
4. Remove-best-5 net avgR > 0
5. ES 4-tick net avgR > 0

All conditions passed.

Interpretation: S1 earns access to the untouched 2025 holdout. No tuning is permitted before 2025.
