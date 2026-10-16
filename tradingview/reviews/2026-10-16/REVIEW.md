# MES forward review — October 16, 2026

Both MES1! 15-minute alerts observed Active in TradingView account iaqhan_sidegig. Saved expiration remains November 12. Forward start remains 2026-10-13T04:10:53.537Z; no reset or rule/script/alert changes.

Four post-start fill events were visible: A/B entry on October 15 at 13:45 ET, both at 7787.50; A/B RTH exit at 16:00 ET, both at 7790.75. Corresponding strategy exports agree. No other post-start trades were present in either export. SIGNAL calls are suppressed by the user-requested fills-only trigger; signal count comes from distinct entry metadata (one per candidate), with signal candle starting 13:30 ET.

| Candidate | Signals | Closed | Win rate | Dollar PF | Expectancy R | Net USD | Closed-equity max DD USD | Near-threshold |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| A | 1 | 1 | 100% | Undefined; no losses | 0.04758 | 14.75 | 0 | N/A |
| B | 1 | 1 | 100% | Undefined; no losses | 0.04758 | 14.75 | 0 | 0 |

Each trade: gross $16.25, commission $1.50, initial risk $310 (62 points), planned stop 7725.50, unrounded target 7805.9811371. B signal ADX 23.95419510, margin 3.95419510, +DI 25.23836440, -DI 17.58265729, spread 7.65570711. No near-threshold exclusion applied. One trade per candidate is insufficient for performance conclusions. Closed-equity drawdown excludes intratrade adverse excursion.

Export favorable/adverse excursions were $70.50 / -$115.75 per trade. Raw export values are preserved in added columns. MFE/MAE in points and R are blank pending verification of the export's fee convention; no conversion was invented. Actual market slippage is unavailable: emulator data is not a paper-account or real-account fill.

Logging defect: the emitted symbol string embeds an unescaped extended ticker (settlement-as-close), so raw messages are not valid JSON. Raw evidence is preserved byte-for-byte in alert_log_snapshot.txt. events_normalized.json repairs only that exact symbol-string serialization to CME_MINI:MES1!; all numeric fields remain as observed. Raw-message SHA256 hashes provide event deduplication. No live Pine/alert snapshot was changed during this review. This metadata defect warrants a logging-only correction separately; it does not alter the observed fills.

Separate A/B emulator CSVs updated. Actual Paper Trading account CSV untouched; no orders submitted.
