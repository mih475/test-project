import io
import requests
import pandas as pd

BASE='https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv'
YEARS=[2021,2022,2023]
NY='America/New_York'

for y in YEARS:
    r=requests.get(BASE.format(y),timeout=180); r.raise_for_status()
    d=pd.read_csv(io.StringIO(r.text))
    d['datetime_et']=pd.to_datetime(d['datetime_et'],utc=True).dt.tz_convert(NY)
    print('\nYEAR',y,'rows',len(d),'columns',list(d.columns))
    if 'rth' in d.columns:
        print('rth_counts',d['rth'].astype(str).str.lower().value_counts(dropna=False).to_dict())
    print('time_min',d.datetime_et.min(),'time_max',d.datetime_et.max())
    sample=d[d.datetime_et.dt.date==sorted(d.datetime_et.dt.date.unique())[5]].copy()
    print('sample_date',sample.datetime_et.dt.date.iloc[0],'rows',len(sample),'first',sample.datetime_et.min(),'last',sample.datetime_et.max())
    print('sample_hours',sorted(sample.datetime_et.dt.hour.unique().tolist()))
    # For each RTH date, look for same contract rows from prior 18:00 through 09:29.
    if 'symbol' in d.columns:
        d=d.sort_values('datetime_et')
        rth=d[d['rth'].astype(str).str.lower().eq('true')].copy() if 'rth' in d.columns else d.copy()
        dates=sorted(rth.datetime_et.dt.date.unique())[10:30]
        counts=[]
        for sess in dates:
            day=rth[rth.datetime_et.dt.date==sess]
            if len(day)==0: continue
            sym=day.symbol.mode().iloc[0]
            start=pd.Timestamp(sess,tz=NY)-pd.Timedelta(days=1)+pd.Timedelta(hours=18)
            end=pd.Timestamp(sess,tz=NY)+pd.Timedelta(hours=9,minutes=30)
            z=d[(d.symbol==sym)&(d.datetime_et>=start)&(d.datetime_et<end)]
            counts.append(len(z))
        if counts:
            s=pd.Series(counts)
            print('overnight_same_contract_rows_median',float(s.median()),'min',int(s.min()),'max',int(s.max()),'nonzero_pct',round(100*(s>0).mean(),2))
