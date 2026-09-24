import io
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ES_BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEARS = list(range(2017, 2024))
MODERN = [2021, 2022, 2023]
NY = "America/New_York"
CROSS_DIR = Path("round4_crossmarket_data")
TRAIN_SESSIONS = 60
Z_ENTRY = 2.0
MAX_TRADES_PER_DAY = 2
MAX_HOLD_MIN = 30
PRIMARY_FRICTION_BPS = 1.0
SEED = 20260924

SIGNAL_START = 10 * 60
SIGNAL_END = 15 * 60
HARD_EXIT = 15 * 60 + 30
RETURN_LAST_SLOT = 15 * 60 + 25
GRID_START = 9 * 60 + 30
GRID_END = 15 * 60 + 30
EXPECTED_SLOTS = list(range(GRID_START, GRID_END + 1, 5))


def minute_of_day(s):
    return s.dt.hour * 60 + s.dt.minute


def load_es_minutes():
    parts = []
    for year in YEARS:
        r = requests.get(ES_BASE.format(year), timeout=240)
        r.raise_for_status()
        d = pd.read_csv(io.StringIO(r.text))
        d["datetime_et"] = pd.to_datetime(d["datetime_et"], utc=True).dt.tz_convert(NY)
        for c in ["open", "high", "low", "close", "volume"]:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d = d.dropna(subset=["datetime_et", "open", "close", "symbol"]).copy()
        d["rth_bool"] = d["rth"].astype(str).str.lower().eq("true")
        d = d[d.rth_bool].copy()
        d["session"] = d.datetime_et.dt.date
        ns = d.groupby("session").symbol.nunique()
        bad = set(ns[ns > 1].index)
        if bad:
            print("excluding ES roll-switch sessions", year, len(bad), sorted(bad))
        d = d[~d.session.isin(bad)].copy()
        d = (
            d.sort_values(["datetime_et", "volume"], ascending=[True, False])
            .drop_duplicates("datetime_et", keep="first")
            .sort_values("datetime_et")
        )
        print("loaded ES", year, "RTH rows", len(d), "sessions", d.session.nunique())
        parts.append(d[["datetime_et", "session", "open", "close", "symbol"]])
    return pd.concat(parts, ignore_index=True).sort_values("datetime_et")


def load_cross_minutes(prefix):
    parts = []
    id_col = None
    for year in YEARS:
        p = CROSS_DIR / f"{prefix}_{year}.csv.gz"
        if not p.exists() or p.stat().st_size == 0:
            continue
        z = pd.read_csv(p, compression="gzip")
        ts_col = "ts_event" if "ts_event" in z.columns else None
        if ts_col is None:
            candidates = [c for c in z.columns if "time" in c.lower() or c.lower() == "index"]
            if not candidates:
                raise ValueError(f"Cannot identify timestamp column in {p}: {list(z.columns)}")
            ts_col = candidates[0]
        z["datetime_et"] = pd.to_datetime(z[ts_col], utc=True).dt.tz_convert(NY)
        for c in ["open", "close"]:
            z[c] = pd.to_numeric(z[c], errors="coerce")
        z = z.dropna(subset=["datetime_et", "open", "close"]).copy()
        for candidate in ["instrument_id", "symbol"]:
            if candidate in z.columns:
                id_col = candidate
                break
        keep = ["datetime_et", "open", "close"] + ([id_col] if id_col else [])
        parts.append(z[keep])
        print("loaded", prefix, year, "rows", len(z))
    if not parts:
        raise FileNotFoundError(f"No files found for {prefix} in {CROSS_DIR}")
    d = pd.concat(parts, ignore_index=True).sort_values("datetime_et")
    d = d.drop_duplicates("datetime_et", keep="last")
    d["session"] = d.datetime_et.dt.date
    if id_col:
        mod = minute_of_day(d.datetime_et)
        rth = d[(mod >= GRID_START) & (mod <= GRID_END + 4)].copy()
        nids = rth.groupby("session")[id_col].nunique(dropna=True)
        bad = set(nids[nids > 1].index)
        if bad:
            print("excluding", prefix, "identifier-switch sessions", len(bad))
            d = d[~d.session.isin(bad)].copy()
    return d[["datetime_et", "session", "open", "close"]]


def build_5m(minutes, prefix):
    d = minutes.copy()
    d["mod"] = minute_of_day(d.datetime_et)
    d = d[(d["mod"] >= GRID_START) & (d["mod"] <= GRID_END + 4)].copy()
    d["slot"] = (d["mod"] // 5) * 5
    d = d[(d.slot >= GRID_START) & (d.slot <= GRID_END)].copy()
    d = d.sort_values("datetime_et")

    rows = []
    for (sess, slot), g in d.groupby(["session", "slot"], sort=True):
        g = g.sort_values("datetime_et")
        expected = 5 if slot <= RETURN_LAST_SLOT else 1
        if len(g) < expected:
            continue
        if slot <= RETURN_LAST_SLOT:
            gg = g.iloc[:5]
            o = float(gg.iloc[0].open)
            c = float(gg.iloc[-1].close)
            ret = math.log(c / o) if o > 0 and c > 0 else np.nan
        else:
            o = float(g.iloc[0].open)
            ret = np.nan
        rows.append({
            "session": pd.Timestamp(sess),
            "slot": int(slot),
            f"open_{prefix}": o,
            f"ret_{prefix}": ret,
        })
    return pd.DataFrame(rows)


def build_panel():
    es = build_5m(load_es_minutes(), "es")
    nq = build_5m(load_cross_minutes("NQ_v_0"), "nq")
    rty = build_5m(load_cross_minutes("RTY_v_0"), "rty")
    p = es.merge(nq, on=["session", "slot"], how="inner").merge(rty, on=["session", "slot"], how="inner")
    p["year"] = p.session.dt.year
    p = p[p.year.isin(YEARS)].copy()

    complete = []
    for sess, g in p.groupby("session", sort=True):
        slots = sorted(g.slot.astype(int).unique().tolist())
        if slots != EXPECTED_SLOTS:
            continue
        q = g[g.slot <= RETURN_LAST_SLOT]
        cols = ["ret_es", "ret_nq", "ret_rty", "open_es", "open_nq", "open_rty"]
        if not np.isfinite(q[cols].to_numpy(dtype=float)).all():
            continue
        e = g[g.slot == GRID_END]
        if len(e) != 1 or not np.isfinite(e[["open_es", "open_nq", "open_rty"]].to_numpy(dtype=float)).all():
            continue
        complete.append(pd.Timestamp(sess))
    p["complete_session"] = p.session.isin(set(complete))
    print("aligned complete sessions:", len(complete))
    print("complete by year:")
    cs = pd.Series(complete)
    if len(cs):
        print(cs.dt.year.value_counts().sort_index().to_string())
    return p, sorted(complete)


def fit_daily_model(train):
    q = train[train.slot <= RETURN_LAST_SLOT].copy()
    X = q[["ret_nq", "ret_rty"]].to_numpy(dtype=float)
    y = q.ret_es.to_numpy(dtype=float)
    ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X = X[ok]
    y = y[ok]
    A = np.column_stack([np.ones(len(X)), X])
    beta = np.linalg.pinv(A) @ y
    return float(beta[0]), float(beta[1]), float(beta[2])


def slot_stats(train, alpha, b_nq, b_rty):
    q = train[train.slot <= RETURN_LAST_SLOT].copy()
    q["resid"] = q.ret_es - (alpha + b_nq * q.ret_nq + b_rty * q.ret_rty)
    stats = {}
    for slot, g in q.groupby("slot"):
        vals = g.resid.to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        if len(vals) < 40:
            continue
        sd = float(np.std(vals, ddof=1))
        if not np.isfinite(sd) or sd <= 0:
            continue
        stats[int(slot)] = (float(np.mean(vals)), sd, len(vals))
    return stats


def price_at(day, slot, col):
    z = day[day.slot == slot]
    if len(z) != 1:
        return np.nan
    return float(z.iloc[0][col])


def make_trade(day, zmap, signal_slot, alpha, b_nq, b_rty):
    z0 = zmap.get(signal_slot, np.nan)
    if not np.isfinite(z0) or abs(z0) < Z_ENTRY:
        return None
    entry_slot = signal_slot + 5
    if entry_slot > HARD_EXIT:
        return None
    s = -1 if z0 > 0 else 1
    max_exit = min(entry_slot + MAX_HOLD_MIN, HARD_EXIT)
    exit_slot = max_exit
    exit_reason = "max_hold" if max_exit < HARD_EXIT else "hard_exit"

    t = entry_slot
    while t <= min(RETURN_LAST_SLOT, max_exit - 5):
        zt = zmap.get(t, np.nan)
        crossed = np.isfinite(zt) and ((z0 > 0 and zt <= 0) or (z0 < 0 and zt >= 0))
        if crossed:
            exit_slot = t + 5
            exit_reason = "zero_cross"
            break
        t += 5

    pe0 = price_at(day, entry_slot, "open_es")
    pn0 = price_at(day, entry_slot, "open_nq")
    pr0 = price_at(day, entry_slot, "open_rty")
    pe1 = price_at(day, exit_slot, "open_es")
    pn1 = price_at(day, exit_slot, "open_nq")
    pr1 = price_at(day, exit_slot, "open_rty")
    px = [pe0, pn0, pr0, pe1, pn1, pr1]
    if not np.isfinite(px).all() or min(px) <= 0:
        return None

    spread_lr = s * (
        math.log(pe1 / pe0)
        - b_nq * math.log(pn1 / pn0)
        - b_rty * math.log(pr1 / pr0)
    )
    gross_exposure = 1.0 + abs(b_nq) + abs(b_rty)
    gross_bps = 10000.0 * spread_lr / gross_exposure
    return {
        "session": day.iloc[0].session,
        "year": int(day.iloc[0].year),
        "signal_slot": int(signal_slot),
        "entry_slot": int(entry_slot),
        "exit_slot": int(exit_slot),
        "hold_min": int(exit_slot - entry_slot),
        "side": "long_residual" if s == 1 else "short_residual",
        "direction": int(s),
        "entry_z": float(z0),
        "alpha": float(alpha),
        "beta_nq": float(b_nq),
        "beta_rty": float(b_rty),
        "gross_exposure": float(gross_exposure),
        "gross_bps": float(gross_bps),
        "exit_reason": exit_reason,
    }


def generate_trades(panel, complete_sessions):
    trades = []
    fit_rows = []
    eligible_sessions = []
    complete_panel = panel[panel.complete_session].copy()

    for pos, sess in enumerate(complete_sessions):
        if pos < TRAIN_SESSIONS:
            continue
        prior_sessions = complete_sessions[pos - TRAIN_SESSIONS:pos]
        train = complete_panel[complete_panel.session.isin(prior_sessions)].copy()
        if train.session.nunique() != TRAIN_SESSIONS:
            continue
        day = complete_panel[complete_panel.session == sess].sort_values("slot").copy()
        alpha, b_nq, b_rty = fit_daily_model(train)
        stats = slot_stats(train, alpha, b_nq, b_rty)
        day["resid"] = day.ret_es - (alpha + b_nq * day.ret_nq + b_rty * day.ret_rty)
        zmap = {}
        for _, r in day[day.slot <= RETURN_LAST_SLOT].iterrows():
            slot = int(r.slot)
            if slot not in stats or not np.isfinite(r.resid):
                continue
            mu, sd, _ = stats[slot]
            zmap[slot] = float((r.resid - mu) / sd)

        required = [s for s in range(SIGNAL_START, SIGNAL_END + 1, 5)]
        if not all(s in zmap for s in required):
            continue
        eligible_sessions.append(sess)
        fit_rows.append({
            "session": sess,
            "alpha": alpha,
            "beta_nq": b_nq,
            "beta_rty": b_rty,
            "train_sessions": TRAIN_SESSIONS,
        })

        trades_today = 0
        slot = SIGNAL_START
        while slot <= SIGNAL_END and trades_today < MAX_TRADES_PER_DAY:
            tr = make_trade(day, zmap, slot, alpha, b_nq, b_rty)
            if tr is None:
                slot += 5
                continue
            trades.append(tr)
            trades_today += 1
            slot = max(slot + 5, int(tr["exit_slot"]))

    return pd.DataFrame(trades), pd.DataFrame(fit_rows), eligible_sessions


def max_drawdown(vals):
    s = pd.Series(vals, dtype=float).fillna(0.0)
    if len(s) == 0:
        return np.nan
    eq = s.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((eq - peak).min())


def bootstrap_prob_positive_daily(vals, n_resamples=10000):
    x = np.asarray(pd.Series(vals, dtype=float).dropna(), dtype=float)
    if len(x) == 0:
        return np.nan
    rng = np.random.default_rng(SEED)
    positive = 0
    done = 0
    batch = 500
    while done < n_resamples:
        b = min(batch, n_resamples - done)
        idx = rng.integers(0, len(x), size=(b, len(x)))
        positive += int((x[idx].mean(axis=1) > 0).sum())
        done += b
    return positive / n_resamples


def metrics(trades, eligible_sessions, years, friction_bps=PRIMARY_FRICTION_BPS, side=None):
    g = trades[trades.year.isin(years)].copy()
    if side is not None:
        g = g[g.side == side].copy()
    g["net_bps"] = g.gross_bps - float(friction_bps)
    n = len(g)
    if n:
        wins = float((g.net_bps > 0).mean() * 100)
        pos = float(g.loc[g.net_bps > 0, "net_bps"].sum())
        neg = float(g.loc[g.net_bps <= 0, "net_bps"].sum())
        pf = pos / abs(neg) if neg < 0 else np.inf
        avg_gross = float(g.gross_bps.mean())
        avg_net = float(g.net_bps.mean())
        total = float(g.net_bps.sum())
        dd = max_drawdown(g.net_bps)
        med_hold = float(g.hold_min.median())
        avg_hold = float(g.hold_min.mean())
    else:
        wins = pf = avg_gross = avg_net = total = dd = med_hold = avg_hold = np.nan

    elig = [pd.Timestamp(s) for s in eligible_sessions if pd.Timestamp(s).year in years]
    daily = pd.Series(0.0, index=pd.Index(elig))
    if n:
        day_sum = g.groupby("session").net_bps.sum()
        for sess, v in day_sum.items():
            if sess in daily.index:
                daily.loc[sess] = float(v) / 10000.0
    sharpe = (
        float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))
        if len(daily) > 1 and daily.std(ddof=1) > 0
        else np.nan
    )
    boot = float(bootstrap_prob_positive_daily(daily)) if len(daily) else np.nan
    return {
        "years": f"{min(years)}-{max(years)}",
        "friction_bps": float(friction_bps),
        "side": side or "all",
        "eligible_days": len(elig),
        "trades": n,
        "trade_rate_per_day": float(n / len(elig)) if len(elig) else np.nan,
        "win_pct": wins,
        "avg_gross_bps": avg_gross,
        "avg_net_bps": avg_net,
        "PF": pf,
        "total_net_bps": total,
        "DD_bps": dd,
        "sharpe": sharpe,
        "bootstrap_prob_gt0": boot,
        "median_hold_min": med_hold,
        "avg_hold_min": avg_hold,
    }


def tail_metrics(trades, years):
    g = trades[trades.year.isin(years)].copy()
    if len(g) == 0:
        return {"drop_n": 0, "drop_avg_net_bps": np.nan, "drop_PF": np.nan}
    g["net_bps"] = g.gross_bps - PRIMARY_FRICTION_BPS
    drop_n = max(3, math.ceil(0.01 * len(g))) if len(g) >= 300 else 1
    z = g.sort_values("net_bps", ascending=False).iloc[drop_n:].copy()
    pos = float(z.loc[z.net_bps > 0, "net_bps"].sum())
    neg = float(z.loc[z.net_bps <= 0, "net_bps"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    return {
        "drop_n": int(drop_n),
        "drop_avg_net_bps": float(z.net_bps.mean()),
        "drop_PF": float(pf),
    }


def gate(trades, eligible_sessions):
    primary = metrics(trades, eligible_sessions, MODERN, 1.0)
    two = metrics(trades, eligible_sessions, MODERN, 2.0)
    tail = tail_metrics(trades, MODERN)
    yearly = pd.DataFrame([metrics(trades, eligible_sessions, [y], 1.0) for y in MODERN])
    long_side = metrics(trades, eligible_sessions, MODERN, 1.0, "long_residual")
    short_side = metrics(trades, eligible_sessions, MODERN, 1.0, "short_residual")

    positive_years = int((yearly.total_net_bps > 0).sum())
    py = yearly[yearly.total_net_bps > 0].total_net_bps
    share = float(py.max() / py.sum()) if len(py) and py.sum() > 0 else np.inf
    checks = {
        "n_ge_150": primary["trades"] >= 150,
        "avg_net_positive": primary["avg_net_bps"] > 0,
        "PF_ge_1_15": primary["PF"] >= 1.15,
        "positive_2_of_3_years": positive_years >= 2,
        "tail_avg_positive": tail["drop_avg_net_bps"] > 0,
        "bootstrap_ge_0_90": primary["bootstrap_prob_gt0"] >= 0.90,
        "two_bp_avg_positive": two["avg_net_bps"] > 0,
        "max_positive_year_share_le_0_75": share <= 0.75,
        "long_residual_nonnegative": long_side["avg_net_bps"] >= 0,
        "short_residual_nonnegative": short_side["avg_net_bps"] >= 0,
    }
    return checks, all(checks.values()), primary, two, tail, yearly, long_side, short_side, share


def main():
    print("=== ROUND 6 CROSS-INDEX RELATIVE-VALUE RESIDUAL TEST ===")
    print("Hard-frozen data span: 2017-2023. 2024-2026 are not loaded.")
    print("Primary research block: 2021-2023.")
    print("R6S1: prior-60-session ES~NQ+RTY OLS, same-slot residual z, |z|>=2, max 30m hold.")
    print("Stage-1 P&L is synthetic gross-exposure-normalized spread bps; primary friction 1.0 bp.")

    panel, complete_sessions = build_panel()
    trades, fits, eligible_sessions = generate_trades(panel, complete_sessions)
    print("eligible sessions after 60-session warmup:", len(eligible_sessions))
    print("eligible modern sessions:", sum(pd.Timestamp(s).year in MODERN for s in eligible_sessions))
    print("total trades:", len(trades))

    if len(trades) == 0:
        print("No trades. ROUND6_STAGE1_SURVIVOR = False")
        return

    print("\nMODERN 2021-2023 — COST SENSITIVITY")
    cs = pd.DataFrame([metrics(trades, eligible_sessions, MODERN, f) for f in [0.0, 0.5, 1.0, 2.0, 3.0]])
    print(cs[["friction_bps", "trades", "win_pct", "avg_gross_bps", "avg_net_bps", "PF", "total_net_bps", "DD_bps", "sharpe", "bootstrap_prob_gt0"]].round(4).to_string(index=False))

    print("\nYEAR BY YEAR — PRIMARY 1.0 BP")
    yr = pd.DataFrame([metrics(trades, eligible_sessions, [y], 1.0) for y in MODERN])
    print(yr[["years", "trades", "win_pct", "avg_net_bps", "PF", "total_net_bps", "DD_bps", "sharpe"]].round(4).to_string(index=False))

    print("\nSIDE DIAGNOSTICS — PRIMARY 1.0 BP")
    sides = pd.DataFrame([
        metrics(trades, eligible_sessions, MODERN, 1.0, "long_residual"),
        metrics(trades, eligible_sessions, MODERN, 1.0, "short_residual"),
    ])
    print(sides[["side", "trades", "win_pct", "avg_net_bps", "PF", "total_net_bps"]].round(4).to_string(index=False))

    print("\nEXIT / HOLD DIAGNOSTICS")
    modern_trades = trades[trades.year.isin(MODERN)].copy()
    print(modern_trades.exit_reason.value_counts().to_string())
    print("median hold min:", float(modern_trades.hold_min.median()) if len(modern_trades) else np.nan)
    print("mean hold min:", float(modern_trades.hold_min.mean()) if len(modern_trades) else np.nan)
    print("median |entry z|:", float(modern_trades.entry_z.abs().median()) if len(modern_trades) else np.nan)

    checks, survives, primary, two, tail, yearly, long_side, short_side, share = gate(trades, eligible_sessions)
    print("\nTAIL ROBUSTNESS:", tail)
    print("\nSTAGE-1 GATE")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("max_positive_year_share:", share)
    print("ROUND6_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R6S1 earns a separately frozen executable MES/MNQ/M2K conversion study before 2024 can be revealed.")
    else:
        print("2024 stays protected. Retire exact R6S1; do not tune it using 2021-2023.")

    trades.to_csv("round6_stage1_trades.csv", index=False)
    fits.to_csv("round6_stage1_daily_fits.csv", index=False)
    cs.to_csv("round6_stage1_cost_sensitivity.csv", index=False)
    yr.to_csv("round6_stage1_yearly.csv", index=False)
    sides.to_csv("round6_stage1_sides.csv", index=False)
    print("\nSaved Round-6 CSV outputs.")


if __name__ == "__main__":
    main()
