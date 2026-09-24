from pathlib import Path
import pandas as pd

DATA_DIR = Path("round4_crossmarket_data")
SYMBOLS = ["NQ_v_0", "RTY_v_0", "ZN_v_0"]
YEARS = list(range(2016, 2024))
NY = "America/New_York"


def inspect(path):
    if not path.exists():
        return {"status": "MISSING", "rows": 0, "first": "", "last": "", "0930_1000_days": 0}
    if path.stat().st_size == 0:
        return {"status": "EMPTY_FILE", "rows": 0, "first": "", "last": "", "0930_1000_days": 0}
    try:
        d = pd.read_csv(path, compression="gzip")
    except Exception as exc:
        return {"status": f"READ_ERROR:{type(exc).__name__}", "rows": 0, "first": "", "last": "", "0930_1000_days": 0}
    if len(d) == 0:
        return {"status": "NO_ROWS", "rows": 0, "first": "", "last": "", "0930_1000_days": 0}
    ts_col = "ts_event" if "ts_event" in d.columns else None
    if ts_col is None:
        candidates = [c for c in d.columns if "time" in c.lower() or c.lower() == "index"]
        if not candidates:
            return {"status": "NO_TIMESTAMP_COLUMN", "rows": len(d), "first": "", "last": "", "0930_1000_days": 0}
        ts_col = candidates[0]
    t = pd.to_datetime(d[ts_col], utc=True, errors="coerce").dropna().dt.tz_convert(NY)
    if len(t) == 0:
        return {"status": "NO_VALID_TIMESTAMPS", "rows": len(d), "first": "", "last": "", "0930_1000_days": 0}
    x = pd.DataFrame({"t": t})
    x["date"] = x.t.dt.date
    x["hm"] = x.t.dt.strftime("%H:%M")
    piv = x[x.hm.isin(["09:30", "10:00"])].drop_duplicates(["date", "hm"]).groupby("date").hm.nunique()
    coverage = int((piv == 2).sum())
    return {
        "status": "OK",
        "rows": len(d),
        "first": str(t.min()),
        "last": str(t.max()),
        "0930_1000_days": coverage,
    }


def main():
    print("=== ROUND 4 CROSS-MARKET DATA AUDIT ===")
    rows = []
    for symbol in SYMBOLS:
        for year in YEARS:
            if symbol == "RTY_v_0" and year == 2016:
                continue
            path = DATA_DIR / f"{symbol}_{year}.csv.gz"
            r = inspect(path)
            rows.append({"symbol": symbol, "year": year, "file": str(path), **r})
    out = pd.DataFrame(rows)
    print(out[["symbol", "year", "status", "rows", "0930_1000_days", "first", "last"]].to_string(index=False))
    print("\nCoverage by year (minimum across required cross-markets):")
    req = out[out.status.eq("OK")].copy()
    if len(req):
        cov = req.groupby("year").agg(symbols_ok=("symbol", "nunique"), min_days=("0930_1000_days", "min"), max_days=("0930_1000_days", "max"))
        print(cov.to_string())
    print("\nExpected modern coverage: NQ/RTY/ZN should each have substantial 09:30+10:00 coverage in 2021, 2022, and 2023.")
    print("If 2023 is missing/empty/short for any one symbol, do not interpret the Round-4 model result yet.")


if __name__ == "__main__":
    main()
