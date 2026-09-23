import numpy as np
import pandas as pd
import multiyear_backtest as mb
import phase2b_diagnostics as p2

# Phase 3E deliberately tests ONE entry/regime filter at a time. Thresholds are
# learned only from 2021-23 quartiles; 2024 validates; 2025/26 are reveal-only.
FEATURES=['dir_vwap_slope_z','range_ratio_prior20','or_ratio_prior20','relvol20','vol20','distance_from_vwap_z','risk_pts','target_R']
MIN_DEV=80
MIN_VAL=25

def stats(vals):
    v=pd.Series(vals,dtype=float).dropna(); w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return {'n':len(v),'win':100*(v>0).mean() if len(v) else np.nan,'avgR':v.mean() if len(v) else np.nan,
            'PF':pf,'DD':dd.min() if len(v) else np.nan}

def net_r(g,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0; comm=5.0 if product=='ES' else 1.50
    return g.R.to_numpy()-((slip_ticks*mb.TICK)+(comm/point))/g.risk_pts.to_numpy()

def metrics(g):
    raw=stats(g.R); es=stats(net_r(g,'ES',1)); mes=stats(net_r(g,'MES',1))
    return {'n':raw['n'],'raw_win':raw['win'],'raw_avgR':raw['avgR'],'raw_PF':raw['PF'],
            'ES1_avgR':es['avgR'],'ES1_PF':es['PF'],'ES1_DD':es['DD'],'MES1_avgR':mes['avgR'],'MES1_PF':mes['PF']}

def main():
    raw=mb.load_all(); frame=mb.build_frame(raw)
    t=p2.add_regime_features(frame,p2.generate_diagnostic(frame)).replace([np.inf,-np.inf],np.nan).reset_index(drop=True)
    dev=t[t.year<=2023]; val=t[t.year==2024]
    print('=== PHASE 3E: ONE-FILTER ENTRY SELECTIVITY ===')
    print('Original entry/stop/VWAP exit frozen. Exactly one filter is tested per rule. Thresholds come only from 2021-23 quartiles; 2024 validates; 2025/2026 reveal-only.')
    print('Costs: ES $5 RT and MES $1.50 RT plus 1 total adverse tick. No 2025/26 data participate in ranking.')
    candidates=[]
    for feat in FEATURES:
        x=dev[feat].dropna()
        if len(x)<100: continue
        qs=sorted(set(float(z) for z in x.quantile([.25,.5,.75]).values))
        for q in qs:
            for side in ('LE','GE'):
                md=(dev[feat]<=q) if side=='LE' else (dev[feat]>=q)
                mv=(val[feat]<=q) if side=='LE' else (val[feat]>=q)
                gd=dev[md]; gv=val[mv]
                if len(gd)<MIN_DEV or len(gv)<MIN_VAL: continue
                a=metrics(gd); b=metrics(gv)
                candidates.append({'feature':feat,'side':side,'threshold':q,'dev_n':len(gd),'val_n':len(gv),
                    'dev_win':a['raw_win'],'val_win':b['raw_win'],'dev_ES1_avgR':a['ES1_avgR'],'val_ES1_avgR':b['ES1_avgR'],
                    'dev_ES1_PF':a['ES1_PF'],'val_ES1_PF':b['ES1_PF'],'floor_avgR':min(a['ES1_avgR'],b['ES1_avgR']),
                    'floor_PF':min(a['ES1_PF'],b['ES1_PF'])})
    c=pd.DataFrame(candidates).sort_values(['floor_avgR','floor_PF'],ascending=False).reset_index(drop=True)
    print('\nTOP SINGLE-FILTER RULES -- RANKED WITHOUT 2025/26')
    print(c.head(20).round(4).to_string(index=False))
    # Require positive after-cost expectancy and PF>1 in BOTH development and validation.
    q=c[(c.floor_avgR>0)&(c.floor_PF>1.0)]
    if len(q)==0:
        print('\nFROZEN_CANDIDATE NONE')
        print('INTERPRETATION: no single simple entry/regime filter produced positive ES after-cost expectancy in both development and 2024 validation. Further threshold mining would risk overfit.')
    else:
        best=q.iloc[0]; feat=best.feature; th=float(best.threshold); side=best.side
        print(f'\nFROZEN_CANDIDATE {feat} {side} {th:.8g}')
        mask=(t[feat]<=th) if side=='LE' else (t[feat]>=th)
        z=t[mask].copy()
        periods={'DEV21-23':z.year<=2023,'VAL24':z.year==2024,'EVAL25':z.year==2025,'RECENT26':z.year==2026,'ALL':pd.Series(True,index=z.index)}
        rows=[]
        for name,m in periods.items():
            mm=metrics(z[m]); mm['period']=name; rows.append(mm)
        reveal=pd.DataFrame(rows)
        print('\nFROZEN RULE REVEAL'); print(reveal[['period','n','raw_win','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))
        a=reveal[reveal.period=='DEV21-23'].iloc[0]; b=reveal[reveal.period=='VAL24'].iloc[0]
        qualifies70=bool(a.raw_win>=70 and b.raw_win>=70 and a.ES1_PF>=1.25 and b.ES1_PF>=1.25 and a.ES1_avgR>0 and b.ES1_avgR>0)
        print('ROBUSTNESS_GATE_70',qualifies70)
    c.to_csv('phase3a_all_candidates.csv',index=False); c.head(20).to_csv('phase3a_top_candidates.csv',index=False)
    t.to_csv('phase3a_enriched_trades.csv',index=False); pd.DataFrame().to_csv('phase3a_random_controls.csv',index=False)
    c.to_csv('phase3a_stop_economics.csv',index=False)
if __name__=='__main__': main()
