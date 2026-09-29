import pandas as pd

import round7_cpi_event as base


DURABLE_YEARS = [2021, 2022, 2023]
DURABLE_DATES = {
    2021: [
        "2021-01-27", "2021-02-25", "2021-03-24", "2021-04-26",
        "2021-05-27", "2021-06-24", "2021-07-27", "2021-08-25",
        "2021-09-27", "2021-10-27", "2021-11-24", "2021-12-23",
    ],
    2022: [
        "2022-01-27", "2022-02-25", "2022-03-24", "2022-04-26",
        "2022-05-25", "2022-06-27", "2022-07-27", "2022-08-24",
        "2022-09-27", "2022-10-27", "2022-11-23", "2022-12-23",
    ],
    2023: [
        "2023-01-26", "2023-02-27", "2023-03-24", "2023-04-26",
        "2023-05-26", "2023-06-27", "2023-07-27", "2023-08-24",
        "2023-09-27", "2023-10-26", "2023-11-22", "2023-12-22",
    ],
}


def durable_calendar():
    rows = []
    for year in DURABLE_YEARS:
        dates = DURABLE_DATES.get(year, [])
        if len(dates) != 12:
            raise RuntimeError(f"Frozen Durable Goods calendar for {year} has {len(dates)} dates, expected 12")
        print(f"Census Advance Durable Goods {year}: 12 frozen 08:30 ET releases")
        rows.extend(pd.Timestamp(x) for x in dates)
    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


def main():
    base.YEARS = DURABLE_YEARS.copy()
    base.MODERN = DURABLE_YEARS.copy()

    print("=== ROUND 7 DURABLE GOODS EVENT STRATEGY ===")
    print("Frozen candidate R7DUR1: unanimous ES/NQ/RTY 08:30->08:35 shock continuation.")
    print("Entry 08:35 ET, exit 09:00 ET. One trade max per Advance Durable Goods release.")
    print("Official U.S. Census Bureau dates frozen offline. Stage-1 years hard-frozen to 2021-2023.")
    print("2024-2026 are not loaded.")

    cal = durable_calendar()
    events = base.build_events(cal)

    print("\nEVENT DATA AUDIT")
    print(events.groupby(["year", "status"]).size().to_string())
    ok = events[events.status == "OK"].copy()
    print("complete events:", len(ok), "of", len(events))
    print("unanimous-signal events by year:")
    print(ok.groupby("year").unanimous.sum().to_string())

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            rows.append(base.metrics(events, DURABLE_YEARS, product, slip))
    cs = pd.DataFrame(rows)

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    print(
        cs[["product", "slip_ticks", "trades", "win_pct", "avg_gross_pts", "avg_net_pts",
            "PF", "total_dollars", "DD_dollars", "sharpe", "bootstrap_prob_gt0"]]
        .round(4).to_string(index=False)
    )

    print("\nYEAR BY YEAR — PRIMARY ES +1 tick")
    yr = pd.DataFrame([base.metrics(events, [y], "ES", 1) for y in DURABLE_YEARS])
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
    print("ROUND7_DURABLE_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7DUR1 earns a separate protected 2024 Durable Goods validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7DUR1; do not flip it to reversal using these results.")

    events.to_csv("round7_durable_stage1_events.csv", index=False)
    cs.to_csv("round7_durable_stage1_metrics.csv", index=False)
    yr.to_csv("round7_durable_stage1_yearly.csv", index=False)
    sides.to_csv("round7_durable_stage1_sides.csv", index=False)
    print("\nSaved Round-7 Durable Goods CSV outputs.")


if __name__ == "__main__":
    main()
