# Round 7 FOMC Statement Strategy — Frozen Stage-1 Specification

## Candidate

`R7FOMC1` — scheduled FOMC statement shock continuation.

This is a new event hypothesis. It is not derived by tuning the CPI or NFP results.

## Event universe

Use only regular/scheduled FOMC policy-decision dates with the policy statement released at **2:00 p.m. Eastern Time**.

Years: 2018–2023 only.

- Context: 2018–2020.
- Primary Stage-1 score: 2021–2023.
- Protected: 2024–2026 are not loaded.

Exclude unscheduled/notation-vote actions. In particular, 2020 emergency actions on March 3 (10:00 a.m.) and March 15 (5:00 p.m.) are excluded, and the originally scheduled March 17–18 meeting was cancelled.

Frozen release dates:

- 2018: Jan 31, Mar 21, May 2, Jun 13, Aug 1, Sep 26, Nov 8, Dec 19
- 2019: Jan 30, Mar 20, May 1, Jun 19, Jul 31, Sep 18, Oct 30, Dec 11
- 2020: Jan 29, Apr 29, Jun 10, Jul 29, Sep 16, Nov 5, Dec 16
- 2021: Jan 27, Mar 17, Apr 28, Jun 16, Jul 28, Sep 22, Nov 3, Dec 15
- 2022: Jan 26, Mar 16, May 4, Jun 15, Jul 27, Sep 21, Nov 2, Dec 14
- 2023: Feb 1, Mar 22, May 3, Jun 14, Jul 26, Sep 20, Nov 1, Dec 13

## Signal and execution

At each eligible FOMC event:

1. Measure ES, NQ and RTY price direction from the **14:00 open** to the **14:05 open**.
2. If all three are positive, go **long ES** at 14:05.
3. If all three are negative, go **short ES** at 14:05.
4. Otherwise no trade.
5. Exit at the **14:30 open**.
6. One trade maximum per FOMC decision.

No magnitude threshold. No stop-loss optimization. No alternate exit. No reversal rescue. The 14:30 exit is intended to isolate the statement reaction from the Chair press-conference window.

## Costs

Same convention as CPI/NFP:

- ES round-trip commission: $5 = 0.10 ES point.
- MES round-trip commission: $1.50 = 0.30 MES point.
- Slippage diagnostics: 0, 1, 2, 4 adverse ticks round trip.
- Primary: ES +1 adverse tick.

## Stage-1 gate

R7FOMC1 must pass **all** of the following on 2021–2023:

1. At least 15 trades.
2. Positive after-cost expectancy at ES +1 tick.
3. PF >= 1.25.
4. Positive total P/L in at least 2 of 3 years.
5. Positive expectancy after removing the single best trade.
6. Bootstrap P(mean return > 0) >= 90%.
7. Positive expectancy at ES +2 ticks.
8. No single positive year contributes more than 75% of total positive-year profits.
9. Long signals have non-negative average after-cost expectancy.
10. Short signals have non-negative average after-cost expectancy.

The lower minimum trade count versus CPI/NFP reflects the smaller fixed universe of eight regular FOMC decisions per year (24 maximum modern events), not a result-driven adjustment.

## Anti-overfit rule

If R7FOMC1 fails, retire the exact rule. Do not change 14:05 entry, 14:30 exit, unanimity, direction, or select only SEP/non-SEP meetings after seeing results. Do not reveal 2024 as a rescue.
