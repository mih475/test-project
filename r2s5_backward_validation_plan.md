# R2S5 Backward Validation — Frozen Before Results

Date frozen: 2026-09-24

R2S5 (ETH ADX / RTH VWAP / ETH EMA20 trend pullback) was discovered in the Round-2 2021-2023 tournament with only 54 trades. It is NOT a formal survivor because the frozen sample-size gate required 100 trades.

No R2S5 rule, indicator, time window, entry, stop, target, or cost assumption may change for this test.

## Data blocks
- Backward unseen block: 2016-2020. These years were not used to select or tune R2S5.
- Original development block: 2021-2023, retained only for combined robustness reporting.
- 2024+ remain untouched.

## Exact strategy
Use the R2S5 implementation frozen in `strategy_tournament_round2.py` at commit `44afe2aef0876e196bd18738043ad0bb2e4f4826` / strategy implementation commit `ebf1fe310d052d2c4073400612e71c990c163f07`:
- same-contract Globex session beginning 18:00 ET
- ETH 15m ADX(14) in [25,35] and rising
- ETH 5m ADX(14) rising
- ETH 5m EMA20
- NY RTH session VWAP
- search RTH 10:30-15:00
- long: 5m close > VWAP, EMA20 > VWAP, candle touches/breaches EMA20 and closes back above; short mirror
- enter next 5m open
- stop 1 tick beyond pullback candle extreme
- target 2R
- max 2 trades/day, one active at a time
- same-bar stop+target => stop first

## Costs
Primary: ES $5 round-trip commission + 1 tick total adverse slippage.
Stress: ES and MES at 0/1/2/4 ticks.

## Pre-frozen backward-validation gate
R2S5 earns access to 2024 only if ALL are true:

1. Backward unseen 2016-2020 block has at least 60 trades.
2. Backward unseen block ES1 net average R > 0.
3. Backward unseen block ES1 PF >= 1.10.
4. At least 3 of the 5 backward years have positive ES1 net total R.
5. Combined 2016-2023 sample has at least 100 trades.
6. Combined 2016-2023 ES1 net average R > 0.10 and PF >= 1.20.
7. Combined ES4 net average R > 0.
8. Combined results after removing the five best trades still have avgR > 0 and PF >= 1.10.
9. No single trade contributes more than 20% of combined gross positive R.

If any gate fails, do not tune R2S5 using the older data and do not expose 2024 as a rescue attempt.
