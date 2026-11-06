# MES forward review — November 6, 2026

Signed-in account iaqhan_sidegig, saved MES1! 15-minute chart. Both A/B Diagnostic Forward alerts visibly Active at approximately 2026-11-06T22:45:21Z. Original forward clock 2026-10-13T04:10:53.537Z retained.

| Candidate | Signals / completed | Win rate | Dollar PF after commissions | Expectancy R | Net USD | Closed-equity max drawdown USD | Near-threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 10 / 10 | 60% | 1.5533 | 0.2009 | 208.75 | 224.25 | 0 |
| B | 8 / 8 | 37.5% | 0.9004 | -0.0333 | -30.75 | 123.75 | 0 |

Added two trades per candidate, eight fill events and four inferred SIGNAL events since October 30. All new fills match the post-start strategy exports, including prices and commission. Both strategies earned 78.25 USD this week. No new trades appear November 3, 5 or 6 in either export or alert log.

## New trades
- November 2: signal candle 09:45 ET, entry 10:00 ET at 7659.00; TARGET_EXIT alert 10:24:32 ET at 7689.50; gross 152.50 USD, commission 1.50 USD, net +151.00 USD each. Stop 7641.50; captured target 7689.30256041.
- November 4: signal candle 10:00 ET, entry 10:15 ET at 7736.00; RTH_CLOSE 16:00 ET at 7721.75; gross -71.25 USD, commission 1.50 USD, net -72.75 USD each. Stop 7679.50; captured target 7774.92845680.

ET timestamps use UTC-5 after the November 1 DST transition; prior October rows retain UTC-4. Export RTH exit labels 15:45, the candle closing at 16:00; live alert confirms the RTH close. Intrabar exit time is the alert trigger time, not an independently verified execution timestamp.

## B metadata
- November 2: ADX14 45.19675810, margin 25.19675810, +DI14 31.71145833, -DI14 22.47469635, spread 9.23676199.
- November 4: ADX14 31.03649834, margin 11.03649834, +DI14 47.73333406, -DI14 10.29953681, spread 37.43379725.
No new or cumulative B signal lies within abs(ADX-20)<=0.10. Tags do not affect eligibility.

## Reconciliation and limitations
Candidate+signal timestamp keys deduplicate entries; semantic IDs deduplicate fill events. Full visible alert log has 36 post-start fills, corresponding to 18 total entries and exits. Post-start exports contain 10 A and 8 B trades. Existing saved rows preserved.

October 28 discrepancy remains unchanged: live stop 7762.25 vs recalculated export 7763.50. The saved forward totals retain live fills (-84.00 USD each), 6.25 USD worse per strategy than the export. No new fill mismatch was found. Recalculated export excursions for those earlier mismatched rows remain excluded from the forward excursion fields.

New matching export favorable/adverse excursion USD values preserved separately. Point/R MFE/MAE conversions remain blank because their fee convention is not established. Actual account slippage remains blank. R = net trade P&L / initial entry-to-OR-low risk in MES dollars. Dollar PF uses positive and negative net trade USD after commissions. Drawdown is post-start closed-trade equity from zero, excluding intratrade excursion.

Standalone SIGNAL alert() calls are suppressed by Order fills only; derived SIGNAL events are labeled as inferred from ENTRY_FILL metadata. Raw alert messages retain the known malformed extended-symbol JSON. Only that exact symbol field is normalized during parsing. No Pine or alert snapshot change was made.

## Alert expiration
Both alerts remain Active but expire November 12, six calendar days away, before the next weekly review. Saved UI expirations: A November 12 at 21:08, B November 12 at 22:10; UI timezone unlabeled. Renewal is needed before November 12 to prevent a forward-record gap. This review did not renew/recreate alerts or restart the forward clock.

No rule changes, optimization, new filters, upgrades, real-money orders or actual Paper Trading account orders. Paper account records remain separate and untouched. No historical retesting or web research.
