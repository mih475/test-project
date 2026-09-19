import io, requests, numpy as np, pandas as pd

BASE='https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv'
YEARS=range(2021,2027)


def stats(t):
    if t.empty: return {'n':0}
    wins=t.loc[t.R>0,'R']; losses=t.loc[t.R<=0,'R']
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum()) else np.inf
    eq=t.R.cumsum(); dd=eq-eq.cummax()
    return {'n':len(t),'win_pct':100*(t.R>0).mean(),'avgR':t.R.mean(),'PF':pf,'totalR':t.R.sum(),'maxDD_R':dd.min()}


def show(label,t):
    s=stats(t)
    print(f"{label}: "+' '.join(f'{k}={v:.4f}' if isinstance(v,(float,np.floating)) else f'{k}={v}' for k,v in s.items()))


def load_rth():
    parts=[]
    for y in YEARS:
        r=requests.get(BASE.format(y),timeout=180); r.raise_for_status()
        d=pd.read_csv(io.StringIO(r.text))
        d['datetime_et']=pd.to_datetime(d['datetime_et'],utc=True).dt.tz_convert('America/New_York')
        d=d[d.rth.astype(str).str.lower().eq('true')].copy()
        d['session']=d.datetime_et.dt.date
        parts.append(d[['datetime_et','open','high','low','close','volume','session']])
    return pd.concat(parts,ignore_index=True).sort_values('datetime_et')


def add_daily_reference(raw):
    g=raw.groupby('session',sort=True)
    daily=g.agg(day_high=('high','max'),day_low=('low','min'))
    daily['day_range']=daily.day_high-daily.day_low
    # Opening range first 30m (09:30 through 09:59 ET)
    first30=raw[(raw.datetime_et.dt.hour==9)&(raw.datetime_et.dt.minute<60)].copy()
    first30=first30[first30.datetime_et.dt.minute>=30]
    orng=first30.groupby('session').agg(or_high=('high','max'),or_low=('low','min'))
    daily=daily.join(orng,how='left'); daily['or30']=daily.or_high-daily.or_low
    daily['prior20_day_range_med']=daily.day_range.shift(1).rolling(20,min_periods=10).median()
    daily['prior20_or30_med']=daily.or30.shift(1).rolling(20,min_periods=10).median()
    return daily


def session_features(raw, daily):
    out=[]
    for sess,d in raw.groupby('session',sort=False):
        d=d.sort_values('datetime_et').copy()
        tp=(d.high+d.low+d.close)/3
        cv=d.volume.cumsum(); cp=(tp*d.volume).cumsum(); cp2=((tp**2)*d.volume).cumsum()
        d['vwap']=cp/cv
        var=(cp2/cv)-d.vwap**2
        d['sd']=np.sqrt(var.clip(lower=0))
        d['vwap_slope30_z']=(d.vwap-d.vwap.shift(30))/d.sd.replace(0,np.nan)
        d['ret30_z']=(d.close-d.close.shift(30))/d.sd.replace(0,np.nan)
        d['session_high_sofar']=d.high.cummax(); d['session_low_sofar']=d.low.cummin()
        d['range_sofar']=d.session_high_sofar-d.session_low_sofar
        ref=daily.loc[sess] if sess in daily.index else None
        prior_day=np.nan if ref is None else ref.prior20_day_range_med
        prior_or=np.nan if ref is None else ref.prior20_or30_med
        d['range_ratio_prior20']=d.range_sofar/prior_day if pd.notna(prior_day) and prior_day>0 else np.nan
        d['or_ratio_prior20']=(ref.or30/prior_or) if ref is not None and pd.notna(ref.or30) and pd.notna(prior_or) and prior_or>0 else np.nan
        out.append(d[['datetime_et','vwap','sd','vwap_slope30_z','ret30_z','range_ratio_prior20','or_ratio_prior20']])
    return pd.concat(out,ignore_index=True)


def period_table(t, mask_name, mask):
    print('\nFILTER',mask_name)
    z=t[mask].copy()
    for label,pmask in [
        ('DEV21-23',z.year<=2023),
        ('VAL24',z.year==2024),
        ('HOLD25',z.year==2025),
        ('RECENT26',z.year==2026),
        ('ALL',pd.Series(True,index=z.index))]:
        show(label,z[pmask])


def main():
    t=pd.read_csv('multiyear_trades.csv')
    t['signal_time']=pd.to_datetime(t.signal_time,utc=True).dt.tz_convert('America/New_York')
    t['year']=t['year'].astype(int)
    print('TRADES',len(t))

    # Winner concentration / fragility
    print('\n=== WINNER CONCENTRATION ===')
    for y,g in t.groupby('year'):
        pos=g[g.R>0].sort_values('R',ascending=False)
        total=g.R.sum(); win_sum=pos.R.sum()
        top1=pos.R.head(1).sum(); top3=pos.R.head(3).sum(); top5=pos.R.head(5).sum()
        trimmed=g.drop(pos.head(5).index)
        print(y,'n',len(g),'totalR',round(total,3),'winsR',round(win_sum,3),'top1',round(top1,3),'top3',round(top3,3),'top5',round(top5,3),'trim_top5_avgR',round(trimmed.R.mean(),4),'trim_top5_PF',round(stats(trimmed).get('PF',np.nan),3))
    allpos=t[t.R>0].sort_values('R',ascending=False)
    for pct in [0.01,0.05,0.10]:
        n=max(1,int(np.ceil(len(t)*pct)))
        removed=t.drop(allpos.head(n).index)
        print('remove_top',int(pct*100),'pct_winners','n_removed',n,'remaining_avgR',round(removed.R.mean(),4),'PF',round(stats(removed).get('PF',np.nan),3),'totalR',round(removed.R.sum(),2))

    raw=load_rth(); daily=add_daily_reference(raw); f=session_features(raw,daily)
    t=pd.merge_asof(t.sort_values('signal_time'),f.sort_values('datetime_et'),left_on='signal_time',right_on='datetime_et',direction='backward',tolerance=pd.Timedelta('0min'))
    t['dir_sign']=np.where(t.direction.eq('long'),1,-1)
    t['dir_slope30_z']=t.dir_sign*t.vwap_slope30_z

    print('\n=== YEAR FEATURE MEDIANS ===')
    for y,g in t.groupby('year'):
        print(y,'slope_abs',round(g.vwap_slope30_z.abs().median(),3),'dir_slope',round(g.dir_slope30_z.median(),3),'range_ratio',round(g.range_ratio_prior20.median(),3),'or_ratio',round(g.or_ratio_prior20.median(),3),'R',round(g.R.mean(),3))

    # Predefined, coarse filters only. Evaluate chronologically; do not tune using 2025/2026.
    candidates={
      'baseline':pd.Series(True,index=t.index),
      'long_only':t.direction.eq('long'),
      'exclude_11am':t.entry_hour.ne(11),
      'hours_13_14':t.entry_hour.isin([13,14]),
      'weak_vwap_slope_abs_lt_0.20':t.vwap_slope30_z.abs()<0.20,
      'weak_vwap_slope_abs_lt_0.35':t.vwap_slope30_z.abs()<0.35,
      'slope_not_strongly_against':t.dir_slope30_z>-0.20,
      'range_sofar_lt_0.8_prior20':t.range_ratio_prior20<0.8,
      'normal_opening_range_0.7_1.4':t.or_ratio_prior20.between(0.7,1.4),
      'long_and_weak_slope':t.direction.eq('long') & (t.vwap_slope30_z.abs()<0.35),
      'long_and_not_11':t.direction.eq('long') & t.entry_hour.ne(11),
    }
    for name,mask in candidates.items(): period_table(t,name,mask.fillna(False))

    print('\n=== COARSE BUCKETS ===')
    t['slope_bucket']=pd.cut(t.vwap_slope30_z.abs(),[-np.inf,.15,.35,.70,np.inf],labels=['<.15','.15-.35','.35-.70','>.70'])
    for b,g in t.groupby('slope_bucket',observed=True):
        print('slope',b); show('  all',g); show('  2025',g[g.year==2025]); show('  2026',g[g.year==2026])
    t['range_bucket']=pd.cut(t.range_ratio_prior20,[-np.inf,.5,.8,1.2,np.inf],labels=['<.5','.5-.8','.8-1.2','>1.2'])
    for b,g in t.groupby('range_bucket',observed=True):
        print('range',b); show('  all',g); show('  2025',g[g.year==2025]); show('  2026',g[g.year==2026])

    # Bootstrap expectancy intervals by period, preserving trade-level distribution (diagnostic, not proof of iid).
    print('\n=== BOOTSTRAP AVG-R 95% CI ===')
    rng=np.random.default_rng(42)
    for label,g in [('21-23',t[t.year<=2023]),('2024',t[t.year==2024]),('2025',t[t.year==2025]),('2026',t[t.year==2026])]:
        vals=g.R.to_numpy()
        if not len(vals): continue
        means=np.array([rng.choice(vals,size=len(vals),replace=True).mean() for _ in range(5000)])
        lo,hi=np.quantile(means,[.025,.975])
        print(label,'n',len(vals),'avgR',round(vals.mean(),4),'CI',round(lo,4),round(hi,4))

    t.to_csv('forensic_enriched_trades.csv',index=False)

if __name__=='__main__': main()
