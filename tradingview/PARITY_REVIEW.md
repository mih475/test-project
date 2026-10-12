# Frozen ORB A/B parity review

## Status

The Pine implementations are written from the user-approved frozen rules. They are not yet verified candle-for-candle against the historical research output. Do not start counting forward-test sessions until this review is resolved and the same-data comparison passes.

TradingView setup progress (2026-10-12): Candidate A and Candidate B were copied into separate private Pine strategies, added to the `CME_MINI:MES1!` 15-minute chart, and their editor text was checked against the frozen source. An implementation-only ATR minimum-tick filter was removed from both Pine versions because it is absent from the frozen specification. The chart timezone is New York. No alert has been created and no paper or live order was placed.

TradingView currently reports that higher-detail Bar Magnifier data requires Premium. Paper Trading was connected on 2026-10-12; its Orders tab showed no trading data and its Positions tab showed no open positions. No order was submitted. The parity gate remains open.

## Confirmed mismatch in current Python variant path

The current repository's orb_walkforward_regime.py builds one baseline trade per session with orb_refinement_stage2.signal_for(). That signal function scans for the first breakout in either direction, long or short. The LONG_ONLY and LONG_ADX20_DMI variants then filter the resulting completed baseline trade.

The frozen A/B definitions instead scan for a long breakout and apply the filters to that long signal. If a qualifying short breakout happens before a qualifying long breakout, the post-filtered Python variant can omit the session while the frozen long-only strategy can still take its later long signal. The current research variants can therefore differ from the frozen A/B signal rules.

The Python trade builder also drops a trade if entry-to-stop risk is under one tick. That guard is not listed in the user's frozen rules. It needs to be surfaced in any same-data comparison rather than silently added to the Pine rule set.

## Exit-resolution limitation

The research simulator checks RTH one-minute bars, gives the stop priority when a one-minute candle touches both target and stop, and uses the final RTH one-minute close for an EOD exit. The Pine strategies use TradingView's strategy emulator on a 15-minute chart with Bar Magnifier enabled. Fills may differ because of symbol data, contract roll adjustment, intrabar coverage, stop gaps, or a same-minute stop/target collision.

## Required parity gate

1. Generate Python signal rows for A and B using the frozen long-only conditions, without changing the user's candidate rules.
2. Use the same MES contract data and RTH 15-minute OHLC series on both sides.
3. Compare every 15-minute signal candle, EMA50, ATR7, and (for B) ADX14/+DI14/−DI14 value. Compare entry dates and next-bar opens.
4. Reconcile every exit using the original one-minute Python sequence and TradingView Bar Magnifier's available one-minute sequence. Record data-source and tie-break differences.
5. Start the live paper log only after signal and indicator rows match and all remaining fill differences are classified.

## Reproduction and frozen-rule audit (2026-10-12)

Recovered GitHub Actions run 38119196219 and artifact 11694733532. The artifact ZIP SHA256 is 5efc7c1f22bf34542d53b4622343c929813042d444dbbeb7571a01cebac8f5bd. Downloaded the original ES one-minute source files for 2016–2026; cleaned coverage ends on 2026-06-11 at 15:59 ET. All 2,404 archived baseline trades reproduced, including direction, signal/entry/exit timestamps, entry/stop/target, ATR, ADX, risk, raw P&L, and exit reason (numeric tolerance 1e-10).

| Candidate | Archived filtered trades | First qualifying long, research cutoff | First qualifying long, entry before 16:00 |
| --- | ---: | ---: | ---: |
| A | 1,393 | 1,630 | 1,657 |
| B | 763 | 1,198 | 1,221 |

The literal frozen-rule interpretation adds 264 sessions for A and 458 for B. Shared sessions retain the same signal timestamps. Lists are in parity/candidate_A_changed_sessions.csv and parity/candidate_B_changed_sessions.csv; summary and source SHA256 hashes are alongside them. No nonpositive entry-to-stop risks or ATR values below one tick occurred in the frozen candidate rows.

The research cutoff excludes the 15:30–15:45 signal candle. That candle's next open is 15:45, still inside RTH, so the cutoff is an additional restriction absent from the user's specification. The current Pine files still use that research cutoff; correction and TradingView validation remain pending.

The daily-reset correction is committed for both Pine files: entering RTH now resets state even when the previous chart bar is an ETH bar on the same date. A Python control-flow check over three sessions passed on both ETH and RTH-only timelines. This correction has not yet been installed or compiled in TradingView.

These are Python reproduction and signal-rule checks on ES data, not Pine-versus-Python candle parity on MES. The audit inherits the research data-cleaning, indicator, missing-bar, and stop-first intrabar conventions. No alerts were activated and no forward-test sessions are counted.

To reproduce: put the source ES_1min_YEAR.csv files in data/ at the repository root and extract the original workflow artifact into results/. Install pandas, numpy, and requests, then run python orb_frozen_parity_audit.py. The script refuses to continue if archived reproduction fails; it writes the frozen rows and changed-session reports at the repository root.
