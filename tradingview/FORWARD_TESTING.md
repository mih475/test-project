# MES ORB TradingView forward test

## Current setup status (2026-10-12)

- Candidate A and Candidate B were saved as separate private TradingView Pine strategies and added to the `CME_MINI:MES1!` 15-minute chart, set to the New York timezone.
- The TradingView editor code was checked against the local Pine files. The unapproved ATR minimum-tick filter was removed from both implementations.
- Paper Trading is connected. The account showed no open positions or trading data in Orders. No order was submitted.
- Alerts remain uncreated until the candle-for-candle parity gate passes. No paper or live orders have been placed. Do not count forward-test sessions yet.
- TradingView's current plan reports that higher-detail Bar Magnifier data requires Premium, so emulator exit-fill parity remains an open limitation.

## Frozen candidates

- **A:** 15-minute MES, RTH 09:30–16:00 America/New_York, 09:30–09:45 opening range; long only; a completed 15-minute close strictly above the OR high and EMA50; ATR(7); enter at the next 15-minute open; target entry + 1.5 × signal-bar ATR(7); stop at OR low; one entry per session; exit at stop, target, or the 15:45–16:00 RTH candle close.
- **B:** Same as A, with ADX(14) ≥ 20 and +DI(14) > −DI(14) on the signal candle.

Both scripts reject any chart timeframe other than 15 minutes. They calculate EMA, ATR, and (for B) DMI/ADX from RTH bars only, matching the Python pipeline's RTH-only 15-minute resample. The signal is evaluated only after its bar closes; process_orders_on_close=false models a market entry at the next 15-minute open. The ATR value is captured on the signal candle; the target uses the actual simulated fill.

## Paper-only setup

1. Open a continuous MES chart (MES1! or the available CME MES continuous symbol), switch to 15 minutes, and use standard candles.
2. Add the matching candidate_a.pine or candidate_b.pine strategy. Keep order size at one MES contract. The script creates TradingView strategy-emulator orders only; it has no broker-routing code.
3. Connect Trading Panel → Paper Trading for manual simulated orders. Do not connect a funded broker for this test.
4. Create an alert for the strategy and select Order fills only. The order messages are prefixed A_ or B_. Keep webhook delivery disabled. Use an alert title containing candidate and symbol.
5. Compare the strategy-emulator fill with the manual Paper Trading fill, and record the difference in the log. TradingView alerts notify; they do not automatically execute a strategy in Paper Trading.
6. Keep A and B as separate chart layouts/alerts. Do not run both as broker-connected automated orders.

The scripts use $0.75 per contract per side ($1.50 round trip) and zero modeled slippage. This keeps slippage visible for the forward log and avoids applying a round-trip research assumption as if it were per-order slippage. Record actual entry/exit slippage in ticks. use_bar_magnifier=false uses the available default emulator. Historical intrabar exits are not verified against the research one-minute sequence.

## Research parity boundary

The Python source uses RTH-only 15-minute signals and indicators, takes entries at the next 15-minute open, then resolves stop/target/EOD exits against RTH one-minute bars. If a one-minute bar touches stop and target, Python resolves stop first. TradingView's 15-minute strategy emulator can use Bar Magnifier, but it can still differ when the TradingView data vendor or an individual one-minute bar's OHLC path differs from the Python source. A successful Pine compile is not proof of candle-for-candle parity. Before counting forward-test sessions, compare exported chart data and strategy trades with the Python reference on the same dates and data; record any mismatch and its cause. Do not alter either strategy to force a match.

The Python pipeline's trade-signal cutoff is before the 15:30 ET bar. This also excludes a 15:30–15:45 signal whose next open is 15:45, still inside RTH. That extra restriction is absent from the frozen specification. Pine now allows that signal, with runtime installation completed; same-candle parity is pending. The final 15-minute RTH bar starts at 15:45 and ends at 16:00.

## Log fields and summary

forward_test_log.csv has one row per observed signal/trade and includes planned/actual entries and exits, fill type, slippage, commissions, R, MFE/MAE, ambiguity, chart symbol/data source, and notes. Use positive MFE and negative MAE in points from entry. Calculate r_multiple from net P&L divided by planned initial risk in dollars, and leave it blank for signals that did not fill.

Run: python forward_test_metrics.py forward_test_log.csv

The summary reports completed trades, win rate, profit factor, expectancy in R, net P&L, and maximum peak-to-trough drawdown in R. Keep the CSV as the record of actual fills; the script does not estimate missing data.

## Current verification milestone

The archived 2,404 baseline trades reproduced from the original ES one-minute data. See PARITY_REVIEW.md and parity/ for the additional sessions generated by the frozen long-only signal interpretation. The Pine daily-reset, late-session cutoff, fill-callback isolation, and alert-message corrections are installed and compile in TradingView (A version 4, B version 3). The current chart scripts are not yet forward-test ready. See TRADINGVIEW_CHECKS.md for the remaining holiday and same-data parity blockers.

## Approved session exclusion update

The user approved skipping shortened sessions. Both strategies now block entries on the 2026 dates in HOLIDAY_CALENDAR.md while preserving indicator history. TradingView re-export verified 67 A trades and 56 B trades with no overnight exceptions, and unchanged remaining trade records. See TRADINGVIEW_CHECKS.md and checks/after_calendar/. Prior failure reports are retained as historical evidence. Full candle parity and alert activation remain pending.
