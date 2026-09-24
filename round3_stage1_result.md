# Round 3 Stage 1 — Literature-Derived Tournament Results

Date: 2026-09-24
Frozen implementation: `round3_literature_tournament.py`
Protected years: 2024, 2025, 2026 remain unrevealed.

## Modern 2021-2023 leaderboard
Primary economics: ES $5 round trip commission + 1 total adverse tick.

| Strategy | N | Win % | Avg ES points | Avg $/trade | PF | Total $ | Sharpe | Bootstrap P(mean>0) | Positive years | ES 2-tick avg pts | Drop-tail avg pts | Survivor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| R3S1 Rest-of-day -> last-30m momentum | 722 | 49.58 | -0.0131 | -0.65 | 0.9968 | -472.50 | -0.021 | 48.03% | 1/3 | -0.2631 | -0.4918 | No |
| R3S3 Overnight -> first-30m reversal | 741 | 50.20 | -0.2350 | -11.75 | 0.9537 | -8,705 | -0.260 | 32.29% | 1/3 | -0.4850 | -0.6689 | No |
| R3S5 European-open drift | 554 | 49.46 | -0.5310 | -26.55 | 0.8682 | -14,707.50 | -0.784 | 12.65% | 0/3 | -0.7810 | -0.8979 | No / negative control |
| R3S2 First-30m -> last-30m momentum | 719 | 45.90 | -1.0854 | -54.27 | 0.7649 | -39,020 | -1.453 | 0.64% | 1/3 | -1.3354 | -1.4984 | No |
| R3S4 Large opening-gap reversal | 504 | 46.03 | -1.6407 | -82.03 | 0.7754 | -41,345 | -1.226 | 1.58% | 0/3 | -1.8907 | -2.3274 | No |
| R3S6 High-vol first-30m -> last-30m momentum | 217 | 44.24 | -3.0032 | -150.16 | 0.5994 | -32,585 | -1.617 | 0.17% | 1/3 | -3.2532 | -3.2169 | No |

## R3S1 cost sensitivity
R3S1 is the only near-breakeven modern effect.

- ES commission only / 0 adverse ticks: +0.2369 points/trade, PF 1.0601, +$8,552.50 total, Sharpe 0.318, bootstrap P(mean>0) 70.12%.
- ES +1 adverse tick: -0.0131 points/trade, PF 0.9968.
- ES +2 adverse ticks: -0.2631 points/trade, PF 0.9373.
- MES +1 adverse tick: -0.2131 points/trade, PF 0.9489.

Interpretation: a faint raw continuation effect may remain, but it is not large or statistically robust enough to survive realistic execution friction.

## Year-by-year highlights

R3S1:
- 2021: -0.6298 pts/trade, PF 0.8324
- 2022: +0.6271, PF 1.1173
- 2023: -0.0289, PF 0.9907

R3S5 negative-control behavior:
- Context block 2016-2020: +0.8269 pts/trade, PF 1.3316, Sharpe 1.3563.
- Modern 2021-2023: -0.5310 pts/trade, PF 0.8682, Sharpe -0.7835.
- 2021: -0.1095, PF 0.9658
- 2022: -0.7541, PF 0.8652
- 2023: -0.7293, PF 0.7703

This is directionally consistent with the published narrative that the European-open/overnight drift weakened materially in the modern period.

## R3S4 horizon diagnostic
The extra horizons were diagnostics only and may not replace the frozen 10:30 exit.

Modern 2021-2023 average net ES points from 09:40 entry:
- 10:00: -1.3450
- 10:30: -1.6407 (primary)
- 11:00: -2.2047
- 12:00: -1.5926

All horizons were negative, so there is no evidence that the primary failure was caused by choosing the wrong one of these predeclared diagnostic marks.

## Implementation audit
- No within-strategy overlapping trades were found.
- R3S1: 1,871 total trades across 2016-2023.
- R3S2: 1,862.
- R3S3: 1,932.
- R3S4: 1,233.
- R3S5: 1,255.
- R3S6: 565.
- 2024-2026 were not loaded.

R3S5 has lower eligible-day coverage than the RTH strategies because its test requires a complete same-contract 23:30-03:30 overnight window. Treat it as a conservative negative-control replication rather than a complete census of every overnight session.

## Frozen conclusion
`ROUND3_SURVIVORS = []`

No Round 3 strategy earns 2024 validation. Do not tune these failed rules using 2021-2023, and do not reveal 2024 as a rescue attempt.
