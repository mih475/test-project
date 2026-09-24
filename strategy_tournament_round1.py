import io
import requests
import numpy as np
import pandas as pd

BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEARS = [2021, 2022, 2023]
TICK = 0.25
NY = "America/New_York"

STRATEGY_NAMES = {
    "S1": "15m ORB close-confirmation long-only",
    "S2": "15m ORB + 5m close + retest",
    "S3": "First-40m 9EMA continuation",
    "S4": "Post-10:30 VWAP 2SD confirmed reversion",
    "S5": "Initial-balance failed-break fade",
    "S6": "5m ORB + 1m FVG displacement",
}


def load_dev():
    parts = []
    for y in YEARS:
        r = requests.get(BASE.format(y), timeout=180)
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
            print("excluding roll-switch sessions", y, len(roll_sessions), sorted(roll_sessions))
            df = df[~df.session.isin(roll_sessions)].copy()
        before = len(df)
        df = (df.sort_values(["datetime_et", "volume"], ascending=[True, False])
                .drop_duplicates("datetime_et", keep="first").sort_values("datetime_et"))
        print("loaded", y, "RTH rows", len(df), "sessions", df.session.nunique(),
              "duplicates_resolved", before - len(df))
        parts.append(df)
    x = pd.concat(parts, ignore_index=True).sort_values(["datetime_et", "volume"], ascending=[True, False])
    x = x.drop_duplicates("datetime_et", keep="first").sort_values("datetime_et")
    x = x.set_index("datetime_et")
    x["session"] = x.index.date
    return x


def rth_resample(d, minutes):
    rule = f"{minutes}min"
    r = d[["open", "high", "low", "close", "volume"]].resample(
        rule, origin="start_day", offset="30min", label="left", closed="left"
    ).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    r["end"] = r.index + pd.Timedelta(minutes=minutes)
    return r


def session_vwap_bands(d):
    x = d.copy()
    tp = (x.high + x.low + x.close) / 3.0
    pv = tp * x.volume
    p2v = (tp ** 2) * x.volume
    cv = x.volume.cumsum()
    cpv = pv.cumsum()
    cp2v = p2v.cumsum()
    x["vwap"] = cpv / cv
    var = (cp2v / cv) - x.vwap ** 2
    x["sd"] = np.sqrt(var.clip(lower=0))
    x["u1"] = x.vwap + x.sd
    x["l1"] = x.vwap - x.sd
    x["u2"] = x.vwap + 2 * x.sd
    x["l2"] = x.vwap - 2 * x.sd
    return x


def tod(ts):
    return ts.hour * 60 + ts.minute


def at_or_after(ts, hh, mm=0):
    return tod(ts) >= hh * 60 + mm


def before(ts, hh, mm=0):
    return tod(ts) < hh * 60 + mm


def simulate_1m(d, entry_time, entry, direction, stop, target):
    risk = (entry - stop) if direction == 1 else (stop - entry)
    if risk < TICK - 1e-12:
        return None
    z = d[d.index >= entry_time]
    if len(z) == 0:
        return None
    mfe = 0.0
    mae = 0.0
    for ts, r in z.iterrows():
        if direction == 1:
            mfe = max(mfe, (r.high - entry) / risk)
            mae = min(mae, (r.low - entry) / risk)
            hit_s = r.low <= stop
            hit_t = r.high >= target
        else:
            mfe = max(mfe, (entry - r.low) / risk)
            mae = min(mae, (entry - r.high) / risk)
            hit_s = r.high >= stop
            hit_t = r.low <= target
        if hit_s and hit_t:
            return -1.0, ts, "ambiguous_stop_first", mfe, mae
        if hit_s:
            return -1.0, ts, "stop", mfe, mae
        if hit_t:
            rr = ((target - entry) / risk) if direction == 1 else ((entry - target) / risk)
            return rr, ts, "target", mfe, mae
    ts = z.index[-1]
    px = float(z.iloc[-1].close)
    rr = ((px - entry) / risk) if direction == 1 else ((entry - px) / risk)
    return rr, ts, "eod", mfe, mae


def add_trade(out, sid, sess, direction, signal_time, entry_time, entry, stop, target, sim, note=""):
    rr, exit_time, why, mfe, mae = sim
    out.append({
        "strategy": sid,
        "strategy_name": STRATEGY_NAMES[sid],
        "session": pd.Timestamp(sess),
        "year": pd.Timestamp(sess).year,
        "direction": "long" if direction == 1 else "short",
        "signal_time": signal_time,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry": float(entry),
        "stop": float(stop),
        "target": float(target),
        "risk_pts": abs(float(entry) - float(stop)),
        "R": float(rr),
        "MFE_R": float(mfe),
        "MAE_R": float(mae),
        "exit_reason": why,
        "note": note,
    })


def s1(d, sess):
    out = []
    orx = d[(d.index.time >= pd.Timestamp("09:30").time()) & (d.index.time < pd.Timestamp("09:45").time())]
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
        sim = simulate_1m(d, entry_time, entry, 1, stop, target)
        if sim:
            add_trade(out, "S1", sess, 1, end, entry_time, entry, stop, target, sim)
            busy_until = sim[1]
    return out


def s2(d, sess):
    out = []
    orx = d[(d.index.time >= pd.Timestamp("09:30").time()) & (d.index.time < pd.Timestamp("09:45").time())]
    if len(orx) < 10:
        return out
    orh, orl = float(orx.high.max()), float(orx.low.min())
    b5 = rth_resample(d, 5)
    breakout = None
    for ts, b in b5.iterrows():
        end = b["end"]
        if end <= pd.Timestamp(f"{sess} 09:45", tz=NY):
            continue
        if not before(end, 12, 0):
            break
        if float(b.close) > orh:
            breakout = (1, ts, end, b)
            break
        if float(b.close) < orl:
            breakout = (-1, ts, end, b)
            break
    if breakout is None:
        return out
    direction, _, bend, bb = breakout
    boundary = orh if direction == 1 else orl
    stop = float(bb.low) - TICK if direction == 1 else float(bb.high) + TICK
    risk = boundary - stop if direction == 1 else stop - boundary
    if risk < TICK:
        return out
    for ts, b in b5[b5.index >= bend].iterrows():
        end = b["end"]
        if tod(ts) >= 12 * 60:
            break
        mins = d[(d.index >= ts) & (d.index < end)]
        touched = mins[(mins.low <= boundary) & (mins.high >= boundary)]
        if len(touched):
            entry_time = touched.index[0]
            target = boundary + direction * 2.0 * risk
            sim = simulate_1m(d, entry_time, boundary, direction, stop, target)
            if sim:
                add_trade(out, "S2", sess, direction, bend, entry_time, boundary, stop, target, sim)
            return out
        invalid = (direction == 1 and float(b.close) < orl) or (direction == -1 and float(b.close) > orh)
        if invalid:
            return out
    return out


def simulate_s3_2m(b2, entry_bar_pos, entry, direction, stop, ref_low, ref_high):
    risk = (entry - stop) if direction == 1 else (stop - entry)
    if risk < TICK:
        return None
    be_active = False
    pending_be = False
    mfe = 0.0
    mae = 0.0
    target = entry + direction * 2.0 * risk
    for j in range(entry_bar_pos, len(b2)):
        ts = b2.index[j]
        r = b2.iloc[j]
        if pending_be:
            be_active = True
            pending_be = False
        cur_stop = entry if be_active else stop
        if direction == 1:
            mfe = max(mfe, (r.high - entry) / risk)
            mae = min(mae, (r.low - entry) / risk)
            hit_s = r.low <= cur_stop
            hit_t = r.high >= target
        else:
            mfe = max(mfe, (entry - r.low) / risk)
            mae = min(mae, (entry - r.high) / risk)
            hit_s = r.high >= cur_stop
            hit_t = r.low <= target
        if hit_s and hit_t:
            rr = 0.0 if be_active else -1.0
            return rr, ts, "breakeven" if be_active else "ambiguous_stop_first", mfe, mae
        if hit_s:
            rr = 0.0 if be_active else -1.0
            return rr, ts, "breakeven" if be_active else "stop", mfe, mae
        if hit_t:
            return 2.0, ts, "target", mfe, mae
        if not be_active:
            inside = float(r.close) > ref_low and float(r.close) < ref_high
            if inside:
                rr = ((float(r.close) - entry) / risk) if direction == 1 else ((entry - float(r.close)) / risk)
                return rr, ts, "inside_range_close", mfe, mae
        if mfe >= 0.85 and not be_active:
            pending_be = True
    ts = b2.index[-1]
    px = float(b2.iloc[-1].close)
    rr = ((px - entry) / risk) if direction == 1 else ((entry - px) / risk)
    return rr, ts, "eod", mfe, mae


def s3(d, sess):
    out = []
    b2 = rth_resample(d, 2)
    b2["ema9"] = b2.close.ewm(span=9, adjust=False).mean()
    busy_until = None
    i = 1
    cutoff = pd.Timestamp(f"{sess} 10:10", tz=NY)
    while i < len(b2) - 1:
        ts = b2.index[i]
        end = b2.iloc[i]["end"]
        if end > cutoff:
            break
        if busy_until is not None and ts <= busy_until:
            i += 1
            continue
        r = b2.iloc[i]
        prev = b2.iloc[i - 1]
        dirn = 0
        if float(r.close) < float(prev.close) and float(r.close) < float(r.ema9):
            dirn = -1
        elif float(r.close) > float(prev.close) and float(r.close) > float(r.ema9):
            dirn = 1
        if dirn == 0:
            i += 1
            continue
        j = i + 1
        while j < len(b2):
            jr = b2.iloc[j]
            if jr["end"] > cutoff:
                break
            opposite_color = ((dirn == -1 and float(jr.close) > float(jr.open)) or
                              (dirn == 1 and float(jr.close) < float(jr.open)))
            if opposite_color:
                break
            j += 1
        if j >= len(b2) or b2.iloc[j]["end"] > cutoff:
            break
        ref = b2.iloc[j]
        entry = float(ref.low) - TICK if dirn == -1 else float(ref.high) + TICK
        stop = float(ref.high) + TICK if dirn == -1 else float(ref.low) - TICK
        risk = abs(entry - stop)
        if risk < TICK:
            i = j + 1
            continue
        k = j + 1
        if k >= len(b2) or b2.iloc[k]["end"] > cutoff:
            break
        order_bar = b2.iloc[k]
        triggered = ((dirn == -1 and float(order_bar.low) <= entry) or
                     (dirn == 1 and float(order_bar.high) >= entry))
        if not triggered:
            i = k + 1
            continue
        target = entry + dirn * 2 * risk
        sim = simulate_s3_2m(b2, k, entry, dirn, stop, float(ref.low), float(ref.high))
        if sim:
            add_trade(out, "S3", sess, dirn, ref["end"], b2.index[k], entry, stop, target, sim)
            busy_until = sim[1]
        i = k + 1
    return out


def s4(d, sess):
    out = []
    x = session_vwap_bands(d)
    setup = None
    busy_until = None
    for i in range(len(x) - 1):
        ts = x.index[i]
        r = x.iloc[i]
        if not at_or_after(ts, 10, 30):
            continue
        if busy_until is not None and ts <= busy_until:
            continue
        if setup is None:
            if np.isfinite(r.l2) and float(r.low) <= float(r.l2):
                setup = {"dir": 1, "extreme": float(r.low)}
            elif np.isfinite(r.u2) and float(r.high) >= float(r.u2):
                setup = {"dir": -1, "extreme": float(r.high)}
            continue
        dirn = setup["dir"]
        if dirn == 1 and np.isfinite(r.l2) and float(r.low) <= float(r.l2):
            setup["extreme"] = min(setup["extreme"], float(r.low))
        if dirn == -1 and np.isfinite(r.u2) and float(r.high) >= float(r.u2):
            setup["extreme"] = max(setup["extreme"], float(r.high))
        confirm = ((dirn == 1 and float(r.open) > float(r.l1) and float(r.open) < float(r.vwap)
                    and float(r.close) > float(r.l1) and float(r.close) < float(r.vwap)) or
                   (dirn == -1 and float(r.open) > float(r.vwap) and float(r.open) < float(r.u1)
                    and float(r.close) > float(r.vwap) and float(r.close) < float(r.u1)))
        if not confirm:
            continue
        entry_time = x.index[i + 1]
        if tod(entry_time) > 15 * 60 + 30:
            setup = None
            continue
        entry = float(x.iloc[i + 1].open)
        stop = setup["extreme"] - TICK if dirn == 1 else setup["extreme"] + TICK
        target = float(r.vwap)
        risk = (entry - stop) if dirn == 1 else (stop - entry)
        favorable = (dirn == 1 and target > entry) or (dirn == -1 and target < entry)
        if risk < TICK or not favorable:
            setup = None
            continue
        sim = simulate_1m(d, entry_time, entry, dirn, stop, target)
        if sim:
            add_trade(out, "S4", sess, dirn, ts, entry_time, entry, stop, target, sim)
            busy_until = sim[1]
        setup = None
    return out


def s5(d, sess):
    out = []
    ib = d[(d.index.time >= pd.Timestamp("09:30").time()) & (d.index.time < pd.Timestamp("10:30").time())]
    if len(ib) < 40:
        return out
    ibh, ibl = float(ib.high.max()), float(ib.low.min())
    x = session_vwap_bands(d)
    b5 = rth_resample(d, 5)
    state = None
    extreme = None
    for ts, b in b5.iterrows():
        end = b["end"]
        if end <= pd.Timestamp(f"{sess} 10:30", tz=NY):
            continue
        if not before(end, 14, 0):
            break
        mins = d[(d.index >= ts) & (d.index < end)]
        if len(mins) == 0:
            continue
        if state is None:
            up = mins[mins.high >= ibh + TICK]
            dn = mins[mins.low <= ibl - TICK]
            if len(up) == 0 and len(dn) == 0:
                continue
            if len(up) > 0 and (len(dn) == 0 or up.index[0] <= dn.index[0]):
                state = 1
                extreme = float(mins.loc[mins.index >= up.index[0]].high.max())
            else:
                state = -1
                extreme = float(mins.loc[mins.index >= dn.index[0]].low.min())
        else:
            extreme = max(extreme, float(mins.high.max())) if state == 1 else min(extreme, float(mins.low.min()))
        failure = (state == 1 and float(b.close) < ibh) or (state == -1 and float(b.close) > ibl)
        if not failure:
            continue
        dirn = -1 if state == 1 else 1
        entry_time = end
        entry_rows = d[d.index >= entry_time]
        if len(entry_rows) == 0:
            return out
        entry = float(entry_rows.iloc[0].open)
        stop = extreme + TICK if dirn == -1 else extreme - TICK
        vwap_rows = x[x.index < end]
        if len(vwap_rows) == 0:
            return out
        target = float(vwap_rows.iloc[-1].vwap)
        risk = (stop - entry) if dirn == -1 else (entry - stop)
        favorable = (dirn == 1 and target > entry) or (dirn == -1 and target < entry)
        if risk < TICK or not favorable:
            return out
        sim = simulate_1m(d, entry_time, entry, dirn, stop, target)
        if sim:
            add_trade(out, "S5", sess, dirn, end, entry_time, entry, stop, target, sim)
        return out
    return out


def s6(d, sess):
    out = []
    orx = d[(d.index.time >= pd.Timestamp("09:30").time()) & (d.index.time < pd.Timestamp("09:35").time())]
    if len(orx) < 4:
        return out
    orh, orl = float(orx.high.max()), float(orx.low.min())
    busy_until = None
    first_result = None
    trades_taken = 0
    for i in range(2, len(d) - 1):
        t3 = d.index[i]
        close_time = t3 + pd.Timedelta(minutes=1)
        if close_time <= pd.Timestamp(f"{sess} 09:35", tz=NY):
            continue
        entry_time = d.index[i + 1]
        if not before(entry_time, 12, 0):
            break
        if busy_until is not None and entry_time <= busy_until:
            continue
        if trades_taken >= 2:
            break
        if trades_taken == 1 and first_result is not None and first_result > 0:
            break
        c1 = d.iloc[i - 2]
        c3 = d.iloc[i]
        dirn = 0
        if float(c3.close) > orh and float(c3.low) > float(c1.high):
            dirn = 1
        elif float(c3.close) < orl and float(c3.high) < float(c1.low):
            dirn = -1
        if dirn == 0:
            continue
        entry = float(d.iloc[i + 1].open)
        stop = float(c1.high) - TICK if dirn == 1 else float(c1.low) + TICK
        risk = (entry - stop) if dirn == 1 else (stop - entry)
        if risk < TICK:
            continue
        multiple = 2.0 if risk <= 40.0 else 1.5
        target = entry + dirn * multiple * risk
        sim = simulate_1m(d, entry_time, entry, dirn, stop, target)
        if sim:
            add_trade(out, "S6", sess, dirn, close_time, entry_time, entry, stop, target, sim)
            trades_taken += 1
            if trades_taken == 1:
                first_result = sim[0]
            busy_until = sim[1]
    return out


def net_r(t, product="ES", slip_ticks=1):
    if len(t) == 0:
        return pd.Series(dtype=float)
    point = 50.0 if product == "ES" else 5.0
    commission = 5.0 if product == "ES" else 1.50
    cost_pts = slip_ticks * TICK + commission / point
    return t.R.astype(float) - cost_pts / t.risk_pts.astype(float)


def stats_from_r(v):
    v = pd.Series(v, dtype=float).dropna()
    if len(v) == 0:
        return {"n": 0, "win_pct": np.nan, "avgR": np.nan, "PF": np.nan, "totalR": 0.0, "maxDD_R": np.nan}
    wins = v[v > 0]
    losses = v[v <= 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) and abs(losses.sum()) > 0 else np.inf
    eq = v.cumsum()
    dd = eq - eq.cummax()
    return {"n": len(v), "win_pct": 100 * (v > 0).mean(), "avgR": v.mean(), "PF": pf,
            "totalR": v.sum(), "maxDD_R": dd.min()}


def evaluate(t):
    rows = []
    for sid, g in t.groupby("strategy"):
        raw = stats_from_r(g.R)
        base = stats_from_r(net_r(g, "ES", 1))
        byyear = {}
        positive_years = 0
        floor_pf = np.inf
        all_years_represented = True
        for y in YEARS:
            gy = g[g.year == y]
            st = stats_from_r(net_r(gy, "ES", 1))
            byyear[y] = st
            if st["n"] == 0:
                all_years_represented = False
            else:
                floor_pf = min(floor_pf, st["PF"])
            if st["totalR"] > 0:
                positive_years += 1
        if sid in {"S2", "S5"}:
            sample_gate = len(g) >= 75 and all_years_represented
        else:
            sample_gate = len(g) >= 100
        nv = net_r(g, "ES", 1).sort_values(ascending=False)
        drop5 = stats_from_r(nv.iloc[min(5, len(nv)):])
        rawwins = g[g.R > 0].R
        max_share = (rawwins.max() / rawwins.sum()) if len(rawwins) and rawwins.sum() > 0 else np.inf
        slip0 = stats_from_r(net_r(g, "ES", 0))
        slip2 = stats_from_r(net_r(g, "ES", 2))
        slip4 = stats_from_r(net_r(g, "ES", 4))
        mes1 = stats_from_r(net_r(g, "MES", 1))
        survive = (sample_gate and base["avgR"] > 0 and base["PF"] >= 1.10 and positive_years >= 2
                   and (drop5["avgR"] > 0 or drop5["PF"] >= 1.05) and max_share <= 0.20)
        row = {
            "strategy": sid, "name": STRATEGY_NAMES[sid], "n": len(g),
            "raw_win": raw["win_pct"], "raw_avgR": raw["avgR"], "raw_PF": raw["PF"],
            "net_win": base["win_pct"], "net_avgR": base["avgR"], "net_PF": base["PF"],
            "net_totalR": base["totalR"], "net_DD": base["maxDD_R"],
            "positive_years": positive_years, "floor_year_PF": floor_pf,
            "drop5_avgR": drop5["avgR"], "drop5_PF": drop5["PF"],
            "max_winner_gross_share": max_share,
            "ES0_avgR": slip0["avgR"], "ES2_avgR": slip2["avgR"], "ES4_avgR": slip4["avgR"],
            "MES1_avgR": mes1["avgR"], "MES1_PF": mes1["PF"],
            "survivor": survive,
        }
        for y in YEARS:
            row[f"{y}_n"] = byyear[y]["n"]
            row[f"{y}_avgR"] = byyear[y]["avgR"]
            row[f"{y}_PF"] = byyear[y]["PF"]
            row[f"{y}_totalR"] = byyear[y]["totalR"]
        rows.append(row)
    board = pd.DataFrame(rows)
    metrics = ["floor_year_PF", "net_avgR", "net_DD", "n", "ES4_avgR", "drop5_avgR"]
    rankcols = []
    for col in metrics:
        rc = f"_rank_{col}"
        board[rc] = board[col].rank(pct=True, ascending=True) * 100
        rankcols.append(rc)
    board["robustness_score"] = board[rankcols].mean(axis=1)
    board = board.sort_values(["survivor", "robustness_score", "net_PF"], ascending=[False, False, False]).reset_index(drop=True)
    return board


def main():
    print("=== STRATEGY TOURNAMENT ROUND 1 ===")
    print("Frozen development only: 2021-2023. 2024+ are not loaded.")
    raw = load_dev()
    print("DEV rows", len(raw), "sessions", raw.session.nunique(), "start", raw.index.min(), "end", raw.index.max())
    all_trades = []
    for sess, d in raw.groupby("session", sort=True):
        d = d.copy()
        for fn in (s1, s2, s3, s4, s5, s6):
            try:
                all_trades.extend(fn(d, sess))
            except Exception as exc:
                raise RuntimeError(f"{fn.__name__} failed on {sess}: {exc}") from exc
    t = pd.DataFrame(all_trades)
    if len(t) == 0:
        raise SystemExit("No trades generated; implementation failure.")
    missing = set(STRATEGY_NAMES) - set(t.strategy.unique())
    if missing:
        print("WARNING strategies with zero trades:", sorted(missing))
    t = t.sort_values(["strategy", "entry_time"]).reset_index(drop=True)
    t.to_csv("strategy_tournament_round1_trades.csv", index=False)
    board = evaluate(t)
    board.to_csv("strategy_tournament_round1_leaderboard.csv", index=False)

    pd.set_option("display.max_columns", 100)
    print("\nLEADERBOARD -- ES $5 RT + 1 TICK TOTAL ADVERSE SLIPPAGE")
    cols = ["strategy", "n", "net_win", "net_avgR", "net_PF", "net_totalR", "net_DD", "positive_years",
            "floor_year_PF", "drop5_avgR", "drop5_PF", "max_winner_gross_share", "ES4_avgR", "MES1_avgR",
            "robustness_score", "survivor"]
    print(board[cols].round(4).to_string(index=False))

    print("\nYEAR BY YEAR -- ES 1 TICK")
    ycols = ["strategy"]
    for y in YEARS:
        ycols += [f"{y}_n", f"{y}_avgR", f"{y}_PF", f"{y}_totalR"]
    print(board[ycols].round(4).to_string(index=False))

    print("\nCOST SENSITIVITY SUMMARY")
    print(board[["strategy", "ES0_avgR", "net_avgR", "ES2_avgR", "ES4_avgR", "MES1_avgR", "MES1_PF"]].round(4).to_string(index=False))

    survivors = board[board.survivor]
    print("\nROUND1_SURVIVORS", survivors.strategy.tolist())
    if len(survivors) == 0:
        print("INTERPRETATION: no strategy clears the pre-frozen gate. Do not reveal 2024.")
    else:
        print("INTERPRETATION: freeze surviving implementations before any 2024 validation.")


if __name__ == "__main__":
    main()
