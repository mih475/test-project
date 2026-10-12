#!/usr/bin/env python3
"""Summarize the ORB forward-test CSV without changing its frozen rules."""
import csv
import math
import sys
from collections import defaultdict


def num(row, key):
    try:
        value = row.get(key, "")
        return float(value) if value not in ("", None) else math.nan
    except (TypeError, ValueError):
        return math.nan


def summarize(rows):
    done = [r for r in rows if math.isfinite(num(r, "r_multiple"))]
    if not done:
        return {"trades": 0, "wins": 0, "win_rate": math.nan, "profit_factor": math.nan,
                "expectancy_r": math.nan, "max_drawdown_r": math.nan, "net_pnl_usd": 0.0}
    rs = [num(r, "r_multiple") for r in done]
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    eq = peak = 0.0
    max_dd = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        max_dd = min(max_dd, eq - peak)
    pnl = sum(num(r, "net_pnl_usd") for r in done if math.isfinite(num(r, "net_pnl_usd")))
    return {
        "trades": len(rs), "wins": len(wins), "win_rate": len(wins) / len(rs),
        "profit_factor": sum(wins) / abs(sum(losses)) if losses and sum(losses) else math.inf,
        "expectancy_r": sum(rs) / len(rs), "max_drawdown_r": max_dd, "net_pnl_usd": pnl,
    }


def fmt(value):
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def main(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    groups = {"ALL": rows}
    for row in rows:
        groups.setdefault(row.get("candidate", "UNKNOWN"), []).append(row)
    for name, group in groups.items():
        result = summarize(group)
        print(name + ": " + ", ".join(f"{k}={fmt(v)}" for k, v in result.items()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "forward_test_log.csv")
