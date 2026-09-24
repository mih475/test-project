import io
import math
import re
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd
import requests

NY = "America/New_York"
TICK = 0.25
SEED = 20260924
YEARS = list(range(2018, 2024))
MODERN = [2021, 2022, 2023]
HISTORICAL = [2018, 2019, 2020]
ES_BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
CROSS_DIR = Path("round4_crossmarket_data")
CROSS_FILES = {"NQ": "NQ_v_0", "RTY": "RTY_v_0"}
BLS_URL = "https://www.bls.gov/schedule/{year}/home.htm"


class RowParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.in_row = False
        self.in_cell = False
        self.row = []
        self.cell = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self.in_row = True
            self.row = []
        elif self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.cell = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.in_row and self.in_cell and tag in ("td", "th"):
            txt = " ".join(" ".join(self.cell).split())
            self.row.append(txt)
            self.in_cell = False
            self.cell = []
        elif self.in_row and tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
            self.row = []


def fetch_cpi_calendar():
    dates = []
    headers = {"User-Agent": "Mozilla/5.0 Round7-CPI-research/1.0"}
    for year in YEARS:
        url = BLS_URL.format(year=year)
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        p = RowParser()
        p.feed(r.text)
        found = []
        for row in p.rows:
            joined = " | ".join(row)
            if "Consumer Price Index" not in joined:
                continue
            date_cell = next((x for x in row if re.search(r"\b20\d{2}\b", x)), None)
            time_cell = next((x for x in row if re.search(r"\b\d{1,2}:\d{2}\s*[AP]M\b", x, re.I)), None)
            if not date_cell or not time_cell:
                continue
            dt = pd.to_datetime(date_cell, errors="coerce")
            if pd.isna(dt):
                continue
            norm_time = re.sub(r"\s+", " ", time_cell.strip()).upper()
            if norm_time != "08:30 AM":
                raise RuntimeError(f"Unexpected CPI release time {norm_time!r} for {date_cell} ({url})")
            found.append(pd.Timestamp(dt).normalize())

        found = sorted(set(found))
        if len(found) != 12:
            raise RuntimeError(
                f"BLS calendar parse for {year} returned {len(found)} CPI dates, expected exactly 12. "
                f"Do not continue until the official calendar parse is fixed."
            )
        print(f"BLS CPI {year}: {len(found)} releases, all 08:30 ET")
        dates.extend(found)

    out = pd.DataFrame({"event_date": dates})
    out["year"] = out.event_date.dt.year
    return out


def load_es_year(year):
    r = requests.get(ES_BASE.format(year), timeout=240)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d["datetime_et"] = pd.to_datetime(d["datetime_et"], utc=True).dt.tz_convert(NY)
    for c in ["open", "high", "low", "close", "volume"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["datetime_et", "open", "volume", "symbol"]).copy()
    d["session"] = d.datetime_et.dt.date
    return d[["datetime_et", "open", "volume", "symbol", "session"]].copy()


def load_cross(prefix, year):
    path = CROSS_DIR / f"{prefix}_{year}.csv.gz"
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Missing {path}; Round 7 expects the existing Round-4 data.")
    z = pd.read_csv(path, compression="gzip")
    ts_col = "ts_event" if "ts_event" in z.columns else None
    if ts_col is None:
        candidates = [c for c in z.columns if "time" in c.lower() or c.lower() == "index"]
        if not candidates:
            raise ValueError(f"Cannot identify timestamp in {path}: {list(z.columns)}")
        ts_col = candidates[0]
    z["datetime_et"] = pd.to_datetime(z[ts_col], utc=True).dt.tz_convert(NY)
    z["open"] = pd.to_numeric(z["open"], errors="coerce")
    z = z.dropna(subset=["datetime_et", "open"]).copy()
    z = z.sort_values("datetime_et").drop_duplicates("datetime_et", keep="last")
    return z.set_index("datetime_et")[["open"]]


def exact_cross_open(df, event_date, hhmm):
    t = pd.Timestamp(f"{event_date} {hhmm}", tz=NY)
    if t not in df.index:
        return None
    row = df.loc[t]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[-1]
    px = float(row.open)
    return px if np.isfinite(px) and px > 0 else None


def exact_es_row(df, event_date, hhmm):
    t = pd.Timestamp(f"{event_date} {hhmm}", tz=NY)
    g = df[df.datetime_et == t]
    if len(g) == 0:
        return None
    g = g.sort_values(["volume", "symbol"], ascending=[False, True])
    r = g.iloc[0]
    return {"open": float(r.open), "symbol": str(r.symbol), "volume": float(r.volume)}


def build_events(calendar):
    rows = []
    by_year = {y: calendar[calendar.year == y].event_date.dt.date.tolist() for y in YEARS}
    for year in YEARS:
        print(f"loading event data {year} ...")
        es = load_es_year(year)
        nq = load_cross(CROSS_FILES["NQ"], year)
        rty = load_cross(CROSS_FILES["RTY"], year)

        for ev in by_year[year]:
            erows = {t: exact_es_row(es, ev, t) for t in ["08:30", "08:35", "09:00"]}
            if any(v is None for v in erows.values()):
                rows.append({"event_date": pd.Timestamp(ev), "year": year, "status": "missing_ES"})
                continue
            symbols = {erows[t]["symbol"] for t in erows}
            if len(symbols) != 1:
                rows.append({"event_date": pd.Timestamp(ev), "year": year, "status": "ES_contract_switch"})
                continue

            nq0 = exact_cross_open(nq, ev, "08:30")
            nq5 = exact_cross_open(nq, ev, "08:35")
            r0 = exact_cross_open(rty, ev, "08:30")
            r5 = exact_cross_open(rty, ev, "08:35")
            if any(x is None for x in [nq0, nq5, r0, r5]):
                rows.append({"event_date": pd.Timestamp(ev), "year": year, "status": "missing_cross"})
                continue

            es0 = erows["08:30"]["open"]
            es5 = erows["08:35"]["open"]
            es9 = erows["09:00"]["open"]
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
                    "es_symbol": erows["08:30"]["symbol"],
                    "es_0830": es0,
                    "es_0835": es5,
                    "es_0900": es9,
                    "nq_0830": nq0,
                    "nq_0835": nq5,
                    "rty_0830": r0,
                    "rty_0835": r5,
                    "es_shock_bps": es_shock,
                    "nq_shock_bps": nq_shock,
                    "rty_shock_bps": rty_shock,
                    "unanimous": unanimous,
                    "direction": direction,
                    "gross_pts": direction * (es9 - es5) if direction else 0.0,
                }
            )

    return pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)


def cost_points(product, slip_ticks):
    if product == "ES":
        return 5.0 / 50.0 + slip_ticks * TICK
    if product == "MES":
        return 1.50 / 5.0 + slip_ticks * TICK
    raise ValueError(product)


def max_drawdown(x):
    s = pd.Series(x, dtype=float).fillna(0.0)
    if len(s) == 0:
        return np.nan
    eq = s.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((eq - peak).min())


def bootstrap_prob_positive(x, n_resamples=10000):
    a = np.asarray(pd.Series(x, dtype=float).dropna(), dtype=float)
    if len(a) == 0:
        return np.nan
    rng = np.random.default_rng(SEED)
    positive = 0
    done = 0
    batch = 500
    while done < n_resamples:
        b = min(batch, n_resamples - done)
        idx = rng.integers(0, len(a), size=(b, len(a)))
        positive += int((a[idx].mean(axis=1) > 0).sum())
        done += b
    return positive / n_resamples


def metrics(df, years, product="ES", slip_ticks=1):
    z = df[(df.year.isin(years)) & (df.status == "OK") & (df.direction != 0)].copy()
    cp = cost_points(product, slip_ticks)
    pv = 50.0 if product == "ES" else 5.0
    if len(z) == 0:
        return {
            "years": f"{min(years)}-{max(years)}", "product": product, "slip_ticks": slip_ticks,
            "trades": 0, "win_pct": np.nan, "avg_gross_pts": np.nan, "avg_net_pts": np.nan,
            "avg_dollars": np.nan, "PF": np.nan, "total_dollars": np.nan, "DD_dollars": np.nan,
            "sharpe": np.nan, "bootstrap_prob_gt0": np.nan,
        }

    z["net_pts"] = z.gross_pts - cp
    z["net_dollars"] = z.net_pts * pv
    z["net_ret"] = z.net_pts / z.es_0835.astype(float)
    pos = float(z.loc[z.net_dollars > 0, "net_dollars"].sum())
    neg = float(z.loc[z.net_dollars <= 0, "net_dollars"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    sd = float(z.net_ret.std(ddof=1))
    sharpe = float(z.net_ret.mean() / sd * np.sqrt(12)) if len(z) > 1 and sd > 0 else np.nan
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
        "DD_dollars": max_drawdown(z.net_dollars),
        "sharpe": sharpe,
        "bootstrap_prob_gt0": float(bootstrap_prob_positive(z.net_ret)),
    }


def side_metrics(df):
    z = df[(df.year.isin(MODERN)) & (df.status == "OK") & (df.direction != 0)].copy()
    cp = cost_points("ES", 1)
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
    z = df[(df.year.isin(MODERN)) & (df.status == "OK") & (df.direction != 0)].copy()
    if len(z) <= 1:
        return {"drop_n": 1 if len(z) else 0, "drop_avg_net_pts": np.nan, "drop_PF": np.nan}
    cp = cost_points("ES", 1)
    z["net_pts"] = z.gross_pts - cp
    z["net_dollars"] = z.net_pts * 50.0
    z = z.sort_values("net_dollars", ascending=False).iloc[1:].copy()
    pos = float(z.loc[z.net_dollars > 0, "net_dollars"].sum())
    neg = float(z.loc[z.net_dollars <= 0, "net_dollars"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    return {"drop_n": 1, "drop_avg_net_pts": float(z.net_pts.mean()), "drop_PF": float(pf)}


def gate(df):
    primary = metrics(df, MODERN, "ES", 1)
    two = metrics(df, MODERN, "ES", 2)
    yr = pd.DataFrame([metrics(df, [y], "ES", 1) for y in MODERN])
    tail = tail_metrics(df)
    sides = side_metrics(df)

    positive_years = int((yr.total_dollars > 0).sum())
    pos = yr.loc[yr.total_dollars > 0, "total_dollars"]
    max_share = float(pos.max() / pos.sum()) if len(pos) and pos.sum() > 0 else np.inf
    long_avg = float(sides.loc[sides.side == "long", "avg_net_pts"].iloc[0])
    short_avg = float(sides.loc[sides.side == "short", "avg_net_pts"].iloc[0])

    checks = {
        "n_ge_20": primary["trades"] >= 20,
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
    print("=== ROUND 7 CPI EVENT STRATEGY ===")
    print("Frozen candidate R7CPI1: unanimous ES/NQ/RTY 08:30->08:35 shock continuation.")
    print("Entry 08:35 ET, exit 09:00 ET. One trade max per CPI release.")
    print("Official BLS calendars only. Years hard-frozen to 2018-2023; 2024-2026 are not loaded.")

    cal = fetch_cpi_calendar()
    events = build_events(cal)

    print("\nEVENT DATA AUDIT")
    print(events.groupby(["year", "status"]).size().to_string())
    ok = events[events.status == "OK"].copy()
    print("complete events:", len(ok), "of", len(events))
    print("unanimous-signal events by year:")
    print(ok.groupby("year").unanimous.sum().to_string())

    print("\nHISTORICAL CONTEXT 2018-2020 — ES +1 tick")
    h = metrics(events, HISTORICAL, "ES", 1)
    print(pd.DataFrame([h]).round(4).to_string(index=False))

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            rows.append(metrics(events, MODERN, product, slip))
    cs = pd.DataFrame(rows)

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    print(
        cs[["product", "slip_ticks", "trades", "win_pct", "avg_gross_pts", "avg_net_pts",
            "PF", "total_dollars", "DD_dollars", "sharpe", "bootstrap_prob_gt0"]]
        .round(4).to_string(index=False)
    )

    print("\nYEAR BY YEAR — PRIMARY ES +1 tick")
    yr = pd.DataFrame([metrics(events, [y], "ES", 1) for y in MODERN])
    print(
        yr[["years", "trades", "win_pct", "avg_net_pts", "PF", "total_dollars", "DD_dollars", "sharpe"]]
        .round(4).to_string(index=False)
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
    print("ROUND7_CPI_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R7CPI1 earns a separate protected 2024 CPI validation. Do not change its rules.")
    else:
        print("2024 stays protected. Retire exact R7CPI1; do not flip it to reversal using these results.")

    events.to_csv("round7_cpi_stage1_events.csv", index=False)
    cs.to_csv("round7_cpi_stage1_metrics.csv", index=False)
    yr.to_csv("round7_cpi_stage1_yearly.csv", index=False)
    sides.to_csv("round7_cpi_stage1_sides.csv", index=False)
    print("\nSaved Round-7 CPI CSV outputs.")


if __name__ == "__main__":
    main()
