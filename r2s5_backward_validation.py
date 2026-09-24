import io
import requests
import numpy as np
import pandas as pd
import strategy_tournament_round2 as r2

BASE = r2.BASE
YEARS = list(range(2016, 2024))
BACKWARD = list(range(2016, 2021))
NY = r2.NY


def load_one_year(y):
    q=requests.get(BASE.format(y),timeout=180); q.raise_for_status()
    d=pd.read_csv(io.StringIO(q.text))
    d['datetime_et']=pd.to_datetime(d['datetime_et'],utc=True).dt.tz_convert(NY)
    for c in ['open','high','low','close','volume']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime_et','open','high','low','close','volume','symbol']).copy()
    d['rth_bool']=d['rth'].astype(str).str.lower().eq('true')
    d=d.sort_values(['datetime_et','symbol'])
    rr=d[d.rth_bool].copy(); rr['session']=rr.datetime_et.dt.date
    ns=rr.groupby('session').symbol.nunique(); roll=set(ns[ns>1].index)
    if roll: print('excluding roll-switch sessions',y,len(roll),sorted(roll))
    rr=rr[~rr.session.isin(roll)].copy()
    before=len(rr)
    rr=(rr.sort_values(['datetime_et','volume'],ascending=[True,False])
          .drop_duplicates('datetime_et',keep='first').sort_values('datetime_et'))
    print('loaded',y,'RTH rows',len(rr),'sessions',rr.session.nunique(),'duplicates_resolved',before-len(rr))
    rr=rr.set_index('datetime_et'); rr['session']=rr.index.date
    return d,rr


def block_stats(g, years, product='ES', slip=1):
    z=g[g.year.isin(years)]
    return r2.stats(r2.net_r(z,product,slip)) if len(z) else r2.stats([])


def fmt(x):
    return {k:(round(float(v),4) if isinstance(v,(float,np.floating)) and np.isfinite(v) else v) for k,v in x.items()}


def main():
    print('=== R2S5 FROZEN BACKWARD VALIDATION ===')
    print('Unseen backward block: 2016-2020. Original development: 2021-2023. 2024+ are not loaded.')
    print('Exact Round-2 R2S5 strategy function is reused without modification.')
    print('Year-by-year loading is a performance optimization only; strategy logic is unchanged.')
    trades=[]
    for y in YEARS:
        full,rth=load_one_year(y)
        for sess,d in rth.groupby('session',sort=False):
            sym=d.symbol.iloc[0]
            eth=r2.full_for_session(full,sess,sym)
            trades.extend(r2.s5_trend(d.copy(),eth,sess))
    t=pd.DataFrame(trades).sort_values(['entry_time','exit_time']).reset_index(drop=True)
    t.to_csv('r2s5_backward_validation_trades.csv',index=False)

    print('\nIMPLEMENTATION AUDIT')
    by=t.groupby('session').size() if len(t) else pd.Series(dtype=int)
    overlap=0
    if len(t):
        tt=t.copy()
        tt['entry_time']=pd.to_datetime(tt.entry_time,utc=True).dt.tz_convert(NY)
        tt['exit_time']=pd.to_datetime(tt.exit_time,utc=True).dt.tz_convert(NY)
        mins=tt.entry_time.dt.hour*60+tt.entry_time.dt.minute
        for _,g in tt.groupby('session'):
            prev=None
            for _,x in g.sort_values('entry_time').iterrows():
                if prev is not None and x.entry_time<=prev: overlap+=1
                prev=x.exit_time
        print({'trades':len(t),'sessions_with_trade':int(t.session.nunique()),'max_trades_day':int(by.max()),
               'overlaps':overlap,'before_1030':int((mins<630).sum()),'after_1500':int((mins>900).sum()),
               'median_risk_pts':round(float(t.risk_pts.median()),4),'min_risk_pts':round(float(t.risk_pts.min()),4),
               'max_risk_pts':round(float(t.risk_pts.max()),4),
               'longs':int((t.direction=='long').sum()),'shorts':int((t.direction=='short').sum())})
        print('exit_reasons',t.exit_reason.value_counts().to_dict())

    b=block_stats(t,BACKWARD,'ES',1)
    dev=block_stats(t,[2021,2022,2023],'ES',1)
    all1=block_stats(t,YEARS,'ES',1)
    all4=block_stats(t,YEARS,'ES',4)
    print('\nBACKWARD_UNSEEN_2016_2020_ES1',fmt(b))
    print('ORIGINAL_DEV_2021_2023_ES1',fmt(dev))
    print('COMBINED_2016_2023_ES1',fmt(all1))
    print('COMBINED_2016_2023_ES4',fmt(all4))

    print('\nYEAR BY YEAR -- ES 1 TICK')
    pos_back=0; rows=[]
    for y in YEARS:
        g=t[t.year==y]
        s=r2.stats(r2.net_r(g,'ES',1)) if len(g) else r2.stats([])
        if y in BACKWARD and s['totalR']>0: pos_back+=1
        rows.append({'year':y,**s})
    yd=pd.DataFrame(rows)
    print(yd.round(4).to_string(index=False))

    print('\nCOST SENSITIVITY -- COMBINED 2016-2023')
    cost=[]
    for product in ['ES','MES']:
        for slip in [0,1,2,4]:
            s=block_stats(t,YEARS,product,slip)
            cost.append({'product':product,'slip_ticks':slip,**s})
    cd=pd.DataFrame(cost); cd.to_csv('r2s5_backward_validation_costs.csv',index=False)
    print(cd.round(4).to_string(index=False))

    net=pd.Series(r2.net_r(t,'ES',1),index=t.index)
    ranked=net.sort_values(ascending=False)
    drop5=r2.stats(net.drop(index=ranked.index[:min(5,len(ranked))]))
    gross=net[net>0].sum(); max_share=float(net.max()/gross) if gross>0 else np.nan
    print('\nTAIL_ROBUSTNESS_DROP5',fmt(drop5))
    print('MAX_WINNER_GROSS_SHARE',round(max_share,6) if np.isfinite(max_share) else max_share)

    gate=bool(
        b['n']>=60 and b['avgR']>0 and b['PF']>=1.10 and pos_back>=3 and
        all1['n']>=100 and all1['avgR']>0.10 and all1['PF']>=1.20 and
        all4['avgR']>0 and drop5['avgR']>0 and drop5['PF']>=1.10 and
        (np.isnan(max_share) or max_share<=0.20)
    )
    print('\nBACKWARD_POSITIVE_YEARS',pos_back,'of 5')
    print('FROZEN_R2S5_BACKWARD_GATE',gate)
    if gate:
        print('INTERPRETATION: R2S5 earns 2024 validation. Do not tune before 2024.')
    else:
        print('INTERPRETATION: R2S5 fails backward validation. Do not tune or reveal 2024 as rescue.')

if __name__=='__main__': main()
