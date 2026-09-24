import argparse
import os
from pathlib import Path


DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
DEFAULT_SYMBOLS = ["NQ.v.0", "RTY.v.0", "ZN.v.0"]
DEFAULT_YEARS = list(range(2016, 2024))
OUTDIR = Path("round4_crossmarket_data")


def safe_name(symbol):
    return symbol.replace(".", "_")


def main():
    ap = argparse.ArgumentParser(
        description="Download Round 4 cross-market OHLCV only after reviewing round4_databento_cost.py output."
    )
    ap.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    ap.add_argument("--years", nargs="+", type=int, default=DEFAULT_YEARS)
    ap.add_argument("--download", action="store_true", help="Required safety flag. Without it, nothing is purchased/downloaded.")
    args = ap.parse_args()

    if not args.download:
        print("Safety stop: no data requested.")
        print("First run: py round4_databento_cost.py")
        print("Only after reviewing that quote, rerun this script with --download.")
        return

    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit("Install Databento first: py -m pip install databento") from exc

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set in this terminal.")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = db.Historical(key)
    manifest = []

    print("=== ROUND 4 CROSS-MARKET DOWNLOAD ===")
    print("Protected years 2024-2026 are not in the default request.")
    print("Resume behavior: an existing non-empty .csv.gz file is skipped.")

    for symbol in args.symbols:
        for year in args.years:
            path = OUTDIR / f"{safe_name(symbol)}_{year}.csv.gz"
            if path.exists() and path.stat().st_size > 0:
                print("SKIP cached", path)
                manifest.append((symbol, year, str(path), "cached"))
                continue

            start = f"{year}-01-01"
            end = f"{year + 1}-01-01"
            print(f"DOWNLOAD {symbol} {year} ...")
            try:
                data = client.timeseries.get_range(
                    dataset=DATASET,
                    schema=SCHEMA,
                    symbols=symbol,
                    stype_in="continuous",
                    start=start,
                    end=end,
                )
                df = data.to_df()
                if len(df) == 0:
                    print("  no rows")
                    manifest.append((symbol, year, str(path), "empty"))
                    continue

                df = df.reset_index()
                df.to_csv(path, index=False, compression="gzip")
                print(f"  saved {len(df):,} rows -> {path}")
                manifest.append((symbol, year, str(path), f"saved:{len(df)}"))
            except Exception as exc:
                print(f"  ERROR {type(exc).__name__}: {exc}")
                manifest.append((symbol, year, str(path), f"error:{type(exc).__name__}:{exc}"))

    import pandas as pd
    pd.DataFrame(manifest, columns=["symbol", "year", "path", "status"]).to_csv(
        OUTDIR / "download_manifest.csv", index=False
    )
    print("Manifest:", OUTDIR / "download_manifest.csv")


if __name__ == "__main__":
    main()
