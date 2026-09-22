import numpy as np
import pandas as pd
import multiyear_backtest as mb
import phase2b_diagnostics as p2

BE_TRIGGERS=[0.5,0.75,1.0,1.5,2.0]

def simulate_be(d,tr,trigger_r):
    """Original VWAP target and initial stop, with one change: after price reaches
    +trigger_r R, move the stop to entry. Conservative 1-minute ordering: if a bar
    can both arm BE and touch the original stop/target, adverse outcome is assumed.
    Once BE is armed, a bar touching both BE and target is scored as BE.
    """
    entry=float(tr.entry_price); risk=float(tr.risk_pts); direction=int(tr.dir_sign)
    stop=float(tr.stop_price); target=float(tr.target_price)
    loc=d.index.get_indexer([tr.entry_time])[0]
    if loc<0:return np.nan,'missing_entry'
    armed=False
    trigger=entry+direction*trigger_r*risk
    for j in range(loc,len(d)):
        r=d.iloc[j]
        if direction==1:
            hit_orig=r.low<=stop; hit_target=r.high>=target; hit_trigger=r.high>=trigger; hit_be=r.low<=entry
        else:
            hit_orig=r.high>=stop; hit_target=r.low<=target; hit_trigger=r.low<=trigger; hit_be=r.high>=entry
        if not armed:
            if hit_orig and (hit_target or hit_trigger): return -1.0,'ambiguous_original_stop_first'
            if hit_orig:return -1.0,'stop'
            if hit_target:
                rr=direction*(target-entry)/risk
                return rr,'target_before_be'
            if hit_trigger:
                # Intrabar path after trigger is unknowable. If the same bar also
                # touches entry, conservatively assume BE immediately after arming.
                if hit_be:return 0.0,'ambiguous_arm_then_be'
                armed=True
        else:
            if hit_be and hit_target:return 0.0,'ambiguous_be_first'
            if hit_be:return 0.0,'breakeven'
            if hit_target:
                rr=direction*(target-entry)/risk
                return rr,'target'
    px=float(d.iloc[-1].close)
    rr=direction*(px-entry)/risk
    if armed and rr<0: rr=0.0
    return rr,'eod'

def stats(vals):
    v=pd.Series(vals,dtype=float).dropna(); w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return len(v),100*(v>0).mean(),v.mean(),pf,v.sum(),dd.min(),100*(v==0).mean()

def net(vals,risk_pts,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0; comm=5.0 if product=='ES' else 1.50
    return np.asarray(vals)-((slip_ticks*mb.TICK)+(comm/point))/np.asarray(risk_pts)

def report(label,g,col):
    raw=stats(g[col]); es=stats(net(g[col],g.risk_pts,'ES',1)); mes=stats(net(g[col],g.risk_pts,'MES',1))
    return {'exit':label,'n':raw[0],'raw_win':raw[1],'raw_be':raw[6],'raw_avgR':raw[2],'raw_PF':raw[3],
            'ES1_avgR':es[2],'ES1_PF':es[3],'ES1_DD':es[5],'MES1_avgR':mes[2],'MES1_PF':mes[3]}

def main():
    raw=mb.load_all(); frame=mb.build_frame(raw); t=p2.generate_diagnostic(frame).reset_index(drop=True)
    print('=== PHASE 3C: BREAKEVEN PROTECTION ONLY ===')
    print('Entry, initial stop, and original VWAP target are frozen. Only change: move stop to entry after +X R.')
    print('Conservative 1-minute ambiguity rules favor the adverse/BE outcome. Selection uses 2021-23 + 2024 only; 2025/2026 reveal-only.')
    by={pd.Timestamp(s):d.copy().sort_index() for s,d in frame.groupby('session',sort=False)}
    for trig in BE_TRIGGERS:
        vals=[]
        for _,tr in t.iterrows():
            d=by.get(pd.Timestamp(tr.session)); rr,_=simulate_be(d,tr,trig) if d is not None else (np.nan,'missing_session'); vals.append(rr)
        t[f'R_be{str(trig).replace(".","p")}']=vals
    periods={'DEV21-23':t.year<=2023,'VAL24':t.year==2024,'EVAL25':t.year==2025,'RECENT26':t.year==2026,'ALL':pd.Series(True,index=t.index)}
    rows=[]
    for trig in BE_TRIGGERS:
        col=f'R_be{str(trig).replace(".","p")}'
        for per,mask in periods.items():
            x=report(f'BE_after_{trig:g}R',t[mask],col); x['period']=per; rows.append(x)
    out=pd.DataFrame(rows)
    print('\nBREAKEVEN RESULTS')
    print(out[['exit','period','n','raw_win','raw_be','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))
    sel=[]
    for trig in BE_TRIGGERS:
        label=f'BE_after_{trig:g}R'; a=out[(out.exit==label)&(out.period=='DEV21-23')].iloc[0]; b=out[(out.exit==label)&(out.period=='VAL24')].iloc[0]
        sel.append({'trigger_R':trig,'dev_win':a.raw_win,'val24_win':b.raw_win,'dev_ES1_avgR':a.ES1_avgR,'val24_ES1_avgR':b.ES1_avgR,
                    'dev_ES1_PF':a.ES1_PF,'val24_ES1_PF':b.ES1_PF,'floor_avgR':min(a.ES1_avgR,b.ES1_avgR),'floor_PF':min(a.ES1_PF,b.ES1_PF)})
    sel=pd.DataFrame(sel).sort_values(['floor_avgR','floor_PF'],ascending=False)
    print('\nSELECTION TABLE (2025/2026 NOT USED)'); print(sel.round(4).to_string(index=False))
    q=sel[(sel.floor_avgR>0)&(sel.floor_PF>1.0)]
    if len(q):
        chosen=float(q.iloc[0].trigger_R); label=f'BE_after_{chosen:g}R'; print('FROZEN_CANDIDATE_BE_TRIGGER_R',chosen)
        print('\nOUT-OF-SAMPLE REVEAL'); print(out[out.exit==label][['period','n','raw_win','raw_be','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))
    else: print('FROZEN_CANDIDATE_BE_TRIGGER_R NONE')
    print('\n70_PERCENT_CHECK')
    for trig in BE_TRIGGERS:
        label=f'BE_after_{trig:g}R'; a=out[(out.exit==label)&(out.period=='DEV21-23')].iloc[0]; b=out[(out.exit==label)&(out.period=='VAL24')].iloc[0]
        print(f'BE {trig:g}R dev_win={a.raw_win:.2f}% val24_win={b.raw_win:.2f}% both_ge70={bool(a.raw_win>=70 and b.raw_win>=70)}')
    out.to_csv('phase3a_stop_economics.csv',index=False); sel.to_csv('phase3a_top_candidates.csv',index=False); t.to_csv('phase3a_enriched_trades.csv',index=False)
    pd.DataFrame().to_csv('phase3a_random_controls.csv',index=False); sel.to_csv('phase3a_all_candidates.csv',index=False)
if __name__=='__main__': main()
