"""Reproduce archived research and isolate frozen-rule differences. Offline inputs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import orb_refinement_stage2 as s2
import orb_filter_diagnostics as fd
import orb_walkforward_regime as wf

ROOT = Path(__file__).resolve().parent

class CachedResponse:
    def __init__(self, url):
        self.content = (ROOT / 'data' / url.rsplit('/', 1)[-1]).read_bytes()
        self.text = self.content.decode()
        self.status_code = 200
    def raise_for_status(self):
        pass

def frozen_trade(xd, de, sess, candidate, cutoff):
    opening = s2.get_or(xd, sess, 15)
    if opening is None:
        return None
    orh, orl, end = opening
    valid = (de.index >= end) & (de.index.map(s2.tod) < cutoff)
    valid &= (de.close > orh) & (de.close > de.ema50) & de.atr7.notna()
    if candidate == 'B':
        valid &= (de.adx14 >= 20) & (de.pdi14 > de.mdi14)
    qualifying = de[valid]
    if qualifying.empty:
        return None
    ts = qualifying.index[0]
    b = qualifying.iloc[0]
    entry_info = s2.entry_info(xd, ts, b, 15, 'next_open')
    if entry_info is None:
        return None
    entry_ts, entry = entry_info
    atr = float(b.atr7)
    risk = entry - orl
    target = entry + 1.5 * atr
    outcome = None
    for exit_ts, bar in xd[xd.index >= entry_ts].iterrows():
        hit_stop = bar.low <= orl
        hit_target = bar.high >= target
        if hit_stop:
            outcome = (orl - entry, exit_ts, 'ambiguous_stop_first' if hit_target else 'stop')
            break
        if hit_target:
            outcome = (target - entry, exit_ts, 'target')
            break
    if outcome is None:
        last = xd[xd.index >= entry_ts].iloc[-1]
        outcome = (float(last.close) - entry, last.name, 'eod')
    pnl, exit_ts, reason = outcome
    return dict(session=str(sess), candidate=candidate, signal_time=str(ts),
                entry_time=str(entry_ts), exit_time=str(exit_ts), entry=entry,
                stop=orl, target=target, atr=atr, risk_pts=risk,
                raw_pnl_pts=pnl, raw_R=pnl/risk if risk > 0 else np.nan,
                exit_reason=reason, invalid_risk=risk <= 0,
                below_legacy_atr_min=atr < .25)

def main():
    s2.requests.get = lambda url, **kwargs: CachedResponse(url)
    x = s2.load_all()
    ex = fd.add_indicators(s2.resample_exec(x, 15))
    rebuilt = fd.build_trade_features(x, ex)
    archived = pd.read_csv(ROOT / 'results/orb_wf_trade_features.csv')
    numeric = ['entry', 'stop', 'target', 'atr', 'risk_pts', 'raw_pnl_pts', 'adx14']
    checks = {'row_count': len(rebuilt) == len(archived)}
    for col in numeric:
        checks[col] = bool(np.allclose(rebuilt[col], archived[col], rtol=1e-10,
                                      atol=1e-10, equal_nan=True))
    for col in ['signal_time', 'entry_time', 'exit_time']:
        checks[col] = bool(np.array_equal(pd.to_datetime(rebuilt[col], utc=True),
                                          pd.to_datetime(archived[col], utc=True)))
    checks['direction'] = rebuilt.direction.tolist() == archived.direction.tolist()
    checks['exit_reason'] = rebuilt.exit_reason.tolist() == archived.exit_reason.tolist()
    print('Archived reproduction:', checks, flush=True)
    if not all(checks.values()):
        raise RuntimeError('Archived reproduction failed; investigate input/source drift first.')
    grouped = dict(tuple(ex.groupby('session')))
    rows = {(c, cutoff): [] for c in ['A', 'B'] for cutoff in [930, 945]}
    for sess, xd in x.groupby('session'):
        de = grouped.get(sess)
        if de is None:
            continue
        for (candidate, cutoff), output in rows.items():
            row = frozen_trade(xd, de, sess, candidate, cutoff)
            if row is not None:
                output.append(row)
    report = {'archived_rows': len(archived), 'reproduction': checks,
              'input_start': str(x.index.min()), 'input_end': str(x.index.max()),
              'data_product': 'ES; MES cost model only', 'candidates': {}}
    for candidate, variant in [('A', 'LONG_ONLY'), ('B', 'LONG_ADX20_DMI')]:
        legacy = wf.apply_variant(rebuilt, variant).copy()
        legacy['session'] = legacy.session.astype(str)
        early = pd.DataFrame(rows[(candidate, 930)])
        literal = pd.DataFrame(rows[(candidate, 945)])
        early.to_csv(ROOT / f'candidate_{candidate}_research_cutoff.csv', index=False)
        literal.to_csv(ROOT / f'candidate_{candidate}_frozen_rules.csv', index=False)
        merged = legacy[['session', 'signal_time']].merge(
            literal[['session', 'signal_time']], on='session', how='outer',
            suffixes=('_research', '_frozen'), indicator=True)
        both = merged['_merge'].eq('both')
        a = pd.to_datetime(merged.signal_time_research, utc=True)
        b = pd.to_datetime(merged.signal_time_frozen, utc=True)
        changed = ~both | a.ne(b)
        merged[changed].to_csv(ROOT / f'candidate_{candidate}_changed_sessions.csv', index=False)
        report['candidates'][candidate] = dict(
            research_trades=len(legacy), first_qualifying_long_same_cutoff=len(early),
            frozen_rules_trades=len(literal), changed_sessions=int(changed.sum()),
            added_sessions=int(merged['_merge'].eq('right_only').sum()),
            removed_sessions=int(merged['_merge'].eq('left_only').sum()),
            different_signal_on_shared_session=int((both & a.ne(b)).sum()),
            invalid_risk=int(literal.invalid_risk.sum()),
            below_legacy_atr_min=int(literal.below_legacy_atr_min.sum()))
    (ROOT / 'parity_audit_summary.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)

if __name__ == '__main__':
    main()
