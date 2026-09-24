# Round 7 CPI Stage-1 Result

## Frozen candidate
R7CPI1: unanimous ES/NQ/RTY 08:30→08:35 CPI shock continuation; enter ES at 08:35 ET, exit 09:00 ET; one trade max per CPI release.

## Data audit
- Frozen years: 2018–2023.
- Official BLS CPI release dates were frozen offline at 12 per year.
- 71/72 events had complete data; one 2020 event was missing ES data.
- Modern unanimous-signal events: 2021=12, 2022=12, 2023=10.

## Historical context 2018–2020
At ES +1 tick:
- 28 trades
- win rate 39.29%
- avg gross +0.2857 pts
- avg net -0.0643 pts
- PF 0.9623
- total -$90
- bootstrap P(mean>0) 40.35%

## Modern 2021–2023
At ES +1 tick:
- 34 trades
- win rate 67.65%
- avg gross +4.5221 pts
- avg net +4.1721 pts
- PF 2.1986
- total +$7,092.50
- bootstrap P(mean>0) 95.33%

Cost sensitivity remained positive through 4 adverse ticks. MES also remained positive through 4 adverse ticks.

### Year by year, ES +1 tick
- 2021: 12 trades, avg -0.4125 pts, PF 0.8278, total -$247.50
- 2022: 12 trades, avg +12.1917 pts, PF 6.3297, total +$7,315.00
- 2023: 10 trades, avg +0.0500 pts, PF 1.0080, total +$25.00

### Sides, ES +1 tick
- Long: 19 trades, avg +3.9526 pts
- Short: 15 trades, avg +4.4500 pts

### Tail robustness
After removing the single best trade:
- avg +3.1348 pts
- PF 1.8741

## Frozen gate
Pass:
- n_ge_20
- avg_net_positive
- PF_ge_1_25
- positive_2_of_3_years
- tail_avg_positive
- bootstrap_ge_0_90
- two_tick_avg_positive
- long_signal_nonnegative
- short_signal_nonnegative

Fail:
- max_positive_year_share_le_0_75

Observed max positive-year share: 0.996594, because almost all positive-year profit came from 2022.

## Decision
`ROUND7_CPI_STAGE1_SURVIVOR = False`

2024 remains protected. Retire exact R7CPI1. Do not weaken the concentration gate, change the exit, add magnitude filters, or flip the direction based on 2021–2023.

Interpretation: CPI continuation is the strongest modern signal found so far, but it is not sufficiently stable across years to justify protected 2024 validation under the frozen protocol.
