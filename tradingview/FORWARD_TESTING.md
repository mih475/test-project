# MES ORB TradingView forward test

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

The scripts use $0.75 per contract per side ($1.50 round trip) and zero modeled slippage. This keeps slippage visible for the forward log and avoids applying a round-trip research assumption as if it were per-order slippage. Record actual entry/exit slippage in ticks. use_bar_magnifier=true requests lower-timeframe backtest fills where TradingView has that data.

## Research parity boundary

The Python source uses RTH-only 15-minute signals and indicators, takes entries at the next 15-minute open, then resolves stop/target/EOD exits against RTH one-minute bars. If a one-minute bar touches stop and target, Python resolves stop first. TradingView's 15-minute strategy emulator can use Bar Magnifier, but it can still differ when the TradingView data vendor or an individual one-minute bar's OHLC path differs from the Python source. A successful Pine compile is not proof of candle-for-candle parity. Before counting forward-test sessions, compare exported chart data and strategy trades with the Python reference on the same dates and data; record any mismatch and its cause. Do not alter either strategy to force a match.

The Python pipeline's trade-signal cutoff is before the 15:30 ET bar. This permits a 15:15–15:30 signal to enter at 15:30, while preventing a signal whose next open would be outside RTH. The final 15-minute RTH bar starts at 15:45 and ends at 16:00.

## Log fields and summary

forward_test_log.csv has one row per observed signal/trade and includes planned/actual entries and exits, fill type, slippage, commissions, R, MFE/MAE, ambiguity, chart symbol/data source, and notes. Use positive MFE and negative MAE in points from entry. Calculate r_multiple from net P&L divided by planned initial risk in dollars, and leave it blank for signals that did not fill.

Run: python forward_test_metrics.py forward_test_log.csv

The summary reports completed trades, win rate, profit factor, expectancy in R, net P&L, and maximum peak-to-trough drawdown in R. Keep the CSV as the record of actual fills; the script does not estimate missing data.
