import argparse
import io
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ES_BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEARS = list(range(2016, 2024))
MODERN = [2021, 2022, 2023]
NY = "America/New_York"
TICK = 0.25
SEED = 20260924
MIN_TRAIN = 504
REFIT_EVERY = 20
CROSS_DIR = Path("round4_crossmarket_data")
CROSS_SYMBOLS = {"nq": "NQ_v_0", "rty": "RTY_v_0", "zn": "ZN_v_0"}

FEATURES = [
    "es_gap_bps",
    "es_first30_bps",
    "nq_first30_bps",
    "rty_first30_bps",
    "zn_first30_bps",
    "equity_consensus",
    "equity_dispersion_bps",
    "nq_minus_rty_bps",
    "es_open_range_rel20",
    "es_prev_range_rel20",
    "es_open_volume_rel20",
    "gap_open_alignment",
]
B3_FEATURES = [
    "es_gap_bps",
    "es_first30_bps",
    "nq_first30_bps",
    "rty_first30_bps",
    "zn_first30_bps",
]

NAMES = {
    "R4M1": "Cross-market regime OLS",
    "B1": "ES first-30 continuation",
    "B2": "Unanimous equity continuation",
    "B3": "Cross-market OLS without regime variables",
}


def ts(sess, hhmm):
    return pd.Timestamp(f"{sess} {hhmm}", tz=NY)


def load_es_year(year):
    r = requests.get(ES_BASE.format(year), timeout=240)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d["datetime_et"] = pd.to_datetime(d["datetime_et"], utc=True).dt.tz_convert(NY)
    for c in ["open", "high", "low", "close", "volume"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["datetime_et", "open", "high", "low", "close", "volume", "symbol"]).copy()
    d["rth_bool"] = d["rth"].astype(str).str.lower().eq("true")
    d = d.sort_values(["datetime_et", "symbol", "volume"], ascending=[True, True, False])
    d = d.drop_duplicates(["datetime_et", "symbol"], keep="first")
    rth = d[d.rth_bool].copy()
    rth["session"] = rth.datetime_et.dt.date
    ns = rth.groupby("session").symbol.nunique()
    roll = set(ns[ns > 1].index)
    if roll:
        print("excluding ES roll-switch sessions", year, len(roll), sorted(roll))
    rth = rth[~rth.session.isin(roll)].copy()
    before = len(rth)
    rth = (
        rth.sort_values(["datetime_et", "volume"], ascending=[True, False])
        .drop_duplicates("datetime_et", keep="first")
        .sort_values("datetime_et")
    )
    print(
        "loaded ES", year,
        "RTH rows", len(rth),
        "sessions", rth.session.nunique(),
        "duplicates_resolved", before - len(rth),
    )
    return rth.set_index("datetime_et")


def exact_open(d, sess, hhmm):
    t = ts(sess, hhmm)
    if t not in d.index:
        return None
    row = d.loc[t]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return float(row.open)


def build_es_features():
    rows = []
    prior = None
    first30_ranges = []
    first30_volumes = []
    session_ranges = []

    for year in YEARS:
        rth = load_es_year(year)
        for sess, d in rth.groupby("session", sort=True):
            d = d.sort_index()
            if len(d) == 0:
                continue
            symbol = str(d.iloc[0].symbol)
            p0930 = exact_open(d, sess, "09:30")
            p1000 = exact_open(d, sess, "10:00")
            p1530 = exact_open(d, sess, "15:30")
            f30 = d[(d.index >= ts(sess, "09:30")) & (d.index < ts(sess, "10:00"))]

            row = {
                "session": pd.Timestamp(sess),
                "year": int(pd.Timestamp(sess).year),
                "symbol": symbol,
            }

            complete = len(f30) == 30 and p0930 is not None and p1000 is not None and p1530 is not None
            if complete:
                f30_range = float(f30.high.max() - f30.low.min())
                f30_vol = float(f30.volume.sum())
                sess_range = float(d.high.max() - d.low.min())
                row.update(
                    {
                        "entry": p1000,
                        "exit": p1530,
                        "target_bps": (p1530 / p1000 - 1.0) * 10000.0,
                        "es_first30_bps": (p1000 / p0930 - 1.0) * 10000.0,
                        "es_first30_range": f30_range,
                        "es_first30_volume": f30_vol,
                        "es_session_range": sess_range,
                    }
                )

                same_contract_prior = prior is not None and prior["symbol"] == symbol
                if same_contract_prior:
                    row["es_gap_bps"] = (p0930 / prior["close"] - 1.0) * 10000.0
                    row["es_prev_range"] = prior["range"]
                else:
                    row["es_gap_bps"] = np.nan
                    row["es_prev_range"] = np.nan

                if len(first30_ranges) >= 20:
                    med = float(np.median(first30_ranges[-20:]))
                    row["es_open_range_rel20"] = f30_range / med if med > 0 else np.nan
                else:
                    row["es_open_range_rel20"] = np.nan

                if len(first30_volumes) >= 20:
                    med = float(np.median(first30_volumes[-20:]))
                    row["es_open_volume_rel20"] = f30_vol / med if med > 0 else np.nan
                else:
                    row["es_open_volume_rel20"] = np.nan

                if len(session_ranges) >= 20 and same_contract_prior:
                    med = float(np.median(session_ranges[-20:]))
                    row["es_prev_range_rel20"] = prior["range"] / med if med > 0 else np.nan
                else:
                    row["es_prev_range_rel20"] = np.nan

                first30_ranges.append(f30_range)
                first30_volumes.append(f30_vol)
                session_ranges.append(sess_range)

                prior = {
                    "symbol": symbol,
                    "close": float(d.iloc[-1].close),
                    "range": sess_range,
                }
            else:
                # Incomplete sessions are not allowed to seed next-session features.
                row.update(
                    {
                        "entry": np.nan,
                        "exit": np.nan,
                        "target_bps": np.nan,
                        "es_first30_bps": np.nan,
                        "es_gap_bps": np.nan,
                        "es_open_range_rel20": np.nan,
                        "es_prev_range_rel20": np.nan,
                        "es_open_volume_rel20": np.nan,
                    }
                )
                prior = None

            rows.append(row)

    out = pd.DataFrame(rows).sort_values("session").reset_index(drop=True)
    return out


def read_cross_symbol(prefix):
    files = []
    for year in YEARS:
        p = CROSS_DIR / f"{prefix}_{year}.csv.gz"
        if p.exists() and p.stat().st_size > 0:
            files.append(p)
    if not files:
        raise FileNotFoundError(
            f"No Round-4 files found for {prefix} in {CROSS_DIR}. "
            f"Run round4_databento_download.py only after reviewing the cost quote."
        )

    parts = []
    for p in files:
        z = pd.read_csv(p, compression="gzip")
        ts_col = "ts_event" if "ts_event" in z.columns else None
        if ts_col is None:
            candidates = [c for c in z.columns if "time" in c.lower() or c.lower() == "index"]
            if not candidates:
                raise ValueError(f"Cannot identify timestamp column in {p}: {list(z.columns)}")
            ts_col = candidates[0]
        z["datetime_et"] = pd.to_datetime(z[ts_col], utc=True).dt.tz_convert(NY)
        for c in ["open", "high", "low", "close", "volume"]:
            if c in z.columns:
                z[c] = pd.to_numeric(z[c], errors="coerce")
        z = z.dropna(subset=["datetime_et", "open", "close"]).copy()
        parts.append(z[["datetime_et", "open", "close"]])

    d = pd.concat(parts, ignore_index=True).sort_values("datetime_et")
    d = d.drop_duplicates("datetime_et", keep="last")
    d["session"] = d.datetime_et.dt.date
    d = d.set_index("datetime_et")

    rows = []
    for sess, g in d.groupby("session", sort=True):
        t0930, t1000 = ts(sess, "09:30"), ts(sess, "10:00")
        if t0930 not in g.index or t1000 not in g.index:
            continue
        a, b = g.loc[t0930], g.loc[t1000]
        if isinstance(a, pd.DataFrame):
            a = a.iloc[-1]
        if isinstance(b, pd.DataFrame):
            b = b.iloc[-1]
        p0, p1 = float(a.open), float(b.open)
        if p0 <= 0 or p1 <= 0:
            continue
        rows.append(
            {
                "session": pd.Timestamp(sess),
                "first30_bps": (p1 / p0 - 1.0) * 10000.0,
            }
        )
    return pd.DataFrame(rows)


def add_cross_market(es):
    out = es.copy()
    for key, prefix in CROSS_SYMBOLS.items():
        x = read_cross_symbol(prefix).rename(columns={"first30_bps": f"{key}_first30_bps"})
        out = out.merge(x, on="session", how="left")

    eq = out[["es_first30_bps", "nq_first30_bps", "rty_first30_bps"]].to_numpy(dtype=float)
    valid = np.isfinite(eq).all(axis=1)
    consensus = np.full(len(out), np.nan)
    dispersion = np.full(len(out), np.nan)
    consensus[valid] = np.sign(eq[valid]).mean(axis=1)
    dispersion[valid] = np.std(eq[valid], axis=1, ddof=0)
    out["equity_consensus"] = consensus
    out["equity_dispersion_bps"] = dispersion
    out["nq_minus_rty_bps"] = out.nq_first30_bps - out.rty_first30_bps

    s1 = np.sign(out.es_gap_bps.to_numpy(dtype=float))
    s2 = np.sign(out.es_first30_bps.to_numpy(dtype=float))
    align = np.full(len(out), np.nan)
    v = np.isfinite(s1) & np.isfinite(s2)
    align[v] = np.where((s1[v] == 0) | (s2[v] == 0), 0.0, np.where(s1[v] == s2[v], 1.0, -1.0))
    out["gap_open_alignment"] = align
    return out


def add_prior_only_terciles(df, col, out_col):
    vals = df[col].to_numpy(dtype=float)
    labels = np.array(["NA"] * len(df), dtype=object)
    for i in range(len(df)):
        hist = vals[max(0, i - 252):i]
        hist = hist[np.isfinite(hist)]
        if len(hist) < 126 or not np.isfinite(vals[i]):
            continue
        q1, q2 = np.quantile(hist, [1 / 3, 2 / 3])
        if vals[i] <= q1:
            labels[i] = "low"
        elif vals[i] >= q2:
            labels[i] = "high"
        else:
            labels[i] = "mid"
    df[out_col] = labels


def standardize_fit(X):
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0, ddof=0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-12), sd, 1.0)
    return mu, sd


def walk_forward_ols(df, feature_cols, name):
    n = len(df)
    pred = np.full(n, np.nan)
    coef_rows = []

    eligible = np.isfinite(df[feature_cols + ["target_bps"]].to_numpy(dtype=float)).all(axis=1)
    eligible_idx = np.flatnonzero(eligible)
    last_fit_train_n = -10**9
    beta = mu = sd = None

    for pos, idx in enumerate(eligible_idx):
        prior_idx = eligible_idx[:pos]
        if len(prior_idx) < MIN_TRAIN:
            continue

        if beta is None or (len(prior_idx) - last_fit_train_n) >= REFIT_EVERY:
            Xtr = df.loc[prior_idx, feature_cols].to_numpy(dtype=float)
            ytr = df.loc[prior_idx, "target_bps"].to_numpy(dtype=float)
            mu, sd = standardize_fit(Xtr)
            Xz = (Xtr - mu) / sd
            A = np.column_stack([np.ones(len(Xz)), Xz])
            beta = np.linalg.pinv(A) @ ytr
            last_fit_train_n = len(prior_idx)
            crow = {
                "model": name,
                "fit_session": df.loc[idx, "session"],
                "train_n": len(prior_idx),
                "intercept": float(beta[0]),
            }
            for j, c in enumerate(feature_cols):
                crow[f"coef_{c}"] = float(beta[j + 1])
            coef_rows.append(crow)

        x = df.loc[idx, feature_cols].to_numpy(dtype=float)
        xz = (x - mu) / sd
        pred[idx] = float(np.r_[1.0, xz] @ beta)

    return pred, coef_rows


def apply_strategies(df):
    out = df.copy()
    p1, c1 = walk_forward_ols(out, FEATURES, "R4M1")
    p3, c3 = walk_forward_ols(out, B3_FEATURES, "B3")
    out["pred_R4M1_bps"] = p1
    out["pred_B3_bps"] = p3

    primary_cost_pts = cost_points("ES", 1)
    friction_bps = primary_cost_pts / out.entry.astype(float) * 10000.0
    out["primary_friction_bps"] = friction_bps

    out["dir_R4M1"] = 0
    ok = np.isfinite(out.pred_R4M1_bps) & np.isfinite(friction_bps)
    out.loc[ok & (out.pred_R4M1_bps > friction_bps), "dir_R4M1"] = 1
    out.loc[ok & (out.pred_R4M1_bps < -friction_bps), "dir_R4M1"] = -1

    out["dir_B3"] = 0
    ok = np.isfinite(out.pred_B3_bps) & np.isfinite(friction_bps)
    out.loc[ok & (out.pred_B3_bps > friction_bps), "dir_B3"] = 1
    out.loc[ok & (out.pred_B3_bps < -friction_bps), "dir_B3"] = -1

    d1 = np.zeros(len(out), dtype=int)
    b1_ok = np.isfinite(out.es_first30_bps.to_numpy(dtype=float))
    d1[b1_ok] = np.sign(out.loc[b1_ok, "es_first30_bps"].to_numpy(dtype=float)).astype(int)
    out["dir_B1"] = d1

    eq = out[["es_first30_bps", "nq_first30_bps", "rty_first30_bps"]].to_numpy(dtype=float)
    d2 = np.zeros(len(out), dtype=int)
    all_pos = np.isfinite(eq).all(axis=1) & (eq > 0).all(axis=1)
    all_neg = np.isfinite(eq).all(axis=1) & (eq < 0).all(axis=1)
    d2[all_pos] = 1
    d2[all_neg] = -1
    out["dir_B2"] = d2

    finite_px = np.isfinite(out.entry.to_numpy(dtype=float)) & np.isfinite(out.exit.to_numpy(dtype=float))
    out["eligible_R4M1"] = np.isfinite(out.pred_R4M1_bps.to_numpy(dtype=float)) & finite_px
    out["eligible_B3"] = np.isfinite(out.pred_B3_bps.to_numpy(dtype=float)) & finite_px
    out["eligible_B1"] = b1_ok & finite_px
    out["eligible_B2"] = np.isfinite(eq).all(axis=1) & finite_px

    for sid in NAMES:
        direction = out[f"dir_{sid}"].to_numpy(dtype=int)
        out[f"gross_pts_{sid}"] = direction * (out.exit - out.entry)
        out.loc[direction == 0, f"gross_pts_{sid}"] = 0.0

    return out, pd.DataFrame(c1 + c3)


def cost_points(product, slip_ticks):
    point_value = 50.0 if product == "ES" else 5.0
    commission = 5.0 if product == "ES" else 1.50
    return commission / point_value + slip_ticks * TICK


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


def strategy_metrics(df, sid, years, product="ES", slip_ticks=1):
    mask = df.year.isin(years)
    elig_col = f"eligible_{sid}"
    if elig_col in df.columns:
        mask = mask & df[elig_col].fillna(False)
    block = df[mask].copy()
    trade = block[block[f"dir_{sid}"] != 0].copy()
    cp = cost_points(product, slip_ticks)
    point_value = 50.0 if product == "ES" else 5.0

    block["daily_net_ret"] = 0.0
    if len(trade):
        trade["net_pts"] = trade[f"gross_pts_{sid}"] - cp
        trade["net_dollars"] = trade.net_pts * point_value
        trade["net_ret"] = trade.net_pts / trade.entry.astype(float)
        trade["net_bps"] = trade.net_ret * 10000.0

        for idx, r in trade.iterrows():
            block.loc[idx, "daily_net_ret"] = float(r.net_ret)

        wins = float((trade.net_pts > 0).mean() * 100)
        pos = float(trade.loc[trade.net_dollars > 0, "net_dollars"].sum())
        neg = float(trade.loc[trade.net_dollars <= 0, "net_dollars"].sum())
        pf = pos / abs(neg) if neg < 0 else np.inf
        avg_gross = float(trade[f"gross_pts_{sid}"].mean())
        avg_net = float(trade.net_pts.mean())
        avg_dollars = float(trade.net_dollars.mean())
        total_dollars = float(trade.net_dollars.sum())
        dd = max_drawdown(trade.net_dollars)
        boot = float(bootstrap_prob_positive(trade.net_ret))
        direction_acc = float((trade[f"gross_pts_{sid}"].to_numpy(dtype=float) > 0).mean() * 100)
    else:
        wins = pf = avg_gross = avg_net = avg_dollars = total_dollars = dd = boot = direction_acc = np.nan

    daily = block.daily_net_ret.astype(float)
    sharpe = (
        float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))
        if len(daily) > 1 and daily.std(ddof=1) > 0
        else np.nan
    )

    pred_col = f"pred_{sid}_bps"
    if pred_col in trade.columns and len(trade) >= 3:
        pred_corr = float(trade[pred_col].corr(trade.target_bps))
    else:
        pred_corr = np.nan

    return {
        "strategy": sid,
        "name": NAMES[sid],
        "years": f"{min(years)}-{max(years)}",
        "product": product,
        "slip_ticks": slip_ticks,
        "eligible_days": int(len(block)),
        "trades": int(len(trade)),
        "trade_rate_pct": float(len(trade) / len(block) * 100) if len(block) else np.nan,
        "longs": int((trade[f"dir_{sid}"] > 0).sum()) if len(trade) else 0,
        "shorts": int((trade[f"dir_{sid}"] < 0).sum()) if len(trade) else 0,
        "win_pct": wins,
        "avg_gross_pts": avg_gross,
        "avg_net_pts": avg_net,
        "avg_dollars": avg_dollars,
        "PF": pf,
        "total_dollars": total_dollars,
        "DD_dollars": dd,
        "sharpe": sharpe,
        "bootstrap_prob_gt0": boot,
        "prediction_realized_corr": pred_corr,
        "direction_accuracy_pct": direction_acc,
    }


def tail_metrics(df, sid, years):
    block = df[df.year.isin(years)].copy()
    trade = block[block[f"dir_{sid}"] != 0].copy()
    if len(trade) == 0:
        return {"drop_n": 0, "drop_avg_net_pts": np.nan, "drop_PF": np.nan}
    cp = cost_points("ES", 1)
    trade["net_pts"] = trade[f"gross_pts_{sid}"] - cp
    trade["net_dollars"] = trade.net_pts * 50.0
    drop_n = max(3, math.ceil(0.01 * len(trade))) if len(trade) >= 300 else 1
    z = trade.sort_values("net_dollars", ascending=False).iloc[drop_n:].copy()
    if len(z) == 0:
        return {"drop_n": drop_n, "drop_avg_net_pts": np.nan, "drop_PF": np.nan}
    pos = float(z.loc[z.net_dollars > 0, "net_dollars"].sum())
    neg = float(z.loc[z.net_dollars <= 0, "net_dollars"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    return {
        "drop_n": int(drop_n),
        "drop_avg_net_pts": float(z.net_pts.mean()),
        "drop_PF": float(pf),
    }


def yearly_totals(df, sid, product="ES", slip_ticks=1):
    rows = []
    for year in MODERN:
        m = strategy_metrics(df, sid, [year], product, slip_ticks)
        rows.append(m)
    return pd.DataFrame(rows)


def gate(df):
    primary = strategy_metrics(df, "R4M1", MODERN, "ES", 1)
    two_tick = strategy_metrics(df, "R4M1", MODERN, "ES", 2)
    tail = tail_metrics(df, "R4M1", MODERN)
    yr = yearly_totals(df, "R4M1", "ES", 1)

    positive_years = int((yr.total_dollars > 0).sum())
    positive_totals = yr.loc[yr.total_dollars > 0, "total_dollars"]
    if len(positive_totals) and positive_totals.sum() > 0:
        max_year_share = float(positive_totals.max() / positive_totals.sum())
    else:
        max_year_share = np.inf

    checks = {
        "n_ge_150": primary["trades"] >= 150,
        "avg_net_positive": primary["avg_net_pts"] > 0,
        "PF_ge_1_10": primary["PF"] >= 1.10,
        "positive_2_of_3_years": positive_years >= 2,
        "tail_avg_positive": tail["drop_avg_net_pts"] > 0,
        "bootstrap_ge_0_90": primary["bootstrap_prob_gt0"] >= 0.90,
        "two_tick_avg_ge_minus_0_05": two_tick["avg_net_pts"] >= -0.05,
        "max_positive_year_share_le_0_80": max_year_share <= 0.80,
    }
    return checks, all(checks.values()), primary, two_tick, tail, yr, max_year_share


def regime_diagnostics(df):
    rows = []
    modern = df[df.year.isin(MODERN)].copy()
    for label_col in ["vol_tercile", "disp_tercile"]:
        for label, g in modern.groupby(label_col):
            if label == "NA":
                continue
            m = strategy_metrics(g, "R4M1", MODERN, "ES", 1)
            m["diagnostic"] = label_col
            m["bucket"] = label
            rows.append(m)
    for label, g in modern.groupby("equity_consensus"):
        m = strategy_metrics(g, "R4M1", MODERN, "ES", 1)
        m["diagnostic"] = "equity_consensus"
        m["bucket"] = str(label)
        rows.append(m)
    return pd.DataFrame(rows)


def main():
    global CROSS_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--cross-dir", default=str(CROSS_DIR))
    args = ap.parse_args()

    CROSS_DIR = Path(args.cross_dir)

    print("=== ROUND 4 CROSS-MARKET / REGIME MODEL ===")
    print("Data span is hard-frozen to 2016-2023. 2024-2026 are not loaded.")
    print("Primary candidate: R4M1 only. Baselines cannot independently unlock 2024.")

    es = build_es_features()
    frame = add_cross_market(es)
    add_prior_only_terciles(frame, "es_open_range_rel20", "vol_tercile")
    add_prior_only_terciles(frame, "equity_dispersion_bps", "disp_tercile")

    complete = np.isfinite(frame[FEATURES + ["target_bps", "entry", "exit"]].to_numpy(dtype=float)).all(axis=1)
    print("sessions total:", len(frame))
    print("complete cross-market feature sessions:", int(complete.sum()))
    print("complete by year:")
    print(frame.assign(complete=complete).groupby("year").complete.sum().to_string())

    scored, coefs = apply_strategies(frame)

    results = []
    for sid in NAMES:
        for product in ["ES", "MES"]:
            for slip in [0, 1, 2, 4]:
                results.append(strategy_metrics(scored, sid, MODERN, product, slip))
    results = pd.DataFrame(results)

    print("\nMODERN 2021-2023 — PRIMARY ECONOMICS (ES +1 tick)")
    primary_table = results[(results.product == "ES") & (results.slip_ticks == 1)].copy()
    cols = [
        "strategy", "trades", "trade_rate_pct", "win_pct", "avg_net_pts",
        "avg_dollars", "PF", "total_dollars", "DD_dollars", "sharpe",
        "bootstrap_prob_gt0", "prediction_realized_corr",
    ]
    print(primary_table[cols].round(4).to_string(index=False))

    print("\nR4M1 YEAR BY YEAR — ES +1 tick")
    yrtab = yearly_totals(scored, "R4M1", "ES", 1)
    print(yrtab[["years", "trades", "win_pct", "avg_net_pts", "PF", "total_dollars", "sharpe"]].round(4).to_string(index=False))

    print("\nR4M1 COST SENSITIVITY")
    cs = results[results.strategy == "R4M1"]
    print(cs[["product", "slip_ticks", "trades", "avg_net_pts", "PF", "total_dollars", "sharpe"]].round(4).to_string(index=False))

    tail = tail_metrics(scored, "R4M1", MODERN)
    print("\nR4M1 TAIL ROBUSTNESS:", tail)

    checks, survives, primary, two_tick, tail, yr, max_share = gate(scored)
    print("\nSTAGE-1 GATE")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("max_positive_year_share:", max_share)
    print("ROUND4_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R4M1 earns a separate 2024 validation run. Do not change its rules.")
    else:
        print("2024 stays protected. Do not tune R4M1 using 2021-2023.")

    regimes = regime_diagnostics(scored)

    scored.to_csv("round4_stage1_predictions.csv", index=False)
    coefs.to_csv("round4_stage1_coefficients.csv", index=False)
    results.to_csv("round4_stage1_metrics.csv", index=False)
    regimes.to_csv("round4_stage1_regime_diagnostics.csv", index=False)

    print("\nSaved:")
    print(" round4_stage1_predictions.csv")
    print(" round4_stage1_coefficients.csv")
    print(" round4_stage1_metrics.csv")
    print(" round4_stage1_regime_diagnostics.csv")


if __name__ == "__main__":
    main()
