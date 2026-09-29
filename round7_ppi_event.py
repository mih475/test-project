import pandas as pd

import round7_cpi_event as base


PPI_DATES = {
    2018: [
        "2018-01-11", "2018-02-15", "2018-03-14", "2018-04-10",
        "2018-05-09", "2018-06-13", "2018-07-11", "2018-08-09",
        "2018-09-12", "2018-10-10", "2018-11-09", "2018-12-11",
    ],
    2019: [
        "2019-01-15", "2019-02-14", "2019-03-13", "2019-04-11",
        "2019-05-09", "2019-06-11", "2019-07-12", "2019-08-09",
        "2019-09-11", "2019-10-08", "2019-11-14", "2019-12-12",
    ],
    2020: [
        "2020-01-15", "2020-02-19", "2020-03-12", "2020-04-09",
        "2020-05-13", "2020-06-11", "2020-07-10", "2020-08-11",
        "2020-09-10", "2020-10-14", "2020-11-13", "2020-12-11",
    ],
    2021: [
        "2021-01-15", "2021-02-17", "2021-03-12", "2021-04-09",
        "2021-05-13", "2021-06-15", "2021-07-14", "2021-08-12",
        "2021-09-10", "2021-10-14", "2021-11-09", "2021-12-14",
    ],
    2022: [
        "2022-01-13", "2022-02-15", "2022-03-15", "2022-04-13",
        "2022-05-12", "2022-06-14", "2022-07-14", "2022-08-11",
        "2022-09-14", "2022-10-12", "2022-11-15", "2022-12-09",
    ],
    2023: [
        "2023-01-18", "2023-02-16", "2023-03-15", "2023-04-13",
        "2023-05-11", "2023-06-14", "2023-07-13", "2023-08-11",
        "2023-09-14", "2023-10-11", "2023-11-15", "2023-12-13",
    ],
}


def ppi_calendar():
    rows = []
    for year in base.YEARS:
        dates = PPI_DATES.get(year, [])
        if len(dates) != 12:
            raise RuntimeError(f"Frozen PPI calendar for {year} has {len(dates)} dates, expected 12")
        print(f"BLS Producer Price Index {year}: 12 frozen releases, all 08:30 ET")
        rows.extend(pd.Timestamp(x) for x in dates)
    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


def main():
    base.YEARS = list(range(2018, 2024))
    base.HISTORICAL = [2018, 2019, 2020]
    base.MODERN = [2021, 2022, 2023]

    print("=== ROUND 7 PPI EVENT STRATEGY ===")
    print("Frozen candidate R7PPI1: unanimous ES/NQ/RTY 08:30->08:35 shock continuation.")
    print("Entry 08:35 ET, exit 09:00 ET. One trade max per Producer Price Index release.")
    print("Official BLS dates frozen offline. Years hard-frozen to 2018-2023; 2024-2026 are not loaded.")

    cal = ppi_calendar()
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
    print("ROUND7_PPI_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7PPI1 earns a separate protected 2024 PPI validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7PPI1; do not flip it to reversal using these results.")

    events.to_csv("round7_ppi_stage1_events.csv", index=False)
    cs.to_csv("round7_ppi_stage1_metrics.csv", index=False)
    yr.to_csv("round7_ppi_stage1_yearly.csv", index=False)
    sides.to_csv("round7_ppi_stage1_sides.csv", index=False)
    print("\nSaved Round-7 PPI CSV outputs.")


if __name__ == "__main__":
    main()
