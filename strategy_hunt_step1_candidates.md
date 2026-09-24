# Step 1 — Community Strategy Hunt (ES/MES)

Status: source-discovery and rule-extraction only. No backtest results from our data are used to select or tune these candidates.

## Research protocol

- Primary instrument for tournament: ES/MES.
- Development: 2021–2023 only.
- 2024 validation remains unseen until a rule survives development.
- 2025 true holdout; 2026 recent-regime check.
- Community profit claims are treated as hypotheses, not evidence.
- First-pass implementation must use source rules as closely as possible.
- Any rule that requires us to invent a threshold is marked NEEDS FREEZE before coding.

## A-tier: sufficiently mechanical to code now

### A1 — 15-minute ORB close-confirmation continuation
Source: https://www.reddit.com/r/algotrading/comments/1j9pxsr/backtest_results_for_the_opening_range_breakout/

Source rules:
- Opening range = 09:30–09:45 ET high/low.
- Long: a later candle breaks above OR high and closes above it.
- Short mirror can be tested separately; source author later noted SP500 shorts were mixed/unprofitable, so long and short must be reported separately.
- Entry = next candle open.
- Only signals before 12:00 ET.
- Stop = opposite side of opening range.
- Target = 1.5R.

Why include: very explicit, simple, independently reproducible, substantial community attention.
Caution: source test used S&P 500 CFD data and omitted futures commissions/slippage.

### A2 — 15-minute ORB + 5-minute close + retest
Source: https://www.reddit.com/r/FuturesTrading/comments/1f5obss/opening_range_breakout_traders/

Source rules:
- Opening range = first 15 minutes.
- Use 5-minute bars for confirmation/entry.
- Require 5m candle close outside OR.
- Wait for retest of OR boundary.
- Entry at the retest (limit-style logic).
- Stop below breakout candle for long / above for short.
- Target = 2R.

Why include: directly addresses ORB fakeouts rather than blindly taking first break.
Caution: retest-fill assumptions need conservative bar handling.

### A3 — 15-minute ORB breakout + pullback, time exit
Source: https://www.reddit.com/r/FuturesTrading/comments/1joy48s/15_minute_opening_range_break_strategy/

Source rules:
- Opening range = 09:30–09:45 ET wick-to-wick.
- Wait for breakout.
- Wait for pullback to the broken boundary.
- Enter in breakout direction on pullback.
- Stop slightly beyond opposite side of OR.
- Exit at 11:00 ET regardless of P/L.

Why include: exit structure is materially different from fixed-R ORB.
NEEDS FREEZE: define "slightly beyond" as one ES tick; define retest as first bar touching boundary after confirmed break.

### A4 — First-40-minutes 9EMA continuation pattern
Source: https://www.reddit.com/r/Daytrading/comments/1eyyl9m/heres_my_strategy/

Source rules (2-minute chart, RTH only; originally NQ/MNQ):
Short:
- Close below previous candle and below 9EMA.
- Then wait for a green candle (pullback/pause).
- Enter on a new low below that green/pullback candle using stop-limit logic.
- Stop above the entry/pullback candle.
Long = exact mirror.
- Take every setup in first 40 minutes of NY session.
- Move stop to breakeven after +0.85R.
- If price closes back within the entry candle, exit for partial loss.
- Full target = 2R.

Why include: unusually explicit and mechanically testable.
Caution: source is NQ/MNQ-specific; ES test is a transfer hypothesis, not reproduction.

### A5 — VWAP standard-deviation mean reversion after 10:30
Source: https://www.reddit.com/r/FuturesTrading/comments/1pladiq/the_vwap_mean_reversion_is_my_new_jam/

Source rules:
- Session VWAP with standard-deviation bands.
- Wait until after 10:30 ET.
- Price first stretches into outer VWAP deviation bands.
- Require a return toward the first deviation.
- Entry only after a candle OPENS and CLOSES between the first deviation band and VWAP (confirmation/follow-through, not just a wick).
- Target = VWAP (source also allows key S/R, but tournament base version uses VWAP to remain mechanical).

Why include: later-session reversion, different timing and trigger from the retired 2-sigma/CVD strategy.
NEEDS FREEZE: source does not specify stop. Pre-test freeze should use the excursion extreme + 1 tick or a fixed structural stop; do not optimize.

### A6 — Initial-Balance failed-break fade to NY VWAP
Source: https://www.reddit.com/r/FuturesTrading/comments/1uto3kr/initial_balance_strategy/

Community rule found in discussion:
- Initial Balance = first hour of RTH, 09:30–10:30 ET.
- If IB high breaks but fails to hold/continue, fade back toward NY VWAP; mirror for IB low.

Why include: structurally different "failed auction" idea; first-hour range is used as trap/failure level rather than breakout trigger.
NEEDS FREEZE before coding:
- "Failure" = proposed single 5m close back inside IB after trading beyond it.
- Entry = next 5m open.
- Stop = sweep extreme + 1 tick.
- Target = NY session VWAP.
These proposed rules are our mechanical translation, not claimed verbatim by source; freeze once, no optimization in first pass.

## B-tier: promising but one or more source rules remain discretionary

### B1 — FVG + ORB breakout/retest/engulfing
Source: https://www.reddit.com/r/algorithmictrading/comments/1s4qbax/i_coded_a_fvg_opening_range_breakout_strategy_on/

Source description:
- MES, 1-minute, 09:30 opening-range context.
- Wait for fair-value-gap breakout.
- Retest.
- Engulfing candle confirmation.
- Entry after confirmation.
- Approx stop = 9.25 points.
- Approx target = 18 points.
Community claim: 2025–26 PF ~1.70 and 3-year PF ~1.53, but older 2020–22 2-minute test reportedly fell to PF ~1.039.

Why parked for now: FVG definition and exact OR construction are not fully specified in the post. We should not invent them until we decide on one canonical definition.

### B2 — ES 25/75 EMA pullback-resumption
Source: https://www.reddit.com/r/FuturesTrading/comments/1ey7w5s/my_ema_strategy/

Source rules:
Short:
- Fast EMA below slow EMA; source says 25/75 works better on ES.
- Price pulls back above both EMAs and closes above.
- Price then closes back below fast EMA while fast remains below slow.
- Look for CCI/price divergence.
- Long mirror.
- Backtest entry can be signal-candle close; discretionary live entry often waits for EMA retest.

Why parked: CCI divergence is not numerically defined; stops/targets are ticker-specific in source. Could test a stripped mechanical base only if explicitly frozen before seeing results.

### B3 — ADX + VWAP + EMA20 trend pullback
Source: https://www.reddit.com/r/Daytrading/comments/1rv0vci/hows_my_strategy/

Source rules:
- 15m ADX 25–35 and rising; 5m ADX also rising.
- Bullish trend: whole 5m trend above VWAP; bearish mirror.
- Wait for pullback to 20EMA, with a wick/reaction.
- Wait for candle close and next-candle directional confirmation.
- Target about 2R.

Why parked: "whole trend", reaction, and next-candle direction need precise definitions; community feedback on ADX edge is mixed.

### B4 — VWAP reclaim reversal
Source: https://www.reddit.com/r/Daytrading/comments/1t6ensi/vwap_reclaim_trade_setup_example_from_today/

Source concept:
- Market trends strongly one way from open.
- Then reverses heavily toward opposite HOD/LOD.
- Pulls back to session/multi-session VWAP area.
- Enter on a strong engulfing candle in reversal direction.
- Stop beyond pullback low/high.
- Target HOD/LOD or premarket high/low if >= ~1.5R.

Why parked: "strong trend" and "reverses heavily" are discretionary and must be quantified before testing.

## C-tier / research context, not yet tournament entries

### C1 — Plain Initial Balance breakout
Sources/community discussion show first-hour IB breakout is popular, but at least one recent participant reported extensive negative-expectancy simulation without regime selection. A public 2015–2025 ES/NQ summary also reports that IB sides break very frequently, while full-range extensions are much less common. This suggests "break occurred" alone is not enough of an entry rule.

### C2 — Overnight-high/low breakout
Community frequently uses overnight high/low as context, but source discussion explicitly warns that breaking ONH/ONL may identify a trending day without providing a good entry. Keep as a future context/regime feature, not a standalone strategy in Round 1.

### C3 — Prior-day high/low touch/sweep
Recent large-sample crypto analysis found higher subsequent volatility near prior-day extremes but no reliable direction. That is not ES evidence, but it is a warning against assuming simple bounce/rejection edge. Use PDH/PDL as a location feature only until a fully mechanical trigger is sourced.

### C4 — Gap-fill / Gap-and-Go
Community considers ES cash-close-to-open gaps useful, but rules for deciding fill vs continuation are inconsistent and often discretionary. Keep for a later focused research pass after exact gap-size/regime rules are sourced.

## Recommended Round-1 tournament set

Start with the six most diverse/testable hypotheses:
1. A1 — 15m ORB close-confirmation, 1.5R.
2. A2 — 15m ORB + 5m close + retest, 2R.
3. A4 — first-40m 9EMA continuation pattern (ES transfer test).
4. A5 — after-10:30 VWAP SD reversion.
5. A6 — first-hour IB failed-break fade to VWAP.
6. B2 mechanical base — ES 25/75 EMA pullback/resumption, but only after its missing stop/target/divergence choices are frozen without optimization.

FVG-ORB (B1) should be tested in Round 2 after we obtain or freeze an exact FVG definition.

## Anti-overfit rule

For each Round-1 strategy, one base specification only. No threshold sweeps in the initial tournament. If a strategy fails badly, retire it. If it is near breakeven but shows a coherent mechanism, one pre-justified robustness variation may be allowed later. 2024 cannot be used to tune any rules.