import argparse
import os
import time
from pathlib import Path

import pandas as pd

import multiyear_backtest as mb
from databento_event_windows import discover_price_candidates
from databento_cvd_minimal_cost import build_minimal_windows

DATASET = "GLBX.MDP3"
SCHEMA = "trades"
SYMBOL = "ES.v.0"
STYPE = "continuous"
DEFAULT_YEARS = [2021, 2022, 2023]


def minute_delta(df):
    if len(df) == 0:
        return pd.DataFrame(columns=["minute_utc", "buy_volume", "sell_volume", "unknown_volume", "trade_records", "delta"])
    x = df.copy()
    x["minute_utc"] = pd.to_datetime(x["ts_event"], utc=True).dt.floor("min")
    side = x["side"].astype(str)
    size = pd.to_numeric(x["size"], errors="coerce").fillna(0)
    x["buy_volume"] = size.where(side.eq("B"), 0)
    x["sell_volume"] = size.where(side.eq("A"), 0)
    x["unknown_volume"] = size.where(~side.isin(["A", "B"]), 0)
    m = x.groupby("minute_utc", as_index=False).agg(
        buy_volume=("buy_volume", "sum"),
        sell_volume=("sell_volume", "sum"),
        unknown_volume=("unknown_volume", "sum"),
        trade_records=("size", "size"),
    )
    m["delta"] = m.buy_volume - m.sell_volume
    return m


def safe_name(year, idx, start_utc, end_utc):
    s = pd.Timestamp(start_utc).strftime("%Y%m%dT%H%M%S")
    e = pd.Timestamp(end_utc).strftime("%Y%m%dT%H%M%S")
    return f"{year}_{idx:04d}_{s}_{e}"


def consolidate(minute_files, out_path):
    parts = []
    for p in minute_files:
        if p.exists():
            parts.append(pd.read_parquet(p))
    if not parts:
        return None
    allm = pd.concat(parts, ignore_index=True)
    out = allm.groupby("minute_utc", as_index=False).agg(
        buy_volume=("buy_volume", "sum"),
        sell_volume=("sell_volume", "sum"),
        unknown_volume=("unknown_volume", "sum"),
        trade_records=("trade_records", "sum"),
    ).sort_values("minute_utc")
    out["delta"] = out.buy_volume - out.sell_volume
    out.to_parquet(out_path, index=False)
    csv_path = out_path.with_suffix(".csv")
    out.to_csv(csv_path, index=False)
    return out


def main():
    ap = argparse.ArgumentParser(description="Resume-safe staged Databento true-CVD downloader")
    ap.add_argument("--download", action="store_true", help="REQUIRED to make billable Databento time-series requests")
    ap.add_argument("--years", nargs="+", type=int, default=DEFAULT_YEARS,
                    help="Years to download; default is development only: 2021 2022 2023")
    ap.add_argument("--out", default="databento_true_cvd", help="Output folder")
    ap.add_argument("--sleep", type=float, default=0.10, help="Pause between successful requests")
    args = ap.parse_args()

    years = sorted(set(args.years))
    if any(y not in range(2021, 2027) for y in years):
        raise SystemExit("Years must be within 2021-2026 for this frozen research dataset.")

    print("Building frozen price/MTF candidate windows from the free 1-minute dataset...")
    raw = mb.load_all()
    frame = mb.build_frame(raw)
    candidates = discover_price_candidates(frame)
    exact, quote = build_minimal_windows(candidates)
    selected = exact[exact.year.isin(years)].copy().sort_values(["year", "session", "exact_start_et"]).reset_index(drop=True)

    print("\n=== TRUE-CVD STAGED DOWNLOAD PLAN ===")
    print("Years:", years)
    print("Exact merged windows:", len(selected))
    print("Exact required minutes:", round(selected.exact_minutes.sum(), 1))
    print("This script uses exact windows, not the larger 10-minute quote envelopes.")
    print("Completed windows are cached locally and skipped on rerun.")

    if not args.download:
        print("\nNO DATA DOWNLOADED. Re-run with --download only when you intend to spend Databento credits.")
        print("Recommended first stage: --download --years 2021 2022 2023")
        return

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set in this terminal.")

    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit("Install dependencies: py -m pip install databento pandas pyarrow") from exc

    outdir = Path(args.out)
    rawdir = outdir / "raw_windows"
    mindir = outdir / "minute_windows"
    rawdir.mkdir(parents=True, exist_ok=True)
    mindir.mkdir(parents=True, exist_ok=True)

    client = db.Historical(key)
    manifest_rows = []
    minute_files = []

    for idx, r in selected.iterrows():
        year = int(r.year)
        # Planner timestamps are New York aware. Databento accepts UTC ISO timestamps.
        start_utc = pd.Timestamp(r.exact_start_et).tz_convert("UTC")
        end_utc = pd.Timestamp(r.exact_end_et).tz_convert("UTC")
        stem = safe_name(year, idx, start_utc, end_utc)
        raw_path = rawdir / f"{stem}.parquet"
        min_path = mindir / f"{stem}.parquet"
        minute_files.append(min_path)

        if raw_path.exists() and min_path.exists():
            manifest_rows.append({"window": stem, "year": year, "start_utc": start_utc, "end_utc": end_utc,
                                  "status": "cached", "rows": None, "error": ""})
            if (idx + 1) % 25 == 0 or idx + 1 == len(selected):
                print(f"processed {idx + 1}/{len(selected)} (cached where available)")
            continue

        if raw_path.exists() and not min_path.exists():
            df = pd.read_parquet(raw_path)
            minute_delta(df).to_parquet(min_path, index=False)
            manifest_rows.append({"window": stem, "year": year, "start_utc": start_utc, "end_utc": end_utc,
                                  "status": "rebuilt_minute_from_cache", "rows": len(df), "error": ""})
            continue

        last_err = None
        for attempt in range(1, 4):
            try:
                data = client.timeseries.get_range(
                    dataset=DATASET,
                    schema=SCHEMA,
                    symbols=SYMBOL,
                    stype_in=STYPE,
                    start=start_utc.isoformat(),
                    end=end_utc.isoformat(),
                )
                df = data.to_df().reset_index()
                # Preserve the paid trade-level data locally so later analysis never needs to repurchase it.
                keep = [c for c in ["ts_recv", "ts_event", "instrument_id", "action", "side", "price", "size", "sequence", "symbol"] if c in df.columns]
                df = df[keep].copy()
                df.to_parquet(raw_path, index=False)
                minute_delta(df).to_parquet(min_path, index=False)
                manifest_rows.append({"window": stem, "year": year, "start_utc": start_utc, "end_utc": end_utc,
                                      "status": "downloaded", "rows": len(df), "error": ""})
                last_err = None
                time.sleep(args.sleep)
                break
            except Exception as exc:
                last_err = str(exc)
                print(f"window {idx + 1}/{len(selected)} attempt {attempt}/3 failed: {exc}")
                time.sleep(2 * attempt)

        if last_err is not None:
            manifest_rows.append({"window": stem, "year": year, "start_utc": start_utc, "end_utc": end_utc,
                                  "status": "FAILED", "rows": None, "error": last_err})
            pd.DataFrame(manifest_rows).to_csv(outdir / "download_manifest.csv", index=False)
            raise SystemExit(f"Stopped after repeated failure on {stem}. Re-run the same command to resume safely.")

        if (idx + 1) % 25 == 0 or idx + 1 == len(selected):
            print(f"downloaded/processed {idx + 1}/{len(selected)} windows")
            pd.DataFrame(manifest_rows).to_csv(outdir / "download_manifest.csv", index=False)

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(outdir / "download_manifest.csv", index=False)
    tag = "_".join(str(y) for y in years)
    combined_path = outdir / f"true_cvd_minute_delta_{tag}.parquet"
    combined = consolidate(minute_files, combined_path)

    print("\n=== DOWNLOAD COMPLETE ===")
    print("Windows:", len(selected))
    print("Failed:", int((manifest.status == "FAILED").sum()) if len(manifest) else 0)
    print("Raw trade windows saved under:", rawdir)
    print("Minute delta windows saved under:", mindir)
    if combined is not None:
        print("Combined minute-delta rows:", len(combined))
        print("Combined Parquet:", combined_path)
        print("Combined CSV:", combined_path.with_suffix('.csv'))
        print("Buyer volume:", int(combined.buy_volume.sum()))
        print("Seller volume:", int(combined.sell_volume.sum()))
        print("Net delta:", int(combined.delta.sum()))


if __name__ == "__main__":
    main()
