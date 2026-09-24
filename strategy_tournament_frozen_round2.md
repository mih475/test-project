# Strategy Tournament — Frozen Round 2 Definitions

Date frozen: 2026-09-24
Development only: 2021-2023. Do not inspect 2024+ when defining/tuning these rules.
Instrument: ES. Use same roll-session exclusions/duplicate rules as prior research.

## Common execution and scoring
- New York time.
- Use actual 1m source bars for fills/stop/target simulation.
- One active trade per strategy at a time.
- Same-bar stop+target ambiguity => stop first.
- Primary economics: ES $5 RT commission + 1 tick total adverse slippage.
- Also report ES 0/2/4 ticks and MES 0/1/2/4 ticks.
- No parameter optimization in Round 2.
- Stage-1 survivor gate is unchanged from Round 1: generally n>=100 (or >=75 for structurally low-frequency one-trade/day systems), net avgR>0, net PF>=1.10, positive net total R in >=2 of 3 years, drop-5-winners avgR>0 OR PF>=1.05, and no single winner >20% of gross positive R.

## R2S1 — RTH gap-fill with first-30m confirmation
Status: pre-test mechanical translation of widely discussed ES RTH gap-fill setup.
Sources:
- https://www.reddit.com/r/Daytrading/comments/1wfi1fs/rth_gap_fill/
- https://www.reddit.com/r/Daytrading/comments/zq4ebl/how_i_trade_gaps_in_es_spy/
Rules:
1. Prior RTH close must come from the immediately prior valid session on the same futures contract.
2. Gap = current 09:30 RTH open minus prior RTH close. Require |gap| >= 0.10% of prior close.
3. Search 09:30-10:00 only for confirmation.
4. Gap up: first completed 5m bar that closes below the 09:30 open confirms a fill attempt; enter short at next 5m open. Gap down: first completed 5m bar closing above the 09:30 open; enter long next 5m open.
5. Stop = 1 tick beyond the session extreme reached through the confirmation bar.
6. Target = prior RTH close.
7. Skip if target is not favorable or stop distance <1 tick.
8. One trade/day; exit stop/target/RTH close.
Hypothesis: meaningful RTH gaps that immediately show counter-gap acceptance tend to rebalance toward the prior close.

## R2S2 — Overnight high/low break + retest continuation
Status: community-derived mechanical translation.
Sources:
- https://www.reddit.com/r/FuturesTrading/comments/1fpv04v/
- https://www.reddit.com/r/FuturesTrading/comments/1kg7h03/
Rules:
1. Overnight range uses same active contract from 18:00 ET prior calendar day through 09:29 ET current day. Require >=500 valid 1m rows.
2. ONH/ONL = overnight high/low.
3. From 09:30 to 12:00, identify first completed 5m candle closing strictly above ONH or below ONL.
4. After breakout close, place limit at breached ON boundary; order remains active until 12:00 unless invalidated by a completed 5m close through the opposite ON boundary.
5. First touch fills at boundary.
6. Long stop = 1 tick below low of breakout 5m candle. Short stop = 1 tick above breakout-candle high.
7. Skip if stop is not protective by >=1 tick.
8. Target = 2R. One trade/day.
Hypothesis: acceptance outside the overnight auction followed by a controlled retest can continue during RTH.

## R2S3 — Initial-balance accepted-break continuation
Status: mechanical test derived from ES IB single-break statistics/discussion.
Sources:
- https://www.reddit.com/r/FuturesTrading/comments/1bycosx/
- https://www.reddit.com/r/FuturesTrading/comments/1uto3kr/initial_balance_strategy/
Rules:
1. IB = 09:30-10:30 RTH high/low.
2. Search 10:30-14:00.
3. First completed 5m candle closing strictly above IB high => long candidate; below IB low => short candidate.
4. Enter at next 5m open.
5. Long stop = IB high - 1 tick. Short stop = IB low + 1 tick.
6. Skip if stop distance <1 tick.
7. Target = 1.5R.
8. One trade/day; exit stop/target/RTH close.
Hypothesis: once the first-hour auction accepts outside one side of the IB, continuation is more likely than a full rotation through the range.

## R2S4 — Prior-day high/low break + retest continuation
Status: pre-test mechanical level-break strategy.
Supporting community context:
- https://www.reddit.com/r/Daytrading/comments/1nyboro/
- https://www.reddit.com/r/FuturesTrading/comments/19flktw/
Rules:
1. Prior-day high/low are from immediately prior valid RTH session on the same contract.
2. Search 09:30-14:00 for first completed 5m close strictly beyond PDH or PDL.
3. After breakout close, place limit at breached prior-day level through 14:00.
4. First touch fills at level.
5. Long stop = 1 tick below breakout-candle low. Short stop = 1 tick above breakout-candle high.
6. Skip if stop is not protective by >=1 tick.
7. Target = 2R.
8. One trade/day.
Hypothesis: prior-day extremes act as auction reference levels; acceptance through the level plus a successful retest can continue.

## R2S5 — ADX/VWAP/EMA20 trend pullback
Status: source-inspired mechanical translation.
Source: https://www.reddit.com/r/Daytrading/comments/1rv0vci/hows_my_strategy/
Rules:
1. RTH 15m ADX(14) must be 25-35 inclusive and rising versus previous completed 15m bar.
2. RTH 5m ADX(14) must be rising versus previous completed 5m bar.
3. Use RTH session VWAP and 5m EMA20.
4. Search 10:30-15:00.
5. Long trend condition: 5m close > VWAP, EMA20 > VWAP. Pullback candle must trade at/below EMA20 and close back above EMA20.
6. Short mirror: close < VWAP, EMA20 < VWAP; candle trades at/above EMA20 and closes below it.
7. Enter next 5m open.
8. Stop 1 tick beyond pullback candle extreme.
9. Target 2R.
10. Max 2 trades/day, one active at a time.
Hypothesis: a rising-trend-strength regime plus VWAP alignment filters EMA pullbacks to directional continuation rather than chop.

## R2S6 — 1m EMA9/EMA19 retest scalp
Status: strict mechanical translation of a highly discussed NQ/indices setup; tests the codified rule, not the author's discretionary screenshots.
Source: https://www.reddit.com/r/Daytrading/comments/1ln0lpm/im_getting_a_lot_of_questions_about_my_strategy/
Rules:
1. RTH 1m EMA9 and EMA19.
2. Search 09:45-12:00.
3. Long eligibility at end of minute t: EMA9>EMA19 and the last 3 completed closes are all above both EMA9 and EMA19.
4. For minute t+1, place a buy limit at EMA9(t). If touched, enter there. Stop = EMA19(t)-1 tick.
5. Short mirror: EMA9<EMA19, last 3 closes below both; sell limit EMA9(t), stop EMA19(t)+1 tick.
6. Skip if stop distance <1 tick or >8 ES points (source repeatedly emphasizes tight stops; 8 points is frozen pre-test mechanical cap).
7. Target = 2R.
8. Max 3 trades/day; one active trade at a time.
Hypothesis: very short-term directional EMA alignment followed by a shallow fast-EMA retest can produce asymmetric continuation.

## Parked for later
- Raw overnight touch/reversal without confirmation: too discretionary.
- Gap-and-go: highly overlapping with breakout families; revisit only if gap-fill or ON breakout provides evidence.
- Order-flow/DOM level strategies: require broader paid event data; only justify later if price-only level strategy survives.
- Compression/Narrow-range breakout: promising but threshold definition is too easy to data-mine; hold for a separately frozen study.
