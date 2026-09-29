# ES/MES Systematic Research — Rounds 1 through 7 Synthesis

## Executive conclusion
After seven research rounds, there is still no prop-ready ES/MES strategy that has survived the frozen robustness gates and protected validation process.

The strongest recurring lesson is not that markets are completely patternless. Several families show apparent gross or regime-specific edge. The problem is persistence: edges either disappear after realistic friction, collapse across years, depend on one exceptional regime, fail tail robustness, or decay on later holdouts.

Do not continue adding small variants to the same strategy families. Any next round should represent a materially different economic/data hypothesis and should be frozen before opening new protected data.

## Round-by-round summary

### Round 1 — 15-minute ORB
Best candidate: long-only close-confirmed opening-range breakout.
- 2021-2023 development: 473 trades, +0.1219R/trade, PF 1.2828.
- 2024 validation: 184 trades, +0.0596R/trade, PF 1.1212; validation gate passed.
- 2025 final holdout: 166 trades, +0.0363R/trade, PF 1.0805; higher-cost and tail-robustness tests failed.
Conclusion: plausible but decaying/fragile ORB edge; not prop-ready.

### Round 2 — Intraday pattern tournament
No survivor.
Best modern candidate was R2S5 ADX/VWAP/EMA20 trend pullback:
- 2021-2023: 54 trades, +0.3812R/trade, PF 1.6885, but failed minimum-sample gate.
- 2016-2020: 81 trades, -0.1859R/trade, PF 0.7617.
- Combined 2016-2023: 135 trades, +0.0409R/trade, PF 1.0594; failed cost and tail tests.
Conclusion: attractive small-sample modern result did not generalize backward.

### Round 3 — Time-of-day directional hypotheses
No survivor.
Best modern candidate R3S1 rest-of-day -> last-30-minute momentum:
- 2021-2023: 722 trades, -0.0131 ES points/trade, PF 0.9968 after costs.
- At zero cost it was mildly positive (+0.2369 points, PF 1.0601), but realistic friction erased the edge.
A separate EU-open drift showed positive 2016-2020 behavior but collapsed in the modern period.
Conclusion: generic directional time-of-day effects were too weak or unstable.

### Round 4 — Cross-market regime model
Walk-forward OLS using ES/NQ/RTY/ZN and 12 pre-10:00 features.
Primary modern ES +1 tick:
- 648 trades, +0.0238 points/trade, PF 1.0019.
- 2021 positive, 2022 negative, 2023 positive.
- Failed PF, tail robustness, bootstrap, and 2-tick cost gates.
Conclusion: broad cross-market state information did not produce enough economic edge after friction.

### Round 5 — Three-state classifier
CONT / REV / NT classifier using the same pre-10:00 feature family.
- 104 trades, -1.5375 ES points/trade, PF 0.8987.
- Classification accuracy 51.87% versus 51.73% majority baseline; balanced accuracy 37.42%.
Conclusion: classifier mostly learned the dominant no-trade state and did not discover actionable directional structure.

### Round 6 — Cross-index relative-value residual
Market-neutral ES/NQ/RTY residual mean reversion.
- Modern 2021-2023, zero friction: 1,090 trades, +0.2373 bp/trade, PF 1.3241, Sharpe 1.7426, bootstrap 99.85%.
- At 0.5 bp friction: -0.2627 bp/trade, PF 0.7232.
- At 1.0 bp friction: -0.7627 bp/trade, PF 0.3867.
Conclusion: a statistically convincing micro-edge may exist, but it is economically inaccessible at realistic retail/prop friction and holding times.

## Round 7 — Scheduled macro-event continuation
Common rule for most releases: measure unanimous ES/NQ/RTY reaction during the first five minutes after the scheduled release, enter ES in that direction, and exit 25 minutes later. FOMC used the equivalent 14:00->14:05 / 14:05->14:30 statement window.

### CPI
- 34 modern trades.
- ES +1 tick: +4.1721 points/trade, PF 2.1986, bootstrap 95.33%.
- Survived 2- and 4-tick costs and removal of the best trade.
- Both long and short signals profitable.
- 2021: -$247.50; 2022: +$7,315; 2023: +$25.
- 99.66% of positive-year profits came from 2022, violating the pre-frozen <=75% concentration gate.
Conclusion: strongest Round-7 candidate, but overwhelmingly 2022-regime dependent. No protected validation.

### NFP / Employment Situation
- 30 trades, -4.1167 points/trade, PF 0.4269.
- Negative in 2021, 2022 and 2023; both sides negative.
Conclusion: decisive reject.

### FOMC statement
- 21 trades, +0.6857 points/trade, PF 1.2439.
- Only 2022 profitable.
- Bootstrap 63.23%; best-trade removal negative; long side negative.
Conclusion: non-robust, 2022-concentrated near-miss.

### PCE / Personal Income and Outlays
- 27 trades, -1.1833 points/trade, PF 0.6698.
- Negative in all three years and both directions.
Conclusion: decisive reject.

### Retail Sales
- 29 trades, -0.5569 points/trade, PF 0.8460.
- Positive 2021 and 2022, sharply negative 2023.
- Long side positive, short side negative; tail removal negative.
Conclusion: reject; no one-side rescue.

### PPI
- 25 trades, -1.2700 points/trade, PF 0.6058.
- 2021 strongly positive, 2022-2023 negative.
- Both long and short sides negative overall.
Conclusion: reject; undermines the idea of a stable broad inflation-release continuation effect.

### Durable Goods
- 29 trades, -2.9276 points/trade, PF 0.2611.
- Negative in every modern year and on both sides.
Conclusion: decisive reject.

### ISM Manufacturing
- 25 trades, +2.5200 points/trade, PF 1.6778.
- Positive after 4 ticks and after removing the best trade.
- 2021: -$1,012.50; 2022: +$4,832.50; 2023: -$670.
- Long side slightly negative; short side strongly positive.
- Only 2022 profitable; positive-year concentration 100%; bootstrap 83.77%.
Conclusion: another economically interesting but 2022-concentrated near-miss.

### ISM Services
- 26 trades, +0.3038 points/trade, PF 1.0743.
- 2021 and 2022 positive; 2023 negative.
- Best-trade removal: -0.4700 points/trade, PF 0.8895.
- Long side positive; short side negative.
- Bootstrap 59.27%.
Conclusion: weak, tail-fragile, side-dependent; reject.

## Cross-round findings

1. **Friction is a central constraint.** Several effects are positive before costs but disappear after modest execution assumptions. Round 6 is the clearest example.

2. **2022 repeatedly creates false comfort.** CPI, FOMC and ISM Manufacturing all look materially better because of 2022. The pattern is not stable in surrounding years.

3. **Later holdouts matter.** Round 1 looked strong enough to pass 2024, then weakened on 2025. This validates the conservative multi-stage protocol.

4. **Direction-specific rescues are prohibited after observation.** Some failed candidates show a profitable long or short side, but converting them after seeing results would be data mining.

5. **Generic ES intraday directional rules remain hard to monetize.** Time-of-day, trend/reversion, cross-market regression and classification all failed to produce robust post-cost expectancy.

6. **Macro events can create larger gross moves than normal sessions, but the simple post-shock continuation rule is not stable enough.** CPI was the closest, yet its positive-year profit was 99.66% concentrated in 2022.

## Research stop rule after Round 7
Do not add more scheduled releases to the same five-minute continuation template. Doing so would expand the search space after repeated failures and increase multiple-testing risk.

Any Round 8 should satisfy all of the following:
- materially different economic mechanism, not a timing/threshold/filter tweak;
- rules frozen before opening any new protected data;
- realistic prop/retail execution costs modeled from the beginning;
- enough independent observations to test stability, not just aggregate profitability;
- explicit tail and regime robustness;
- no reuse of 2021-2023 as if it were pristine out-of-sample data.

## Recommended next direction
The most defensible next research program is **event-surprise / information-content trading**, not another price-only post-event continuation rule. The hypothesis would use the signed magnitude of the actual economic surprise versus consensus (for example CPI/NFP/FOMC-related information) and pre-register how that information maps to ES and possibly rates/equity cross-asset confirmation. This is a new information set and economic mechanism.

However, because the 2021-2023 price behavior has now been observed extensively, the model must be designed without tuning to those event outcomes and then tested on genuinely newer protected data acquired after the specification is frozen. If suitable clean surprise/consensus history and protected 2024-2025 market data cannot be obtained economically, stop the systematic ES project rather than weaken the evidence standard.
