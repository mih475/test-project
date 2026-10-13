# Shortened-session exclusion

Approved by user October 12, 2026: skip shortened trading sessions entirely.

Implemented as an entry-only calendar gate in both candidates. Indicators still consume available RTH bars; EMA/ATR/ADX state, OR construction, targets, stops and normal 16:00 exits are unchanged. Calendar membership uses the New York calendar date, known before the open; no future bar counts or lookahead. Closed dates are listed defensively too.

2026 exclusions: January 1, January 19, February 16, April 3, May 25, June 19, July 3, September 7, November 26–27, December 24–25. July 2, May 22, December 31, Columbus Day and Veterans Day are not excluded just because another CME product or trading floor has special hours. Equity-index Globex hours, not floor or bond hours, govern MES.

Sources checked October 12, 2026:
- CME Globex holiday schedule and notes: https://www.cmegroup.com/trading-hours.html
- CME 2026 trading-days calendar: https://investor.cmegroup.com/static-files/1047cbcc-7569-40ab-bb6b-6973eea07ea3
- Equity-market RTH holiday/early-close dates cross-check: https://www.nasdaqtrader.com/Trader.aspx?id=Calendar

CME states schedules are subject to change and typically finalized about two weeks before the holiday. Upcoming November/December exclusions must be reviewed against finalized equity-index schedules before alerts are activated across those dates. No claim of a perpetual exchange calendar is made. The script allows entries only in 2026 and raises a visible error if the latest chart bar is outside 2026, requiring a calendar update before further use. Unscheduled closures cannot be predicted by this static calendar.

This exclusion changes the tested session set with explicit user approval. Previous research and pre-exclusion TradingView results are retained as separate evidence, not relabeled as post-exclusion results.
