# Round 3 Step 1 — Frozen Literature-Derived Specifications

Date frozen: 2026-09-24
Repository: mih475/test-project
Instrument: ES (E-mini S&P 500 futures), with MES economics also reported.

## Purpose
Round 3 is not another community-pattern search. These tests are derived from published intraday-return research. The first pass must preserve the source hypothesis as closely as practical. Stops, profit targets, EMA/RSI filters, CVD filters, and discretionary confirmation are prohibited unless explicitly part of a later, separately frozen risk-management study.

## Common data and execution conventions
- New York time.
- Same continuous-contract construction, duplicate handling, and roll-switch-session exclusions used in prior ES research.
- Use actual 1-minute bars for signal prices and fixed-time exits.
- For scheduled timestamps, use the first available 1-minute bar at/after the intended timestamp; reject a day if a required timestamp is missing by more than 1 minute.
- For prior RTH close, use the immediately prior valid same-contract RTH session close.
- RTH reference window: 09:30-16:00 ET unless the paper explicitly uses another window.
- No same-day overlapping positions within a strategy.
- Primary economics: ES $5 round-trip commission + 1 tick total adverse slippage.
- Stress: ES and MES at 0/1/2/4 total adverse ticks.
- For fixed-time strategies, primary performance units are points/trade, dollars/contract, basis points/return, win rate, annualized Sharpe of daily net returns, cumulative net P&L, max drawdown, year-by-year consistency, bootstrap confidence/probability for mean > 0, and tail robustness.
- R-multiple metrics are secondary/not applicable unless a later risk-managed implementation adds an ex-ante stop.
- Same-day transaction cost is applied once per round trip.
- No threshold sweeps in Round 3 Stage 1.

## Era labels
These labels are source-specific; they prevent us from calling overlapping paper data “out of sample.”

- 2016-2020: backward/post-sample audit block. Depending on source, this may overlap the original paper sample or be post-sample/pre-publication.
- 2021-2023: common modern research block used for the Round 3 tournament. No tuning inside this block beyond the exact frozen rules below.
- 2024: protected validation.
- 2025: protected final holdout.
- 2026: protected current-regime confirmation; only reveal after prior gates.

For every strategy, report results separately for 2016-2020 and 2021-2023 before any 2024 test.

---

## R3S1 — Rest-of-Day -> Last-30-Minute Momentum

### Source
Baltussen, Da, Lammers, Martens, “Hedging Demand and Market Intraday Momentum,” Journal of Financial Economics 142 (2021), 377-403.
- Published sample: more than 60 futures, 1974-May 2020.
- ES is explicitly included with common trading hours 09:30-16:00 ET.
- Source definition: rest-of-day (ROD) return is from previous market close through the start of the final 30 minutes; last-half-hour (LH) return is the final 30 minutes.

### Frozen rule
1. At 15:30 ET on day t, compute `rod_ret = price(15:30_t) / prior_RTH_close - 1`.
2. If `rod_ret > 0`, enter long at 15:30 ET.
3. If `rod_ret < 0`, enter short at 15:30 ET.
4. If exactly zero, no trade.
5. Exit at 16:00 ET.
6. One trade/day; no stop or target.

### Era interpretation
- 2016-May 2020 overlaps the paper's ES sample: replication only.
- 2021 onward is post-publication/post-sample evidence and is the key test.

### Hypothesis
Directional movement accumulated from the prior close through 15:30 predicts continuation during the final 30 minutes, consistent with hedging/rebalancing demand.

---

## R3S2 — First-30-Minute -> Last-30-Minute Momentum

### Source
Gao, Han, Li, Zhou, “Market Intraday Momentum,” Journal of Financial Economics 129 (2018), 394-414.
- Main S&P 500 ETF sample: Feb 1993-Dec 2013.
- The first-half-hour return is measured from the previous market close to the end of the first 30 minutes.
- Their market-timing rule goes long in the last half-hour when the first-half-hour signal is positive and short when negative; exit at market close.

### Frozen ES translation
1. Compute `first30_signal = price(10:00_t) / prior_RTH_close - 1`.
2. At 15:30 ET, if signal > 0, enter long.
3. If signal < 0, enter short.
4. If signal == 0, no trade.
5. Exit at 16:00 ET.
6. No stop or target.

### Era interpretation
- The source sample ends in 2013, so all of our 2016+ data are post-sample.
- 2018+ is also post-publication.

### Hypothesis
Information incorporated from the prior close through the first 30 minutes continues to influence the final 30 minutes.

---

## R3S3 — Overnight Return -> First-30-Minute Reversal

### Sources
Liu & Tse, “Overnight Returns of Stock Indexes: Evidence from ETFs and Futures,” International Review of Economics & Finance 48 (2017), 440-451.
- Sample: 1999-2014.
- Finds a negative relationship between overnight return and 09:30-10:00 return in U.S. markets.

Iwanaga & Sakemoto, “Does overnight return predict the first half-hour return for U.S. market indices?”, North American Journal of Economics and Finance 86 (2026), 102707.
- Confirms negative overnight-to-first-half-hour relation for U.S. market-index ETFs, stronger in stress/high-volatility periods and weaker after the 2010s.

### Frozen ES translation
1. `overnight_ret = current_09:30_open / prior_RTH_close - 1`.
2. If overnight_ret > 0, enter short at 09:30 ET.
3. If overnight_ret < 0, enter long at 09:30 ET.
4. If zero, no trade.
5. Exit at 10:00 ET.
6. No stop or target.

### Era interpretation
- Source sample ends 2014; all 2016+ observations are post-sample.
- Recent literature explicitly warns that the effect weakened in later years, so modern persistence is uncertain by design.

### Hypothesis
Overnight price pressure partially reverses during the first half-hour of U.S. trading.

---

## R3S4 — Large Opening-Gap Reversal After 10-Minute Continuation

### Source
Grant, Wolf, Yu, “Intraday price reversals in the US stock index futures market: A 15-year study,” Journal of Banking & Finance 29 (2005), 1311-1327.
- S&P 500 futures sample: Nov 1987-Sep 2002.
- Examines opening-gap filters ±0.10%, ±0.20%, ±0.30%; published presentation emphasizes ±0.20%.
- Finds roughly 10 minutes of continuation after the open followed by reversal; transaction costs materially reduce the effect.

### Frozen live-test translation
1. `gap = current_09:30_open / prior_RTH_close - 1`.
2. Require `abs(gap) >= 0.20%` exactly; no alternate threshold test in Stage 1.
3. Do nothing for the first 10 minutes.
4. At 09:40 ET:
   - gap > 0 -> enter short;
   - gap < 0 -> enter long.
5. Primary exit = 10:30 ET. This is a pre-test mechanical translation of the paper's documented post-10-minute reversal horizon, not claimed as the paper's exact trading rule.
6. No stop or target.
7. One trade/day.

### Required diagnostic, not optimization
Also report the same 09:40 entry marked-to-market at 10:00, 11:00, and 12:00 ET as a horizon profile. The 10:30 exit is the only tournament score. The extra horizons may not be used to replace the primary rule after results are seen.

### Era interpretation
- Paper sample ends 2002 and publication is 2005; all 2016+ data are clean post-publication evidence.

### Hypothesis
Large opening dislocations initially continue for ~10 minutes, then partially reverse.

---

## R3S5 — European-Open Four-Hour Drift

### Source
Bondarenko & Muravyev, “Market Return Around the Clock: A Puzzle,” Journal of Financial and Quantitative Analysis 58 (2023), 939-967; working paper 2020/online 2022.
- E-mini S&P primary sample: Jan 2004-Jul 2018.
- Main EU-open window: 23:30-03:30 ET.
- Source reports the four-hour window accounts for essentially all average market return in its sample and remains positive after costs.
- Later New York Fed evidence (2026) reports that the narrower 02:00-03:00 overnight drift was approximately flat during 2021-2025, so decay is a known risk.

### Frozen rule
1. Enter long ES at 23:30 ET.
2. Exit at 03:30 ET.
3. Attribute the trade to the calendar/RTH session that follows the overnight window.
4. No signal filter, stop, target, weekday filter, or VIX conditioning.
5. Skip incomplete overnight sessions or contract-mismatch/roll-contaminated windows.

### Era interpretation
- 2016-Jul 2018 overlaps the source sample: replication only.
- Aug 2018-2020 is post-sample but mostly pre-publication/working-paper era.
- 2021 onward is the most important modern/post-publication test.

### Hypothesis
Uncertainty resolution around Asian close/European open historically produced a persistent positive ES drift.

---

## R3S6 — High-Volatility First-30 -> Last-30 Momentum

### Source
Gao, Han, Li, Zhou (2018), same study as R3S2.
- The paper computes first-half-hour realized volatility from 1-minute returns and sorts days into volatility terciles.
- Intraday momentum is materially stronger in the high-volatility tercile.

### Frozen live-safe translation
This is source-motivated but cannot use full-sample ex-post terciles in a tradable backtest.

1. Compute 1-minute log returns within 09:30-10:00 ET.
2. First-half-hour realized volatility = `sqrt(sum(r_1m^2))` over those 30 one-minute returns.
3. Before trading day t, compute the 66.6667th percentile of first-half-hour realized volatility using the immediately preceding 252 valid sessions only.
4. Require at least 126 prior valid observations; otherwise no trade.
5. If current first-half-hour realized vol is strictly above that prior-only threshold, the day qualifies as “high volatility.”
6. Direction signal is exactly R3S2: previous RTH close -> 10:00 return.
7. At 15:30 ET, enter long if signal > 0, short if signal < 0.
8. Exit at 16:00 ET.
9. No stop or target.

### Era interpretation
Same as R3S2: all 2016+ data are post-sample; 2018+ is post-publication.

### Hypothesis
The first-to-last half-hour continuation effect strengthens when the opening half-hour contains unusually high realized volatility.

---

# Round 3 Stage-1 scoring and frozen gate

The strategies differ in frequency, so there is no arbitrary requirement for hundreds of trades if the source itself produces fewer events. However, a strategy must have enough independent observations to make a meaningful claim.

## Primary modern block: 2021-2023
To earn 2024 validation, a strategy must satisfy ALL of the following on 2021-2023 unless explicitly labeled a negative-control test:
1. At least 100 trades/events.
2. Positive ES net mean return/expectancy at $5 RT + 1 tick total adverse slippage.
3. Annualized net Sharpe >= 0.50.
4. Positive net total in at least 2 of 3 years.
5. Positive net expectancy at 2 ticks total adverse slippage.
6. After removing the best 1% of trades (minimum 3 when n>=300; otherwise the best 1 trade), net expectancy remains > 0.
7. No single trade contributes > 10% of total gross positive P&L.
8. Fixed-seed bootstrap (10,000 resamples of daily/trade net returns) gives >= 90% probability that mean net expectancy > 0.

## Context block: 2016-2020
- Report exactly the same metrics, but do not tune from them.
- Label overlap/post-sample status strategy-by-strategy as defined above.
- A strategy that is strongly positive only in 2021-2023 but clearly negative across a genuinely post-sample/post-publication 2016-2020 block is flagged regime-sensitive even if it technically passes the modern gate.

## 2024/2025/2026 protection
- 2024 is revealed only for a Stage-1 survivor.
- 2025 remains final holdout.
- 2026 remains current-regime confirmation.
- No parameter, time-window, threshold, direction, stop, or target changes are permitted after seeing any protected year.

# Negative-control interpretation
R3S5 is partly a negative-control/decay test because newer evidence says the narrower European-open drift weakened sharply after 2020. Failure in 2021-2023 is therefore informative and should increase confidence in the framework rather than invite optimization.

# What is explicitly prohibited in Stage 1
- Testing nearby times and keeping the best one.
- Replacing 30 minutes with 15/20/45/60 after seeing results.
- Altering the 0.20% gap threshold.
- Adding VIX, volume, day-of-week, news, EMA, VWAP, CVD, gamma, or order-flow filters after seeing results.
- Adding stops/targets to rescue a fixed-time anomaly.
- Deleting long or short signals post hoc.
- Reclassifying 2016-2020 as “out of sample” when it overlaps a source paper's sample.

# Next action
Implement one Round-3 backtester that reproduces these six frozen strategies, loads only 2016-2023, prints source-era labels and all frozen metrics, and does not load 2024-2026.