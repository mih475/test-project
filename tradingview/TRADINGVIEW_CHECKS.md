# TradingView checks — 2026-10-12 ET

Status: shortened-session failure resolved; full candle parity still blocks forward-test activation. No alerts or orders submitted.

## Installed and saved

Layout: MES ORB A-B Review, CME_MINI:MES1!, standard 15-minute candles, New York timezone, ETH display, contract adjustment off. Private saved Pine A version 4 and B version 3 compile and run without runtime errors. Superseded chart instances were removed. Layout saved and re-opened successfully.

Fixes: RTH daily reset on ETH and RTH-only charts; permit 15:30 signal/15:45 entry; isolate order-fill callbacks from indicator/closed-candle processing; persist state across realtime rollback; freeze signal ATR; alert placeholders in strategy annotation; disable unsupported Bar Magnifier. These implement the written frozen specification, not a performance optimization. Realtime fill-callback behavior still needs observation.

B properties visibly confirmed: one contract, pyramiding zero, $0.75 per contract per side, zero slippage, default four-tick historical detail, execution on bar close and order fill, order execution delay one tick. TradingView displays a possible look-ahead warning for order-fill recalculation. Code guards avoid consuming candle OHLC in fill callbacks, but the warning is not dismissed as proof of correctness.

## Exported trade checks

Trade-list CSV export succeeded. A has 70 closed trades; B has 58, through October 9. Both pass: long-only, size one, maximum one entry/day, quarter-hour entries 10:00–15:45 ET, $1.50 round-trip commission. All explicit RTH-close exits are assigned to the 15:45 bar (its closing tick is 16:00; export timestamps label the bar).

FAILED: same-day exit. A trade 32 and B trade 26 entered July 3 at 11:00 and exited July 5 at 18:00. The fixed 15:45-bar closing condition does not handle a shortened session without that bar. A calendar-aware early close or exclusion of shortened sessions requires explicit user choice before altering the frozen session definition. No holiday exception has been added.

Reproduce with: python tradingview/checks/check_trades.py. CSVs and machine-readable results are in checks/. These are emulator history, never paper-account fills or forward-test results.

## Full parity blocked

Download chart data presented an upgrade gate: current Essential, recommended Premium. No upgrade was purchased and no gated export was bypassed. Without matching OHLC and plotted indicator rows, candle-by-candle EMA/ATR/ADX/DI/signals and next-open entry parity remain unverified. Trade export alone cannot establish them. Need a legitimately obtained matching chart CSV including both strategies' parity plots and appropriate warmup history. Intrabar exits additionally require same-source one-minute data and classification of emulator path, gaps, tick rounding and stop/target collisions.

The original research uses ES prices and MES costs, and its post-filtered long variants differ from the literal frozen long-only scan. See PARITY_REVIEW.md. Do not equate archived performance with these literal frozen candidates.

## Paper connection rechecked — October 12, 23:28 ET

Paper Trading reconnected successfully. Balance/equity $100,000, realized/unrealized P&L $0; Positions showed no open positions and Orders/All showed no trading data. No order was submitted. Both strategies remain visible on the saved MES 15-minute layout.

## Shortened-session exclusion approved and verified

User approved skipping shortened sessions on October 12. Both saved Pine strategies now include the same predeclared 2026 calendar entry gate. Indicators still consume available RTH bars. No future-bar inspection is used. See HOLIDAY_CALENDAR.md for dates, coverage and review requirements.

Updated TradingView exports contain 67 A trades and 56 B trades. All structural checks pass, including same-day exits, long-only, one contract, maximum one entry per day and entry times. There are no overnight exceptions in this exported sample. A removed May 25, June 19 and July 3; B removed May 25 and July 3. Every remaining trade's entry/exit timestamps, prices, size, net P&L, commission and duration matches the corresponding pre-exclusion export exactly. Original failed checks are preserved; new evidence is in checks/after_calendar/.

Both updated chart scripts compile without runtime errors and the layout was saved. The complete candle/indicator comparison remains blocked by chart-data export access. These checks do not establish full parity or future profitability. Alerts remain off; no paper or live orders were submitted.

## Focused 10-session verification completed

See checks/VERIFICATION.md and selected_verification.json. Selected OR, recurrence, next-open entries, brackets and close checks passed. June 1 B differed from the Python ES export because MES ADX crossed 20 one candle earlier; same-feed full parity remains unverified. Forward alerts remain inactive.
