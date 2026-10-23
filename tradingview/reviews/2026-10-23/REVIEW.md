# MES forward review — October 23, 2026

Reviewed the signed-in iaqhan_sidegig MES1! 15-minute chart after RTH close. Both diagnostic alerts visibly Active. Forward start remains 2026-10-13T04:10:53.537Z.

| Candidate | Signals inferred from entries | Completed | Win rate | Dollar PF after commissions | Expectancy R | Net USD | Closed-equity max drawdown USD | Near-threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 4 | 75% | 2.7477 | 0.1725 | 140.25 | 80.25 | 0 |
| B | 3 | 3 | 33.33% | 0.1199 | -0.3905 | -108.25 | 123.00 | 0 |

Added 3 A and 2 B trades since the October 16 saved review. All 14 visible fill events reconciled to matching post-start exports: 7 entries, 2 target exits, 2 stop exits and 3 RTH-close exits. No trades appear on October 22–23 in either export. Signals are reconstructed from entry metadata; no standalone SIGNAL alerts are emitted under Order fills only. Derived signals are explicitly labeled in events_normalized.json.

October 20: A +116 USD; B no trade. October 21: A entered 11:15 ET and targeted out +89.75 USD; B entered 13:30 ET and exited at RTH close -42.75 USD. Latest B signal ADX 20.43970665, margin 0.43970665, +DI 33.25297149, -DI 14.80898637, spread 18.44398512. None of B's 3 signals meets abs(ADX-20)<=0.10. Tagging never changes eligibility.

Net P&L reconciles to export after 1.50 USD round-trip commission per trade. R = net P&L / (entry minus OR low) / 5 USD per point / contracts. Dollar PF sums positive net trade USD divided by absolute negative net trade USD. Drawdown uses only post-start closed-trade equity, including initial zero; it excludes intratrade excursion.

Export favorable/adverse excursion USD fields are preserved without conversion. Fee conventions for those excursion fields are not established, so MFE/MAE in points/R remain blank. Actual slippage and unavailable values remain blank. For new rows, exit timestamp is the live alert trigger time; exact intrabar execution time is not independently available. RTH export labels the closing 15:45 candle while live alerts confirm 16:00 ET.

Known message defect remains: an unescaped extended symbol string makes raw messages invalid JSON. Only the exact symbol field was normalized during reconciliation. Raw messages are preserved alongside normalized events. No Pine or alert snapshot changes were made.

Alerts remain Active. Saved expiration dates: A November 12, 2026 at 21:08; B November 12, 2026 at 22:10 (UI timezone unlabeled). Renew before November 12; 20 calendar days remain. Clock not restarted. Actual Paper Trading account records were not modified. No account orders, upgrades, rule changes or historical retesting.

Small prospective sample. A currently leads B by 248.50 USD; no conclusion of reliable profitability follows from 4/3 trades.
