# MES forward review — November 20, 2026

Direct browser review at approximately 22:50 UTC of https://www.tradingview.com/chart/R2bPHMJh/, signed in as iaqhan_sidegig.

Both alerts visually green Active on CME_MINI:MES1!, 15m:
- MES ORB A — Diagnostic Forward — 15m: expiration January 14, 2027 at 21:12.
- MES ORB B — Diagnostic Forward — 15m: expiration January 14, 2027 at 21:11.

Expiration dialog timezone unlabeled. Both conditions are their corresponding Pine strategy, Order fills only; original JSON message and App/Toasts preserved. Edit dialogs inspected then canceled; no alert changes saved.

Latest log events remain November 12: A TARGET_EXIT at 16:06:39Z; B RTH_CLOSE at 21:00:00Z. Both strategy trade lists, with range ending November 20, likewise end November 12. No new SIGNAL metadata, ENTRY_FILL, TARGET_EXIT, STOP_EXIT, or RTH_CLOSE events found. Existing CSVs read and retained unchanged; no duplicate rows added. No new exports were needed for reconciliation because no new trades appeared. Missing MFE/MAE and slippage values remain blank; prior live/export discrepancies remain preserved.

| Cumulative recorded metric | A | B |
|---|---:|---:|
| Signals inferred from entry metadata | 14 | 11 |
| Completed trades | 14 | 11 |
| Win rate | 64.29% | 45.45% |
| Dollar profit factor after commissions | 1.8976 | 1.1695 |
| Expectancy R | 0.2214 | 0.0679 |
| Net P&L USD | 512.75 | 93.50 |
| Closed-equity maximum drawdown USD | 224.25 | 242.75 |
| Near-threshold signals | 0 | 0 |

Metrics remain the reconciled November 13 review totals through November 12. No newly recorded trades this week; absence of events does not prove uninterrupted alert coverage. User reported renewal November 16; exact reactivation timestamp is not exposed by the inspected UI. Preserve original start 2026-10-13T04:10:53.537Z and November 13-to-reactivation recording gap; no historical backfill.

2026-only calendar still requires reviewed 2027 holiday maintenance and refreshed alert snapshots before January. Strategy report displays its look-ahead warning and alert editors display the corresponding warning; this review does not revalidate historical execution assumptions. No frozen rules, source, calendar, or snapshots changed. No real or Paper Trading account orders placed. Actual account fills remain separate.
