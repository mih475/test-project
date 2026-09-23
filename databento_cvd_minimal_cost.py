import argparse
import os
import time

import pandas as pd

import multiyear_backtest as mb
from databento_event_windows import discover_price_candidates

# Minimal data needed to reproduce the original CVD-divergence comparison:
# trade delta from the reference-price minute through the final excursion-extreme
# minute. Reclaim/MTF/entry geometry already comes from the free 1-minute dataset.
ROUND_FREQ = "10min"


def _merge_intervals(rows):
    if not rows:
        return []
    rows = sorted(rows, key=lambda x: (x[0], x[1]))
    out = []
    cur_s, cur_e, cur_n = rows[0]
    for s, e, n in rows[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
            cur_n += n
        else:
            out.append((cur_s, cur_e, cur_n))
            cur_s, cur_e, cur_n = s, e, n
    out.append((cur_s, cur_e, cur_n))
    return out


def build_minimal_windows(candidates):
    exact_rows = []
    for sess, g in candidates.groupby("session", sort=True):
        intervals = []
        for _, r in g.iterrows():
            # Include the entire reference minute and final extreme minute.
            # When cumulative delta at the reference is subtracted from cumulative
            # delta at the extreme, the reference-minute contribution cancels.
            s = pd.Timestamp(r.ref_time)
            e = pd.Timestamp(r.extreme_time) + pd.Timedelta(minutes=1)
            if e > s:
                intervals.append((s, e, 1))
        for s, e, n in _merge_intervals(intervals):
            exact_rows.append({
                "session": pd.Timestamp(sess),
                "year": pd.Timestamp(sess).year,
                "exact_start_et": s,
                "exact_end_et": e,
                "exact_minutes": (e - s).total_seconds() / 60.0,
                "candidate_count": n,
            })

    exact = pd.DataFrame(exact_rows)
    if len(exact) == 0:
        return exact, exact

    # get_cost can over-report arbitrary sub-10-minute ranges. Quote conservative
    # 10-minute-aligned envelopes, but preserve exact intervals separately so an
    # eventual downloader can request only the actual required bytes.
    quote_rows = []
    for sess, g in exact.groupby("session", sort=True):
        intervals = []
        for _, r in g.iterrows():
            s = pd.Timestamp(r.exact_start_et).floor(ROUND_FREQ)
            e = pd.Timestamp(r.exact_end_et).ceil(ROUND_FREQ)
            if e <= s:
                e = s + pd.Timedelta(minutes=10)
            intervals.append((s, e, int(r.candidate_count)))
        for s, e, n in _merge_intervals(intervals):
            quote_rows.append({
                "session": pd.Timestamp(sess),
                "year": pd.Timestamp(sess).year,
                "start_utc": pd.Timestamp(s).tz_convert("UTC"),
                "end_utc": pd.Timestamp(e).tz_convert("UTC"),
                "quote_minutes": (e - s).total_seconds() / 60.0,
                "candidate_count": n,
            })

    quote = pd.DataFrame(quote_rows)
    return exact, quote


def quote_cost(quote, years):
    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit("Install Databento first: py -m pip install databento") from exc

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set in this terminal.")

    client = db.Historical(key)
    selected = quote[quote.year.isin(years)].copy().reset_index(drop=True)
    costs = []
    print(f"\nQuoting {len(selected)} minimal CVD windows for years {years}. No time-series data will be downloaded.")
    for idx, r in selected.iterrows():
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3",
            schema="trades",
            symbols="ES.v.0",
            stype_in="continuous",
            start=r.start_utc.isoformat(),
            end=r.end_utc.isoformat(),
        )
        costs.append(float(cost))
        if (idx + 1) % 50 == 0 or idx + 1 == len(selected):
            print(f"quoted {idx + 1}/{len(selected)} windows")
        time.sleep(0.06)

    selected["estimated_cost"] = costs
    selected.to_csv("databento_cvd_minimal_costs.csv", index=False)
    by_year = selected.groupby("year").agg(
        windows=("estimated_cost", "size"),
        quote_minutes=("quote_minutes", "sum"),
        candidates=("candidate_count", "sum"),
        estimated_cost=("estimated_cost", "sum"),
    )
    print("\nMINIMAL CVD COST BY YEAR")
    print(by_year.round({"quote_minutes": 0, "estimated_cost": 2}).to_string())
    print("--------------------")
    print(f"TOTAL MINIMAL ESTIMATED COST: ${selected.estimated_cost.sum():.2f}")
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate-cost", action="store_true")
    ap.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023, 2024])
    args = ap.parse_args()

    raw = mb.load_all()
    frame = mb.build_frame(raw)
    candidates = discover_price_candidates(frame)
    exact, quote = build_minimal_windows(candidates)

    exact.to_csv("databento_cvd_exact_windows.csv", index=False)
    quote.to_csv("databento_cvd_quote_windows.csv", index=False)

    print("=== MINIMAL TRUE-CVD WINDOW PLAN ===")
    print(f"price/MTF candidates before CVD: {len(candidates)}")
    print(f"exact merged windows: {len(exact)}")
    print(f"10-minute-aligned quote windows: {len(quote)}")
    print(f"exact required minutes, all years: {exact.exact_minutes.sum():.0f}")
    print(f"conservative quoted minutes, all years: {quote.quote_minutes.sum():.0f}")
    print("\nWINDOWS BY YEAR")
    summary = quote.groupby("year").agg(
        windows=("year", "size"),
        quote_minutes=("quote_minutes", "sum"),
        candidates=("candidate_count", "sum"),
    )
    print(summary.round(0).to_string())

    if args.estimate_cost:
        quote_cost(quote, args.years)
    else:
        print("\nNo Databento cost calls made. Add --estimate-cost to quote only.")


if __name__ == "__main__":
    main()
