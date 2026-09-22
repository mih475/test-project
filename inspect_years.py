import io
import requests
import pandas as pd
import numpy as np

BASE='https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv'
YEARS=range(2021,2027)


def load_year(y):
    r=requests.get(BASE.format(y),timeout=180)
    print('\nYEAR',y,'status',r.status_code,'bytes',len(r.content))
    r.raise_for_status()
    d=pd.read_csv(io.StringIO(r.text))
    d['datetime_et']=pd.to_datetime(d['datetime_et'],utc=True).dt.tz_convert('America/New_York')
    d=d[d['rth'].astype(str).str.lower().eq('true')].copy()
    for c in ['open','high','low','close','volume']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['datetime_et','open','high','low','close','volume','symbol'])
    d['session']=d.datetime_et.dt.date
    return d.sort_values(['datetime_et','symbol'])


def describe_year(y,d):
    n=len(d); uniq_ts=d.datetime_et.nunique(); dup_rows=n-uniq_ts
    per_ts=d.groupby('datetime_et').symbol.nunique()
    overlap_ts=int((per_ts>1).sum())
    print('rows',n,'unique_ts',uniq_ts,'extra_rows_same_ts',dup_rows,'overlap_timestamps_multi_symbol',overlap_ts,
          'overlap_pct',round(100*overlap_ts/max(1,uniq_ts),3))
    print('symbols',sorted(d.symbol.unique()))
    print('rows_by_symbol',d.groupby('symbol').size().to_dict())

    # Session completeness before selecting a contract.
    raw_counts=d.groupby('session').datetime_et.nunique()
    print('sessions',len(raw_counts),'median_unique_minutes',float(raw_counts.median()),
          'sessions_lt_380',int((raw_counts<380).sum()),'sessions_eq_390',int((raw_counts==390).sum()))

    # Determine the most liquid contract for each session using total RTH volume.
    dayvol=d.groupby(['session','symbol'],as_index=False).volume.sum()
    idx=dayvol.groupby('session').volume.idxmax()
    active=dayvol.loc[idx,['session','symbol','volume']].rename(columns={'symbol':'active_symbol','volume':'active_day_volume'})
    print('active_symbol_session_counts',active.groupby('active_symbol').size().to_dict())

    # Compare the current baseline's implicit first-row selection against the daily most-liquid contract.
    first=d.drop_duplicates('datetime_et',keep='first')[['datetime_et','session','symbol','close','volume']].rename(columns={'symbol':'first_symbol','close':'first_close','volume':'first_volume'})
    selected=d.merge(active[['session','active_symbol']],on='session',how='left')
    selected=selected[selected.symbol.eq(selected.active_symbol)].drop_duplicates('datetime_et',keep='first')
    selected=selected[['datetime_et','session','symbol','close','volume']].rename(columns={'symbol':'active_symbol','close':'active_close','volume':'active_volume'})
    cmp=first.merge(selected,on=['datetime_et','session'],how='inner')
    cmp['same_symbol']=cmp.first_symbol.eq(cmp.active_symbol)
    cmp['close_diff_abs']=(cmp.first_close-cmp.active_close).abs()
    mismatch=cmp[~cmp.same_symbol]
    print('baseline_vs_daily_liquid compared_rows',len(cmp),'symbol_mismatch_rows',len(mismatch),
          'mismatch_pct',round(100*len(mismatch)/max(1,len(cmp)),3),
          'median_abs_price_diff_mismatch',round(float(mismatch.close_diff_abs.median()),4) if len(mismatch) else 0.0,
          'max_abs_price_diff_mismatch',round(float(mismatch.close_diff_abs.max()),4) if len(mismatch) else 0.0)

    # Show the largest mismatch examples so roll/contract contamination is obvious in logs.
    if len(mismatch):
        cols=['datetime_et','first_symbol','active_symbol','first_close','active_close','close_diff_abs']
        print('largest_mismatches')
        print(mismatch.nlargest(10,'close_diff_abs')[cols].to_string(index=False))

    # Audit selected-continuous series for session completeness and roll transitions.
    sc=selected.groupby('session').size()
    print('daily_liquid_session_minutes median',float(sc.median()),'lt380',int((sc<380).sum()),'eq390',int((sc==390).sum()))
    active=active.sort_values('session').reset_index(drop=True)
    active['prev_symbol']=active.active_symbol.shift(1)
    rolls=active[active.active_symbol.ne(active.prev_symbol) & active.prev_symbol.notna()]
    print('roll_transitions',len(rolls))
    print(rolls[['session','prev_symbol','active_symbol']].to_string(index=False) if len(rolls) else 'none')

    # Close-to-next-open gaps in active series; flag extreme transitions, especially around rolls.
    byday=[]
    for sess,g in selected.groupby('session'):
        g=g.sort_values('datetime_et')
        byday.append({'session':sess,'symbol':g.active_symbol.iloc[0],'open':g.iloc[0].active_close,'close':g.iloc[-1].active_close})
    bd=pd.DataFrame(byday).sort_values('session')
    bd['prev_close']=bd['close'].shift(1); bd['gap']=bd['open']-bd['prev_close']; bd['prev_symbol']=bd.symbol.shift(1)
    bd['roll']=bd.symbol.ne(bd.prev_symbol)&bd.prev_symbol.notna()
    print('largest_abs_overnight_gaps')
    print(bd.nlargest(10,bd.gap.abs().name if False else 'gap')[['session','prev_symbol','symbol','gap','roll']].to_string(index=False))


all_parts=[]
for y in YEARS:
    d=load_year(y)
    describe_year(y,d)
    all_parts.append(d)

all_d=pd.concat(all_parts,ignore_index=True).sort_values(['datetime_et','symbol'])
print('\n=== CROSS-YEAR SUMMARY ===')
print('rows',len(all_d),'unique_ts',all_d.datetime_et.nunique(),'symbols',sorted(all_d.symbol.unique()))
per_ts=all_d.groupby('datetime_et').symbol.nunique()
print('timestamps_with_multiple_symbols',int((per_ts>1).sum()),'of',len(per_ts),'pct',round(100*(per_ts>1).mean(),3))
