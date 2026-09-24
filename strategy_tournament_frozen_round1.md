# Strategy Tournament — Frozen Round 1 Definitions

Date frozen: 2026-09-24
Instrument for first pass: ES continuous 1-minute source, RTH-derived bars unless explicitly stated.
Development only for first pass: 2021-2023. Do not inspect 2024+ when defining/tuning these rules.

## Common execution conventions

- Use New York time.
- Use the same roll-session exclusions and duplicate handling as `multiyear_backtest.py`.
- One active trade per strategy at a time.
- When stop and target are both touched inside the same source bar and order is unknowable, assume stop first.
- Initial Round-1 leaderboard uses ES with $5 round-trip commission and 1 tick total adverse slippage; also report 0/1/2/4 tick sensitivity and MES economics.
- Do not optimize parameters in Round 1. These definitions are frozen before seeing 2021-2023 tournament results.
- A strategy may be source-faithful or a pre-test mechanical translation. Mechanical translations test our codified version, not every discretionary interpretation a community trader may use.

---

## S1 — 15-minute ORB close-confirmation, long only

**Status:** Source-faithful to the S&P version described by Russ_CW, including the author's observation that shorts were not profitable on S&P.

**Source:** Reddit r/algotrading, “Backtest Results for the Opening Range Breakout Strategy” (2025).
https://www.reddit.com/r/algotrading/comments/1j9pxsr/backtest_results_for_the_opening_range_breakout/

**Bars:** 15-minute RTH bars.

**Rules:**
1. Opening range = high/low of 09:30-09:45 ET bar.
2. Starting after 09:45, a qualifying long signal occurs when a completed 15m candle closes strictly above opening-range high.
3. Enter at next 15m bar open, only if that entry is before 12:00 ET.
4. Stop = opening-range low.
5. Target = 1.5R.
6. After a trade exits, another qualifying long setup may be taken before 12:00; no fixed one-trade-per-day cap, matching the source's clarification.
7. No short trades in S1.
8. No new entries at/after 12:00. Open trades may continue until stop/target or RTH close; RTH-close exit at final bar close.

**Hypothesis:** strong opening upside acceptance can produce continuation in ES.

---

## S2 — 15-minute ORB + 5-minute close + retest

**Status:** Pre-test mechanical translation of a commonly described ORB retest method.

**Source:** Reddit r/FuturesTrading, “Opening range breakout traders” (2024). A contributor described 15m ORB, 5m closure outside, retest limit entry, stop below breakout candle, and 1:2 RR.
https://www.reddit.com/r/FuturesTrading/comments/1f5obss/

**Bars:** 15m opening range, 5m signal/entry bars.

**Rules:**
1. Opening range = 09:30-09:45 ET high/low.
2. After 09:45 and before 12:00, wait for the first completed 5m candle to close strictly outside the OR.
3. Long breakout: close > OR high. Short breakout: close < OR low.
4. After that breakout close, place a limit at the breached OR boundary: OR high for long, OR low for short.
5. Limit remains active until 12:00 ET unless invalidated first.
6. Long invalidation before fill: a completed 5m candle closes below OR low. Short invalidation: completed 5m candle closes above OR high.
7. On first touch/fill of boundary, enter.
8. Long stop = 1 tick below low of the 5m breakout candle. Short stop = 1 tick above high of breakout candle.
9. If stop is not on the protective side of entry by at least 1 tick, skip the setup.
10. Target = 2R.
11. Maximum one S2 trade per day, using the earliest valid filled retest.
12. Any open trade exits at stop, target, or RTH close.

**Hypothesis:** requiring both acceptance outside the OR and a retest avoids the worst first-break fakeouts.

---

## S3 — First-40-minute 9EMA continuation pattern

**Status:** Mostly source-faithful, with exact tick offsets and conservative OHLC ambiguity conventions frozen here.

**Source:** Reddit r/Daytrading, “Here’s my strategy” (2024).
https://www.reddit.com/r/Daytrading/comments/1eyyl9m/heres_my_strategy/

**Bars:** 2-minute RTH bars. 9EMA calculated on 2m RTH bars only, matching the source's “turn ETH off.”

**Trading window:** 09:30 through 10:10 ET. Signal sequence must begin and entry must occur before 10:10.

**Short rules:**
1. Weakness bar: completed 2m candle closes below the prior candle's close AND below 9EMA.
2. After weakness bar, wait for the first green 2m candle (close > open). This is the pullback/entry-reference candle.
3. Place sell-stop entry 1 tick below that green candle's low.
4. Entry order stays valid through the next completed 2m bar only. If not triggered, cancel and wait for a new full setup.
5. Initial stop = 1 tick above entry-reference candle high.
6. Long rules are the exact mirror: strength bar closes above prior close and 9EMA; first red pullback candle; buy-stop 1 tick above its high; stop 1 tick below its low.
7. At +0.85R favorable excursion, move stop to breakeven, effective from the next source bar to avoid unknowable intrabar ordering.
8. Before BE activation, if a completed 2m candle closes back inside the entry-reference candle's full high-low range, exit at that close (“partial-loss” rule from source).
9. Final target = 2R.
10. Take every sequential qualifying setup in the first 40 minutes, but only one active trade at a time.
11. Open trade at 10:10 may continue; no new setup may start after 10:10. Exit any survivor at RTH close.

**Hypothesis:** a short pause/pullback after immediate opening-session directional weakness/strength can continue with favorable 2R asymmetry.

---

## S4 — Later-session VWAP 2SD reversion with confirmed return

**Status:** Pre-test mechanical translation. Source gives the entry concept and target but not a mechanical stop, so stop is frozen here before testing.

**Source:** Reddit r/FuturesTrading, “The VWAP mean reversion is my new jam” (2025).
https://www.reddit.com/r/FuturesTrading/comments/1pladiq/the_vwap_mean_reversion_is_my_new_jam/

**Bars:** 1-minute RTH bars. Session VWAP and volume-weighted population SD bands calculated exactly as in existing research infrastructure.

**Rules:**
1. No setup before 10:30 ET.
2. Long setup begins only after price trades at or below VWAP - 2SD. Short setup begins only after price trades at or above VWAP + 2SD.
3. Track the most extreme price reached while outside/at 2SD.
4. Long confirmation: a later 1m candle both OPENS and CLOSES strictly between VWAP - 1SD and VWAP. Short confirmation: opens and closes strictly between VWAP and VWAP + 1SD.
5. Enter at next 1m open.
6. Stop = 1 tick beyond the tracked excursion extreme.
7. Target = current session VWAP from the confirmation bar.
8. Skip if target is not favorable relative to entry or stop distance < 1 tick.
9. One active trade at a time; after exit, a new independent 2SD excursion may create another setup.
10. No new entries after 15:30 ET. Exit survivors at RTH close.

**Hypothesis:** after the opening hour, an extreme VWAP displacement that has already shown follow-through back through the 1SD band has mean-reversion value.

---

## S5 — Initial-balance failed-break fade to NY VWAP

**Status:** Pre-test mechanical translation of an explicitly described community concept: if IB high/low fails to hold, fade back to NY VWAP.

**Sources:**
- Reddit r/FuturesTrading, “Initial balance strategy” (2026), discussion explicitly describes “if the IB high fails to hold and continue you fade it back to New York vwap.”
  https://www.reddit.com/r/FuturesTrading/comments/1uto3kr/initial_balance_strategy/
- Supporting ES IB statistics discussion: https://www.reddit.com/r/FuturesTrading/comments/1bycosx/

**Bars:** IB from 1m RTH data; 5m confirmation bars.

**Rules:**
1. Initial balance (IB) = 09:30-10:30 ET high/low.
2. Only search after 10:30 and before 14:00 ET.
3. Failed upside break: price trades at least 1 tick above IB high, then a completed 5m candle closes strictly back below IB high.
4. Failed downside break: price trades at least 1 tick below IB low, then a completed 5m candle closes strictly back above IB low.
5. Enter at next 5m bar open in the fade direction (short after failed high, long after failed low).
6. Stop = 1 tick beyond the most extreme price reached outside IB before the failure close.
7. Target = NY session VWAP value on the failure-confirmation bar.
8. Skip if VWAP is not on the profitable side of entry or stop distance < 1 tick.
9. Maximum one S5 trade per day, using the first valid failure.
10. Exit at stop, VWAP target, or RTH close.

**Hypothesis:** failure to establish acceptance beyond the first-hour auction extreme leads to rotation back toward fair value.

---

## S6 — 5-minute ORB + 1-minute FVG displacement breakout

**Status:** Community-derived mechanical strategy. Included despite overlap with ORB because it makes a materially different claim: imbalance/displacement, not merely breakout, creates the edge. It also has a useful public failure story over longer history, making it an excellent independent test candidate.

**Sources:**
- Reddit r/Trading, “$23,645 From 124 Trades Using a 5Min ORB Setup” (2026).
- Reddit follow-up long-history critique: “I backtested that 5-min ORB strategy ... 5 months look great. 7 years don't.” (2026).

**Bars:** 5m opening range; 1m entry/FVG logic.

**Rules:**
1. Opening range = high/low from 09:30-09:35 ET.
2. A long candidate requires a completed 1m candle to close above OR high and the breakout sequence to leave a bullish 3-candle fair-value gap: low of candle 3 > high of candle 1. Short mirror: high of candle 3 < low of candle 1.
3. The candle-3 close must be the breakout close beyond the OR boundary.
4. Enter at candle-3 close, modeled as next 1m open for executable backtest conservatism.
5. Long stop = 1 tick below the lower edge of the FVG sequence (candle-1 high). Short stop = 1 tick above upper edge (candle-1 low).
6. If stop distance < 1 tick, skip.
7. Target = 2R when stop distance <= 40 ES points; 1.5R when stop distance > 40 points, preserving the published rule family even though a 40-point ES stop should be rare.
8. If first trade wins, no more S6 trades that day. If first trade loses, allow one additional qualifying setup; maximum 2 trades/day.
9. No new entries after 12:00 ET. Exit survivors at stop, target, or RTH close.

**Hypothesis:** the subset of ORB breaks accompanied by a measurable 1m imbalance has better continuation than a naked breakout.

---

## Parked — not allowed into Round 1 without a new pre-test freeze

### P1 — ES 25/75 EMA pullback-resumption
Reason parked: the source explicitly uses ETH EMA calculations for futures and says stop/target are ticker-specific; those exact parameters were not disclosed. We will not invent them and call it a faithful replication.
Source: https://www.reddit.com/r/FuturesTrading/comments/1ey7w5s/my_ema_strategy/

### P2 — PDH/PDL liquidity sweep + order-flow absorption
Reason parked: compelling market mechanism, but the community descriptions rely on CVD/tape absorption and our purchased true-order-flow windows are currently specific to the retired strategy's event windows, not all PDH/PDL events. Price-only version could be designed later as a separate hypothesis.

### P3 — VWAP reclaim reversal
Reason parked: source is clear conceptually but target selection and “strong pressure” confirmation are discretionary. Could be mechanized later if Round 1 leaves room for a second wave.

---

## Frozen Stage-1 survival gate

For 2021-2023 development, a strategy is a Round-1 survivor if ALL are true under ES $5 RT commission + 1 tick total adverse slippage:

1. At least 100 completed trades, OR at least 75 if the strategy is structurally limited to one trade/day and all three years are represented.
2. Net average R > 0.
3. Net PF >= 1.10.
4. Positive net total R in at least 2 of 3 individual years.
5. After removing the five best trades, remaining net average R > 0 OR PF >= 1.05.
6. No single trade contributes >20% of total positive gross R.

Ranking among survivors is by a robustness score, not win rate: floor of yearly PF, net avgR, max drawdown, sample size, cost sensitivity, and top-winner dependence.

2024 remains unseen until rules and Round-1 survivors are frozen.