# MES diagnostic forward test active

Forward clock: 2026-10-13T04:10:53.537Z. Both TradingView alerts were observed Active.

A private Pine version 6; B private Pine version 5. Separate alerts named MES ORB A/B — Diagnostic Forward — 15m. Conditions: Order fills and alert() function calls, same chart 15 minutes. App and toast notifications enabled; webhook and email disabled. Initial expiration is November 12, 2026, shown in TradingView's alert dialog; review/renew before expiry. Alert snapshots are frozen when created; script changes require explicit review and new alerts.

Source of truth is TradingView MES 15-minute candles and the installed Python-style RTH indicator calculations, as approved. Historical ES exports are reference only. B remains ADX14 >=20 and +DI14 > -DI14. The recorded B values are from the signal candle, including ADX margin, DI spread, and near-threshold/feed-sensitive tag when abs(ADX-20)<=0.10. Tagging never changes eligibility.

TradingView's server alert log is the automatic event record. SIGNAL calls record every qualifying completed candle; entry, target, stop and RTH-close order fills record emulator events with actual simulated fill price. No webhook collector is connected, so GitHub CSVs do not update on each realtime event. Reconcile the alert log and strategy-trade exports into the separate A/B emulator logs during reviews; preserve signal-time metadata and ignore all events before the forward clock. Paper account fills belong exclusively in forward_test_paper_account.csv. Never relabel historical or paper-account fills as prospective emulator fills.

Emulator zero modeled slippage does not imply executable market fills. Target prices can round to ticks. MFE/MAE and R come from matching post-start trade exports and captured initial stop risk; missing values remain blank. Full same-feed historical initialization and one-minute intrabar parity remain limitations accepted for diagnostic observation.

No real or paper-account orders were submitted. Rules and shortened-session exclusions remain frozen. Calendar reviewed for 2026 only; update before 2027. Do not optimize based on interim results.

Weekly reconciliation and performance review is scheduled for Friday afternoons, America/Chicago, starting October 16. The review retrieves available alert events/trade exports and updates the separate GitHub CSVs; access failures are reported. The alert log runs on TradingView servers; CSV synchronization happens during reviews, not continuously.
