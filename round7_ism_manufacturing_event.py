import numpy as np
import pandas as pd

import round7_cpi_event as base


YEARS = [2018, 2019, 2020, 2021, 2022, 2023]
MODERN = [2021, 2022, 2023]
HISTORICAL = [2018, 2019, 2020]

# Frozen offline calendar based on ISM's stated cadence:
# Manufacturing PMI at 10:00 ET on the first business day of the month,
# except January, when it is released on the second business day.
ISM_DATES = {
    2018: [
        "2018-01-03", "2018-02-01", "2018-03-01", "2018-04-02",
        "2018-05-01", "2018-06-01", "2018-07-02", "2018-08-01",
        "2018-09-04", "2018-10-01", "2018-11-01", "2018-12-03",
    ],
    2019: [
        "2019-01-03", "2019-02-01", "2019-03-01", "2019-04-01",
        "2019-05-01", "2019-06-03", "2019-07-01", "2019-08-01",
        "2019-09-03", "2019-10-01", "2019-11-01", "2019-12-02",
    ],
    2020: [
        "2020-01-03", "2020-02-03", "2020-03-02", "2020-04-01",
        "2020-05-01", "2020-06-01", "2020-07-01", "2020-08-03",
        "2020-09-01", "2020-10-01", "2020-11-02", "2020-12-01",
    ],
    2021: [
        "2021-01-05", "2021-02-01", "2021-03-01", "2021-04-01",
        "2021-05-03", "2021-06-01", "2021-07-01", "2021-08-02",
        "2021-09-01", "2021-10-01", "2021-11-01", "2021-12-01",
    ],
    2022: [
        "2022-01-04", "2022-02-01", "2022-03-01", "2022-04-01",
        "2022-05-02", "2022-06-01", "2022-07-01", "2022-08-01",
        "2022-09-01", "2022-10-03", "2022-11-01", "2022-12-01",
    ],
    2023: [
        "2023-01-04", "2023-02-01", "2023-03-01", "2023-04-03",
        "2023-05-01", "2023-06-01", "2023-07-03", "2023-08-01",
        "2023-09-01", "2023-10-02", "2023-11-01", "2023-12-01",
    ],
}


def ism_calendar():
    rows = []
    for year in YEARS:
        dates = ISM_DATES[year]
        if len(dates) != 12:
            raise RuntimeError(f"Frozen ISM calendar for {year} has {len(dates)} dates, expected 12")
        print(f"ISM Manufacturing {year}: 12 frozen 10:00 ET releases")
        rows.extend(pd.Timestamp(x) for x in dates)
    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


def build_events(calendar):
    rows = []
    by_year = {y: calendar[calendar.year == y].event_date.dt.date.tolist() for y in YEARS}

    for year in YEARS:
        print(f"loading ISM event data {year} ...")
        es = base.load_es_year(year)
        nq = base.load_cross(base.CROSS_FILES["NQ"], year)
        rty = base.load_cross(base.CROSS_FILES["RTY"], year)

        for ev in by_year[year]:
            erows = {t: base.exact_es_row(es, ev, t) for t in ["10:00", "10:05", "10:30"]}
            if any(v is None for v in erows.values()):
                rows.append({"event_date": pd.Timestamp(ev), "year": year, "status": "missing_ES"})
                continue

            symbols = {erows[t]["symbol"] for t in erows}
            if len(symbols) != 1:
                rows.append({"event_date": pd.Timestamp(ev), "year": year, "status": "ES_contract_switch"})
                continue

            nq0 = base.exact_cross_open(nq, ev, "10:00")
            nq5 = base.exact_cross_open(nq, ev, "10:05")
            r0 = base.exact_cross_open(rty, ev, "10:00")
            r5 = base.exact_cross_open(rty, ev, "10:05")
            if any(x is None for x in [nq0, nq5, r0, r5]):
                rows.append({"event_date": pd.Timestamp(ev), "year": year, "status": "missing_cross"})
                continue

            es0 = erows["10:00"]["open"]
            es5 = erows["10:05"]["open"]
            es30 = erows["10:30"]["open"]

            es_shock = (es5 / es0 - 1.0) * 10000.0
            nq_shock = (nq5 / nq0 - 1.0) * 10000.0
            rty_shock = (r5 / r0 - 1.0) * 10000.0
            signs = np.sign([es_shock, nq_shock, rty_shock]).astype(int)
            unanimous = bool(np.all(signs == 1) or np.all(signs == -1))
            direction = int(signs[0]) if unanimous else 0

            rows.append(
                {
                    "event_date": pd.Timestamp(ev),
                    "year": year,
                    "status": "OK",
                    "es_symbol": erows["10:00"]["symbol"],
                    "es_1000": es0,
                    "es_1005": es5,
                    "es_1030": es30,
                    # Compatibility alias for the shared event-metrics engine.
                    "es_0835": es5,
                    "nq_1000": nq0,
                    "nq_1005": nq5,
                    "rty_1000": r0,
                    "rty_1005": r5,
                    "es_shock_bps": es_shock,
                    "nq_shock_bps": nq_shock,
                    "rty_shock_bps": rty_shock,
                    "unanimous": unanimous,
                    "direction": direction,
                    "gross_pts": direction * (es30 - es5) if direction else 0.0,
                }
            )

    return pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)


def main():
    base.YEARS = YEARS.copy()
    base.MODERN = MODERN.copy()
    base.HISTORICAL = HISTORICAL.copy()

    print("=== ROUND 7 ISM MANUFACTURING EVENT STRATEGY ===")
    print("Frozen candidate R7ISM1: unanimous ES/NQ/RTY 10:00->10:05 shock continuation.")
    print("Entry 10:05 ET, exit 10:30 ET. One trade max per ISM Manufacturing release.")
    print("Official ISM cadence frozen offline. Years hard-frozen to 2018-2023; 2024-2026 are not loaded.")

    cal = ism_calendar()
    events = build_events(cal)

    print("\nEVENT DATA AUDIT")
    print(events.groupby(["year", "status"]).size().to_string())
    ok = events[events.status == "OK"].copy()
    print("complete events:", len(ok), "of", len(events))
    print("unanimous-signal events by year:")
    print(ok.groupby("year").unanimous.sum().to_string())

    print("\nHISTORICAL CONTEXT 2018-2020 — ES +1 tick")
    h = base.metrics(events, HISTORICAL, "ES", 1)
    print(pd.DataFrame([h]).round(4).to_string(index=False))

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            rows.append(base.metrics(events, MODERN, product, slip))
    cs = pd.DataFrame(rows)

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    print(
        cs[["product", "slip_ticks", "trades", "win_pct", "avg_gross_pts", "avg_net_pts",
            "PF", "total_dollars", "DD_dollars", "sharpe", "bootstrap_prob_gt0"]]
        .round(4).to_string(index=False)
    )

    print("\nYEAR BY YEAR — PRIMARY ES +1 tick")
    yr = pd.DataFrame([base.metrics(events, [y], "ES", 1) for y in MODERN])
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
    print("ROUND7_ISM_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7ISM1 earns a separate protected 2024 ISM validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7ISM1; do not flip or retime it using these results.")

    events.to_csv("round7_ism_stage1_events.csv", index=False)
    cs.to_csv("round7_ism_stage1_metrics.csv", index=False)
    yr.to_csv("round7_ism_stage1_yearly.csv", index=False)
    sides.to_csv("round7_ism_stage1_sides.csv", index=False)
    print("\nSaved Round-7 ISM CSV outputs.")


if __name__ == "__main__":
    main()
