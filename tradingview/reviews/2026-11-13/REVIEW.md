# MES forward review — November 13, 2026

Both MES ORB Diagnostic Forward alerts were directly observed in account iaqhan_sidegig as **Stopped — Expired**. They expired November 12. The prospective alert record currently ends with November 12 fills; November 13 and later are a recording gap until alerts are renewed. Original forward start 2026-10-13T04:10:53.537Z retained.

| Candidate | Signals / completed | Win rate | Dollar PF after commissions | Expectancy R | Net USD | Closed-equity max drawdown USD | Near-threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 14 / 14 | 64.29% | 1.8976 | 0.2214 | 512.75 | 224.25 | 0 |
| B | 11 / 11 | 45.45% | 1.1695 | 0.0679 | 93.50 | 242.75 | 0 |

Added four A and three B completed trades from November 9–12: 14 fill events and seven inferred SIGNAL events. Week net A +304.00 USD and B +124.25 USD. Full visible alert log contains 50 post-start fills, accounting for 25 entries and exits. Matching chart exports contain 14 A and 11 B post-start trades. Existing rows and original forward clock preserved. No post-expiration chart result was substituted for a missing realtime alert.

## New trades
- November 9: both entry 7523.25 at 10:00 ET, target 7567.50; +219.75 USD net each.
- November 10: A entry 7551.25 at 10:00 ET, live STOP_EXIT 7512.75; -194.00 USD net. B no recorded trade.
- November 11: both entry 7632.25 at 11:00 ET, target 7662.00; +147.25 USD net each.
- November 12: A entry 7629.75 at 10:45 ET, target 7656.25; +131.00 USD net. B qualified later, entry 7664.75 at 11:15 ET, RTH_CLOSE 7616.50; -242.75 USD net.

All net results include 1.50 USD round-trip commission from matching exports. Entry/exit values come from live TradingView strategy-emulator alerts. Actual Paper Trading account fills remain separate and untouched.

## New discrepancy
A's November 10 live stop alert filled 7512.75; recalculated chart export shows 7514.25. Live net is -194.00 USD versus export -186.50 USD, a -7.50 USD difference. The forward row retains the live fill and records export price/P&L and difference in reconciliation columns. Cause is not established. MFE/MAE and raw excursion columns for this mismatched row are left blank; raw chart export retained separately.

The previous October 28 A/B discrepancy remains preserved: live stop 7762.25 vs recalculated 7763.50, -6.25 USD difference per candidate. Other new entry/exit prices and net P&L match exports.

## B signal values
- Nov 9: ADX 27.78877042, margin 7.78877042, +DI 34.56505246, -DI 17.57301340, spread 16.99203905.
- Nov 11: ADX 31.21446733, margin 11.21446733, +DI 39.62587560, -DI 11.24449425, spread 28.38138135.
- Nov 12: ADX 31.64671719, margin 11.64671719, +DI 32.61488877, -DI 25.66882701, spread 6.94606176.
No new/cumulative B signal is within abs(ADX-20)<=0.10. Tagging never excludes signals.

## Definitions and access
Signals inferred from ENTRY_FILL metadata because Order fills only suppresses standalone SIGNAL alert() calls. New event evidence preserves raw original messages and semantic IDs. Known malformed extended-symbol JSON is normalized only for parsing. No source or alert snapshot changes made.

ET uses UTC-5 in November after DST. Exit timestamps are alert trigger times, not independently verified execution timestamps. RTH export labels the 15:45 closing bar while the live alert confirms 16:00. R = net P&L divided by entry-to-OR-low initial risk at MES 5 USD per point. Dollar profit factor uses positive/negative net dollars after commissions. Drawdown is closed-trade forward equity from zero, excluding intratrade excursion. Actual slippage and MFE/MAE point/R conversions remain blank. Matching raw export excursion USD values retained only where fill parity holds.

Saved expiry displays: A November 12 at 21:08; B November 12 at 22:10, UI timezone unlabeled. Manager rows now explicitly show Stopped — Expired; timestamps beside those statuses are last-trigger displays, not independently established expiration times.

Further live event collection is blocked by expired alerts. Weekly review paused pending alert renewal, to avoid repeatedly reviewing an inactive stream. No alerts renewed/recreated, rules changed, parameters optimized, new filters added, upgrades purchased or account orders placed. No historical retesting or web research.
