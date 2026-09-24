# Round 6 Stage 1 — Cross-Index Relative-Value Result

Date: 2026-09-24
Primary candidate: R6S1
Protected years: 2024, 2025, 2026 remain unrevealed.

## Coverage
- Aligned complete sessions: 1,518
- 2017: 75
- 2018: 236
- 2019: 234
- 2020: 239
- 2021: 247
- 2022: 244
- 2023: 243
- Eligible after 60-session warmup: 1,458
- Eligible modern sessions: 734
- Total trades all eras: 2,095
- Modern 2021-2023 trades: 1,090

## Modern 2021-2023 cost sensitivity
| Friction (bps) | Trades | Win % | Avg gross bps | Avg net bps | PF | Total net bps | Sharpe | Bootstrap P(mean>0) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 1090 | 64.4954 | 0.2373 | 0.2373 | 1.3241 | 258.6466 | 1.7426 | 0.9985 |
| 0.5 | 1090 | 48.7156 | 0.2373 | -0.2627 | 0.7232 | -286.3534 | -1.9292 | 0.0007 |
| 1.0 | 1090 | 34.3119 | 0.2373 | -0.7627 | 0.3867 | -831.3534 | -5.5272 | 0.0000 |
| 2.0 | 1090 | 17.2477 | 0.2373 | -1.7627 | 0.1173 | -1921.3534 | -12.0156 | 0.0000 |
| 3.0 | 1090 | 7.7982 | 0.2373 | -2.7627 | 0.0406 | -3011.3534 | -17.1398 | 0.0000 |

## Year by year at primary 1.0 bp
- 2021: 336 trades, avg -0.6437 bps, PF 0.4739, total -216.2822 bps, Sharpe -4.0531
- 2022: 386 trades, avg -0.6146 bps, PF 0.5141, total -237.2394 bps, Sharpe -4.1006
- 2023: 368 trades, avg -1.0267 bps, PF 0.1717, total -377.8317 bps, Sharpe -10.4330

## Side diagnostics at 1.0 bp
- Long residual: 578 trades, avg -0.6750 bps, PF 0.4550
- Short residual: 512 trades, avg -0.8618 bps, PF 0.3103

## Exit / hold diagnostics
- Zero-cross exits: 1,079
- Max-hold exits: 11
- Median hold: 5 minutes
- Mean hold: 9.53 minutes
- Median absolute entry z-score: 2.3361

## Tail robustness
- Drop best 11 trades (1%): avg -0.8415 bps, PF 0.3302

## Frozen gate
- n_ge_150: PASS
- avg_net_positive: FAIL
- PF_ge_1_15: FAIL
- positive_2_of_3_years: FAIL
- tail_avg_positive: FAIL
- bootstrap_ge_0_90: FAIL
- two_bp_avg_positive: FAIL
- max_positive_year_share_le_0_75: FAIL
- long_residual_nonnegative: FAIL
- short_residual_nonnegative: FAIL

`ROUND6_STAGE1_SURVIVOR = False`

## Interpretation
The residual-reversion effect is visible before costs: +0.2373 bps/trade, PF 1.3241, Sharpe 1.7426, bootstrap probability 99.85%. But the edge is smaller than even 0.5 bp of round-trip friction, where expectancy becomes negative. This is therefore best interpreted as a real-looking but economically inaccessible short-horizon arbitrage effect for a retail/prop-firm implementation.

2024 remains protected. Do not tune z-score threshold, holding period, side selection, hedge window, or exit logic using 2021-2023 results. Do not proceed to integer micro-contract validation because the fractional idealized spread already fails realistic friction.
