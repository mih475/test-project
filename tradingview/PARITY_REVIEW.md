# Frozen ORB A/B parity review

## Status

The Pine implementations are written from the user-approved frozen rules. They are not yet verified candle-for-candle against the historical research output. Do not start counting forward-test sessions until this review is resolved and the same-data comparison passes.

TradingView setup progress (2026-10-12): Candidate A and Candidate B were copied into separate private Pine strategies, added to the `CME_MINI:MES1!` 15-minute chart, and their editor text was checked against the frozen source. An implementation-only ATR minimum-tick filter was removed from both Pine versions because it is absent from the frozen specification. The chart timezone is New York. No alert has been created and no paper or live order was placed.

TradingView currently reports that higher-detail Bar Magnifier data requires Premium. Its Trading panel also reports that this account session was disconnected after access from another browser/device; reconnecting may take over the single active market-data session. Paper Trading is not connected. These setup limits do not change the parity gate below.

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
