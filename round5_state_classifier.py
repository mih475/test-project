import math
import numpy as np
import pandas as pd

import round4_regime_model as r4

MODERN = [2021, 2022, 2023]
SEED = 20260924
MIN_LABEL_HISTORY = 252
MIN_TRAIN = 504
REFIT_EVERY = 20
CLASSES = ["CONT", "REV", "NT"]
PRIMARY = "R5C1"
NAMES = {
    "R5C1": "Three-state walk-forward LDA",
    "B_CONT": "Always opening-direction continuation",
    "B_REV": "Always opening-direction reversal",
}


def add_state_labels(df):
    out = df.copy()
    targ = out["target_bps"].to_numpy(dtype=float)
    first = out["es_first30_bps"].to_numpy(dtype=float)
    threshold = np.full(len(out), np.nan)
    label = np.array([None] * len(out), dtype=object)

    for i in range(len(out)):
        prior = np.abs(targ[:i])
        prior = prior[np.isfinite(prior)]
        if len(prior) < MIN_LABEL_HISTORY or not np.isfinite(targ[i]) or not np.isfinite(first[i]):
            continue
        if first[i] == 0:
            continue
        hist = prior[-MIN_LABEL_HISTORY:]
        q = float(np.median(hist))
        threshold[i] = q
        if abs(targ[i]) <= q:
            label[i] = "NT"
        elif np.sign(targ[i]) == np.sign(first[i]):
            label[i] = "CONT"
        else:
            label[i] = "REV"

    out["state_threshold_bps"] = threshold
    out["state_label"] = label
    return out


def fit_lda(X, y):
    classes = [c for c in CLASSES if np.any(y == c)]
    if len(classes) < 2:
        return None

    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0, ddof=0)
    sd = np.where(np.isfinite(sd) & (sd > 1e-12), sd, 1.0)
    Z = (X - mu) / sd

    class_means = {}
    priors = {}
    centered = []
    for c in classes:
        zc = Z[y == c]
        class_means[c] = zc.mean(axis=0)
        priors[c] = len(zc) / len(Z)
        centered.append(zc - class_means[c])

    E = np.vstack(centered)
    if len(E) <= 1:
        return None
    cov = (E.T @ E) / max(1, len(E) - len(classes))
    inv_cov = np.linalg.pinv(cov, rcond=1e-10)
    return {
        "mu": mu,
        "sd": sd,
        "classes": classes,
        "class_means": class_means,
        "priors": priors,
        "inv_cov": inv_cov,
    }


def lda_predict(model, x):
    z = (x - model["mu"]) / model["sd"]
    scores = []
    for c in model["classes"]:
        m = model["class_means"][c]
        s = float(z @ model["inv_cov"] @ m - 0.5 * m @ model["inv_cov"] @ m + np.log(model["priors"][c]))
        scores.append(s)
    scores = np.asarray(scores, dtype=float)
    mx = float(np.max(scores))
    probs = np.exp(scores - mx)
    probs = probs / probs.sum()
    j = int(np.argmax(probs))
    return model["classes"][j], float(probs[j]), {c: float(p) for c, p in zip(model["classes"], probs)}


def walk_forward_classify(df):
    out = df.copy()
    pred = np.array([None] * len(out), dtype=object)
    conf = np.full(len(out), np.nan)
    proba = {c: np.full(len(out), np.nan) for c in CLASSES}
    fit_rows = []

    needed = r4.FEATURES
    eligible = (
        np.isfinite(out[needed].to_numpy(dtype=float)).all(axis=1)
        & out["state_label"].notna().to_numpy()
        & np.isfinite(out["entry"].to_numpy(dtype=float))
        & np.isfinite(out["exit"].to_numpy(dtype=float))
    )
    idxs = np.flatnonzero(eligible)
    model = None
    last_fit_n = -10**9

    for pos, idx in enumerate(idxs):
        prior_idx = idxs[:pos]
        if len(prior_idx) < MIN_TRAIN:
            continue
        if model is None or (len(prior_idx) - last_fit_n) >= REFIT_EVERY:
            Xtr = out.loc[prior_idx, needed].to_numpy(dtype=float)
            ytr = out.loc[prior_idx, "state_label"].to_numpy(dtype=object)
            model = fit_lda(Xtr, ytr)
            last_fit_n = len(prior_idx)
            if model is None:
                continue
            row = {
                "fit_session": out.loc[idx, "session"],
                "train_n": len(prior_idx),
            }
            counts = pd.Series(ytr).value_counts()
            for c in CLASSES:
                row[f"train_{c}"] = int(counts.get(c, 0))
            fit_rows.append(row)

        x = out.loc[idx, needed].to_numpy(dtype=float)
        c, p, pp = lda_predict(model, x)
        pred[idx] = c
        conf[idx] = p
        for cls, val in pp.items():
            proba[cls][idx] = val

    out["pred_state"] = pred
    out["pred_confidence"] = conf
    for c in CLASSES:
        out[f"prob_{c}"] = proba[c]
    return out, pd.DataFrame(fit_rows)


def apply_actions(df):
    out = df.copy()
    open_sign = np.sign(out["es_first30_bps"].to_numpy(dtype=float))
    open_sign[~np.isfinite(open_sign)] = 0
    open_sign = open_sign.astype(int)

    d = np.zeros(len(out), dtype=int)
    d[out.pred_state == "CONT"] = open_sign[out.pred_state == "CONT"]
    d[out.pred_state == "REV"] = -open_sign[out.pred_state == "REV"]
    out["dir_R5C1"] = d
    out["eligible_R5C1"] = out.pred_state.notna() & np.isfinite(out.entry) & np.isfinite(out.exit)

    out["dir_B_CONT"] = open_sign
    out["dir_B_REV"] = -open_sign
    finite = np.isfinite(out.entry) & np.isfinite(out.exit) & np.isfinite(out.es_first30_bps)
    out["eligible_B_CONT"] = finite
    out["eligible_B_REV"] = finite

    for sid in NAMES:
        direction = out[f"dir_{sid}"].to_numpy(dtype=int)
        out[f"gross_pts_{sid}"] = direction * (out.exit - out.entry)
        out.loc[direction == 0, f"gross_pts_{sid}"] = 0.0
    return out


def max_drawdown(x):
    s = pd.Series(x, dtype=float).fillna(0.0)
    if len(s) == 0:
        return np.nan
    eq = s.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((eq - peak).min())


def bootstrap_prob_positive_daily(x, n_resamples=10000):
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


def metrics(df, sid, years, product="ES", slip_ticks=1):
    mask = df.year.isin(years) & df[f"eligible_{sid}"].fillna(False)
    block = df[mask].copy()
    trade = block[block[f"dir_{sid}"] != 0].copy()
    cp = r4.cost_points(product, slip_ticks)
    point_value = 50.0 if product == "ES" else 5.0

    block["daily_net_ret"] = 0.0
    if len(trade):
        trade["net_pts"] = trade[f"gross_pts_{sid}"] - cp
        trade["net_dollars"] = trade.net_pts * point_value
        trade["net_ret"] = trade.net_pts / trade.entry.astype(float)
        for idx, rr in trade.iterrows():
            block.loc[idx, "daily_net_ret"] = float(rr.net_ret)
        wins = float((trade.net_pts > 0).mean() * 100)
        pos = float(trade.loc[trade.net_dollars > 0, "net_dollars"].sum())
        neg = float(trade.loc[trade.net_dollars <= 0, "net_dollars"].sum())
        pf = pos / abs(neg) if neg < 0 else np.inf
        avg_net = float(trade.net_pts.mean())
        avg_dollars = float(trade.net_dollars.mean())
        total_dollars = float(trade.net_dollars.sum())
        dd = max_drawdown(trade.net_dollars)
    else:
        wins = pf = avg_net = avg_dollars = total_dollars = dd = np.nan

    daily = block.daily_net_ret.astype(float)
    sharpe = float(daily.mean() / daily.std(ddof=1) * np.sqrt(252)) if len(daily) > 1 and daily.std(ddof=1) > 0 else np.nan
    boot = bootstrap_prob_positive_daily(daily)

    return {
        "strategy": sid,
        "name": NAMES[sid],
        "years": f"{min(years)}-{max(years)}",
        "product": product,
        "slip_ticks": slip_ticks,
        "eligible_days": int(len(block)),
        "trades": int(len(trade)),
        "trade_rate_pct": float(len(trade) / len(block) * 100) if len(block) else np.nan,
        "win_pct": wins,
        "avg_net_pts": avg_net,
        "avg_dollars": avg_dollars,
        "PF": pf,
        "total_dollars": total_dollars,
        "DD_dollars": dd,
        "sharpe": sharpe,
        "bootstrap_prob_gt0": boot,
    }


def tail_metrics(df, sid, years):
    block = df[df.year.isin(years) & df[f"eligible_{sid}"].fillna(False)].copy()
    trade = block[block[f"dir_{sid}"] != 0].copy()
    if len(trade) == 0:
        return {"drop_n": 0, "drop_avg_net_pts": np.nan, "drop_PF": np.nan}
    cp = r4.cost_points("ES", 1)
    trade["net_pts"] = trade[f"gross_pts_{sid}"] - cp
    trade["net_dollars"] = trade.net_pts * 50.0
    drop_n = max(3, math.ceil(0.01 * len(trade))) if len(trade) >= 300 else 1
    z = trade.sort_values("net_dollars", ascending=False).iloc[drop_n:].copy()
    pos = float(z.loc[z.net_dollars > 0, "net_dollars"].sum())
    neg = float(z.loc[z.net_dollars <= 0, "net_dollars"].sum())
    pf = pos / abs(neg) if neg < 0 else np.inf
    return {
        "drop_n": int(drop_n),
        "drop_avg_net_pts": float(z.net_pts.mean()),
        "drop_PF": float(pf),
    }


def classification_metrics(df, years):
    z = df[df.year.isin(years) & df.pred_state.notna() & df.state_label.notna()].copy()
    if len(z) == 0:
        return {}
    acc = float((z.pred_state == z.state_label).mean())
    counts = z.state_label.value_counts(normalize=True)
    majority = float(counts.max())
    recalls = []
    for c in CLASSES:
        g = z[z.state_label == c]
        recalls.append(float((g.pred_state == c).mean()) if len(g) else np.nan)
    bal = float(np.nanmean(recalls))
    trade_mask = z.pred_state.isin(["CONT", "REV"])
    nt_mask = z.pred_state == "NT"
    traded_abs = float(z.loc[trade_mask, "target_bps"].abs().median()) if trade_mask.any() else np.nan
    nt_abs = float(z.loc[nt_mask, "target_bps"].abs().median()) if nt_mask.any() else np.nan
    return {
        "n": int(len(z)),
        "accuracy": acc,
        "majority_baseline_accuracy": majority,
        "balanced_accuracy": bal,
        "median_abs_target_bps_traded": traded_abs,
        "median_abs_target_bps_pred_nt": nt_abs,
    }


def yearly(df, sid):
    return pd.DataFrame([metrics(df, sid, [y], "ES", 1) for y in MODERN])


def gate(df):
    primary = metrics(df, PRIMARY, MODERN, "ES", 1)
    two = metrics(df, PRIMARY, MODERN, "ES", 2)
    tail = tail_metrics(df, PRIMARY, MODERN)
    yr = yearly(df, PRIMARY)
    cls = classification_metrics(df, MODERN)

    pos_years = int((yr.total_dollars > 0).sum())
    positive_totals = yr.loc[yr.total_dollars > 0, "total_dollars"]
    share = float(positive_totals.max() / positive_totals.sum()) if len(positive_totals) and positive_totals.sum() > 0 else np.inf
    checks = {
        "n_ge_150": primary["trades"] >= 150,
        "avg_net_positive": primary["avg_net_pts"] > 0,
        "PF_ge_1_15": primary["PF"] >= 1.15,
        "positive_2_of_3_years": pos_years >= 2,
        "tail_avg_positive": tail["drop_avg_net_pts"] > 0,
        "bootstrap_ge_0_90": primary["bootstrap_prob_gt0"] >= 0.90,
        "two_tick_avg_positive": two["avg_net_pts"] > 0,
        "max_positive_year_share_le_0_75": share <= 0.75,
        "classification_beats_majority": bool(cls) and cls["accuracy"] > cls["majority_baseline_accuracy"],
    }
    return checks, all(checks.values()), primary, two, tail, yr, cls, share


def main():
    print("=== ROUND 5 THREE-STATE MARKET CLASSIFIER ===")
    print("Hard-frozen data span: 2016-2023. 2024-2026 are not loaded.")
    print("Primary candidate: R5C1 only. Same 12 pre-10:00 features as Round 4.")
    print("Target states: continuation / reversal / no-trade.")
    print("No-trade label uses prior-252-session median absolute 10:00->15:30 return; no threshold sweep.")

    es = r4.build_es_features()
    frame = r4.add_cross_market(es)
    frame = add_state_labels(frame)

    complete_features = np.isfinite(frame[r4.FEATURES + ["target_bps", "entry", "exit"]].to_numpy(dtype=float)).all(axis=1)
    print("sessions total:", len(frame))
    print("complete cross-market feature sessions:", int(complete_features.sum()))
    print("labeled sessions:", int(frame.state_label.notna().sum()))
    print("label distribution 2021-2023:")
    print(frame[frame.year.isin(MODERN)].state_label.value_counts(dropna=False).to_string())

    scored, fits = walk_forward_classify(frame)
    scored = apply_actions(scored)

    results = []
    for sid in NAMES:
        for product in ["ES", "MES"]:
            for slip in [0, 1, 2, 4]:
                results.append(metrics(scored, sid, MODERN, product, slip))
    results = pd.DataFrame(results)

    print("\nMODERN 2021-2023 — PRIMARY ECONOMICS (ES +1 tick)")
    tab = results[(results["product"] == "ES") & (results["slip_ticks"] == 1)]
    cols = ["strategy", "trades", "trade_rate_pct", "win_pct", "avg_net_pts", "PF", "total_dollars", "DD_dollars", "sharpe", "bootstrap_prob_gt0"]
    print(tab[cols].round(4).to_string(index=False))

    print("\nR5C1 YEAR BY YEAR — ES +1 tick")
    y = yearly(scored, PRIMARY)
    print(y[["years", "trades", "trade_rate_pct", "win_pct", "avg_net_pts", "PF", "total_dollars", "sharpe"]].round(4).to_string(index=False))

    print("\nR5C1 COST SENSITIVITY")
    cs = results[results.strategy == PRIMARY]
    print(cs[["product", "slip_ticks", "trades", "avg_net_pts", "PF", "total_dollars", "sharpe"]].round(4).to_string(index=False))

    print("\nR5C1 CLASSIFICATION DIAGNOSTICS")
    print(classification_metrics(scored, MODERN))
    print("\nR5C1 TAIL ROBUSTNESS:", tail_metrics(scored, PRIMARY, MODERN))

    checks, survives, primary, two, tail, yr, cls, share = gate(scored)
    print("\nSTAGE-1 GATE")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("max_positive_year_share:", share)
    print("ROUND5_STAGE1_SURVIVOR =", survives)
    if survives:
        print("R5C1 earns a separate 2024 validation run. Do not change its rules.")
    else:
        print("2024 stays protected. Do not tune R5C1 using 2021-2023.")

    scored.to_csv("round5_stage1_predictions.csv", index=False)
    fits.to_csv("round5_stage1_fit_log.csv", index=False)
    results.to_csv("round5_stage1_metrics.csv", index=False)
    print("\nSaved:")
    print(" round5_stage1_predictions.csv")
    print(" round5_stage1_fit_log.csv")
    print(" round5_stage1_metrics.csv")


if __name__ == "__main__":
    main()
