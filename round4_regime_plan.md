# Round 4 — Cross-Market / Regime-Conditioned ES Model

Date frozen: 2026-09-24

## Objective

Test whether a small, economically motivated cross-market state vector can forecast the direction and size of the **ES 10:00 ET -> 15:30 ET** return well enough to survive realistic ES/MES execution costs.

This round is intentionally different from prior setup hunting. We are not searching for another ORB/VWAP/reversal pattern. The hypothesis is that ES continuation/reversal behavior depends on the broader market state visible by 10:00 ET.

## Protected data

- Model-development / walk-forward research: 2016-2023 only.
- Primary modern scoring block: 2021-2023.
- Historical/context block: 2018-2020, generated only from genuine past-only walk-forward predictions.
- Minimum training history before a prediction: 504 prior eligible sessions.
- 2024: protected validation; do not load/reveal unless the frozen Stage-1 gate passes.
- 2025: protected holdout.
- 2026: recent-regime confirmation only after 2024 and 2025 survive.

No model/rule may be changed after seeing 2024+.

## Instruments

Primary traded instrument: ES.

Cross-market features:
- ES — S&P 500 E-mini
- NQ — Nasdaq-100 E-mini
- RTY — Russell 2000 E-mini
- ZN — 10-Year Treasury Note futures

ES remains sourced from the already-audited free 1-minute series where possible. NQ/RTY/ZN are requested from Databento only after a cost quote. Use `GLBX.MDP3`, `ohlcv-1m`, volume-ranked continuous contracts (`NQ.v.0`, `RTY.v.0`, `ZN.v.0`, `stype_in="continuous"`).

Databento continuous prices are unadjusted. Because Round 4 uses same-session percentage returns for NQ/RTY/ZN rather than multi-day price differences, roll-level jumps should not mechanically enter those features. Missing/abnormal roll sessions are still audited.

## Decision and trade horizon

All primary features must be observable by **10:00:00 ET**.

Primary trade:
- Entry: ES 10:00 ET open.
- Exit: ES 15:30 ET open.
- Direction: long, short, or flat according to the frozen model forecast.
- Maximum one trade per session.
- No stops/targets in Stage 1; this first asks whether the conditional directional edge exists at all. Prop-style stop/risk engineering is a later phase only if the signal survives.

Primary target for model fitting:
- ES 10:00 -> 15:30 return in basis points.

## Frozen feature set

No features observed after 10:00 ET are permitted.

1. `es_gap_bps` — previous eligible ES RTH close -> current 09:30 open.
2. `es_first30_bps` — ES 09:30 -> 10:00 return.
3. `nq_first30_bps` — NQ 09:30 -> 10:00 return.
4. `rty_first30_bps` — RTY 09:30 -> 10:00 return.
5. `zn_first30_bps` — ZN 09:30 -> 10:00 return.
6. `equity_consensus` — mean sign of ES/NQ/RTY first-30-minute returns; values in {-1, -1/3, +1/3, +1}; zero components contribute 0.
7. `equity_dispersion_bps` — cross-sectional standard deviation of ES/NQ/RTY first-30-minute returns.
8. `nq_minus_rty_bps` — NQ first-30 return minus RTY first-30 return.
9. `es_open_range_rel20` — ES 09:30-10:00 high-low range divided by the median first-30 range of the preceding 20 eligible sessions.
10. `es_prev_range_rel20` — prior ES RTH high-low range divided by the median prior-session range over the preceding 20 eligible sessions.
11. `es_open_volume_rel20` — ES 09:30-10:00 volume divided by the median first-30 volume of the preceding 20 eligible sessions.
12. `gap_open_alignment` — sign agreement between `es_gap_bps` and `es_first30_bps`: +1 same sign, -1 opposite sign, 0 if either is zero.

Rolling medians are strictly prior-only; the current session is excluded.

## Primary model — R4M1

A deliberately simple walk-forward linear model.

- Model: ordinary least squares regression with intercept.
- Inputs: the 12 frozen features above.
- Standardization: training-sample mean and standard deviation only; applied unchanged to the prediction row.
- Training window: expanding history using every eligible session strictly before the prediction session.
- Minimum training observations: 504.
- Refit cadence: every 20 eligible sessions; predictions between refits use the most recent fitted coefficients.
- Missing feature row: no trade.
- Singular/ill-conditioned fit: use Moore-Penrose pseudo-inverse; no feature deletion based on results.

The model predicts the ES 10:00->15:30 return in basis points.

### Frozen trade conversion

At the 10:00 ES entry price, convert assumed friction to basis points.

Primary ES friction:
- $5 round-trip commission = 0.10 ES points.
- 1 total adverse tick = 0.25 points.
- Total primary friction = 0.35 ES points.

Trade only when `abs(predicted_move_bps)` is greater than the primary friction expressed in basis points at the current ES entry price.

- prediction > +friction_bps: long
- prediction < -friction_bps: short
- otherwise: flat

This threshold is economic break-even, not fitted to historical performance.

## Diagnostic baselines — not independently eligible to unlock 2024

These are comparators, not extra optimization paths.

### B1 — ES-only first-30 continuation
Long if ES first-30 return > 0, short if < 0; 10:00 -> 15:30.

### B2 — Equity-consensus continuation
Long only when ES/NQ/RTY first-30 returns are all positive; short only when all are negative; otherwise flat.

### B3 — Cross-market OLS without regime variables
OLS using only `es_gap_bps`, `es_first30_bps`, `nq_first30_bps`, `rty_first30_bps`, and `zn_first30_bps`. Same walk-forward and economic threshold as R4M1. This measures whether the explicit dispersion/volatility-state features add value.

Only R4M1 is the primary candidate. The baselines cannot rescue a failed R4M1 without a separately pre-registered new round.

## Diagnostics

Report for R4M1 and baselines:
- eligible sessions
- trades / trade rate
- long / short split
- win rate
- average gross points
- average net ES points
- average dollars/trade
- profit factor
- total dollars per one ES contract
- maximum drawdown
- annualized daily Sharpe with flat/no-trade sessions included as zero
- bootstrap P(mean net return > 0)
- year-by-year metrics
- cost sensitivity: ES 0/1/2/4 adverse ticks and MES 0/1/2/4 ticks
- tail robustness after removing the largest 1% of winning trades (minimum 3 when sample >=300)
- prediction/realized correlation
- directional accuracy on traded sessions
- coefficient snapshots through time
- performance by prior-only volatility tercile, equity-consensus state, and dispersion tercile

Regime buckets are diagnostics only and may not be turned into filters after results are seen.

## Stage-1 survival gate

R4M1 earns a 2024 reveal only if the **2021-2023 primary block** satisfies all of the following under ES $5 round trip + 1 adverse tick:

1. At least 150 trades.
2. Positive average net points/trade.
3. Profit factor >= 1.10.
4. Positive net result in at least 2 of 3 years.
5. Positive average net points after removing the largest 1% of winning trades.
6. Bootstrap P(mean net return > 0) >= 0.90.
7. ES +2 adverse ticks is not materially negative: average net points/trade >= -0.05.
8. No single year contributes more than 80% of total positive net dollars.

If any gate fails: `ROUND4_STAGE1_SURVIVOR = False` and 2024 stays hidden.

## Why these inputs are legitimate hypotheses

The literature supports three broad ideas rather than one fixed setup:

- intraday predictive relations can be regime-dependent rather than stable through calendar time;
- overnight/opening information can forecast specific later intraday intervals, but published effects can decay out of sample;
- cross-market relationships and volatility/stress states change the strength of price discovery and lead-lag behavior.

Round 4 therefore tests a parsimonious state model rather than presuming that momentum or mean reversion is always active.

## Anti-overfitting rules

- No threshold sweep.
- No changing the 10:00 entry or 15:30 exit after viewing results.
- No adding/removing individual features because their coefficients look weak.
- No cherry-picking volatility/consensus buckets into trading filters.
- No nonlinear model in this round if R4M1 fails.
- No 2024 reveal to diagnose a failed Stage 1.
- Databento order-flow data is not required for Stage 1 and will not be purchased for this model unless price-level evidence first survives.

## Immediate data step

Before downloading NQ/RTY/ZN history, run the Round-4 Databento cost estimator. It performs metadata cost calls only and downloads no time-series data.
