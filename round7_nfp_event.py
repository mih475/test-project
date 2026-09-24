import pandas as pd

import round7_cpi_event as base


NFP_DATES = {
    2018: [
        "2018-01-05", "2018-02-02", "2018-03-09", "2018-04-06",
        "2018-05-04", "2018-06-01", "2018-07-06", "2018-08-03",
        "2018-09-07", "2018-10-05", "2018-11-02", "2018-12-07",
    ],
    2019: [
        "2019-01-04", "2019-02-01", "2019-03-08", "2019-04-05",
        "2019-05-03", "2019-06-07", "2019-07-05", "2019-08-02",
        "2019-09-06", "2019-10-04", "2019-11-01", "2019-12-06",
    ],
    2020: [
        "2020-01-10", "2020-02-07", "2020-03-06", "2020-04-03",
        "2020-05-08", "2020-06-05", "2020-07-02", "2020-08-07",
        "2020-09-04", "2020-10-02", "2020-11-06", "2020-12-04",
    ],
    2021: [
        "2021-01-08", "2021-02-05", "2021-03-05", "2021-04-02",
        "2021-05-07", "2021-06-04", "2021-07-02", "2021-08-06",
        "2021-09-03", "2021-10-08", "2021-11-05", "2021-12-03",
    ],
    2022: [
        "2022-01-07", "2022-02-04", "2022-03-04", "2022-04-01",
        "2022-05-06", "2022-06-03", "2022-07-08", "2022-08-05",
        "2022-09-02", "2022-10-07", "2022-11-04", "2022-12-02",
    ],
    2023: [
        "2023-01-06", "2023-02-03", "2023-03-10", "2023-04-07",
        "2023-05-05", "2023-06-02", "2023-07-07", "2023-08-04",
        "2023-09-01", "2023-10-06", "2023-11-03", "2023-12-08",
    ],
}


def nfp_calendar():
    rows = []
    for year in base.YEARS:
        dates = NFP_DATES.get(year, [])
        if len(dates) != 12:
            raise RuntimeError(f"Frozen NFP calendar for {year} has {len(dates)} dates, expected 12")
        print(f"BLS Employment Situation {year}: 12 verified releases, all 08:30 ET (offline frozen calendar)")
        rows.extend(pd.Timestamp(x) for x in dates)
    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


def main():
    print("=== ROUND 7 NFP / EMPLOYMENT SITUATION EVENT STRATEGY ===")
    print("Frozen candidate R7NFP1: unanimous ES/NQ/RTY 08:30->08:35 shock continuation.")
    print("Entry 08:35 ET, exit 09:00 ET. One trade max per Employment Situation release.")
    print("Official BLS dates frozen offline. Years hard-frozen to 2018-2023; 2024-2026 are not loaded.")

    cal = nfp_calendar()
    events = base.build_events(cal)

    print("\nEVENT DATA AUDIT")
    print(events.groupby(["year", "status"]).size().to_string())
    ok = events[events.status == "OK"].copy()
    print("complete events:", len(ok), "of", len(events))
    print("unanimous-signal events by year:")
    print(ok.groupby("year").unanimous.sum().to_string())

    print("\nHISTORICAL CONTEXT 2018-2020 — ES +1 tick")
    h = base.metrics(events, base.HISTORICAL, "ES", 1)
    print(pd.DataFrame([h]).round(4).to_string(index=False))

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            rows.append(base.metrics(events, base.MODERN, product, slip))
    cs = pd.DataFrame(rows)

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    print(
        cs[["product", "slip_ticks", "trades", "win_pct", "avg_gross_pts", "avg_net_pts",
            "PF", "total_dollars", "DD_dollars", "sharpe", "bootstrap_prob_gt0"]]
        .round(4).to_string(index=False)
    )

    print("\nYEAR BY YEAR — PRIMARY ES +1 tick")
    yr = pd.DataFrame([base.metrics(events, [y], "ES", 1) for y in base.MODERN])
    print(
        yr[["years", "trades", "win_pct", "avg_net_pts", "PF", "total_dollars", "DD_dollars", "sharpe"]]
        .round(4).to_string(index=False)
    )

    print("\nSIDE DIAGNOSTICS — PRIMARY ES +1 tick")
    sides = base.side_metrics(events)
    print(sides.round(4).to_string(index=False))

    tail = base.tail_metrics(events)
    print("\nTAIL ROBUSTNESS:", tail)

    checks, survives, primary, two, yr, tail, sides, max_share = base.gate(events)
    print("\nSTAGE-1 GATE")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("max_positive_year_share:", max_share)
    print("ROUND7_NFP_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7NFP1 earns a separate protected 2024 NFP validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7NFP1; do not flip it to reversal using these results.")

    events.to_csv("round7_nfp_stage1_events.csv", index=False)
    cs.to_csv("round7_nfp_stage1_metrics.csv", index=False)
    yr.to_csv("round7_nfp_stage1_yearly.csv", index=False)
    sides.to_csv("round7_nfp_stage1_sides.csv", index=False)
    print("\nSaved Round-7 NFP CSV outputs.")


if __name__ == "__main__":
    main()
