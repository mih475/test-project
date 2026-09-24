import io
import math
import requests
import numpy as np
import pandas as pd

BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEARS = list(range(2016, 2024))
MODERN = [2021, 2022, 2023]
CONTEXT = [2016, 2017, 2018, 2019, 2020]
NY = "America/New_York"
TICK = 0.25
SEED = 20260924

NAMES = {
    "R3S1": "Rest-of-day to last-30m momentum",
    "R3S2": "First-30m to last-30m momentum",
    "R3S3": "Overnight to first-30m reversal",
    "R3S4": "Large opening-gap reversal",
    "R3S5": "European-open four-hour drift",
    "R3S6": "High-vol first-30m to last-30m momentum",
}

ERA = {
    "R3S1": "2016-May2020 overlaps source ES sample; 2021+ post-sample/post-publication",
    "R3S2": "All 2016+ post-sample; 2018+ post-publication",
    "R3S3": "All 2016+ post-sample; recent literature warns of decay",
    "R3S4": "All 2016+ clean post-publication",
    "R3S5": "2016-Jul2018 replication; Aug2018-2020 post-sample; 2021+ key modern test",
    "R3S6": "All 2016+ post-sample; 2018+ post-publication",
}


def load_year(year):
    r = requests.get(BASE.format(year), timeout=240)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d["datetime_et"] = pd.to_datetime(d["datetime_et"], utc=True).dt.tz_convert(NY)
    for c in ["open", "high", "low", "close", "volume"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["datetime_et", "open", "high", "low", "close", "volume", "symbol"]).copy()
    d["rth_bool"] = d["rth"].astype(str).str.lower().eq("true")
    d = d.sort_values(["datetime_et", "symbol", "volume"], ascending=[True, True, False])
    full = d.drop_duplicates(["datetime_et", "symbol"], keep="first").copy()
    rth = full[full.rth_bool].copy()
    rth["session"] = rth.datetime_et.dt.date
    ns = rth.groupby("session").symbol.nunique()
    roll = set(ns[ns > 1].index)
    if roll:
        print("excluding roll-switch sessions", year, len(roll), sorted(roll))
    rth = rth[~rth.session.isin(roll)].copy()
    before = len(rth)
    rth = (rth.sort_values(["datetime_et", "volume"], ascending=[True, False])
              .drop_duplicates("datetime_et", keep="first")
              .sort_values("datetime_et"))
    print("loaded", year, "RTH rows", len(rth), "sessions", rth.session.nunique(), "duplicates_resolved", before-len(rth))
    return full.sort_values("datetime_et"), rth


def ts(sess, hhmm):
    return pd.Timestamp(f"{sess} {hhmm}", tz=NY)


def scheduled_open(symfull, target):
    z = symfull[(symfull.index >= target) & (symfull.index <= target + pd.Timedelta(minutes=1))]
    if len(z) == 0:
        return None, None
    row = z.iloc[0]
    return float(row.open), z.index[0]


def prior_close_info(prev, symbol):
    if prev is None or prev["symbol"] != symbol:
        return None
    return float(prev["close"])


def trade_row(sid, sess, direction, entry_time, entry, exit_time, exit_px, signal_value=np.nan, note=""):
    direction = int(direction)
    gross_pts = direction * (float(exit_px) - float(entry))
    return {
        "strategy": sid,
        "strategy_name": NAMES[sid],
        "session": pd.Timestamp(sess),
        "year": pd.Timestamp(sess).year,
        "direction": "long" if direction == 1 else "short",
        "dir": direction,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry": float(entry),
        "exit": float(exit_px),
        "gross_pts": float(gross_pts),
        "signal_value": float(signal_value) if np.isfinite(signal_value) else np.nan,
        "note": note,
    }


def first30_rv(rth_idx, sess):
    a, b = ts(sess, "09:30"), ts(sess, "10:00")
    z = rth_idx[(rth_idx.index >= a) & (rth_idx.index < b)]
    if len(z) < 30:
        return None
    z = z.iloc[:30]
    # Coding-time convention fixed before results: each minute return is log(close/open),
    # giving exactly 30 one-minute returns for 09:30-09:59.
    rr = np.log(z.close.to_numpy(dtype=float) / z.open.to_numpy(dtype=float))
    if len(rr) != 30 or not np.isfinite(rr).all():
        return None
    return float(np.sqrt(np.sum(rr * rr)))


def cost_points(product, slip_ticks):
    point = 50.0 if product == "ES" else 5.0
    comm = 5.0 if product == "ES" else 1.50
    return comm / point + slip_ticks * TICK


def enrich_net(g, product="ES", slip_ticks=1):
    if len(g) == 0:
        return g.assign(net_pts=pd.Series(dtype=float), net_ret=pd.Series(dtype=float), net_dollars=pd.Series(dtype=float), net_bps=pd.Series(dtype=float))
    point = 50.0 if product == "ES" else 5.0
    cp = cost_points(product, slip_ticks)
    z = g.copy()
    z["net_pts"] = z.gross_pts.astype(float) - cp
    z["net_ret"] = z.net_pts / z.entry.astype(float)
    z["net_bps"] = z.net_ret * 10000.0
    z["net_dollars"] = z.net_pts * point
    return z


def max_drawdown(v):
    v = pd.Series(v, dtype=float).dropna()
    if len(v) == 0:
        return np.nan
    eq = v.cumsum()
    peak = eq.cummax().clip(lower=0)
    dd = eq - peak
    return float(dd.min())


def bootstrap_prob_positive(values, n_resamples=10000):
    x = np.asarray(pd.Series(values, dtype=float).dropna(), dtype=float)
    n = len(x)
    if n == 0:
        return np.nan
    rng = np.random.default_rng(SEED)
    positive = 0
    done = 0
    batch = 500
    while done < n_resamples:
        b = min(batch, n_resamples-done)
        idx = rng.integers(0, n, size=(b, n))
        means = x[idx].mean(axis=1)
        positive += int((means > 0).sum())
        done += b
    return positive / n_resamples


def block_metrics(trades, eligible_sessions, sid, years, product="ES", slip_ticks=1):
    g = trades[(trades.strategy == sid) & (trades.year.isin(years))].copy()
    z = enrich_net(g, product, slip_ticks)
    n = len(z)
    if n:
        wins = float((z.net_pts > 0).mean() * 100)
        pos = z[z.net_dollars > 0].net_dollars.sum()
        neg = z[z.net_dollars <= 0].net_dollars.sum()
        pf = float(pos / abs(neg)) if neg < 0 else np.inf
        avg_pts = float(z.net_pts.mean())
        avg_dollars = float(z.net_dollars.mean())
        avg_bps = float(z.net_bps.mean())
        total_dollars = float(z.net_dollars.sum())
        dd = max_drawdown(z.net_dollars)
        boot = float(bootstrap_prob_positive(z.net_ret))
        gross_pos = float(z[z.net_dollars > 0].net_dollars.sum())
        max_share = float(z.net_dollars.max() / gross_pos) if gross_pos > 0 else np.nan
    else:
        wins = pf = avg_pts = avg_dollars = avg_bps = total_dollars = dd = boot = max_share = np.nan

    elig = sorted([s for s in eligible_sessions[sid] if pd.Timestamp(s).year in years])
    daily = pd.Series(0.0, index=pd.Index(elig, dtype=object))
    if n:
        for _, r in z.iterrows():
            key = pd.Timestamp(r.session).date()
            if key in daily.index:
                daily.loc[key] += float(r.net_ret)
    if len(daily) > 1 and daily.std(ddof=1) > 0:
        sharpe = float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))
    else:
        sharpe = np.nan

    return {
        "n": n,
        "win": wins,
        "avg_pts": avg_pts,
        "avg_dollars": avg_dollars,
        "avg_bps": avg_bps,
        "PF": pf,
        "total_dollars": total_dollars,
        "DD_dollars": dd,
        "sharpe": sharpe,
        "bootstrap_prob_gt0": boot,
        "max_winner_gross_share": max_share,
        "eligible_days": len(elig),
    }


def tail_metrics(trades, sid, years):
    g = trades[(trades.strategy == sid) & (trades.year.isin(years))].copy()
    z = enrich_net(g, "ES", 1)
    if len(z) == 0:
        return {"drop_n": 0, "drop_avg_pts": np.nan, "drop_PF": np.nan}
    drop_n = max(3, math.ceil(0.01*len(z))) if len(z) >= 300 else 1
    z = z.sort_values("net_dollars", ascending=False).iloc[drop_n:]
    if len(z) == 0:
        return {"drop_n": drop_n, "drop_avg_pts": np.nan, "drop_PF": np.nan}
    pos = z[z.net_dollars > 0].net_dollars.sum()
    neg = z[z.net_dollars <= 0].net_dollars.sum()
    pf = float(pos/abs(neg)) if neg < 0 else np.inf
    return {"drop_n": drop_n, "drop_avg_pts": float(z.net_pts.mean()), "drop_PF": pf}


def main():
    print("=== ROUND 3 LITERATURE-DERIVED TOURNAMENT ===")
    print("Frozen data span: 2016-2023 only. 2024-2026 are not loaded.")
    print("No stops/targets; fixed-time source-faithful anomaly tests.")
    for sid in NAMES:
        print(sid, ERA[sid])

    trades = []
    eligible = {sid: set() for sid in NAMES}
    rv_history = []  # list of (session, rv), prior-only for R3S6
    prev = None
    gap_horizons = []

    for year in YEARS:
        full, rth = load_year(year)
        full_by_symbol = {sym: g.sort_values("datetime_et").set_index("datetime_et") for sym, g in full.groupby("symbol")}
        rth = rth.sort_values("datetime_et").set_index("datetime_et")

        for sess, d in rth.groupby("session"):
            d = d.sort_index()
            if len(d) == 0:
                continue
            sym = str(d.iloc[0].symbol)
            if sym not in full_by_symbol:
                continue
            sf = full_by_symbol[sym]
            prior_close = prior_close_info(prev, sym)

            p0930, t0930 = scheduled_open(sf, ts(sess, "09:30"))
            p0940, t0940 = scheduled_open(sf, ts(sess, "09:40"))
            p1000, t1000 = scheduled_open(sf, ts(sess, "10:00"))
            p1030, t1030 = scheduled_open(sf, ts(sess, "10:30"))
            p1100, t1100 = scheduled_open(sf, ts(sess, "11:00"))
            p1200, t1200 = scheduled_open(sf, ts(sess, "12:00"))
            p1530, t1530 = scheduled_open(sf, ts(sess, "15:30"))
            p1600, t1600 = scheduled_open(sf, ts(sess, "16:00"))

            # R3S1: rest-of-day -> last 30m momentum
            if prior_close is not None and p1530 is not None and p1600 is not None:
                eligible["R3S1"].add(sess)
                sig = p1530/prior_close - 1.0
                if sig != 0:
                    trades.append(trade_row("R3S1", sess, 1 if sig > 0 else -1, t1530, p1530, t1600, p1600, sig))

            # R3S2: first 30m -> last 30m momentum
            if prior_close is not None and p1000 is not None and p1530 is not None and p1600 is not None:
                eligible["R3S2"].add(sess)
                sig = p1000/prior_close - 1.0
                if sig != 0:
                    trades.append(trade_row("R3S2", sess, 1 if sig > 0 else -1, t1530, p1530, t1600, p1600, sig))

            # R3S3: overnight -> first 30m reversal
            if prior_close is not None and p0930 is not None and p1000 is not None:
                eligible["R3S3"].add(sess)
                sig = p0930/prior_close - 1.0
                if sig != 0:
                    trades.append(trade_row("R3S3", sess, -1 if sig > 0 else 1, t0930, p0930, t1000, p1000, sig))

            # R3S4: large gap reversal after 10m continuation
            if prior_close is not None and p0930 is not None and p0940 is not None and p1030 is not None:
                eligible["R3S4"].add(sess)
                gap = p0930/prior_close - 1.0
                if abs(gap) >= 0.002:
                    direction = -1 if gap > 0 else 1
                    trades.append(trade_row("R3S4", sess, direction, t0940, p0940, t1030, p1030, gap))
                    hr = {"session": pd.Timestamp(sess), "year": pd.Timestamp(sess).year, "direction": direction,
                          "entry": p0940, "gap": gap}
                    for label, px in [("1000", p1000), ("1030", p1030), ("1100", p1100), ("1200", p1200)]:
                        hr[f"px_{label}"] = px
                        hr[f"gross_pts_{label}"] = direction*(px-p0940) if px is not None else np.nan
                    gap_horizons.append(hr)

            # R3S5: European-open 23:30 -> 03:30, attributed to current RTH session
            day = pd.Timestamp(sess, tz=NY)
            e_start = day - pd.Timedelta(days=1) + pd.Timedelta(hours=23, minutes=30)
            e_end = day + pd.Timedelta(hours=3, minutes=30)
            allwin = full[(full.datetime_et >= e_start) & (full.datetime_et <= e_end)]
            symwin = sf[(sf.index >= e_start) & (sf.index < e_end)]
            pe, te = scheduled_open(sf, e_start)
            px, tx = scheduled_open(sf, e_end)
            complete = len(symwin) >= 235
            single_contract = (len(allwin) > 0 and allwin.symbol.nunique() == 1 and str(allwin.iloc[0].symbol) == sym)
            if pe is not None and px is not None and complete and single_contract:
                eligible["R3S5"].add(sess)
                trades.append(trade_row("R3S5", sess, 1, te, pe, tx, px, np.nan, "23:30-03:30"))

            # R3S6: high-volatility first30 -> last30 momentum
            rv = first30_rv(d, sess)
            prior_rvs = [x[1] for x in rv_history[-252:]]
            if rv is not None and len(prior_rvs) >= 126 and prior_close is not None and p1000 is not None and p1530 is not None and p1600 is not None:
                eligible["R3S6"].add(sess)
                threshold = float(np.quantile(prior_rvs, 2.0/3.0))
                if rv > threshold:
                    sig = p1000/prior_close - 1.0
                    if sig != 0:
                        trades.append(trade_row("R3S6", sess, 1 if sig > 0 else -1, t1530, p1530, t1600, p1600, sig,
                                                f"rv={rv:.8f};threshold={threshold:.8f}"))
            if rv is not None:
                rv_history.append((sess, rv))

            prev = {"session": sess, "symbol": sym, "close": float(d.iloc[-1].close)}

    t = pd.DataFrame(trades).sort_values(["strategy", "entry_time"]).reset_index(drop=True)
    t.to_csv("round3_literature_trades.csv", index=False)
    pd.DataFrame(gap_horizons).to_csv("round3_gap_horizon_trades.csv", index=False)

    print("\nIMPLEMENTATION AUDIT")
    audit_rows = []
    for sid in NAMES:
        g = t[t.strategy == sid].copy()
        overlaps = 0
        for _, gg in g.groupby("session"):
            gg = gg.sort_values("entry_time")
            prev_exit = None
            for _, r in gg.iterrows():
                if prev_exit is not None and pd.Timestamp(r.entry_time) < prev_exit:
                    overlaps += 1
                prev_exit = pd.Timestamp(r.exit_time)
        audit_rows.append({"strategy": sid, "trades": len(g), "sessions": g.session.nunique(),
                           "longs": int((g.direction == "long").sum()), "shorts": int((g.direction == "short").sum()),
                           "overlaps": overlaps, "eligible_days": len(eligible[sid])})
    audit = pd.DataFrame(audit_rows)
    print(audit.to_string(index=False))

    leaderboard = []
    year_rows = []
    cost_rows = []

    for sid in NAMES:
        modern = block_metrics(t, eligible, sid, MODERN, "ES", 1)
        context = block_metrics(t, eligible, sid, CONTEXT, "ES", 1)
        tail = tail_metrics(t, sid, MODERN)
        es2 = block_metrics(t, eligible, sid, MODERN, "ES", 2)

        positive_years = 0
        for y in YEARS:
            ym = block_metrics(t, eligible, sid, [y], "ES", 1)
            if y in MODERN and np.isfinite(ym["total_dollars"]) and ym["total_dollars"] > 0:
                positive_years += 1
            year_rows.append({"strategy": sid, "year": y, **ym})

        gate = bool(
            sid != "R3S5" and
            modern["n"] >= 100 and
            modern["avg_pts"] > 0 and
            modern["sharpe"] >= 0.50 and
            positive_years >= 2 and
            es2["avg_pts"] > 0 and
            tail["drop_avg_pts"] > 0 and
            modern["max_winner_gross_share"] <= 0.10 and
            modern["bootstrap_prob_gt0"] >= 0.90
        )
        leaderboard.append({
            "strategy": sid, "name": NAMES[sid],
            "modern_n": modern["n"], "modern_win": modern["win"], "modern_avg_pts": modern["avg_pts"],
            "modern_avg_dollars": modern["avg_dollars"], "modern_avg_bps": modern["avg_bps"],
            "modern_PF": modern["PF"], "modern_total_dollars": modern["total_dollars"],
            "modern_DD_dollars": modern["DD_dollars"], "modern_sharpe": modern["sharpe"],
            "modern_bootstrap_prob": modern["bootstrap_prob_gt0"],
            "modern_max_winner_share": modern["max_winner_gross_share"],
            "modern_positive_years": positive_years, "modern_ES2_avg_pts": es2["avg_pts"],
            "drop_n": tail["drop_n"], "drop_avg_pts": tail["drop_avg_pts"], "drop_PF": tail["drop_PF"],
            "context_n": context["n"], "context_avg_pts": context["avg_pts"], "context_PF": context["PF"],
            "context_sharpe": context["sharpe"], "survivor": gate,
        })

        for block_name, years in [("context_2016_2020", CONTEXT), ("modern_2021_2023", MODERN)]:
            for product in ["ES", "MES"]:
                for slip in [0, 1, 2, 4]:
                    m = block_metrics(t, eligible, sid, years, product, slip)
                    cost_rows.append({"strategy": sid, "block": block_name, "product": product, "slip_ticks": slip, **m})

    lb = pd.DataFrame(leaderboard).sort_values(["survivor", "modern_avg_pts"], ascending=[False, False])
    yr = pd.DataFrame(year_rows)
    costs = pd.DataFrame(cost_rows)
    lb.to_csv("round3_literature_leaderboard.csv", index=False)
    yr.to_csv("round3_literature_year_by_year.csv", index=False)
    costs.to_csv("round3_literature_cost_sensitivity.csv", index=False)

    print("\nMODERN LEADERBOARD -- 2021-2023, ES $5 RT + 1 TICK")
    cols = ["strategy", "modern_n", "modern_win", "modern_avg_pts", "modern_avg_dollars", "modern_PF",
            "modern_total_dollars", "modern_sharpe", "modern_bootstrap_prob", "modern_positive_years",
            "modern_ES2_avg_pts", "drop_avg_pts", "context_avg_pts", "context_PF", "survivor"]
    print(lb[cols].round(4).to_string(index=False))

    print("\nYEAR BY YEAR -- ES 1 TICK")
    show = yr[["strategy", "year", "n", "win", "avg_pts", "PF", "total_dollars", "sharpe"]]
    print(show.round(4).to_string(index=False))

    print("\nR3S4 GAP HORIZON DIAGNOSTIC -- NOT FOR RULE SELECTION")
    gh = pd.DataFrame(gap_horizons)
    hp = []
    if len(gh):
        for years, label in [(CONTEXT, "context_2016_2020"), (MODERN, "modern_2021_2023")]:
            gg = gh[gh.year.isin(years)]
            for h in ["1000", "1030", "1100", "1200"]:
                vals = gg[f"gross_pts_{h}"].dropna() - cost_points("ES", 1)
                hp.append({"block": label, "horizon": h, "n": len(vals), "avg_net_pts": vals.mean() if len(vals) else np.nan,
                           "win": (vals > 0).mean()*100 if len(vals) else np.nan})
    hp = pd.DataFrame(hp)
    hp.to_csv("round3_gap_horizon_profile.csv", index=False)
    print(hp.round(4).to_string(index=False) if len(hp) else "no gap diagnostics")

    survivors = lb[lb.survivor].strategy.tolist()
    print("\nROUND3_SURVIVORS", survivors)
    print("R3S5 is a negative-control/decay test and is never auto-promoted by the survivor gate.")
    if survivors:
        print("INTERPRETATION: freeze survivors exactly before any 2024 validation.")
    else:
        print("INTERPRETATION: no strategy earns 2024 validation under the frozen gate.")


if __name__ == "__main__":
    main()
