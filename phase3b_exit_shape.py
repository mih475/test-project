import numpy as np
import pandas as pd
import multiyear_backtest as mb
import phase2b_diagnostics as p2
import phase3a_stop_regime as p3

# One conservative research change only: replace VWAP exit with a fixed-R take-profit.
# Entry signal, initial stop, session handling, and all data rules remain frozen.
TP_LEVELS=[0.5,0.75,1.0,1.5,2.0,3.0]


def simulate_fixed_tp(d, tr, tp_r):
    entry=float(tr.entry_price); risk=float(tr.risk_pts); direction=int(tr.dir_sign)
    stop=float(tr.stop_price)
    target=entry+direction*tp_r*risk
    loc=d.index.get_indexer([tr.entry_time])[0]
    if loc<0: return np.nan,'missing_entry'
    for j in range(loc,len(d)):
        r=d.iloc[j]
        if direction==1:
            hit_s=r.low<=stop; hit_t=r.high>=target
        else:
            hit_s=r.high>=stop; hit_t=r.low<=target
        if hit_s and hit_t: return -1.0,'ambiguous_stop_first'
        if hit_s: return -1.0,'stop'
        if hit_t: return float(tp_r),'tp'
    px=float(d.iloc[-1].close)
    rr=direction*(px-entry)/risk
    return rr,'eod'


def stats(vals):
    v=pd.Series(vals,dtype=float).dropna(); w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=(eq-eq.cummax()).min()
    return len(v),100*(v>0).mean(),v.mean(),pf,v.sum(),dd


def net(vals,risk_pts,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0
    comm=5.0 if product=='ES' else 1.50
    return np.asarray(vals)-((slip_ticks*mb.TICK)+(comm/point))/np.asarray(risk_pts)


def report(label,g,col):
    raw=stats(g[col]); es=stats(net(g[col],g.risk_pts,'ES',1)); mes=stats(net(g[col],g.risk_pts,'MES',1))
    return {'exit':label,'n':raw[0],'raw_win':raw[1],'raw_avgR':raw[2],'raw_PF':raw[3],'raw_totalR':raw[4],'raw_DD':raw[5],
            'ES1_win':es[1],'ES1_avgR':es[2],'ES1_PF':es[3],'ES1_DD':es[5],
            'MES1_win':mes[1],'MES1_avgR':mes[2],'MES1_PF':mes[3],'MES1_DD':mes[5]}


def main():
    raw=mb.load_all(); frame=mb.build_frame(raw)
    t=p2.generate_diagnostic(frame).reset_index(drop=True)
    print('=== PHASE 3B: EXIT SHAPE ONLY ===')
    print('Entry/stop logic frozen. Fixed-R TP is the only strategy change. Same-bar stop+TP is scored as stop.')
    print('Selection uses 2021-23 development + 2024 validation. 2025/2026 are reveal-only.')
    by={pd.Timestamp(s):d.copy().sort_index() for s,d in frame.groupby('session',sort=False)}
    for tp in TP_LEVELS:
        vals=[]; reasons=[]
        for _,tr in t.iterrows():
            d=by.get(pd.Timestamp(tr.session))
            rr,why=simulate_fixed_tp(d,tr,tp) if d is not None else (np.nan,'missing_session')
            vals.append(rr); reasons.append(why)
        t[f'R_tp{str(tp).replace(".","p")}']=vals
        t[f'why_tp{str(tp).replace(".","p")}']=reasons

    periods={'DEV21-23':t.year<=2023,'VAL24':t.year==2024,'EVAL25':t.year==2025,'RECENT26':t.year==2026,'ALL':pd.Series(True,index=t.index)}
    rows=[]
    for tp in TP_LEVELS:
        col=f'R_tp{str(tp).replace(".","p")}'
        for per,mask in periods.items():
            x=report(f'TP_{tp:g}R',t[mask],col); x['period']=per; rows.append(x)
    out=pd.DataFrame(rows)
    print('\nFIXED TP RESULTS')
    print(out[['exit','period','n','raw_win','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))

    # Freeze selection without 2025/2026: require positive ES expectancy and PF>1 in BOTH dev and 2024.
    piv=[]
    for tp in TP_LEVELS:
        a=out[(out.exit==f'TP_{tp:g}R') & (out.period=='DEV21-23')].iloc[0]
        b=out[(out.exit==f'TP_{tp:g}R') & (out.period=='VAL24')].iloc[0]
        piv.append({'tp_R':tp,'dev_win':a.raw_win,'val24_win':b.raw_win,'dev_ES1_avgR':a.ES1_avgR,'val24_ES1_avgR':b.ES1_avgR,
                    'dev_ES1_PF':a.ES1_PF,'val24_ES1_PF':b.ES1_PF,'floor_avgR':min(a.ES1_avgR,b.ES1_avgR),'floor_PF':min(a.ES1_PF,b.ES1_PF)})
    sel=pd.DataFrame(piv).sort_values(['floor_avgR','floor_PF'],ascending=False)
    print('\nSELECTION TABLE (2025/2026 NOT USED)')
    print(sel.round(4).to_string(index=False))
    qualified=sel[(sel.floor_avgR>0)&(sel.floor_PF>1.0)]
    if len(qualified):
        chosen=float(qualified.iloc[0].tp_R); print('FROZEN_CANDIDATE_TP_R',chosen)
        print('\nOUT-OF-SAMPLE REVEAL FOR FROZEN CANDIDATE')
        print(out[out.exit==f'TP_{chosen:g}R'][['period','n','raw_win','raw_avgR','raw_PF','ES1_avgR','ES1_PF','MES1_avgR','MES1_PF','ES1_DD']].round(4).to_string(index=False))
    else:
        print('FROZEN_CANDIDATE_TP_R NONE -- no fixed TP had positive ES1 expectancy and PF>1 in both DEV21-23 and VAL24')
    print('\n70_PERCENT_CHECK')
    for tp in TP_LEVELS:
        a=out[(out.exit==f'TP_{tp:g}R')&(out.period=='DEV21-23')].iloc[0]; b=out[(out.exit==f'TP_{tp:g}R')&(out.period=='VAL24')].iloc[0]
        print(f'TP {tp:g}R dev_win={a.raw_win:.2f}% val24_win={b.raw_win:.2f}% both_ge70={bool(a.raw_win>=70 and b.raw_win>=70)}')
    out.to_csv('phase3b_exit_results.csv',index=False); sel.to_csv('phase3b_selection.csv',index=False); t.to_csv('phase3b_trades.csv',index=False)

if __name__=='__main__': main()
