import io
import requests
import numpy as np
import pandas as pd

BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEAR = 2024
TICK = 0.25
NY = "America/New_York"


def load_year(year=YEAR):
    r = requests.get(BASE.format(year), timeout=180)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df["datetime_et"] = pd.to_datetime(df["datetime_et"], utc=True).dt.tz_convert(NY)
    if "rth" in df.columns:
        df = df[df["rth"].astype(str).str.lower().eq("true")]
    keep = ["datetime_et", "open", "high", "low", "close", "volume", "symbol"]
    df = df[keep].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna().sort_values(["datetime_et", "symbol"])
    df["session"] = df.datetime_et.dt.date
    sym_per_session = df.groupby("session").symbol.nunique()
    roll_sessions = set(sym_per_session[sym_per_session > 1].index)
    if roll_sessions:
        print("excluding roll-switch sessions", year, len(roll_sessions), sorted(roll_sessions))
        df = df[~df.session.isin(roll_sessions)].copy()
    before = len(df)
    df = (df.sort_values(["datetime_et", "volume"], ascending=[True, False])
            .drop_duplicates("datetime_et", keep="first").sort_values("datetime_et"))
    print("loaded", year, "RTH rows", len(df), "sessions", df.session.nunique(),
          "duplicates_resolved", before - len(df))
    df = df.set_index("datetime_et")
    df["session"] = df.index.date
    return df


def rth_resample(d, minutes):
    r = d[["open", "high", "low", "close", "volume"]].resample(
        f"{minutes}min", origin="start_day", offset="30min", label="left", closed="left"
    ).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    r["end"] = r.index + pd.Timedelta(minutes=minutes)
    return r


def before(ts, hh, mm=0):
    return ts.hour * 60 + ts.minute < hh * 60 + mm


def simulate_1m(d, entry_time, entry, stop, target):
    risk = entry - stop
    if risk < TICK - 1e-12:
        return None
    z = d[d.index >= entry_time]
    if len(z) == 0:
        return None
    mfe = 0.0
    mae = 0.0
    for ts, r in z.iterrows():
        mfe = max(mfe, (float(r.high) - entry) / risk)
        mae = min(mae, (float(r.low) - entry) / risk)
        hit_s = float(r.low) <= stop
        hit_t = float(r.high) >= target
        if hit_s and hit_t:
            return -1.0, ts, "ambiguous_stop_first", mfe, mae
        if hit_s:
            return -1.0, ts, "stop", mfe, mae
        if hit_t:
            return (target - entry) / risk, ts, "target", mfe, mae
    ts = z.index[-1]
    px = float(z.iloc[-1].close)
    return (px - entry) / risk, ts, "eod", mfe, mae


def s1_for_session(d, sess):
    out = []
    orx = d[(d.index.time >= pd.Timestamp("09:30").time()) &
            (d.index.time < pd.Timestamp("09:45").time())]
    if len(orx) < 10:
        return out
    orh, orl = float(orx.high.max()), float(orx.low.min())
    b15 = rth_resample(d, 15)
    busy_until = None
    for _, b in b15.iterrows():
        end = b["end"]
        if end <= pd.Timestamp(f"{sess} 09:45", tz=NY):
            continue
        entry_time = end
        if not before(entry_time, 12, 0):
            continue
        if busy_until is not None and entry_time <= busy_until:
            continue
        if float(b.close) <= orh:
            continue
        entry_rows = d[d.index >= entry_time]
        if len(entry_rows) == 0:
            continue
        entry = float(entry_rows.iloc[0].open)
        stop = orl
        risk = entry - stop
        if risk < TICK:
            continue
        target = entry + 1.5 * risk
        sim = simulate_1m(d, entry_time, entry, stop, target)
        if sim is None:
            continue
        rr, exit_time, why, mfe, mae = sim
        out.append({
            "strategy": "S1", "session": pd.Timestamp(sess), "year": YEAR,
            "direction": "long", "signal_time": end, "entry_time": entry_time,
            "exit_time": exit_time, "entry": entry, "stop": stop, "target": target,
            "risk_pts": risk, "R": rr, "MFE_R": mfe, "MAE_R": mae,
            "exit_reason": why, "or_high": orh, "or_low": orl,
        })
        busy_until = exit_time
    return out


def net_r(t, product="ES", slip_ticks=1):
    point_value = 50.0 if product == "ES" else 5.0
    commission = 5.0 if product == "ES" else 1.50
    cost_pts = commission / point_value + slip_ticks * TICK
    return t.R.to_numpy(dtype=float) - cost_pts / t.risk_pts.to_numpy(dtype=float)


def stats(v):
    v = pd.Series(v, dtype=float).dropna().reset_index(drop=True)
    if len(v) == 0:
        return {"n": 0, "win": np.nan, "avgR": np.nan, "PF": np.nan,
                "totalR": np.nan, "DD": np.nan}
    w = v[v > 0]
    l = v[v <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and abs(l.sum()) > 0 else np.inf
    eq = v.cumsum()
    dd = eq - eq.cummax()
    return {"n": len(v), "win": 100 * (v > 0).mean(), "avgR": v.mean(),
            "PF": pf, "totalR": v.sum(), "DD": dd.min()}


def fmt(s):
    return {k: (round(v, 4) if isinstance(v, (float, np.floating)) else v) for k, v in s.items()}


def main():
    print("=== S1 FROZEN 2024 VALIDATION ===")
    print("Exact S1 implementation frozen after 2021-2023 Round 1. No tuning. 2025 remains unseen.")
    raw = load_year()
    trades = []
    for sess, d in raw.groupby("session", sort=False):
        trades.extend(s1_for_session(d.copy(), sess))
    t = pd.DataFrame(trades).sort_values(["entry_time", "exit_time"]).reset_index(drop=True)
    t.to_csv("s1_validation_2024_trades.csv", index=False)

    print("\nIMPLEMENTATION AUDIT")
    if len(t):
        by_day = t.groupby("session").size()
        overlap = 0
        for _, g in t.groupby("session"):
            g = g.sort_values("entry_time")
            prev_exit = None
            for _, r in g.iterrows():
                if prev_exit is not None and r.entry_time <= prev_exit:
                    overlap += 1
                prev_exit = r.exit_time
        print({
            "trades": len(t), "sessions_with_trade": int(t.session.nunique()),
            "max_trades_day": int(by_day.max()), "overlaps": overlap,
            "entries_at_or_after_noon": int(((pd.to_datetime(t.entry_time).dt.hour * 60 + pd.to_datetime(t.entry_time).dt.minute) >= 720).sum()),
            "median_risk_pts": round(float(t.risk_pts.median()), 4),
            "min_risk_pts": round(float(t.risk_pts.min()), 4),
            "max_risk_pts": round(float(t.risk_pts.max()), 4),
        })
        print("exit_reasons", t.exit_reason.value_counts().to_dict())
    else:
        print({"trades": 0})

    raw_stats = stats(t.R if len(t) else [])
    print("\nRAW", fmt(raw_stats))

    rows = []
    for product in ["ES", "MES"]:
        for slip in [0, 1, 2, 4]:
            s = stats(net_r(t, product, slip) if len(t) else [])
            rows.append({"product": product, "slip_ticks": slip, **s})
    costs = pd.DataFrame(rows)
    costs.to_csv("s1_validation_2024_costs.csv", index=False)
    print("\nCOST SENSITIVITY")
    print(costs.round(4).to_string(index=False))

    es1 = pd.Series(net_r(t, "ES", 1), index=t.index) if len(t) else pd.Series(dtype=float)
    base = stats(es1)
    print("\nPRIMARY ES 1-TICK", fmt(base))

    if len(es1):
        ranked = es1.sort_values(ascending=False)
        tail = {}
        for k in [1, 3, 5]:
            z = es1.drop(index=ranked.index[:min(k, len(ranked))])
            tail[f"drop{k}"] = fmt(stats(z))
        print("TAIL ROBUSTNESS", tail)
        gross_pos = es1[es1 > 0].sum()
        max_share = (es1.max() / gross_pos) if gross_pos > 0 else np.nan
        print("MAX_WINNER_GROSS_SHARE", round(float(max_share), 6))
    else:
        tail = {"drop5": {"avgR": np.nan, "PF": np.nan}}

    es4 = stats(net_r(t, "ES", 4) if len(t) else [])
    drop5 = tail.get("drop5", {})

    gate = bool(
        len(t) >= 100 and
        base["avgR"] > 0 and
        base["PF"] >= 1.10 and
        drop5.get("avgR", -np.inf) > 0 and
        es4["avgR"] > 0
    )
    print("\nFROZEN_2024_VALIDATION_GATE", gate)
    if gate:
        print("INTERPRETATION: S1 earns access to untouched 2025 holdout. Do not tune before 2025.")
    else:
        print("INTERPRETATION: S1 fails validation. Do not repair/tune using 2024.")


if __name__ == "__main__":
    main()
