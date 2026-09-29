# Round 7 ISM Services Stage-1 Result

## Frozen candidate
R7ISMS1: ES/NQ/RTY unanimous 10:00->10:05 ET shock continuation on ISM Services release days. Enter ES at 10:05 in the unanimous direction; exit 10:30. One trade max per release. Stage-1 years: 2021-2023. 2024-2026 protected.

## Data audit
- 36/36 complete scheduled events.
- Unanimous-signal events: 2021=5, 2022=9, 2023=12; total=26.

## Primary ES +1 tick, 2021-2023
- Trades: 26
- Win rate: 57.6923%
- Avg gross: +0.6538 pts/trade
- Avg net: +0.3038 pts/trade
- PF: 1.0743
- Total: +$395
- Max DD: -$2,360
- Sharpe: 0.1513
- Bootstrap P(mean>0): 0.5927

## Cost sensitivity
- ES 0 ticks: +0.5538 pts, PF 1.1390
- ES 1 tick: +0.3038 pts, PF 1.0743
- ES 2 ticks: +0.0538 pts, PF 1.0128
- ES 4 ticks: -0.4462 pts, PF 0.8990
- MES 1 tick: +0.1038 pts, PF 1.0249

## Year by year, ES +1 tick
- 2021: 5 trades, +1.9000 pts/trade, PF 1.9091, +$475
- 2022: 9 trades, +1.7056 pts/trade, PF 1.4562, +$767.50
- 2023: 12 trades, -1.4125 pts/trade, PF 0.7277, -$847.50

## Side diagnostics
- Long: 10 trades, +3.9000 pts/trade, +39.0 total net points
- Short: 16 trades, -1.9438 pts/trade, -31.1 total net points

## Tail robustness
Drop best trade: avg net -0.4700 pts, PF 0.8895.

## Frozen Stage-1 gate
- n_ge_20: PASS
- avg_net_positive: PASS
- PF_ge_1_25: FAIL
- positive_2_of_3_years: PASS
- tail_avg_positive: FAIL
- bootstrap_ge_0_90: FAIL
- two_tick_avg_positive: PASS
- max_positive_year_share_le_0_75: PASS
- long_signal_nonnegative: PASS
- short_signal_nonnegative: FAIL

ROUND7_ISM_SERVICES_STAGE1_SURVIVOR = False

## Conclusion
Reject R7ISMS1. 2024 stays protected. Do not rescue the candidate by keeping only the long side, changing timing, adding filters, or flipping direction after observing these results. The small positive aggregate expectancy is too weak, tail-fragile, and side-dependent to justify validation.
