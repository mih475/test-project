import pandas as pd

import round7_cpi_event as base
import round7_ism_manufacturing_event as mfg


YEARS = [2021, 2022, 2023]

# Frozen offline calendar based on ISM's stated cadence:
# Services PMI at 10:00 ET on the third business day of the month,
# except January, when it is released on the fourth business day.
# Dates reflect early-month NYSE closures/holidays.
ISM_SERVICES_DATES = {
    2021: [
        "2021-01-07", "2021-02-03", "2021-03-03", "2021-04-06",
        "2021-05-05", "2021-06-03", "2021-07-06", "2021-08-04",
        "2021-09-03", "2021-10-05", "2021-11-03", "2021-12-03",
    ],
    2022: [
        "2022-01-06", "2022-02-03", "2022-03-03", "2022-04-05",
        "2022-05-04", "2022-06-03", "2022-07-06", "2022-08-03",
        "2022-09-06", "2022-10-05", "2022-11-03", "2022-12-05",
    ],
    2023: [
        "2023-01-06", "2023-02-03", "2023-03-03", "2023-04-05",
        "2023-05-03", "2023-06-05", "2023-07-06", "2023-08-03",
        "2023-09-06", "2023-10-04", "2023-11-03", "2023-12-05",
    ],
}


def services_calendar():
    rows = []
    for year in YEARS:
        dates = ISM_SERVICES_DATES[year]
        if len(dates) != 12:
            raise RuntimeError(f"Frozen ISM Services calendar for {year} has {len(dates)} dates, expected 12")
        print(f"ISM Services {year}: 12 frozen 10:00 ET releases")
        rows.extend(pd.Timestamp(x) for x in dates)
    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


def main():
    # Reuse the already-frozen 10:00 event engine from ISM Manufacturing,
    # but limit it to the independent 2021-2023 Services calendar.
    mfg.YEARS = YEARS.copy()
    base.YEARS = YEARS.copy()
    base.MODERN = YEARS.copy()

    print("=== ROUND 7 ISM SERVICES EVENT STRATEGY ===")
    print("Frozen candidate R7ISMS1: unanimous ES/NQ/RTY 10:00->10:05 shock continuation.")
    print("Entry 10:05 ET, exit 10:30 ET. One trade max per ISM Services release.")
    print("Official ISM cadence frozen offline. Stage-1 years hard-frozen to 2021-2023.")
    print("2024-2026 are not loaded.")

    cal = services_calendar()
    events = mfg.build_events(cal)

    print("\nEVENT DATA AUDIT")
    print(events.groupby(["year", "status"]).size().to_string())
    ok = events[events.status == "OK"].copy()
    print("complete events:", len(ok), "of", len(events))
    print("unanimous-signal events by year:")
    print(ok.groupby("year").unanimous.sum().to_string())

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            rows.append(base.metrics(events, YEARS, product, slip))
    cs = pd.DataFrame(rows)

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    print(
        cs[["product", "slip_ticks", "trades", "win_pct", "avg_gross_pts", "avg_net_pts",
            "PF", "total_dollars", "DD_dollars", "sharpe", "bootstrap_prob_gt0"]]
        .round(4).to_string(index=False)
    )

    print("\nYEAR BY YEAR — PRIMARY ES +1 tick")
    yr = pd.DataFrame([base.metrics(events, [y], "ES", 1) for y in YEARS])
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
    print("ROUND7_ISM_SERVICES_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7ISMS1 earns a separate protected 2024 ISM Services validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7ISMS1; do not flip, retime, or keep only one side using these results.")

    events.to_csv("round7_ism_services_stage1_events.csv", index=False)
    cs.to_csv("round7_ism_services_stage1_metrics.csv", index=False)
    yr.to_csv("round7_ism_services_stage1_yearly.csv", index=False)
    sides.to_csv("round7_ism_services_stage1_sides.csv", index=False)
    print("\nSaved Round-7 ISM Services CSV outputs.")


if __name__ == "__main__":
    main()
