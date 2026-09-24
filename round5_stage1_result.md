# Round 5 Stage 1 — Three-State Market Classifier Results

Date: 2026-09-24
Primary candidate: `R5C1` three-state walk-forward LDA
Protected years: 2024, 2025, 2026 remain unrevealed.

## Modern 2021–2023 primary economics — ES $5 RT + 1 adverse tick

- Trades: 104
- Trade rate: 14.9856%
- Win rate: 57.6923%
- Average net points/trade: -1.5375
- Profit factor: 0.8987
- Total dollars: -$7,995
- Max drawdown: -$21,310
- Sharpe: -0.2048
- Bootstrap P(mean > 0): 36.31%

## Year by year

- 2021: 44 trades, +5.1898 pts/trade, PF 1.6542, +$11,417.50, Sharpe 1.1995
- 2022: 46 trades, -2.9478 pts/trade, PF 0.8528, -$6,780, Sharpe -0.3391
- 2023: 14 trades, -18.0464 pts/trade, PF 0.1813, -$12,632.50, Sharpe -2.3177

## Cost sensitivity

- ES 0 ticks: -1.2875 pts/trade, PF 0.9146
- ES 1 tick: -1.5375, PF 0.8987
- ES 2 ticks: -1.7875, PF 0.8831
- ES 4 ticks: -2.2875, PF 0.8526
- MES 1 tick: -1.7375, PF 0.8862

## Classification diagnostics

- N scored classification days: 694
- Accuracy: 51.8732%
- Majority-class baseline accuracy: 51.7291%
- Balanced accuracy: 37.4245%
- Median |target| on predicted trade days: 53.4287 bps
- Median |target| on predicted no-trade days: 38.8146 bps

Interpretation: headline accuracy barely exceeds the majority-class baseline by roughly 0.14 percentage points, while balanced accuracy is poor. The classifier does not demonstrate useful state discrimination.

## Tail robustness

After removing the single best trade:
- Average net points/trade: -2.3451
- PF: 0.8470

## Frozen gate

- n >= 150: FAIL
- avg net positive: FAIL
- PF >= 1.15: FAIL
- profitable in >=2/3 years: FAIL
- tail avg positive: FAIL
- bootstrap >= 0.90: FAIL
- two-tick avg positive: FAIL
- max positive-year share <= 0.75: FAIL
- classification beats majority: PASS, but only marginally

`ROUND5_STAGE1_SURVIVOR = False`

## Frozen conclusion

R5C1 is retired. Do not tune class thresholds, confidence cutoffs, features, or LDA settings using 2021–2023. 2024 remains protected and must not be exposed as a rescue attempt.
