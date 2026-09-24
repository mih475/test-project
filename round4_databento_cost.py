import argparse
import os


DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
DEFAULT_SYMBOLS = ["NQ.v.0", "RTY.v.0", "ZN.v.0"]
DEFAULT_YEARS = list(range(2016, 2024))


def main():
    ap = argparse.ArgumentParser(
        description="Quote Databento cost for Round 4 cross-market 1-minute bars. No market data is downloaded."
    )
    ap.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    ap.add_argument("--years", nargs="+", type=int, default=DEFAULT_YEARS)
    args = ap.parse_args()

    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit("Install Databento first: py -m pip install databento") from exc

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not set in this terminal.")

    client = db.Historical(key)

    print("=== ROUND 4 DATABENTO COST QUOTE ===")
    print("Metadata quotes only. No time-series data will be downloaded.")
    print("dataset:", DATASET)
    print("schema:", SCHEMA)
    print("symbols:", args.symbols)
    print("years:", args.years)
    print()

    rows = []
    for symbol in args.symbols:
        for year in args.years:
            start = f"{year}-01-01"
            end = f"{year + 1}-01-01"
            try:
                cost = float(
                    client.metadata.get_cost(
                        dataset=DATASET,
                        schema=SCHEMA,
                        symbols=symbol,
                        stype_in="continuous",
                        start=start,
                        end=end,
                    )
                )
                status = "ok"
            except Exception as exc:
                cost = float("nan")
                status = f"ERROR: {type(exc).__name__}: {exc}"

            rows.append((symbol, year, cost, status))
            if cost == cost:
                print(f"{symbol:8s} {year}: ${cost:8.2f}")
            else:
                print(f"{symbol:8s} {year}: unavailable ({status})")

    print("\nBY SYMBOL")
    grand = 0.0
    for symbol in args.symbols:
        vals = [r[2] for r in rows if r[0] == symbol and r[2] == r[2]]
        subtotal = sum(vals)
        grand += subtotal
        print(f"{symbol:8s}: ${subtotal:.2f}")

    print("--------------------")
    print(f"FULL-PERIOD ESTIMATED TOTAL: ${grand:.2f}")
    print()
    print("Decision rule:")
    print("- If the full-history quote is comfortably small, use full continuous 1-minute data.")
    print("- If it is expensive, do NOT download yet; we will switch to a sparse 09:30-10:00-only window plan.")
    print("- 2024-2026 are intentionally not quoted by default.")


if __name__ == "__main__":
    main()
