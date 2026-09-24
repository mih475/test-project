# Strategy Tournament Round 2 — Final Result

Date: 2026-09-24

## Round-2 development tournament (2021-2023)
Primary economics: ES $5 round-trip commission + 1 tick total adverse slippage.

| Strategy | n | Net avgR | PF | Positive years | Result |
|---|---:|---:|---:|---:|---|
| R2S5 ADX/VWAP/EMA20 trend pullback | 54 | +0.3812 | 1.6885 | 3/3 | Promising but under-sampled; NOT a formal survivor |
| R2S1 RTH gap-fill confirmed | 430 | +0.0029 | 1.0045 | 1/3 | Reject |
| R2S4 prior-day level break-retest | 327 | -0.0081 | 0.9885 | 1/3 | Reject |
| R2S2 overnight range break-retest | 515 | -0.0264 | 0.9627 | 1/3 | Reject |
| R2S6 EMA9/19 retest scalp | 2273 | -0.2444 | 0.7122 | 0/3 | Reject |
| R2S3 initial-balance accepted-break | 675 | -0.3430 | 0.5761 | 0/3 | Reject |

Round-2 formal survivors: NONE.

## R2S5 backward validation
Because R2S5 had only 54 trades but otherwise strong 2021-2023 results, the exact frozen strategy was tested on an unseen backward block, 2016-2020, before exposing 2024.

Frozen backward-validation gate was recorded in `r2s5_backward_validation_plan.md` before results.

### Unseen 2016-2020 block
- n = 81
- ES 1-tick avgR = -0.1859
- PF = 0.7617
- totalR = -15.0567
- positive years = 1/5

Year-by-year ES 1-tick:
- 2016: n11, avgR -0.0758, PF 0.8885
- 2017: n25, avgR -0.4448, PF 0.5319
- 2018: n15, avgR -0.1972, PF 0.7360
- 2019: n16, avgR -0.3016, PF 0.6075
- 2020: n14, avgR +0.3343, PF 1.5536

### Combined 2016-2023
- n = 135
- ES 1-tick avgR = +0.0409
- PF = 1.0594
- totalR = +5.5255
- ES 4-tick avgR = -0.3576, PF 0.6257
- drop-five-best-trades avgR = -0.0335, PF 0.9532
- no single-winner concentration problem (max gross-positive share 2.02%)

Frozen backward gate: FALSE.

## Conclusion
R2S5 appears strongly regime-dependent: it worked very well in 2021-2023 but failed the independent earlier-history block. Do not tune it using 2016-2020 and do not reveal 2024 as a rescue attempt.

Round 2 is closed with no strategy eligible for 2024 validation.
