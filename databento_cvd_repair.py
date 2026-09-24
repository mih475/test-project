import argparse
from pathlib import Path

import pandas as pd


def minute_delta(df):
    if len(df) == 0:
        return pd.DataFrame(columns=["minute_utc", "buy_volume", "sell_volume", "unknown_volume", "trade_records", "delta"])
    x = df.copy()
    x["minute_utc"] = pd.to_datetime(x["ts_event"], utc=True).dt.floor("min")
    side = x["side"].astype(str)
    size = pd.to_numeric(x["size"], errors="coerce").fillna(0).astype("int64")
    x["size_signed"] = size
    x["buy_volume"] = size.where(side.eq("B"), 0).astype("int64")
    x["sell_volume"] = size.where(side.eq("A"), 0).astype("int64")
    x["unknown_volume"] = size.where(~side.isin(["A", "B"]), 0).astype("int64")
    m = x.groupby("minute_utc", as_index=False).agg(
        buy_volume=("buy_volume", "sum"),
        sell_volume=("sell_volume", "sum"),
        unknown_volume=("unknown_volume", "sum"),
        trade_records=("size_signed", "size"),
    )
    for c in ["buy_volume", "sell_volume", "unknown_volume", "trade_records"]:
        m[c] = m[c].astype("int64")
    m["delta"] = m["buy_volume"] - m["sell_volume"]
    return m


def main():
    ap = argparse.ArgumentParser(description="Repair true-CVD minute deltas from cached Databento raw trades; no API calls")
    ap.add_argument("--years", nargs="+", type=int, default=[2021, 2022, 2023])
    ap.add_argument("--out", default="databento_true_cvd")
    args = ap.parse_args()

    years = sorted(set(args.years))
    outdir = Path(args.out)
    rawdir = outdir / "raw_windows"
    mindir = outdir / "minute_windows"
    mindir.mkdir(parents=True, exist_ok=True)

    raw_files = []
    for y in years:
        raw_files.extend(sorted(rawdir.glob(f"{y}_*.parquet")))

    if not raw_files:
        raise SystemExit(f"No cached raw parquet files found for years {years} under {rawdir}")

    minute_parts = []
    repaired = 0
    for i, raw_path in enumerate(raw_files, 1):
        df = pd.read_parquet(raw_path)
        m = minute_delta(df)
        min_path = mindir / raw_path.name
        m.to_parquet(min_path, index=False)
        minute_parts.append(m)
        repaired += 1
        if i % 100 == 0 or i == len(raw_files):
            print(f"rebuilt {i}/{len(raw_files)} minute windows")

    allm = pd.concat(minute_parts, ignore_index=True)
    for c in ["buy_volume", "sell_volume", "unknown_volume", "trade_records"]:
        allm[c] = pd.to_numeric(allm[c], errors="coerce").fillna(0).astype("int64")
    out = allm.groupby("minute_utc", as_index=False).agg(
        buy_volume=("buy_volume", "sum"),
        sell_volume=("sell_volume", "sum"),
        unknown_volume=("unknown_volume", "sum"),
        trade_records=("trade_records", "sum"),
    ).sort_values("minute_utc")
    for c in ["buy_volume", "sell_volume", "unknown_volume", "trade_records"]:
        out[c] = out[c].astype("int64")
    out["delta"] = out["buy_volume"] - out["sell_volume"]

    tag = "_".join(str(y) for y in years)
    pq = outdir / f"true_cvd_minute_delta_{tag}.parquet"
    csv = outdir / f"true_cvd_minute_delta_{tag}.csv"
    out.to_parquet(pq, index=False)
    out.to_csv(csv, index=False)

    buy = int(out.buy_volume.sum())
    sell = int(out.sell_volume.sum())
    net = int(out.delta.sum())

    print("\n=== TRUE-CVD REPAIR COMPLETE ===")
    print("Raw cached windows read:", len(raw_files))
    print("Minute windows rebuilt:", repaired)
    print("Combined minute-delta rows:", len(out))
    print("Buyer volume:", buy)
    print("Seller volume:", sell)
    print("Net delta:", net)
    print("Arithmetic check (buy - sell):", buy - sell)
    print("Parquet:", pq)
    print("CSV:", csv)

    if net != buy - sell:
        raise SystemExit("ERROR: signed-delta arithmetic check failed")


if __name__ == "__main__":
    main()
