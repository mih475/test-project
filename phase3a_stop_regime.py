import numpy as np
import pandas as pd
import multiyear_backtest as mb
import phase2b_diagnostics as p2

PARTIAL_FRACS=[0.25,0.50,0.75]
TRIGGER_R=1.0

def simulate_partial(d,tr,frac):
    """Take frac of position at +1R; leave remainder for original VWAP target.
    Initial stop never moves. Same-bar stop/+1R ambiguity is scored as stop first.
    This is the only strategy change in Phase 3D.
    """
    entry=float(tr.entry_price); risk=float(tr.risk_pts); direction=int(tr.dir_sign)
    stop=float(tr.stop_price); target=float(tr.target_price)
    loc=d.index.get_indexer([tr.entry_time])[0]
    if loc<0:return np.nan,'missing_entry'
    trigger=entry+direction*TRIGGER_R*risk
    partial=False
    for j in range(loc,len(d)):
        r=d.iloc[j]
        if direction==1:
            hit_stop=r.low<=stop; hit_target=r.high>=target; hit_trigger=r.high>=trigger
        else:
            hit_stop=r.high>=stop; hit_target=r.low<=target; hit_trigger=r.low<=trigger
        target_r=direction*(target-entry)/risk
        if not partial:
            if hit_stop and (hit_target or hit_trigger): return -1.0,'ambiguous_stop_first'
            if hit_stop:return -1.0,'stop_before_partial'
            # If VWAP target is closer than +1R, the original target exits the full trade.
            if hit_target and target_r<=TRIGGER_R:return target_r,'target_before_partial'
            if hit_trigger:
                partial=True
                # If target is also touched on this bar after the +1R level, both pieces are realized.
                if hit_target:
                    return frac*TRIGGER_R+(1-frac)*target_r,'partial_then_target_same_bar'
            elif hit_target:
                return target_r,'target'
        else:
            if hit_stop and hit_target:
                runner_r=-1.0
                return frac*TRIGGER_R+(1-frac)*runner_r,'ambiguous_runner_stop_first'
            if hit_stop:
                return frac*TRIGGER_R+(1-frac)*(-1.0),'runner_stop'
            if hit_target:
                return frac*TRIGGER_R+(1-frac)*target_r,'runner_target'
    px=float(d.iloc[-1].close); runner_r=direction*(px-entry)/risk
    if partial:return frac*TRIGGER_R+(1-frac)*runner_r,'partial_runner_eod'
    return runner_r,'eod'

def stats(vals):
    v=pd.Series(vals,dtype=float).dropna(); w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return len(v),100*(v>0).mean(),v.mean(),pf,v.sum(),dd.min()

def net(vals,risk_pts,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0; comm=5.0 if product=='ES' else 1.50
    return np.asarray(vals)-((slip_ticks*mb.TICK)+(comm/point))/np.asarray(risk_pts)

def report(label,g,col):
    raw=stats(g[col]); es=stats(net(g[col],g.risk_pts,'ES',1)); mes=stats(net(g[col],g.risk_pts,'MES',1))
    return {'exit':label,'n':raw[0],'raw_win':raw[1],'raw_avgR':raw[2],'raw_PF':raw[3],'raw_DD':raw[5],
            'ES1_avgR':es[2],'ES1_PF':es[3],'ES1_DD':es[5],'MES1_avgR':mes[2],'MES1_PF':mes[3]}

def main():
    raw=mb.load_all(); frame=mb.build_frame(raw); t=p2.generate_diagnostic(frame).reset_index(drop=True)
    print('=== PHASE 3D: PARTIAL +1R, RUNNER TO ORIGINAL VWAP ===')
    print('Entry, initial stop, and original VWAP target are frozen. Only change: take 25/50/75% at +1R; runner keeps original stop and VWAP target.')
    print('Same-bar stop/+1R ambiguity is adverse. Selection uses 2021-23 + 2024 only; 2025/2026 reveal-only.')
    by={pd.Timestamp(s):d.copy().sort_index() for s,d in frame.groupby('session',sort=False)}
    for frac in PARTIAL_FRACS:
        vals=[]
        for _,tr in t.iterrows():
            d=by.get(pd.Timestamp(tr.session)); rr,_=simulate_partial(d,tr,frac) if d is not None else (np.nan,'missing_session'); vals.append(rr)
        t[f'R_partial{int(frac*100)}']=vals
    periods={'DEV21-23':t.year<=2023,'VAL24':t.year==2024,'EVAL25':t.year==2025,'RECENT26':t.year==2026,'ALL':pd.Series(True,index=t.index)}
    rows=[]
    for frac in PARTIAL_FRACS:
        col=f'R_partial{int(frac*100)}'; label=f'PARTIAL_{int(frac*100)}pct_at_1R'
        for per,mask in periods.items():
            x=report(label,t[mask],col); x['period']=per; rows.append(x)
    out=pd.DataFrame(rows)
    print('\nPARTIAL RESULTS')
    print(out[['exit','period','n','raw_win','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))
    sel=[]
    for frac in PARTIAL_FRACS:
        label=f'PARTIAL_{int(frac*100)}pct_at_1R'; a=out[(out.exit==label)&(out.period=='DEV21-23')].iloc[0]; b=out[(out.exit==label)&(out.period=='VAL24')].iloc[0]
        sel.append({'partial_frac':frac,'dev_win':a.raw_win,'val24_win':b.raw_win,'dev_ES1_avgR':a.ES1_avgR,'val24_ES1_avgR':b.ES1_avgR,
                    'dev_ES1_PF':a.ES1_PF,'val24_ES1_PF':b.ES1_PF,'floor_avgR':min(a.ES1_avgR,b.ES1_avgR),'floor_PF':min(a.ES1_PF,b.ES1_PF)})
    sel=pd.DataFrame(sel).sort_values(['floor_avgR','floor_PF'],ascending=False)
    print('\nSELECTION TABLE (2025/2026 NOT USED)'); print(sel.round(4).to_string(index=False))
    q=sel[(sel.floor_avgR>0)&(sel.floor_PF>1.0)]
    if len(q):
        chosen=float(q.iloc[0].partial_frac); label=f'PARTIAL_{int(chosen*100)}pct_at_1R'; print('FROZEN_CANDIDATE_PARTIAL_FRAC',chosen)
        print('\nOUT-OF-SAMPLE REVEAL'); print(out[out.exit==label][['period','n','raw_win','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))
    else: print('FROZEN_CANDIDATE_PARTIAL_FRAC NONE')
    print('\n70_PERCENT_CHECK')
    for frac in PARTIAL_FRACS:
        label=f'PARTIAL_{int(frac*100)}pct_at_1R'; a=out[(out.exit==label)&(out.period=='DEV21-23')].iloc[0]; b=out[(out.exit==label)&(out.period=='VAL24')].iloc[0]
        print(f'partial={frac:.2f} dev_win={a.raw_win:.2f}% val24_win={b.raw_win:.2f}% both_ge70={bool(a.raw_win>=70 and b.raw_win>=70)}')
    out.to_csv('phase3a_stop_economics.csv',index=False); sel.to_csv('phase3a_top_candidates.csv',index=False); t.to_csv('phase3a_enriched_trades.csv',index=False)
    pd.DataFrame().to_csv('phase3a_random_controls.csv',index=False); sel.to_csv('phase3a_all_candidates.csv',index=False)
if __name__=='__main__': main()
