# ES/MES Strategy Tournament — Frozen Research Protocol

## Objective
Discover mechanically testable ES/MES intraday strategies from trader communities and published research, then independently test them under one common framework. Community claims are treated as hypotheses, not evidence of profitability.

## Data split
- Development: 2021–2023
- Validation: 2024
- Holdout: 2025
- Recent/regime confirmation: 2026

Do not inspect 2024+ for strategy selection until a strategy passes the prior stage.

## Common assumptions
- ES 1-minute RTH data already used in the project unless a strategy explicitly requires overnight data.
- Realistic commissions/slippage reported for both ES and MES.
- One-active-trade or one-trade-per-day rules must be specified per strategy before testing.
- Same-bar stop/target ambiguity handled conservatively (stop first).
- No parameter mining after seeing holdout results.

## Initial candidate families
1. 15-minute Opening Range Breakout — close outside range, next-bar entry, opposite side stop, fixed R target.
2. 5-minute ORB + retest/rejection — breakout, retest of OR boundary, wick/engulfing confirmation, continuation entry.
3. ORB + acceptance filter — breakout close outside, subsequent hold/acceptance outside before entry.
4. ORB + volatility/regime filter — opening-range width relative to recent volatility; trade continuation only when range/regime is suitable.
5. Failed ORB / failed auction reversal — break outside range, close back inside within a fixed number of bars, fade toward opposite range/VWAP.
6. VWAP trend pullback — establish directional regime on one side of VWAP, enter first structured pullback/reclaim in trend direction.
7. Prior-day / overnight high-low liquidity sweep reversal — sweep a key level, fail to hold, reclaim level, enter reversal.
8. Overnight range breakout/continuation — break overnight high/low after RTH open with confirmation.
9. Long-only intraday capitulation mean reversion — completed 15-minute bar, large downside displacement in an uptrend, next-bar entry, fixed stop/target, EOD flat.
10. Prior-day compression / NR-style breakout — previous-session compression plus opening-range expansion trigger.

## Stage 1 screening — 2021–2023 only
Each strategy gets a small number of pre-specified variants only when the source itself defines them (for example 5m vs 15m ORB or 1R vs 2R target). Do not optimize dozens of thresholds.

For every candidate report:
- trades
- raw win rate
- raw avg R
- raw PF
- net avg R after ES costs + 1 adverse tick
- net PF
- total net R
- max drawdown R
- year-by-year performance
- long vs short
- tail test: remove top 1/3/5 winners
- 0/1/2/4 tick slippage sensitivity

## Stage 1 survival gate
A candidate advances only if, in development:
- adequate sample size (normally >=100 trades unless the strategy is intentionally rare)
- positive after-cost expectancy
- PF >= 1.10
- not dominated by a few outlier winners
- no obviously catastrophic single-year failure without an economically pre-specified regime explanation

## Stage 2 — 2024 validation
Freeze the exact rules before revealing 2024.
Preferred validation targets:
- positive after-cost expectancy
- PF >= 1.10, preferably >=1.20
- acceptable slippage sensitivity
- reasonable drawdown/losing streak
- broadly consistent behavior with development

## Stage 3 — 2025 true holdout
No changes after 2024 validation. 2025 determines whether the strategy remains viable.

## Stage 4 — 2026 recent confirmation
Used for regime/current-market relevance, not as a pure holdout.

## Order-flow policy
Do not spend more Databento credits on every strategy. Test price/volume structure first. Use true aggressor-side data only on strategies that already show a plausible price-based edge and where order flow has a clear economic role (e.g., acceptance, absorption, or failed-auction confirmation).

## Initial source leads
- Reddit r/algotrading: 15m ORB backtest with close outside range, next-bar entry, opposite-side stop, 1.5R target.
- Reddit r/Daytrading: 5m ORB breakout + retest + wick/engulfing confirmation, 2R target.
- Reddit r/algorithmictrading/r/quant: MES FVG ORB + retest + engulfing confirmation; strong claimed recent backtest but explicit concerns about OOS robustness.
- Reddit r/algotrading: mechanical long-only 15m intraday capitulation mean reversion on ES/NQ, next-bar entry, fixed stop/target, EOD flat.
- Current ES strategy articles: OR continuation, failed breakout, VWAP reclaim, trend pullback, and volatility-qualified ORB.

## Research principle
The goal is not to find a parameter set that looks good. The goal is to identify a market mechanism that survives independent periods, realistic friction, and simple perturbations.
