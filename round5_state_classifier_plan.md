# Round 5 — Three-State Market Classifier (Frozen Plan)

Date frozen: 2026-09-24

## Objective

Round 5 changes the task from direct return prediction to day-state classification.

At 10:00 ET, using only information known by then, classify the rest of the ES session into one of three states:

1. `CONT` — a large continuation in the direction of the 09:30-10:00 ES move.
2. `REV` — a large reversal against the direction of the 09:30-10:00 ES move.
3. `NT` — low-opportunity / no-trade state.

If the predicted state is `CONT`, trade ES from 10:00 to 15:30 in the opening-30m direction.
If `REV`, trade opposite the opening-30m direction.
If `NT`, do not trade.

No stop or target is added at Stage 1; the goal is to test whether state classification itself creates economic value.

## Why this is a genuinely new round

Rounds 1-3 tested static setups/anomalies. Round 4 used the same pre-10:00 information to predict a numeric 10:00-15:30 return with walk-forward OLS.

Round 5 keeps the feature set fixed and changes only the prediction target and model class. This avoids using Round-4 diagnostics to cherry-pick new predictors.

The general motivation is consistent with intraday literature showing that momentum/reversal behavior varies with market conditions, volatility, and cross-market context. This is not a source-faithful replication of any single paper.

## Data freeze

- ES base source: existing audited 1-minute source.
- Cross-markets: Databento 1-minute continuous NQ, RTY, ZN already downloaded for Round 4.
- Hard code span: 2016-2023 only.
- 2024, 2025, 2026 remain protected and are not loaded.
- 2016 has no RTY and 2017 has partial RTY history; this is acceptable for training availability.
- Primary Stage-1 scoring block: 2021-2023.

Important caveat: 2021-2023 has been observed in prior strategy families, so it is not a pristine untouched holdout for the overall research program. The first truly untouched validation year for R5C1 will be 2024, but only if the frozen Stage-1 gate is passed.

## Frozen feature set

Use exactly the 12 Round-4 features; no additions/removals after seeing Round-4 results:

1. `es_gap_bps`
2. `es_first30_bps`
3. `nq_first30_bps`
4. `rty_first30_bps`
5. `zn_first30_bps`
6. `equity_consensus`
7. `equity_dispersion_bps`
8. `nq_minus_rty_bps`
9. `es_open_range_rel20`
10. `es_prev_range_rel20`
11. `es_open_volume_rel20`
12. `gap_open_alignment`

All are known by 10:00 ET.

## Frozen state-label construction

For each session, define the realized target as the ES 10:00-to-15:30 return in basis points.

Define that day's magnitude threshold as the median absolute 10:00-to-15:30 return from the previous 252 valid ES sessions only.

This threshold is adaptive but uses no future information and is not optimized for performance.

State labels:

- `NT` if `abs(target_bps)` is less than or equal to the prior-252-session median absolute target.
- Otherwise `CONT` if the target direction matches the sign of the ES 09:30-10:00 return.
- Otherwise `REV`.

If the first-30-minute ES return is exactly zero or insufficient history exists, no label is assigned.

The prior-252 median rule is intended to separate materially directional sessions from below-median directional opportunity without fitting a profit-maximizing threshold.

## Frozen model — R5C1

Model: walk-forward multiclass Linear Discriminant Analysis (LDA), implemented directly with NumPy.

Rules:

- standardize features using training data only;
- empirical class priors;
- pooled covariance matrix;
- Moore-Penrose pseudoinverse for numerical stability;
- minimum 504 prior labeled sessions before issuing predictions;
- refit every 20 newly available labeled sessions;
- no regularization sweep;
- no probability/confidence threshold;
- predicted class is simply the class with maximum LDA posterior score.

This model was selected before Stage-1 results because it is a simple multiclass linear classifier without tunable tree depth, hidden layers, learning rate, or probability cutoffs.

## Frozen trading translation

Decision time: 10:00 ET.
Entry: ES 10:00 open.
Exit: ES 15:30 open.
Maximum: one position per day.

Action:

- predicted `CONT`: direction = sign of ES 09:30-10:00 return;
- predicted `REV`: direction = opposite sign;
- predicted `NT`: no trade.

Primary friction: ES $5 round-trip commission + 1 adverse tick total.
Stress tests: ES/MES at 0, 1, 2, and 4 adverse ticks.

## Baselines

For diagnosis only:

- `B_CONT`: always trade in the opening-30m direction.
- `B_REV`: always trade opposite the opening-30m direction.

Baselines cannot unlock 2024.

## Frozen Stage-1 gate

R5C1 must pass every condition on 2021-2023:

1. at least 150 trades;
2. ES +1-tick average net points > 0;
3. ES +1-tick profit factor >= 1.15;
4. positive net total in at least 2 of 3 years;
5. average net points remain > 0 after deleting the best 1% of trades;
6. bootstrap probability of positive mean daily return >= 90%, including no-trade days as zero-return days;
7. ES +2-tick average net points > 0;
8. no single positive year contributes more than 75% of total positive-year profits;
9. classification accuracy must beat the realized majority-class baseline accuracy.

No gate may be changed after seeing results.

## Diagnostics, not tuning handles

Report:

- class distribution;
- confusion/accuracy summary;
- balanced accuracy;
- majority-class baseline accuracy;
- predicted no-trade frequency;
- median absolute target on predicted-trade vs predicted-no-trade days;
- cost sensitivity;
- yearly economics;
- tail robustness.

These diagnostics may explain failure but may not be used to repair R5C1 on 2021-2023.

## Decision rule

- Pass all frozen conditions -> create a separate 2024 validation script with unchanged rules.
- Fail any frozen condition -> retire R5C1; do not tune features, class threshold, LDA, or probability rules using 2021-2023.
