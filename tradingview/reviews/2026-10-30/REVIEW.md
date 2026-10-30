# MES forward review — October 30, 2026

Account iaqhan_sidegig; MES1! 15-minute chart. Both diagnostic alerts directly observed Active at approximately 21:40 UTC. Forward start remains 2026-10-13T04:10:53.537Z; clock not restarted.

| Candidate | Signals / completed | Win rate | Dollar PF after commissions | Expectancy R | Net USD | Closed-equity max drawdown USD | Near-threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 8 / 8 | 62.5% | 1.4286 | 0.0676 | 130.50 | 224.25 | 0 |
| B | 6 / 6 | 33.33% | 0.5381 | -0.2891 | -109.00 | 123.75 | 0 |

Added 4 A and 3 B completed trades, 14 new fill events and 7 inferred signal events after the October 23 review. Existing signal keys were deduplicated by candidate and signal timestamp; existing rows preserved. Full visible alert log contains 28 post-start fills. Matching post-start exports contain 8 A and 6 B entries, all accounted for. No October 30 trade appears in either export or alert log.

October 26–30 net: A -9.75 USD, B -0.75 USD.
New trades:
- Oct 26: A and B target exit, +112.25 USD each.
- Oct 27: A target exit +102.25 USD; B later entry and RTH-close exit -29.00 USD.
- Oct 28: A and B live stop exit -84.00 USD each.
- Oct 29: A stop exit -140.25 USD; B no trade.

## Reconciliation discrepancy
On October 28, both live alerts show entry 7778.75 and STOP_EXIT 7762.25 at 18:00:01 UTC. OR-low stop was 7763.50. Recalculated chart exports show exit 7763.50 and net -77.75 USD. Live alert fill implies gross -82.50 and net -84.00 USD after the matching 1.50 USD commission, a -6.25 USD difference per candidate. Cause is not established. No manual price substitution or rule change was made.

The prospective record retains live strategy-alert fills. Export prices and P&L are preserved in appended reconciliation columns and raw export evidence. Reconciliation status is exit_fill_mismatch_live_retained. MFE/MAE and export excursion columns on these two mismatched rows remain blank; the recalculated excursions cannot be assumed to describe the live path. No actual Paper Trading account fill is involved.

Other new rows match export entry/exit prices and net P&L. Export favorable/adverse excursion USD values are preserved only for matching rows. Points/R conversions remain blank because excursion fee convention is not established. Actual execution slippage remains unavailable. Planned stop vs emulator fill is visible in the record; it is not evidence of actual account slippage.

## B signal metadata
- Oct 26: ADX 23.36334041; margin 3.36334041; +DI 27.24531482; -DI 15.43781605; spread 11.80749877.
- Oct 27: ADX 20.84380504; margin 0.84380504; +DI 36.93068565; -DI 14.99995506; spread 21.93073059.
- Oct 28: ADX 20.31842122; margin 0.31842122; +DI 29.34077126; -DI 15.55871748; spread 13.78205378.
No new or cumulative B signal lies within abs(ADX-20)<=0.10. No signal was excluded by tagging.

## Definitions and limitations
Signal events are explicitly inferred from ENTRY_FILL metadata; standalone alert() SIGNAL calls remain suppressed under Order fills only. New event evidence preserves original raw messages and semantic event IDs. Exact malformed extended-symbol field normalized for parsing only; live Pine/message defect remains unchanged.

R = net P&L divided by initial entry-to-OR-low risk in USD, using MES 5 USD per point and one contract. Profit factor uses sums of positive/negative net trade dollars after commissions. Drawdown is post-start closed-trade equity from zero and excludes intratrade excursion. New exit timestamps are live alert trigger timestamps, not independently verified execution times. RTH live fill confirms 16:00 ET; export labels the 15:45 closing candle.

Chart history now starts May 31, so export trade numbers changed. Match by candidate, entry date/time and price; trade numbers alone are not stable IDs. Previously saved prospective records are preserved. No historical re-verification was performed.

Alerts remain Active. Saved expiry: A November 12, 2026 at 21:08; B November 12, 2026 at 22:10 (UI timezone unlabeled). Thirteen calendar days remain; renew before November 12. This review did not renew/recreate alerts or change their snapshots. Actual Paper Trading records untouched. No account orders, upgrades, strategy changes, optimization or new filters.
