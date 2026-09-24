# Round 6 — Cross-Index Relative-Value Residual Mean Reversion (Frozen Spec)

Frozen: 2026-09-24, before any Round-6 performance output is observed.

## Motivation
Rounds 1-5 failed to produce a robust modern directional ES edge. Round 6 changes the object being forecast. Instead of forecasting ES direction, it tests whether short-lived relative mispricing between ES, NQ and RTY mean-reverts.

Literature basis: pairs/statistical-arbitrage research treats deviations of related assets from a common relation as candidate mean-reverting spreads. Classic frameworks include Elliott, van der Hoek & Malcolm (Quantitative Finance, 2005, DOI 10.1080/14697680500149370) and the review by Krauss (Journal of Economic Surveys, 2017, DOI 10.1111/joes.12153). Price-discovery research documents tight information linkage across U.S. equity-index futures, including S&P 500 and Nasdaq E-minis (Hasbrouck, Journal of Finance, 2003; Ates & Wang, Journal of Futures Markets, 2005).

These papers motivate the family only. They do not validate the exact rule below.

## Data
- ES: existing audited free 1-minute source.
- NQ, RTY: already-downloaded Databento continuous 1-minute data (`NQ.v.0`, `RTY.v.0`).
- No new data purchase.
- Context/training: 2017-2020 where available.
- Primary research block: 2021-2023.
- Protected: 2024 validation, 2025 final holdout, 2026 current-regime confirmation.
- The Round-6 script must never load 2024+.

## 5-minute construction
- New York time.
- RTH grid 09:30-15:30 ET.
- A completed 5-minute return for a bar starting at T is `log(close[T:T+5) / open[T])`.
- Signal is known only after the bar completes.
- Entry/exit fills use the next exact 5-minute bar open.
- A session must have aligned ES/NQ/RTY bars and required entry/exit opens.
- ES RTH sessions with contract switching are excluded exactly as in prior work.
- If a Databento file exposes `symbol` or `instrument_id`, a cross-market session with more than one identifier during RTH is excluded; otherwise the continuous series is used as delivered.

## Daily hedge model
For each current session D:
1. Use the immediately preceding 60 complete aligned sessions only.
2. Pool all completed 5-minute returns from 09:30-15:25 in those sessions.
3. Fit one OLS relation, once before D:
   `r_ES = alpha + beta_NQ*r_NQ + beta_RTY*r_RTY + epsilon`
4. Use a pseudoinverse; no ridge/lasso and no hyperparameter fitting.
5. Coefficients stay fixed all day D.
6. Require all 60 prior complete sessions; otherwise D is ineligible.

## Time-of-day residual normalization
For each 5-minute slot on D:
1. Compute the current residual using D's frozen betas.
2. Recompute residuals for the same clock-time slot in the 60 training sessions using those same betas.
3. `z = (current_residual - mean(prior same-slot residuals)) / sample_std(prior same-slot residuals)`.
4. Require >=40 valid historical same-slot residuals and positive finite std.

This removes the deterministic intraday volatility pattern without using future observations.

## Primary strategy R6S1
- Signal bars: bars starting 10:00 through 15:00 ET inclusive.
- Entry threshold: `|z| >= 2.00` exactly. No nearby threshold sweep.
- If `z >= +2`: short the residual spread.
- If `z <= -2`: long the residual spread.
- Enter at the next 5-minute open.
- Spread weights at entry are frozen to `[ES=1, NQ=-beta_NQ, RTY=-beta_RTY]`; trade direction multiplies all weights.
- Maximum two trades per session; one active spread at a time.

### Exit
First of:
1. Residual z crosses zero relative to the entry dislocation, observed on a completed 5-minute bar; fill at the next 5-minute open.
2. 30 minutes after entry, at the exact 5-minute open.
3. 15:30 ET hard exit.

No stop-loss, profit target, trailing stop, confidence filter, weekday filter, news filter, volatility filter or direction deletion in Stage 1.

## Synthetic spread P&L
For a completed trade with direction `s` (+1 long residual, -1 short residual):
`spread_log_return = s * [log(ES_exit/ES_entry) - beta_NQ*log(NQ_exit/NQ_entry) - beta_RTY*log(RTY_exit/RTY_entry)]`

Normalize by gross dollar weight:
`gross_exposure = 1 + |beta_NQ| + |beta_RTY|`
`gross_bps = 10000 * spread_log_return / gross_exposure`

### Stage-1 friction
Because Stage 1 uses fractional synthetic hedge weights rather than integer futures contracts, costs are represented in basis points of gross exposure rather than pretending fractional contracts have exact commissions.
- Primary: 1.0 bp round-trip total friction.
- Stress: 0.0, 0.5, 1.0, 2.0, 3.0 bps.
- `net_bps = gross_bps - friction_bps`.

If R6S1 survives Stage 1, then BEFORE revealing 2024 we will freeze a second execution layer mapping the hedge to integer MES/MNQ/M2K contracts with explicit commissions/ticks and rerun 2019-2023. Only an execution-layer survivor can unlock 2024.

## Metrics
Primary 2021-2023:
- trades and eligible sessions
- trade rate
- long-residual / short-residual counts
- win rate
- average gross and net bps/trade
- profit factor
- total net bps
- max drawdown in cumulative net bps
- annualized Sharpe of daily net returns, including zero on eligible no-trade sessions
- fixed-seed 10,000-resample bootstrap probability mean daily net return > 0
- yearly metrics
- holding-time distribution
- tail robustness after deleting best 1% of trades (minimum 3 when n>=300, otherwise best 1)
- each residual side reported separately

## Frozen Stage-1 gate
R6S1 may proceed to the executable micro-contract layer only if ALL are true on 2021-2023:
1. >=150 completed trades.
2. Primary 1.0-bp net expectancy > 0.
3. Primary profit factor >=1.15.
4. Positive net total in at least 2 of 3 years.
5. After removing the best 1% trades, net expectancy remains >0.
6. Bootstrap probability mean daily net return >0 is >=90%.
7. At 2.0-bp total friction, net expectancy remains >0.
8. No single positive year contributes >75% of gross positive yearly net P&L.
9. Long-residual trades have non-negative 1.0-bp expectancy.
10. Short-residual trades have non-negative 1.0-bp expectancy.

Any failure => retire exact R6S1. Do not tune threshold, training window, holding period, signal clock range, regressors, exit, or one side using 2021-2023.

## Prohibited after results
- Trying z=1.5/1.75/2.25/etc.
- Trying 10/15/20/45/60-minute holds.
- Changing the 60-session training lookback.
- Dropping NQ or RTY after seeing attribution.
- Keeping only long-residual or short-residual trades.
- Adding volatility/VIX/volume/news/weekday/order-flow filters.
- Revealing 2024 to rescue a Stage-1 failure.
