import argparse
import os
import time

import numpy as np
import pandas as pd

import multiyear_backtest as mb

# Cost-only planner for the true-CVD phase.
# It deliberately discovers ALL price/MTF-qualified reclaims BEFORE any CVD rule
# and without trade-level busy blocking. This prevents the old CVD proxy from
# deciding which Databento windows we purchase.
PRE_PAD_MIN = 2
POST_PAD_MIN = 10
ROUND_FREQ = "10min"


def discover_price_candidates(frame):
    rows = []
    for sess, d in frame.groupby("session", sort=False):
        d = d.copy()
        excursion = None
        if len(d) < 120:
            continue

        # Preserve the original ~60 minute warm-up.
        for i in range(60, len(d) - 1):
            row = d.iloc[i]
            if not np.isfinite(row.u2) or not np.isfinite(row.l2):
                continue

            below = row.low < row.l2
            above = row.high > row.u2

            if excursion is None:
                if below and not above:
                    prior = d.iloc[max(0, i - 20):i]
                    if len(prior) == 0:
                        continue
                    k = prior.low.idxmin()
                    excursion = {
                        "dir": 1,
                        "start_time": d.index[i],
                        "extreme": float(row.low),
                        "extreme_time": d.index[i],
                        "ref_time": k,
                    }
                elif above and not below:
                    prior = d.iloc[max(0, i - 20):i]
                    if len(prior) == 0:
                        continue
                    k = prior.high.idxmax()
                    excursion = {
                        "dir": -1,
                        "start_time": d.index[i],
                        "extreme": float(row.high),
                        "extreme_time": d.index[i],
                        "ref_time": k,
                    }
                continue

            if excursion["dir"] == 1 and row.low < excursion["extreme"]:
                excursion["extreme"] = float(row.low)
                excursion["extreme_time"] = d.index[i]
            if excursion["dir"] == -1 and row.high > excursion["extreme"]:
                excursion["extreme"] = float(row.high)
                excursion["extreme_time"] = d.index[i]

            dirn = excursion["dir"]
            inside1 = (row.close > row.l2) if dirn == 1 else (row.close < row.u2)
            vals = [
                row.get("close5"), row.get("u2_5"), row.get("l2_5"),
                row.get("close30"), row.get("u2_30"), row.get("l2_30"),
            ]
            if not inside1 or any(pd.isna(v) for v in vals):
                continue

            inside5 = (row.close5 > row.l2_5) if dirn == 1 else (row.close5 < row.u2_5)
            inside30 = (row.close30 > row.l2_30) if dirn == 1 else (row.close30 < row.u2_30)
            if not (inside5 and inside30):
                continue

            entry_i = i + 1
            if entry_i >= len(d):
                excursion = None
                continue
            entry = float(d.iloc[entry_i].open)
            stop = excursion["extreme"] - mb.TICK if dirn == 1 else excursion["extreme"] + mb.TICK
            target = float(row.vwap)
            risk = (entry - stop) if dirn == 1 else (stop - entry)

            # Keep the same basic trade geometry as the original strategy, but do
            # NOT apply CVD and do NOT simulate/lock out later candidates.
            if risk < mb.TICK or (dirn == 1 and target <= entry) or (dirn == -1 and target >= entry):
                excursion = None
                continue

            rows.append({
                "session": pd.Timestamp(sess),
                "year": pd.Timestamp(sess).year,
                "direction": "long" if dirn == 1 else "short",
                "ref_time": pd.Timestamp(excursion["ref_time"]),
                "excursion_start_time": pd.Timestamp(excursion["start_time"]),
                "extreme_time": pd.Timestamp(excursion["extreme_time"]),
                "reclaim_time": pd.Timestamp(d.index[i]),
                "planned_entry_time": pd.Timestamp(d.index[entry_i]),
                "risk_pts": float(risk),
                "target_R": abs(target - entry) / risk,
            })
            excursion = None

    return pd.DataFrame(rows)


def round_window(start, end):
    # Databento notes get_cost can over-report ranges that are not discrete
    # multiples of 10 minutes. We intentionally quote/download rounded 10-minute
    # windows, making the quote more reliable and leaving small safety padding.
    start = (start - pd.Timedelta(minutes=PRE_PAD_MIN)).floor(ROUND_FREQ)
    end = (end + pd.Timedelta(minutes=POST_PAD_MIN)).ceil(ROUND_FREQ)
    if end <= start:
        end = start + pd.Timedelta(minutes=10)
    return start, end


def build_merged_windows(candidates):
    if len(candidates) == 0:
        return pd.DataFrame(columns=["session", "year", "start_utc", "end_utc", "minutes", "candidate_count"])

    raw_windows = []
    for _, r in candidates.iterrows():
        # Starting at the reference extreme is sufficient for the delta difference
        # used by the divergence test; include the whole excursion through reclaim.
        start_et = min(r.ref_time, r.excursion_start_time)
        end_et = r.reclaim_time
        start_et, end_et = round_window(start_et, end_et)
        raw_windows.append({
            "session": r.session,
            "year": int(r.year),
            "start_et": start_et,
            "end_et": end_et,
        })

    w = pd.DataFrame(raw_windows).sort_values(["session", "start_et", "end_et"])
    merged = []
    for sess, g in w.groupby("session", sort=True):
        cur_start = None
        cur_end = None
        count = 0
        year = int(g.iloc[0].year)
        for _, r in g.iterrows():
            s, e = r.start_et, r.end_et
            if cur_start is None:
                cur_start, cur_end, count = s, e, 1
            elif s <= cur_end:
                cur_end = max(cur_end, e)
                count += 1
            else:
                merged.append((sess, year, cur_start, cur_end, count))
                cur_start, cur_end, count = s, e, 1
        merged.append((sess, year, cur_start, cur_end, count))

    out = pd.DataFrame(merged, columns=["session", "year", "start_et", "end_et", "candidate_count"])
    out["start_utc"] = pd.to_datetime(out.start_et, utc=True)
    out["end_utc"] = pd.to_datetime(out.end_et, utc=True)
    out["minutes"] = (out.end_utc - out.start_utc).dt.total_seconds() / 60.0
    return out[["session", "year", "start_utc", "end_utc", "minutes", "candidate_count"]]


def estimate_cost(windows, years):
    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit("Install Databento first: py -m pip install databento") from exc

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set in this terminal.")

    client = db.Historical(key)
    selected = windows[windows.year.isin(years)].copy().reset_index(drop=True)
    costs = []
    print(f"\nQuoting {len(selected)} merged windows for years {years}. This does NOT download time-series data.")
    for idx, r in selected.iterrows():
        start = r.start_utc.isoformat()
        end = r.end_utc.isoformat()
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3",
            schema="trades",
            symbols="ES.v.0",
            stype_in="continuous",
            start=start,
            end=end,
        )
        costs.append(float(cost))
        if (idx + 1) % 50 == 0 or idx + 1 == len(selected):
            print(f"quoted {idx + 1}/{len(selected)} windows")
        # Historical metadata limit is 20 requests/sec; stay comfortably below it.
        time.sleep(0.06)

    selected["estimated_cost"] = costs
    selected.to_csv("databento_window_costs.csv", index=False)

    print("\nCOST BY YEAR")
    by_year = selected.groupby("year").agg(
        windows=("estimated_cost", "size"),
        minutes=("minutes", "sum"),
        estimated_cost=("estimated_cost", "sum"),
    )
    print(by_year.round({"minutes": 0, "estimated_cost": 2}).to_string())
    print("--------------------")
    print(f"TOTAL ESTIMATED COST: ${selected.estimated_cost.sum():.2f}")
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate-cost", action="store_true", help="Quote Databento event windows; does not download data")
    ap.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023, 2024])
    args = ap.parse_args()

    raw = mb.load_all()
    frame = mb.build_frame(raw)
    candidates = discover_price_candidates(frame)
    windows = build_merged_windows(candidates)

    candidates.to_csv("databento_price_candidates.csv", index=False)
    windows.to_csv("databento_event_windows.csv", index=False)

    print("=== DATABENTO TRUE-CVD EVENT WINDOW PLAN ===")
    print(f"price/MTF candidates before CVD: {len(candidates)}")
    print(f"merged 10-minute-aligned windows: {len(windows)}")
    print(f"total quoted minutes if all windows downloaded: {windows.minutes.sum():.0f}")
    print("\nWINDOWS BY YEAR")
    print(windows.groupby("year").agg(windows=("year", "size"), minutes=("minutes", "sum"), candidates=("candidate_count", "sum")).round(0).to_string())

    if args.estimate_cost:
        estimate_cost(windows, args.years)
    else:
        print("\nNo Databento cost calls were made. Re-run with --estimate-cost when ready.")


if __name__ == "__main__":
    main()
