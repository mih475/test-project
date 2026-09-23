import numpy as np
import pandas as pd
import multiyear_backtest as mb

# PHASE 3G: structural timeframe test, not a parameter sweep.
# Two pre-specified primary bar sizes only: 3-minute and 5-minute.
# The thesis remains 2-sigma excursion -> CVD-proxy divergence -> reclaim -> VWAP.
# Stop remains one tick beyond the excursion extreme; target remains session VWAP.
# Development = 2021-23, validation = 2024, 2025/26 reveal only after a candidate
# passes positive after-cost expectancy/PF in both development and validation.
TIMEFRAMES=[3,5]
MIN_DEV=60
MIN_VAL=20


def _stats(v):
    v=pd.Series(v,dtype=float).dropna()
    if len(v)==0:
        return {'n':0,'win':np.nan,'avgR':np.nan,'PF':np.nan,'DD':np.nan,'totalR':np.nan}
    w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return {'n':len(v),'win':100*(v>0).mean(),'avgR':v.mean(),'PF':pf,
            'DD':dd.min(),'totalR':v.sum()}


def _net_r(g,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0
    comm=5.0 if product=='ES' else 1.50
    cost_pts=slip_ticks*mb.TICK + comm/point
    return g.R.to_numpy() - cost_pts/g.risk_pts.to_numpy()


def metrics(g,product='ES',slip_ticks=1):
    raw=_stats(g.R)
    net=_stats(_net_r(g,product,slip_ticks))
    return {'n':raw['n'],'raw_win':raw['win'],'raw_avgR':raw['avgR'],'raw_PF':raw['PF'],
            'net_win':net['win'],'net_avgR':net['avgR'],'net_PF':net['PF'],
            'net_DD':net['DD'],'net_totalR':net['totalR']}


def add_cvd_proxy(x):
    x=x.copy()
    prev=x.groupby('session').close.shift(1)
    fallback=np.sign((x.close-prev).fillna(0))
    direction=np.where(x.close>x.open,1,np.where(x.close<x.open,-1,fallback))
    x['delta_proxy']=direction*x.volume
    x['cvd_proxy']=x.groupby('session').delta_proxy.cumsum()
    return x


def build_primary(raw,minutes):
    rule=f'{minutes}min'
    primary=add_cvd_proxy(mb.resample_session(raw,rule))
    tf30=mb.resample_session(raw,'30min')
    tf5=mb.resample_session(raw,'5min') if minutes==3 else None
    pieces=[]
    for sess,g in primary.groupby('session',sort=False):
        z=g.copy().reset_index().rename(columns={'datetime_et':'ts'})
        if minutes==3:
            r=tf5[tf5.session==sess][['close','u2','l2']].reset_index().rename(
                columns={'datetime_et':'tf_ts','close':'close5','u2':'u2_5','l2':'l2_5'})
            z=pd.merge_asof(z.sort_values('ts'),r.sort_values('tf_ts'),
                            left_on='ts',right_on='tf_ts',direction='backward')
        r=tf30[tf30.session==sess][['close','u2','l2']].reset_index().rename(
            columns={'datetime_et':'tf_ts','close':'close30','u2':'u2_30','l2':'l2_30'})
        z=pd.merge_asof(z.sort_values('ts'),r.sort_values('tf_ts'),
                        left_on='ts',right_on='tf_ts',direction='backward')
        z=z.set_index('ts'); z.index.name='datetime_et'; pieces.append(z)
    return pd.concat(pieces).sort_index()


def _start_excursion(d,i,row,below,above,prior_bars):
    if below and not above:
        prior=d.iloc[max(0,i-prior_bars):i]
        if len(prior)==0:return None
        k=prior.low.idxmin()
        return {'dir':1,'extreme':float(row.low),'cvd_ext':float(row.cvd_proxy),
                'ref_price':float(prior.loc[k,'low']),'ref_cvd':float(prior.loc[k,'cvd_proxy'])}
    if above and not below:
        prior=d.iloc[max(0,i-prior_bars):i]
        if len(prior)==0:return None
        k=prior.high.idxmax()
        return {'dir':-1,'extreme':float(row.high),'cvd_ext':float(row.cvd_proxy),
                'ref_price':float(prior.loc[k,'high']),'ref_cvd':float(prior.loc[k,'cvd_proxy'])}
    return None


def generate_primary(frame,minutes):
    trades=[]
    warmup_bars=int(np.ceil(60.0/minutes))
    prior_bars=int(np.ceil(20.0/minutes))
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); busy=-1; excursion=None
        if len(d)<warmup_bars+20:continue
        for i in range(warmup_bars,len(d)-1):
            if i<=busy:continue
            row=d.iloc[i]
            if not np.isfinite(row.u2) or not np.isfinite(row.l2):continue
            below=row.low<row.l2; above=row.high>row.u2
            if excursion is None:
                excursion=_start_excursion(d,i,row,below,above,prior_bars)
                continue

            if excursion['dir']==1 and row.low<excursion['extreme']:
                excursion['extreme']=float(row.low); excursion['cvd_ext']=float(row.cvd_proxy)
            if excursion['dir']==-1 and row.high>excursion['extreme']:
                excursion['extreme']=float(row.high); excursion['cvd_ext']=float(row.cvd_proxy)

            dirn=excursion['dir']
            inside_primary=(row.close>row.l2) if dirn==1 else (row.close<row.u2)
            if not inside_primary:continue

            # Preserve the original MTF intent. 3m still requires 5m + 30m inside.
            # For a 5m primary signal, the primary reclaim itself is the 5m layer,
            # so only the independent 30m confirmation remains.
            vals=[row.get('close30'),row.get('u2_30'),row.get('l2_30')]
            if minutes==3:
                vals += [row.get('close5'),row.get('u2_5'),row.get('l2_5')]
            if any(pd.isna(v) for v in vals):continue
            inside30=(row['close30']>row['l2_30']) if dirn==1 else (row['close30']<row['u2_30'])
            if not inside30:continue
            if minutes==3:
                inside5=(row['close5']>row['l2_5']) if dirn==1 else (row['close5']<row['u2_5'])
                if not inside5:continue

            if dirn==1:
                div=excursion['extreme']<excursion['ref_price'] and excursion['cvd_ext']>excursion['ref_cvd']
            else:
                div=excursion['extreme']>excursion['ref_price'] and excursion['cvd_ext']<excursion['ref_cvd']
            if not div:
                excursion=None; continue

            entry_i=i+1
            entry=float(d.iloc[entry_i].open)
            stop=(excursion['extreme']-mb.TICK) if dirn==1 else (excursion['extreme']+mb.TICK)
            target=float(row.vwap)
            if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                excursion=None; continue
            out=mb.simulate(d,entry_i,dirn,stop,target)
            if out is None:
                excursion=None; continue
            rr,j,why,mfe,mae=out
            trades.append({'session':pd.Timestamp(sess),'year':pd.Timestamp(sess).year,
                'signal_time':d.index[i],'direction':'long' if dirn==1 else 'short',
                'entry_hour':d.index[i].hour,'R':rr,'MFE_R':mfe,'MAE_R':mae,
                'exit_reason':why,'risk_pts':abs(entry-stop),
                'target_R':abs(target-entry)/abs(entry-stop),'primary_minutes':minutes})
            busy=j; excursion=None
    return pd.DataFrame(trades)


def tail_check(g,product='ES',slip_ticks=1):
    if len(g)==0:return {}
    net=pd.Series(_net_r(g,product,slip_ticks),index=g.index)
    base=_stats(net); s=net.sort_values(ascending=False)
    out={'base_avgR':base['avgR'],'base_PF':base['PF'],'base_totalR':base['totalR']}
    for k in (1,3,5):
        z=net.drop(index=s.index[:min(k,len(s))]); st=_stats(z)
        out[f'drop{k}_avgR']=st['avgR']; out[f'drop{k}_PF']=st['PF']; out[f'drop{k}_totalR']=st['totalR']
    return out


def main():
    raw=mb.load_all()
    baseline_frame=mb.build_frame(raw)
    baseline=mb.generate(baseline_frame,use_cvd=True)
    print('=== PHASE 3G: HIGHER-TIMEFRAME STRUCTURAL TEST ===')
    print('Hypothesis: 1-minute setup is too noisy/cost-sensitive. Rebuild the same thesis on 3m and 5m primary bars.')
    print('Exactly two pre-specified timeframes: 3m and 5m. No timeframe/threshold optimization.')
    print('Warm-up remains 60 minutes; CVD-divergence reference remains approximately 20 minutes.')
    print('3m requires primary + 5m + 30m reclaim. 5m requires primary + 30m reclaim.')
    print('Entry is next primary-bar open; stop is 1 tick beyond excursion extreme; target is primary session VWAP.')
    print('Selection uses 2021-23 development + 2024 validation only. 2025/26 reveal-only.')

    print('\n1-MINUTE BASELINE REFERENCE -- ES, 1 TICK TOTAL ADVERSE SLIPPAGE')
    for name,g in [('DEV21-23',baseline[baseline.year<=2023]),('VAL24',baseline[baseline.year==2024])]:
        m=metrics(g,'ES',1)
        print(name,{k:round(v,4) if isinstance(v,(float,np.floating)) else v for k,v in m.items()})

    all_trades=[]; selection=[]
    for minutes in TIMEFRAMES:
        frame=build_primary(raw,minutes)
        t=generate_primary(frame,minutes)
        all_trades.append(t)
        dev=t[t.year<=2023]; val=t[t.year==2024]
        md=metrics(dev,'ES',1); mv=metrics(val,'ES',1)
        selection.append({'primary_minutes':minutes,'dev_n':len(dev),'val_n':len(val),
            'dev_net_win':md['net_win'],'val_net_win':mv['net_win'],
            'dev_ES1_avgR':md['net_avgR'],'val_ES1_avgR':mv['net_avgR'],
            'dev_ES1_PF':md['net_PF'],'val_ES1_PF':mv['net_PF'],
            'floor_avgR':min(md['net_avgR'],mv['net_avgR']),
            'floor_PF':min(md['net_PF'],mv['net_PF'])})

    sel=pd.DataFrame(selection).sort_values(['floor_avgR','floor_PF'],ascending=False).reset_index(drop=True)
    print('\nSELECTION TABLE -- 2025/26 NOT USED')
    print(sel.round(4).to_string(index=False))
    eligible=sel[(sel.dev_n>=MIN_DEV)&(sel.val_n>=MIN_VAL)&
                 (sel.floor_avgR>0)&(sel.floor_PF>1.0)]
    combined=pd.concat(all_trades,ignore_index=True) if all_trades else pd.DataFrame()

    if len(eligible)==0:
        print('\nFROZEN_CANDIDATE NONE')
        print('INTERPRETATION: neither 3m nor 5m produced positive ES after-cost expectancy in both development and 2024 validation with adequate sample size. Do not tune intermediate timeframes after seeing this result.')
        sel.to_csv('phase3a_stop_economics.csv',index=False)
    else:
        chosen=int(eligible.iloc[0].primary_minutes)
        print('\nFROZEN_CANDIDATE',f'{chosen}MIN_PRIMARY')
        z=combined[combined.primary_minutes==chosen].copy()
        periods={'DEV21-23':z.year<=2023,'VAL24':z.year==2024,'EVAL25':z.year==2025,
                 'RECENT26':z.year==2026,'ALL':pd.Series(True,index=z.index)}
        rows=[]
        for name,mask in periods.items():
            g=z[mask]
            for product in ('ES','MES'):
                for slip in (0,1,2,4):
                    m=metrics(g,product,slip)
                    m.update({'period':name,'product':product,'slip_ticks':slip})
                    rows.append(m)
        reveal=pd.DataFrame(rows)
        print('\nFROZEN RULE COST/SLIPPAGE REVEAL')
        print(reveal[['period','product','slip_ticks','n','net_win','net_avgR','net_PF','net_DD']].round(4).to_string(index=False))
        print('\nTAIL ROBUSTNESS -- ES 1 TICK')
        for name in ('DEV21-23','VAL24','EVAL25','RECENT26'):
            g=z[periods[name]]
            print(name,{k:round(v,4) for k,v in tail_check(g,'ES',1).items()})
        a=reveal[(reveal.period=='DEV21-23')&(reveal.product=='ES')&(reveal.slip_ticks==1)].iloc[0]
        b=reveal[(reveal.period=='VAL24')&(reveal.product=='ES')&(reveal.slip_ticks==1)].iloc[0]
        gate70=bool(a.net_win>=70 and b.net_win>=70 and a.net_PF>=1.25 and b.net_PF>=1.25 and a.net_avgR>0 and b.net_avgR>0)
        print('\nROBUSTNESS_GATE_70',gate70)
        reveal.to_csv('phase3a_stop_economics.csv',index=False)

    sel.to_csv('phase3a_top_candidates.csv',index=False)
    sel.to_csv('phase3a_all_candidates.csv',index=False)
    combined.to_csv('phase3a_enriched_trades.csv',index=False)
    pd.DataFrame().to_csv('phase3a_random_controls.csv',index=False)

if __name__=='__main__': main()
