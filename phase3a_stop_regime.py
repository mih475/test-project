import numpy as np
import pandas as pd
import multiyear_backtest as mb

# PHASE 3F: genuinely different entry timing, not another regime-threshold sweep.
# The underlying setup, excursion stop, and VWAP target are frozen at the original
# reclaim bar. Only the entry trigger changes. Two pre-specified confirmations are
# tested inside a fixed 3-minute window.
MODES=['BREAK_TOUCH_3','BREAK_CLOSE_3']
MAX_WAIT=3
MIN_DEV=80
MIN_VAL=25


def _stats(v):
    v=pd.Series(v,dtype=float).dropna()
    if len(v)==0:
        return {'n':0,'win':np.nan,'avgR':np.nan,'PF':np.nan,'DD':np.nan,'totalR':np.nan}
    w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return {'n':len(v),'win':100*(v>0).mean(),'avgR':v.mean(),'PF':pf,'DD':dd.min(),'totalR':v.sum()}


def _net_r(g,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0
    comm=5.0 if product=='ES' else 1.50
    cost_pts=slip_ticks*mb.TICK + comm/point
    return g.R.to_numpy() - cost_pts/g.risk_pts.to_numpy()


def metrics(g,product='ES',slip_ticks=1):
    raw=_stats(g.R)
    net=_stats(_net_r(g,product,slip_ticks))
    return {'n':raw['n'],'raw_win':raw['win'],'raw_avgR':raw['avgR'],'raw_PF':raw['PF'],
            'net_win':net['win'],'net_avgR':net['avgR'],'net_PF':net['PF'],'net_DD':net['DD'],'net_totalR':net['totalR']}


def _start_excursion(d,i,row,below,above):
    if below and not above:
        prior=d.iloc[max(0,i-20):i]
        if len(prior)==0:return None
        k=prior.low.idxmin()
        return {'dir':1,'extreme':float(row.low),'cvd_ext':float(row.cvd_proxy),
                'ref_price':float(prior.loc[k,'low']),'ref_cvd':float(prior.loc[k,'cvd_proxy'])}
    if above and not below:
        prior=d.iloc[max(0,i-20):i]
        if len(prior)==0:return None
        k=prior.high.idxmax()
        return {'dir':-1,'extreme':float(row.high),'cvd_ext':float(row.cvd_proxy),
                'ref_price':float(prior.loc[k,'high']),'ref_cvd':float(prior.loc[k,'cvd_proxy'])}
    return None


def generate_confirmed(frame,mode):
    trades=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); busy=-1; excursion=None; pending=None
        if len(d)<120:continue
        for i in range(60,len(d)-1):
            if i<=busy:continue
            row=d.iloc[i]

            # Once a valid reclaim occurs, wait at most three full 1-minute bars for
            # confirmation. Stop/target/new-extreme before confirmation invalidates
            # the setup; we never enter after the mean-reversion move already happened.
            if pending is not None:
                if i>pending['expires']:
                    pending=None; excursion=None
                else:
                    dirn=pending['dir']; stop=pending['stop']; target=pending['target']
                    if dirn==1:
                        hit_stop=row.low<=stop; hit_target=row.high>=target
                        new_extreme=row.low<pending['extreme']
                        confirm=(row.high>pending['confirm_level']) if mode=='BREAK_TOUCH_3' else (row.close>pending['confirm_level'])
                    else:
                        hit_stop=row.high>=stop; hit_target=row.low<=target
                        new_extreme=row.high>pending['extreme']
                        confirm=(row.low<pending['confirm_level']) if mode=='BREAK_TOUCH_3' else (row.close<pending['confirm_level'])
                    if hit_stop or hit_target or new_extreme:
                        pending=None; excursion=None; continue
                    if confirm:
                        entry_i=i+1
                        if entry_i>=len(d):
                            pending=None; excursion=None; continue
                        entry=float(d.iloc[entry_i].open)
                        if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                            pending=None; excursion=None; continue
                        out=mb.simulate(d,entry_i,dirn,stop,target)
                        if out is None:
                            pending=None; excursion=None; continue
                        rr,j,why,mfe,mae=out
                        trades.append({'session':pd.Timestamp(sess),'year':pd.Timestamp(sess).year,
                            'reclaim_time':pending['reclaim_time'],'signal_time':d.index[i],
                            'direction':'long' if dirn==1 else 'short','entry_hour':d.index[i].hour,
                            'R':rr,'MFE_R':mfe,'MAE_R':mae,'exit_reason':why,
                            'risk_pts':abs(entry-stop),'target_R':abs(target-entry)/abs(entry-stop),
                            'confirm_delay_bars':i-pending['reclaim_i'],'symbol':row.symbol,'mode':mode})
                        busy=j; pending=None; excursion=None; continue
                    # Still waiting for confirmation; don't create another setup simultaneously.
                    continue

            if not np.isfinite(row.u2) or not np.isfinite(row.l2):continue
            below=row.low<row.l2; above=row.high>row.u2
            if excursion is None:
                excursion=_start_excursion(d,i,row,below,above)
                continue

            if excursion['dir']==1 and row.low<excursion['extreme']:
                excursion['extreme']=float(row.low); excursion['cvd_ext']=float(row.cvd_proxy)
            if excursion['dir']==-1 and row.high>excursion['extreme']:
                excursion['extreme']=float(row.high); excursion['cvd_ext']=float(row.cvd_proxy)
            dirn=excursion['dir']
            inside1=(row.close>row.l2) if dirn==1 else (row.close<row.u2)
            vals=[row.get('close5'),row.get('u2_5'),row.get('l2_5'),row.get('close30'),row.get('u2_30'),row.get('l2_30')]
            if not inside1 or any(pd.isna(v) for v in vals):continue
            inside5=(row['close5']>row['l2_5']) if dirn==1 else (row['close5']<row['u2_5'])
            inside30=(row['close30']>row['l2_30']) if dirn==1 else (row['close30']<row['u2_30'])
            if not(inside5 and inside30):continue
            if dirn==1:
                div=excursion['extreme']<excursion['ref_price'] and excursion['cvd_ext']>excursion['ref_cvd']
            else:
                div=excursion['extreme']>excursion['ref_price'] and excursion['cvd_ext']<excursion['ref_cvd']
            if not div:
                excursion=None; continue

            stop=(excursion['extreme']-mb.TICK) if dirn==1 else (excursion['extreme']+mb.TICK)
            target=float(row.vwap)
            # Freeze stop and target at the original reclaim bar. Only entry timing changes.
            pending={'dir':dirn,'extreme':float(excursion['extreme']),'stop':stop,'target':target,
                     'confirm_level':float(row.high if dirn==1 else row.low),'reclaim_i':i,
                     'reclaim_time':d.index[i],'expires':i+MAX_WAIT}
            excursion=None
    return pd.DataFrame(trades)


def tail_check(g,product='ES',slip_ticks=1):
    if len(g)==0:return {}
    net=pd.Series(_net_r(g,product,slip_ticks),index=g.index)
    base=_stats(net)
    s=net.sort_values(ascending=False)
    out={'base_avgR':base['avgR'],'base_PF':base['PF'],'base_totalR':base['totalR']}
    for k in (1,3,5):
        z=net.drop(index=s.index[:min(k,len(s))])
        st=_stats(z); out[f'drop{k}_avgR']=st['avgR']; out[f'drop{k}_PF']=st['PF']; out[f'drop{k}_totalR']=st['totalR']
    return out


def main():
    raw=mb.load_all(); frame=mb.build_frame(raw)
    baseline=mb.generate(frame,use_cvd=True)
    print('=== PHASE 3F: CONFIRMATION-ENTRY REDESIGN ===')
    print('Hypothesis: original reclaim entry is premature. Setup/CVD-proxy/stop/VWAP target are frozen; only entry timing changes.')
    print('Two pre-specified rules only: BREAK_TOUCH_3 and BREAK_CLOSE_3. Confirmation window is fixed at 3 bars.')
    print('If stop, target, or a new excursion extreme occurs before confirmation, setup is cancelled. Entry is next-bar open after confirmation.')
    print('Selection: 2021-23 development + 2024 validation only. 2025/26 reveal-only. Costs include commissions plus total adverse slippage.')

    bdev=baseline[baseline.year<=2023]; bval=baseline[baseline.year==2024]
    print('\nBASELINE REFERENCE')
    for name,g in [('DEV21-23',bdev),('VAL24',bval)]:
        m=metrics(g,'ES',1); print(name,{k:round(v,4) if isinstance(v,(float,np.floating)) else v for k,v in m.items()})

    all_trades=[]; selection=[]
    for mode in MODES:
        t=generate_confirmed(frame,mode)
        all_trades.append(t)
        dev=t[t.year<=2023]; val=t[t.year==2024]
        md=metrics(dev,'ES',1); mv=metrics(val,'ES',1)
        selection.append({'mode':mode,'dev_n':len(dev),'val_n':len(val),'dev_net_win':md['net_win'],'val_net_win':mv['net_win'],
            'dev_ES1_avgR':md['net_avgR'],'val_ES1_avgR':mv['net_avgR'],'dev_ES1_PF':md['net_PF'],'val_ES1_PF':mv['net_PF'],
            'floor_avgR':min(md['net_avgR'],mv['net_avgR']),'floor_PF':min(md['net_PF'],mv['net_PF'])})
    sel=pd.DataFrame(selection).sort_values(['floor_avgR','floor_PF'],ascending=False).reset_index(drop=True)
    print('\nSELECTION TABLE -- 2025/26 NOT USED')
    print(sel.round(4).to_string(index=False))

    eligible=sel[(sel.dev_n>=MIN_DEV)&(sel.val_n>=MIN_VAL)&(sel.floor_avgR>0)&(sel.floor_PF>1.0)]
    combined=pd.concat(all_trades,ignore_index=True) if all_trades else pd.DataFrame()
    if len(eligible)==0:
        print('\nFROZEN_CANDIDATE NONE')
        print('INTERPRETATION: neither pre-specified confirmation entry produced positive ES after-cost expectancy in both development and 2024 validation with adequate sample size.')
    else:
        chosen=eligible.iloc[0].mode
        print('\nFROZEN_CANDIDATE',chosen)
        z=combined[combined['mode']==chosen].copy()
        periods={'DEV21-23':z.year<=2023,'VAL24':z.year==2024,'EVAL25':z.year==2025,'RECENT26':z.year==2026,'ALL':pd.Series(True,index=z.index)}
        rows=[]
        for name,mask in periods.items():
            g=z[mask]
            for product in ('ES','MES'):
                for slip in (0,1,2,4):
                    m=metrics(g,product,slip); m.update({'period':name,'product':product,'slip_ticks':slip}); rows.append(m)
        reveal=pd.DataFrame(rows)
        print('\nFROZEN RULE COST/SLIPPAGE REVEAL')
        print(reveal[['period','product','slip_ticks','n','net_win','net_avgR','net_PF','net_DD']].round(4).to_string(index=False))
        print('\nTAIL ROBUSTNESS -- ES 1 TICK')
        for name in ('DEV21-23','VAL24','EVAL25','RECENT26'):
            g=z[periods[name]]; print(name,{k:round(v,4) for k,v in tail_check(g,'ES',1).items()})
        a=reveal[(reveal.period=='DEV21-23')&(reveal.product=='ES')&(reveal.slip_ticks==1)].iloc[0]
        b=reveal[(reveal.period=='VAL24')&(reveal.product=='ES')&(reveal.slip_ticks==1)].iloc[0]
        gate70=bool(a.net_win>=70 and b.net_win>=70 and a.net_PF>=1.25 and b.net_PF>=1.25 and a.net_avgR>0 and b.net_avgR>0)
        print('\nROBUSTNESS_GATE_70',gate70)
        reveal.to_csv('phase3a_stop_economics.csv',index=False)

    sel.to_csv('phase3a_top_candidates.csv',index=False)
    sel.to_csv('phase3a_all_candidates.csv',index=False)
    combined.to_csv('phase3a_enriched_trades.csv',index=False)
    pd.DataFrame().to_csv('phase3a_random_controls.csv',index=False)
    if len(eligible)==0:
        sel.to_csv('phase3a_stop_economics.csv',index=False)

if __name__=='__main__': main()
