import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import multiyear_backtest as mb

DEV_YEARS=(2021,2022,2023)
DEFAULT_CVD=Path('databento_true_cvd')/'true_cvd_minute_delta_2021_2022_2023.parquet'


def load_true_delta(path):
    p=Path(path)
    if not p.exists():
        raise SystemExit(f'True-CVD file not found: {p}')
    x=pd.read_parquet(p) if p.suffix.lower()=='.parquet' else pd.read_csv(p)
    need={'minute_utc','buy_volume','sell_volume','delta'}
    missing=need-set(x.columns)
    if missing:
        raise SystemExit(f'Missing true-CVD columns: {sorted(missing)}')
    x=x.copy()
    x['minute_utc']=pd.to_datetime(x['minute_utc'],utc=True)
    for c in ('buy_volume','sell_volume','delta'):
        x[c]=pd.to_numeric(x[c],errors='raise').astype('int64')
    x=x.groupby('minute_utc',as_index=False).agg(
        buy_volume=('buy_volume','sum'),sell_volume=('sell_volume','sum'),delta=('delta','sum')
    ).sort_values('minute_utc').reset_index(drop=True)
    arithmetic=int(x.buy_volume.sum())-int(x.sell_volume.sum())
    reported=int(x.delta.sum())
    if arithmetic!=reported:
        raise SystemExit(f'Integrity failure: buy-sell={arithmetic}, delta sum={reported}')
    ts=x['minute_utc'].astype('int64').to_numpy()
    vals=x.delta.to_numpy(dtype=np.int64)
    prefix=np.empty(len(vals)+1,dtype=np.int64); prefix[0]=0
    np.cumsum(vals,dtype=np.int64,out=prefix[1:])
    return x,ts,prefix


def cvd_change(ref_time,extreme_time,ts,prefix):
    ref=pd.Timestamp(ref_time).tz_convert('UTC').value
    ext=pd.Timestamp(extreme_time).tz_convert('UTC').value
    # Equivalent to CVD(extreme)-CVD(reference): sum delta in (reference, extreme].
    a=np.searchsorted(ts,ref,side='right')
    b=np.searchsorted(ts,ext,side='right')
    return int(prefix[b]-prefix[a])


def generate_true(frame,ts,prefix):
    trades=[]; checks=0; price_divs=0; cvd_passes=0
    for sess,d in frame.groupby('session',sort=False):
        year=pd.Timestamp(sess).year
        if year not in DEV_YEARS: continue
        d=d.copy(); busy=-1; excursion=None
        if len(d)<120: continue
        for i in range(60,len(d)-1):
            if i<=busy: continue
            row=d.iloc[i]
            if not np.isfinite(row.u2) or not np.isfinite(row.l2): continue
            below=row.low<row.l2; above=row.high>row.u2
            if excursion is None:
                if below and not above:
                    prior=d.iloc[max(0,i-20):i]
                    if len(prior)==0: continue
                    k=prior.low.idxmin()
                    excursion={'dir':1,'extreme':float(row.low),'extreme_time':d.index[i],
                               'ref_price':float(prior.loc[k,'low']),'ref_time':k}
                elif above and not below:
                    prior=d.iloc[max(0,i-20):i]
                    if len(prior)==0: continue
                    k=prior.high.idxmax()
                    excursion={'dir':-1,'extreme':float(row.high),'extreme_time':d.index[i],
                               'ref_price':float(prior.loc[k,'high']),'ref_time':k}
                continue
            if excursion['dir']==1 and row.low<excursion['extreme']:
                excursion['extreme']=float(row.low); excursion['extreme_time']=d.index[i]
            if excursion['dir']==-1 and row.high>excursion['extreme']:
                excursion['extreme']=float(row.high); excursion['extreme_time']=d.index[i]
            dirn=excursion['dir']
            inside1=(row.close>row.l2) if dirn==1 else (row.close<row.u2)
            vals=[row.get('close5'),row.get('u2_5'),row.get('l2_5'),row.get('close30'),row.get('u2_30'),row.get('l2_30')]
            if not inside1 or any(pd.isna(v) for v in vals): continue
            inside5=(row.close5>row.l2_5) if dirn==1 else (row.close5<row.u2_5)
            inside30=(row.close30>row.l2_30) if dirn==1 else (row.close30<row.u2_30)
            if not(inside5 and inside30): continue
            checks+=1
            price_div=(excursion['extreme']<excursion['ref_price']) if dirn==1 else (excursion['extreme']>excursion['ref_price'])
            if not price_div:
                excursion=None; continue
            price_divs+=1
            delta_change=cvd_change(excursion['ref_time'],excursion['extreme_time'],ts,prefix)
            div=(delta_change>0) if dirn==1 else (delta_change<0)
            if not div:
                excursion=None; continue
            cvd_passes+=1
            entry_i=i+1; entry=float(d.iloc[entry_i].open)
            stop=excursion['extreme']-mb.TICK if dirn==1 else excursion['extreme']+mb.TICK
            target=float(row.vwap)
            if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                excursion=None; continue
            out=mb.simulate(d,entry_i,dirn,stop,target)
            if out is None:
                excursion=None; continue
            rr,j,why,mfe,mae=out
            trades.append({'session':pd.Timestamp(sess),'year':year,'signal_time':d.index[i],
                'direction':'long' if dirn==1 else 'short','entry_hour':d.index[i].hour,
                'R':rr,'MFE_R':mfe,'MAE_R':mae,'exit_reason':why,'risk_pts':abs(entry-stop),
                'symbol':row.symbol,'ref_time':excursion['ref_time'],'extreme_time':excursion['extreme_time'],
                'ref_price':excursion['ref_price'],'extreme_price':excursion['extreme'],
                'true_cvd_change':delta_change})
            busy=j; excursion=None
    return pd.DataFrame(trades),{'mtf_reclaim_checks':checks,'price_divergences':price_divs,'true_cvd_passes_before_geometry':cvd_passes}


def _stats(v):
    v=pd.Series(v,dtype=float).dropna()
    if len(v)==0: return {'n':0,'win':np.nan,'avgR':np.nan,'PF':np.nan,'DD':np.nan,'totalR':np.nan}
    w=v[v>0]; l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum()) else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return {'n':len(v),'win':100*(v>0).mean(),'avgR':v.mean(),'PF':pf,'DD':dd.min(),'totalR':v.sum()}


def net_r(g,product='ES',slip_ticks=1):
    point=50.0 if product=='ES' else 5.0
    comm=5.0 if product=='ES' else 1.50
    cost_pts=slip_ticks*mb.TICK+comm/point
    return g.R.to_numpy()-cost_pts/g.risk_pts.to_numpy()


def metrics(g,product='ES',slip_ticks=1):
    raw=_stats(g.R if len(g) else [])
    net=_stats(net_r(g,product,slip_ticks) if len(g) else [])
    return {'n':raw['n'],'raw_win':raw['win'],'raw_avgR':raw['avgR'],'raw_PF':raw['PF'],
            'net_win':net['win'],'net_avgR':net['avgR'],'net_PF':net['PF'],'net_DD':net['DD'],'net_totalR':net['totalR']}


def rounded(d):
    return {k:(round(v,4) if isinstance(v,(float,np.floating)) else v) for k,v in d.items()}


def tail(g,product='ES',slip_ticks=1):
    if len(g)==0: return {}
    net=pd.Series(net_r(g,product,slip_ticks),index=g.index)
    s=net.sort_values(ascending=False)
    out={}
    for k in (0,1,3,5):
        z=net if k==0 else net.drop(index=s.index[:min(k,len(s))])
        st=_stats(z)
        tag='base' if k==0 else f'drop{k}'
        out[f'{tag}_avgR']=st['avgR']; out[f'{tag}_PF']=st['PF']; out[f'{tag}_totalR']=st['totalR']
    return out


def overlap(a,b):
    ka=set(zip(pd.to_datetime(a.signal_time),a.direction)) if len(a) else set()
    kb=set(zip(pd.to_datetime(b.signal_time),b.direction)) if len(b) else set()
    n=len(ka&kb)
    return {'same_signal_count':n,'pct_of_proxy':100*n/len(ka) if ka else 0,'pct_of_true':100*n/len(kb) if kb else 0}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cvd-file',default=str(DEFAULT_CVD))
    args=ap.parse_args()
    print('=== TRUE-CVD DEVELOPMENT BACKTEST: 2021-2023 ONLY ===')
    print('2024-2026 remain unrevealed. Only the CVD source changes.')
    cvd,ts,prefix=load_true_delta(args.cvd_file)
    print('True-CVD integrity',{'minute_rows':len(cvd),'buy_volume':int(cvd.buy_volume.sum()),
          'sell_volume':int(cvd.sell_volume.sum()),'net_delta':int(cvd.delta.sum())})
    raw=mb.load_all(); frame=mb.build_frame(raw)
    proxy=mb.generate(frame,use_cvd=True); proxy=proxy[proxy.year.isin(DEV_YEARS)].reset_index(drop=True)
    no_cvd=mb.generate(frame,use_cvd=False); no_cvd=no_cvd[no_cvd.year.isin(DEV_YEARS)].reset_index(drop=True)
    true,diag=generate_true(frame,ts,prefix)
    print('\nSIGNAL DIAGNOSTICS'); print(diag); print('proxy_vs_true_overlap',rounded(overlap(proxy,true)))
    print('\nPRIMARY COMPARISON -- ES, $5 RT + 1 TICK TOTAL ADVERSE SLIPPAGE')
    for label,t in [('MTF_NO_CVD',no_cvd),('OLD_PROXY_CVD',proxy),('TRUE_AGGRESSOR_CVD',true)]:
        print(label,rounded(metrics(t,'ES',1)))
    print('\nTRUE-CVD YEAR BY YEAR -- ES, 1 TICK')
    for y in DEV_YEARS: print(y,rounded(metrics(true[true.year==y],'ES',1)))
    print('\nTRUE-CVD COST SENSITIVITY')
    rows=[]
    for product in ('ES','MES'):
        for slip in (0,1,2,4):
            m=metrics(true,product,slip); m.update({'product':product,'slip_ticks':slip}); rows.append(m)
    sens=pd.DataFrame(rows)
    print(sens[['product','slip_ticks','n','net_win','net_avgR','net_PF','net_DD','net_totalR']].round(4).to_string(index=False))
    print('\nTRUE-CVD TAIL ROBUSTNESS -- ES, 1 TICK'); print(rounded(tail(true,'ES',1)))
    print('\nTRUE-CVD DIRECTION -- ES, 1 TICK')
    for k,g in true.groupby('direction'): print(k,rounded(metrics(g,'ES',1)))
    p=metrics(true,'ES',1); tc=tail(true,'ES',1)
    gate=bool(len(true)>=100 and p['net_avgR']>0 and p['net_PF']>=1.10 and tc.get('drop5_avgR',-np.inf)>0)
    print('\nDEVELOPMENT_GATE_FOR_2024_DOWNLOAD',gate)
    print('Interpretation:', 'justify untouched 2024 validation download' if gate else 'do NOT reveal 2024 yet')
    true.to_csv('true_cvd_dev_trades.csv',index=False)
    sens.to_csv('true_cvd_dev_cost_sensitivity.csv',index=False)
    pd.DataFrame([diag]).to_csv('true_cvd_dev_diagnostics.csv',index=False)
    print('Saved true_cvd_dev_trades.csv, true_cvd_dev_cost_sensitivity.csv, true_cvd_dev_diagnostics.csv')


if __name__=='__main__': main()
