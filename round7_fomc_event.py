import numpy as np
import pandas as pd

import round7_cpi_event as base


FOMC_DATES = {
    2018: [
        "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13",
        "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    ],
    2019: [
        "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
        "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    ],
    2020: [
        "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29",
        "2020-09-16", "2020-11-05", "2020-12-16",
    ],
    2021: [
        "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
        "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    ],
    2022: [
        "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
        "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    ],
    2023: [
        "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
        "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    ],
}


def fomc_calendar():
    rows = []
    for year in base.YEARS:
        dates = FOMC_DATES.get(year, [])
        expected = 7 if year == 2020 else 8
        if len(dates) != expected:
            raise RuntimeError(
                f"Frozen FOMC calendar for {year} has {len(dates)} dates, expected {expected}"
            )
        print(
            f"Federal Reserve FOMC {year}: {len(dates)} frozen regular 14:00 ET statement dates"
        )
        rows.extend(pd.Timestamp(x) for x in dates)
    out = pd.DataFrame({"event_date": rows})
    out["year"] = out.event_date.dt.year
    return out


def build_events(calendar):
    rows = []
    by_year = {
        y: calendar[calendar.year == y].event_date.dt.date.tolist()
        for y in base.YEARS
    }

    for year in base.YEARS:
        print(f"loading FOMC event data {year} ...")
        es = base.load_es_year(year)
        nq = base.load_cross(base.CROSS_FILES["NQ"], year)
        rty = base.load_cross(base.CROSS_FILES["RTY"], year)

        for ev in by_year[year]:
            erows = {
                t: base.exact_es_row(es, ev, t)
                for t in ["14:00", "14:05", "14:30"]
            }
            if any(v is None for v in erows.values()):
                rows.append(
                    {"event_date": pd.Timestamp(ev), "year": year, "status": "missing_ES"}
                )
                continue

            symbols = {erows[t]["symbol"] for t in erows}
            if len(symbols) != 1:
                rows.append(
                    {
                        "event_date": pd.Timestamp(ev),
                        "year": year,
                        "status": "ES_contract_switch",
                    }
                )
                continue

            nq0 = base.exact_cross_open(nq, ev, "14:00")
            nq5 = base.exact_cross_open(nq, ev, "14:05")
            r0 = base.exact_cross_open(rty, ev, "14:00")
            r5 = base.exact_cross_open(rty, ev, "14:05")
            if any(x is None for x in [nq0, nq5, r0, r5]):
                rows.append(
                    {
                        "event_date": pd.Timestamp(ev),
                        "year": year,
                        "status": "missing_cross",
                    }
                )
                continue

            es0 = erows["14:00"]["open"]
            es5 = erows["14:05"]["open"]
            es30 = erows["14:30"]["open"]
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
                    "es_symbol": erows["14:00"]["symbol"],
                    "es_1400": es0,
                    "es_1405": es5,
                    "es_1430": es30,
                    # Compatibility name for the common event metrics code shape.
                    "es_0835": es5,
                    "nq_1400": nq0,
                    "nq_1405": nq5,
                    "rty_1400": r0,
                    "rty_1405": r5,
                    "es_shock_bps": es_shock,
                    "nq_shock_bps": nq_shock,
                    "rty_shock_bps": rty_shock,
                    "unanimous": unanimous,
                    "direction": direction,
                    "gross_pts": direction * (es30 - es5) if direction else 0.0,
                }
            )

    return pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)


def metrics(df, years, product="ES", slip_ticks=1):
    z = df[(df.year.isin(years)) & (df.status == "OK") & (df.direction != 0)].copy()
    cp = base.cost_points(product, slip_ticks)
    pv = 50.0 if product == "ES" else 5.0

    if len(z) == 0:
        return {
            "years": f"{min(years)}-{max(years)}",
            "product": product,
            "slip_ticks": slip_ticks,
            "trades": 0,
            "win_pct": np.nan,
            "avg_gross_pts": np.nan,
            "avg_net_pts": np.nan,
            "avg_dollars": np.nan,
            "PF": np.nan,
            "total_dollars": np.nan,
            "DD_dollars": np.nan,
            "sharpe": np.nan,
            "bootstrap_prob_gt0": np.nan,
        }

    z["net_pts"] = z.gross_pts - cp
    z["net_dollars"] = z.net_pts * pv
    z["net_ret"] = z.net_pts / z.es_1405.astype(float)
    pos = float(z.loc[z.net_dollars > 0, "net_dollars"].sum())
    neg = float(z.loc[z.net_dollars <= 0, "net_dollars"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    sd = float(z.net_ret.std(ddof=1))
    sharpe = (
        float(z.net_ret.mean() / sd * np.sqrt(8))
        if len(z) > 1 and sd > 0
        else np.nan
    )

    return {
        "years": f"{min(years)}-{max(years)}",
        "product": product,
        "slip_ticks": slip_ticks,
        "trades": int(len(z)),
        "win_pct": float((z.net_pts > 0).mean() * 100),
        "avg_gross_pts": float(z.gross_pts.mean()),
        "avg_net_pts": float(z.net_pts.mean()),
        "avg_dollars": float(z.net_dollars.mean()),
        "PF": float(pf),
        "total_dollars": float(z.net_dollars.sum()),
        "DD_dollars": base.max_drawdown(z.net_dollars),
        "sharpe": sharpe,
        "bootstrap_prob_gt0": float(base.bootstrap_prob_positive(z.net_ret)),
    }


def side_metrics(df):
    z = df[
        (df.year.isin(base.MODERN))
        & (df.status == "OK")
        & (df.direction != 0)
    ].copy()
    cp = base.cost_points("ES", 1)
    z["net_pts"] = z.gross_pts - cp
    out = []
    for direction, name in [(1, "long"), (-1, "short")]:
        g = z[z.direction == direction]
        out.append(
            {
                "side": name,
                "trades": int(len(g)),
                "win_pct": float((g.net_pts > 0).mean() * 100) if len(g) else np.nan,
                "avg_net_pts": float(g.net_pts.mean()) if len(g) else np.nan,
                "total_net_pts": float(g.net_pts.sum()) if len(g) else np.nan,
            }
        )
    return pd.DataFrame(out)


def tail_metrics(df):
    z = df[
        (df.year.isin(base.MODERN))
        & (df.status == "OK")
        & (df.direction != 0)
    ].copy()
    if len(z) <= 1:
        return {
            "drop_n": 1 if len(z) else 0,
            "drop_avg_net_pts": np.nan,
            "drop_PF": np.nan,
        }

    cp = base.cost_points("ES", 1)
    z["net_pts"] = z.gross_pts - cp
    z["net_dollars"] = z.net_pts * 50.0
    z = z.sort_values("net_dollars", ascending=False).iloc[1:].copy()
    pos = float(z.loc[z.net_dollars > 0, "net_dollars"].sum())
    neg = float(z.loc[z.net_dollars <= 0, "net_dollars"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    return {
        "drop_n": 1,
        "drop_avg_net_pts": float(z.net_pts.mean()),
        "drop_PF": float(pf),
    }


def gate(df):
    primary = metrics(df, base.MODERN, "ES", 1)
    two = metrics(df, base.MODERN, "ES", 2)
    yr = pd.DataFrame([metrics(df, [y], "ES", 1) for y in base.MODERN])
    tail = tail_metrics(df)
    sides = side_metrics(df)

    positive_years = int((yr.total_dollars > 0).sum())
    pos = yr.loc[yr.total_dollars > 0, "total_dollars"]
    max_share = float(pos.max() / pos.sum()) if len(pos) and pos.sum() > 0 else np.inf
    long_avg = float(sides.loc[sides.side == "long", "avg_net_pts"].iloc[0])
    short_avg = float(sides.loc[sides.side == "short", "avg_net_pts"].iloc[0])

    checks = {
        "n_ge_15": primary["trades"] >= 15,
        "avg_net_positive": primary["avg_net_pts"] > 0,
        "PF_ge_1_25": primary["PF"] >= 1.25,
        "positive_2_of_3_years": positive_years >= 2,
        "tail_avg_positive": tail["drop_avg_net_pts"] > 0,
        "bootstrap_ge_0_90": primary["bootstrap_prob_gt0"] >= 0.90,
        "two_tick_avg_positive": two["avg_net_pts"] > 0,
        "max_positive_year_share_le_0_75": max_share <= 0.75,
        "long_signal_nonnegative": np.isfinite(long_avg) and long_avg >= 0,
        "short_signal_nonnegative": np.isfinite(short_avg) and short_avg >= 0,
    }
    return checks, all(checks.values()), primary, two, yr, tail, sides, max_share


def main():
    print("=== ROUND 7 FOMC STATEMENT EVENT STRATEGY ===")
    print("Frozen candidate R7FOMC1: unanimous ES/NQ/RTY 14:00->14:05 shock continuation.")
    print("Entry 14:05 ET, exit 14:30 ET. One trade max per regular FOMC statement.")
    print("Official Federal Reserve dates frozen offline. 2018-2023 only; 2024-2026 are not loaded.")
    print("2020 emergency March actions are excluded because they were not 14:00 ET releases.")

    cal = fomc_calendar()
    events = build_events(cal)

    print("\nEVENT DATA AUDIT")
    print(events.groupby(["year", "status"]).size().to_string())
    ok = events[events.status == "OK"].copy()
    print("complete events:", len(ok), "of", len(events))
    print("unanimous-signal events by year:")
    print(ok.groupby("year").unanimous.sum().to_string())

    print("\nHISTORICAL CONTEXT 2018-2020 — ES +1 tick")
    h = metrics(events, base.HISTORICAL, "ES", 1)
    print(pd.DataFrame([h]).round(4).to_string(index=False))

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            rows.append(metrics(events, base.MODERN, product, slip))
    cs = pd.DataFrame(rows)

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    print(
        cs[[
            "product", "slip_ticks", "trades", "win_pct", "avg_gross_pts",
            "avg_net_pts", "PF", "total_dollars", "DD_dollars", "sharpe",
            "bootstrap_prob_gt0",
        ]].round(4).to_string(index=False)
    )

    print("\nYEAR BY YEAR — PRIMARY ES +1 tick")
    yr = pd.DataFrame([metrics(events, [y], "ES", 1) for y in base.MODERN])
    print(
        yr[[
            "years", "trades", "win_pct", "avg_net_pts", "PF",
            "total_dollars", "DD_dollars", "sharpe",
        ]].round(4).to_string(index=False)
    )

    print("\nSIDE DIAGNOSTICS — PRIMARY ES +1 tick")
    sides = side_metrics(events)
    print(sides.round(4).to_string(index=False))

    tail = tail_metrics(events)
    print("\nTAIL ROBUSTNESS:", tail)

    checks, survives, primary, two, yr, tail, sides, max_share = gate(events)
    print("\nSTAGE-1 GATE")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("max_positive_year_share:", max_share)
    print("ROUND7_FOMC_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7FOMC1 earns a separate protected 2024 FOMC validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7FOMC1; do not tune statement/press-conference windows using these results.")

    events.to_csv("round7_fomc_stage1_events.csv", index=False)
    cs.to_csv("round7_fomc_stage1_metrics.csv", index=False)
    yr.to_csv("round7_fomc_stage1_yearly.csv", index=False)
    sides.to_csv("round7_fomc_stage1_sides.csv", index=False)
    print("\nSaved Round-7 FOMC CSV outputs.")


if __name__ == "__main__":
    main()
