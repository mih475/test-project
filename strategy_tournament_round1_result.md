# Strategy Tournament Round 1 — Frozen Result

Date: 2026-09-24
Development period only: 2021-2023
Implementation commit frozen for survivor selection: `e01bf085cb91de85e80465928e9e9dd2642781f1`
Workflow run: `35971297086`
Artifact: `10796183526`

## Outcome

Only S1 cleared the pre-frozen Round-1 survival gate.

### S1 — 15m ORB close-confirmation, long-only
- Trades: 473
- Net win rate, ES $5 RT + 1 tick total adverse slippage: 52.2199%
- Raw avg R: 0.1461
- Raw PF: 1.3487
- Net avg R: 0.1219
- Net PF: 1.2828
- Net total R: 57.6767
- Net max drawdown: -9.9565R
- Positive net years: 3/3
- Floor yearly PF: 1.1614
- Drop best 5 trades: avg R 0.1073, PF 1.2463
- ES 4-tick stress avg R: 0.0702
- MES 1-tick avg R: 0.1081, PF 1.2469

Year by year, ES 1 tick:
- 2021: n=166, avgR=0.1159, PF=1.2840, totalR=19.2344
- 2022: n=154, avgR=0.0739, PF=1.1614, totalR=11.3874
- 2023: n=153, avgR=0.1768, PF=1.4121, totalR=27.0548

Implementation audit:
- Unique trading sessions: 423
- Total trades: 473
- Maximum trades in one day: 2
- Days with two trades: 50
- Overlapping trades: 0
- Entries at/after 12:00 ET: 0
- Entry times observed: 10:00 through 11:45 ET in 15-minute increments
- Exit reasons: 187 stop, 127 target, 159 RTH-close exits
- Risk points: minimum 2.0, median 17.75, 95th percentile 42.1, maximum 122.25

S1 is now frozen exactly as implemented in commit `e01bf085cb91de85e80465928e9e9dd2642781f1`. Do not change parameters or execution conventions before 2024 validation.

## Rejected in Round 1
- S2 ORB + 5m close + retest: net avgR -0.1507, PF 0.8007
- S3 first-40m 9EMA continuation: net avgR -0.3384, PF 0.3971
- S4 post-10:30 VWAP 2SD reversion: net avgR -0.0560, PF 0.8506
- S5 initial-balance failed-break fade: net avgR -0.1182, PF 0.8271
- S6 5m ORB + 1m FVG displacement: net avgR -0.1161, PF 0.8438

These rejected strategies must not be modified using the 2021-2023 result and then re-entered as if they were untouched Round-1 hypotheses. Any redesigned version must be treated as a new strategy family with a new pre-test freeze.

## Next permitted step
Validate the frozen S1 implementation on 2024 only. No parameter changes are permitted before that validation result is observed.
