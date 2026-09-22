import itertools
import numpy as np
import pandas as pd
import multiyear_backtest as mb
import phase2b_diagnostics as p2

MES_POINT=5.0
ES_POINT=50.0
MES_RT_COMM=1.50   # explicit research assumption, not a broker quote
ES_RT_COMM=5.00    # explicit research assumption, not a broker quote


def fixed_add_regime_features(frame,t):
    rows=[]; daily=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy().sort_index()
        d['ret1']=d.close.pct_change()
        d['vol20']=d.ret1.rolling(20,min_periods=10).std()
        d['vwap_slope30_z']=(d.vwap-d.vwap.shift(30))/d.sd.replace(0,np.nan)
        d['ret30_z']=(d.close-d.close.shift(30))/d.sd.replace(0,np.nan)
        d['range_sofar']=d.high.cummax()-d.low.cummin()
        d['relvol20']=d.volume/d.volume.rolling(20,min_periods=10).median()
        first30=d.iloc[:30]
        daily.append({'session':pd.Timestamp(sess),'day_range':d.high.max()-d.low.min(),
                      'or30':first30.high.max()-first30.low.min()})
        rows.append(d[['vwap_slope30_z','ret30_z','range_sofar','relvol20','vol20']].reset_index())
    f=pd.concat(rows,ignore_index=True).rename(columns={'datetime_et':'signal_time'})
    daily=pd.DataFrame(daily).sort_values('session')
    daily['prior20_range_med']=daily.day_range.shift(1).rolling(20,min_periods=10).median()
    daily['prior20_or_med']=daily.or30.shift(1).rolling(20,min_periods=10).median()
    x=t.copy(); x['session']=pd.to_datetime(x.session)
    x=x.merge(f,on='signal_time',how='left')
    x=x.merge(daily[['session','or30','prior20_range_med','prior20_or_med']],on='session',how='left')
    x['range_ratio_prior20']=x.range_sofar/x.prior20_range_med
    x['or_ratio_prior20']=x.or30/x.prior20_or_med
    x['dir_vwap_slope_z']=x.dir_sign*x.vwap_slope30_z
    x['abs_vwap_slope30_z']=x.vwap_slope30_z.abs()
    x['distance_from_vwap_z']=(x.signal_close-x.signal_vwap).abs()/x.signal_sd.replace(0,np.nan)
    return x.reset_index(drop=True)


def net_r(t, product='MES', slip_ticks=1):
    if product=='MES': point_value,comm=MES_POINT,MES_RT_COMM
    else: point_value,comm=ES_POINT,ES_RT_COMM
    penalty_pts=slip_ticks*mb.TICK + comm/point_value
    return t.R - penalty_pts/t.risk_pts


def perf(t, r=None):
    if len(t)==0: return {'n':0,'win':np.nan,'avg':np.nan,'pf':np.nan,'dd':np.nan}
    v=pd.Series(t.R.to_numpy() if r is None else np.asarray(r),index=t.index,dtype=float)
    wins=v[v>0]; losses=v[v<=0]
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum()) else np.inf
    eq=v.cumsum(); dd=(eq-eq.cummax()).min()
    return {'n':len(v),'win':100*(v>0).mean(),'avg':v.mean(),'pf':pf,'dd':dd}


def stop_economics(t):
    print('\n=== PHASE 3A-1: MINIMUM STOP / RISK ECONOMICS ===')
    print('NOTE: This first table filters frozen Phase-2B trades. A shortlisted threshold must be replayed in signal generation before adoption.')
    periods=[('DEV21-23',t.year<=2023),('VAL24',t.year==2024),('EVAL25',t.year==2025),('RECENT26',t.year==2026),('ALL',pd.Series(True,index=t.index))]
    out=[]
    for minrisk in [0,1.0,1.5,2.0,2.5,3.0,4.0,5.0]:
        print('\nMIN_RISK_PTS',minrisk)
        for label,pm in periods:
            g=t[pm & (t.risk_pts>=minrisk)]
            raw=perf(g); mes1=perf(g,net_r(g,'MES',1)); es1=perf(g,net_r(g,'ES',1))
            print(label,'n',len(g),'raw_win',round(raw['win'],2),'raw_avgR',round(raw['avg'],4),'raw_PF',round(raw['pf'],3),
                  'MES1_avgR',round(mes1['avg'],4),'MES1_PF',round(mes1['pf'],3),
                  'ES1_avgR',round(es1['avg'],4),'ES1_PF',round(es1['pf'],3))
            out.append({'min_risk_pts':minrisk,'period':label,'n':len(g),'raw_win_pct':raw['win'],'raw_avgR':raw['avg'],'raw_PF':raw['pf'],
                        'MES1_avgR':mes1['avg'],'MES1_PF':mes1['pf'],'ES1_avgR':es1['avg'],'ES1_PF':es1['pf']})
    return pd.DataFrame(out)


def controls_rate(controls, ids, threshold):
    c=controls[controls.trade_id.isin(set(ids)) & controls.threshold_R.eq(float(threshold))]
    return 100*c.hit.mean() if len(c) else np.nan


def subset_metrics(t,controls,mask,period_mask):
    g=t[mask & period_mask]
    if not len(g): return {'n':0}
    h1=100*g.hit_1p0R_before_stop.mean(); h2=100*g.hit_2p0R_before_stop.mean()
    r1=controls_rate(controls,g.trade_id,1.0); r2=controls_rate(controls,g.trade_id,2.0)
    raw=perf(g); mes=perf(g,net_r(g,'MES',1)); es=perf(g,net_r(g,'ES',1))
    return {'n':len(g),'win':raw['win'],'avgR':raw['avg'],'PF':raw['pf'],
            'hit1':h1,'lift1':h1-r1,'hit2':h2,'lift2':h2-r2,
            'MES1_avgR':mes['avg'],'MES1_PF':mes['pf'],'ES1_avgR':es['avg'],'ES1_PF':es['pf']}


def build_conditions(t):
    dev=t[t.year<=2023]
    q={}
    for f in ['or_ratio_prior20','range_ratio_prior20','vol20','distance_from_vwap_z','relvol20','abs_vwap_slope30_z','dir_vwap_slope_z']:
        q[f]=dev[f].replace([np.inf,-np.inf],np.nan).dropna().quantile([.25,.5,.75]).to_dict()
    cond=[]
    def add(name,family,series): cond.append((name,family,series.fillna(False)))
    # Economic filters: fixed point distances, chosen before inspecting Phase 3A output.
    for x in [1.5,2.0,2.5,3.0,4.0]: add(f'risk>={x:g}pt','risk',t.risk_pts>=x)
    # Coarse regime hypotheses using only 2021-23 distribution thresholds.
    add('OR>=dev_median','opening_range',t.or_ratio_prior20>=q['or_ratio_prior20'][.5])
    add('OR>=dev_Q3','opening_range',t.or_ratio_prior20>=q['or_ratio_prior20'][.75])
    add('range>=dev_median','range',t.range_ratio_prior20>=q['range_ratio_prior20'][.5])
    add('range>=dev_Q3','range',t.range_ratio_prior20>=q['range_ratio_prior20'][.75])
    add('vol20_mid50','volatility',t.vol20.between(q['vol20'][.25],q['vol20'][.75]))
    add('vol20>=dev_median','volatility',t.vol20>=q['vol20'][.5])
    add('VWAPdist>=dev_median','vwap_distance',t.distance_from_vwap_z>=q['distance_from_vwap_z'][.5])
    add('VWAPdist>=dev_Q3','vwap_distance',t.distance_from_vwap_z>=q['distance_from_vwap_z'][.75])
    add('relvol>=dev_median','relative_volume',t.relvol20>=q['relvol20'][.5])
    add('VWAPslope_abs<=dev_median','vwap_slope',t.abs_vwap_slope30_z<=q['abs_vwap_slope30_z'][.5])
    add('dir_slope>=dev_Q1','directional_slope',t.dir_vwap_slope_z>=q['dir_vwap_slope_z'][.25])
    add('exclude_11am','time',t.entry_hour.ne(11))
    add('hours_13_14','time',t.entry_hour.isin([13,14]))
    return cond,q


def candidate_search(t,controls):
    print('\n=== PHASE 3A-2: SIMPLE REGIME DISCOVERY ===')
    print('Ranking uses DEV 2021-23 + validation 2024 only. 2025/2026 are evaluation columns, never ranking inputs.')
    cond,q=build_conditions(t)
    for f,v in q.items(): print('DEV_QUARTILES',f,{k:round(float(x),6) for k,x in v.items()})
    candidates=[('baseline',(),pd.Series(True,index=t.index))]
    for name,fam,s in cond: candidates.append((name,(fam,),s))
    for (n1,f1,s1),(n2,f2,s2) in itertools.combinations(cond,2):
        if f1==f2: continue
        candidates.append((n1+' & '+n2,(f1,f2),s1&s2))
    periods={'dev':t.year<=2023,'val24':t.year==2024,'eval25':t.year==2025,'recent26':t.year==2026}
    rows=[]
    for name,fams,mask in candidates:
        m={p:subset_metrics(t,controls,mask,pm) for p,pm in periods.items()}
        if m['dev'].get('n',0)<80 or m['val24'].get('n',0)<20: continue
        floor_lift1=min(m['dev']['lift1'],m['val24']['lift1'])
        floor_lift2=min(m['dev']['lift2'],m['val24']['lift2'])
        floor_es=min(m['dev']['ES1_avgR'],m['val24']['ES1_avgR'])
        floor_mes=min(m['dev']['MES1_avgR'],m['val24']['MES1_avgR'])
        # Rank primarily on barrier-edge stability, not total P&L or 2025/2026 behavior.
        robust_edge=floor_lift1+floor_lift2
        row={'rule':name,'conditions':len(fams),'dev_n':m['dev']['n'],'val24_n':m['val24']['n'],
             'edge_floor_1R_pp':floor_lift1,'edge_floor_2R_pp':floor_lift2,'edge_floor_sum':robust_edge,
             'ES1_avgR_floor':floor_es,'MES1_avgR_floor':floor_mes}
        for p in periods:
            for k,v in m[p].items(): row[f'{p}_{k}']=v
        rows.append(row)
    r=pd.DataFrame(rows)
    # Require non-negative signal lift in both development and 2024 before calling a candidate stable.
    stable=r[(r.edge_floor_1R_pp>=0)&(r.edge_floor_2R_pp>=0)].copy()
    stable=stable.sort_values(['edge_floor_sum','ES1_avgR_floor','dev_n'],ascending=[False,False,False])
    print('\nTOP STABLE RULES (selection frozen before looking at 2025/2026 columns)')
    cols=['rule','dev_n','val24_n','edge_floor_1R_pp','edge_floor_2R_pp','dev_win','val24_win','eval25_win','recent26_win',
          'dev_ES1_avgR','val24_ES1_avgR','eval25_ES1_avgR','recent26_ES1_avgR','dev_MES1_avgR','val24_MES1_avgR','eval25_MES1_avgR','recent26_MES1_avgR']
    print(stable.head(15)[cols].round(4).to_string(index=False))
    return r,stable


def high_winrate_report(r):
    print('\n=== 70% WIN-RATE TARGET CHECK ===')
    # A candidate only counts as interesting here if it has enough trades in both dev and 2024.
    x=r[(r.dev_n>=80)&(r.val24_n>=20)].copy()
    x['min_dev_val_win']=x[['dev_win','val24_win']].min(axis=1)
    x=x.sort_values(['min_dev_val_win','edge_floor_sum'],ascending=False)
    cols=['rule','dev_n','val24_n','dev_win','val24_win','eval25_win','recent26_win','edge_floor_1R_pp','edge_floor_2R_pp','ES1_avgR_floor']
    print(x.head(15)[cols].round(4).to_string(index=False))
    over=x[(x.dev_win>=70)&(x.val24_win>=70)]
    print('rules_with_>=70pct_raw_win_in_both_dev_and_2024',len(over))
    if len(over): print(over.head(10)[cols].round(4).to_string(index=False))


def main():
    raw=mb.load_all(); frame=mb.build_frame(raw)
    t=p2.generate_diagnostic(frame)
    t=fixed_add_regime_features(frame,t)
    t['trade_id']=np.arange(len(t))
    base=mb.generate(frame,use_cvd=True)
    print('=== BASELINE REPRODUCTION ===')
    print('base_n',len(base),'phase3_n',len(t),'base_totalR',round(base.R.sum(),6),'phase3_totalR',round(t.R.sum(),6),
          'count_match',len(base)==len(t),'R_diff',round(abs(base.R.sum()-t.R.sum()),10))
    controls=p2.matched_random_controls(frame,t,reps=30)
    stopdf=stop_economics(t)
    allr,stable=candidate_search(t,controls)
    high_winrate_report(allr)
    t.to_csv('phase3a_enriched_trades.csv',index=False)
    controls.to_csv('phase3a_random_controls.csv',index=False)
    stopdf.to_csv('phase3a_stop_economics.csv',index=False)
    allr.to_csv('phase3a_all_candidates.csv',index=False)
    stable.head(25).to_csv('phase3a_top_candidates.csv',index=False)

if __name__=='__main__': main()
