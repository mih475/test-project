import io, requests, numpy as np, pandas as pd

BASE='https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv'
TICK=0.25
YEARS=range(2021,2027)


def load_all():
    parts=[]
    for y in YEARS:
        r=requests.get(BASE.format(y),timeout=180); r.raise_for_status()
        df=pd.read_csv(io.StringIO(r.text))
        # Normalize all provider timestamps to timezone-aware New York time.
        df['datetime_et']=pd.to_datetime(df['datetime_et'],utc=True).dt.tz_convert('America/New_York')
        if 'rth' in df.columns:
            df=df[df['rth'].astype(str).str.lower().eq('true')]
        keep=['datetime_et','open','high','low','close','volume','symbol']
        df=df[keep].copy()
        for c in ['open','high','low','close','volume']:
            df[c]=pd.to_numeric(df[c],errors='coerce')
        df=df.dropna().sort_values(['datetime_et','symbol'])
        df['session']=df.datetime_et.dt.date
        df['year']=y

        # Explicit continuous-contract construction: use the highest-RTH-volume
        # contract for each session, instead of relying on arbitrary timestamp dedupe.
        dayvol=df.groupby(['session','symbol'],as_index=False).volume.sum()
        idx=dayvol.groupby('session').volume.idxmax()
        active=dayvol.loc[idx,['session','symbol']].rename(columns={'symbol':'active_symbol'})
        df=df.merge(active,on='session',how='left')
        df=df[df.symbol.eq(df.active_symbol)].drop(columns='active_symbol')
        df=df.drop_duplicates('datetime_et',keep='first').sort_values('datetime_et')
        parts.append(df)
        print('loaded',y,'RTH rows',len(df),'sessions',df.session.nunique(),'symbols',sorted(df.symbol.dropna().unique())[:8])

    x=pd.concat(parts,ignore_index=True).drop_duplicates('datetime_et',keep='first').sort_values('datetime_et')
    x=x.set_index('datetime_et')
    x['session']=x.index.date
    return x


def session_bands(df):
    x=df.copy()
    tp=(x.high+x.low+x.close)/3.0
    pv=tp*x.volume; p2v=(tp**2)*x.volume
    g=x.groupby('session',sort=False)
    cv=g.volume.cumsum(); cpv=pv.groupby(x.session).cumsum(); cp2v=p2v.groupby(x.session).cumsum()
    x['vwap']=cpv/cv
    var=(cp2v/cv)-x.vwap**2
    x['sd']=np.sqrt(var.clip(lower=0))
    x['u2']=x.vwap+2*x.sd; x['l2']=x.vwap-2*x.sd
    return x


def resample_session(d,rule):
    # For each session, align from 09:30 and make higher-TF values available only at bar close.
    out=[]
    for sess,g in d.groupby('session',sort=False):
        r=g[['open','high','low','close','volume']].resample(rule,origin='start_day',offset='30min',label='right',closed='right').agg({
            'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
        r['session']=sess; out.append(r)
    return session_bands(pd.concat(out).sort_index())


def build_frame(df):
    b1=session_bands(df)
    b5=resample_session(df,'5min')
    b30=resample_session(df,'30min')
    pieces=[]
    # Merge per-session to prevent prior-session higher-TF values leaking into a new day.
    for sess,g in b1.groupby('session',sort=False):
        z=g.copy().reset_index().rename(columns={'datetime_et':'ts'})
        for nm,tf in [('5',b5),('30',b30)]:
            r=tf[tf.session==sess][['close','u2','l2']].reset_index().rename(columns={'datetime_et':'tf_ts','close':f'close{nm}','u2':f'u2_{nm}','l2':f'l2_{nm}'})
            z=pd.merge_asof(z.sort_values('ts'),r.sort_values('tf_ts'),left_on='ts',right_on='tf_ts',direction='backward')
        z=z.set_index('ts'); z.index.name='datetime_et'; pieces.append(z)
    x=pd.concat(pieces).sort_index()
    # Signed bar-volume CVD proxy (not true bid/ask delta). For doji bars,
    # compare with the prior close only within the same session.
    prev=x.groupby('session').close.shift(1)
    fallback=np.sign((x.close-prev).fillna(0))
    direction=np.where(x.close>x.open,1,np.where(x.close<x.open,-1,fallback))
    x['delta_proxy']=direction*x.volume
    x['cvd_proxy']=x.groupby('session').delta_proxy.cumsum()
    return x


def simulate(d, entry_i, direction, stop, target):
    entry=float(d.iloc[entry_i].open)
    risk=(entry-stop) if direction==1 else (stop-entry)
    if risk<TICK:return None
    mfe=0.0; mae=0.0
    for j in range(entry_i,len(d)):
        r=d.iloc[j]
        if direction==1:
            mfe=max(mfe,(r.high-entry)/risk); mae=min(mae,(r.low-entry)/risk)
            hit_s=r.low<=stop; hit_t=r.high>=target
        else:
            mfe=max(mfe,(entry-r.low)/risk); mae=min(mae,(entry-r.high)/risk)
            hit_s=r.high>=stop; hit_t=r.low<=target
        if hit_s and hit_t:return -1.0,j,'ambiguous_stop_first',mfe,mae
        if hit_s:return -1.0,j,'stop',mfe,mae
        if hit_t:
            rr=((target-entry)/risk) if direction==1 else ((entry-target)/risk)
            return rr,j,'target',mfe,mae
    px=float(d.iloc[-1].close)
    rr=((px-entry)/risk) if direction==1 else ((entry-px)/risk)
    return rr,len(d)-1,'eod',mfe,mae


def generate(frame, use_cvd=True):
    trades=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); busy=-1; excursion=None
        if len(d)<120:continue
        for i in range(60,len(d)-1):
            if i<=busy:continue
            row=d.iloc[i]
            if not np.isfinite(row.u2) or not np.isfinite(row.l2):continue
            below=row.low<row.l2; above=row.high>row.u2
            if excursion is None:
                if below and not above:
                    prior=d.iloc[max(0,i-20):i]
                    if len(prior)==0:continue
                    k=prior.low.idxmin()
                    excursion={'dir':1,'extreme':float(row.low),'cvd_ext':float(row.cvd_proxy),'ref_price':float(prior.loc[k,'low']),'ref_cvd':float(prior.loc[k,'cvd_proxy'])}
                elif above and not below:
                    prior=d.iloc[max(0,i-20):i]
                    if len(prior)==0:continue
                    k=prior.high.idxmax()
                    excursion={'dir':-1,'extreme':float(row.high),'cvd_ext':float(row.cvd_proxy),'ref_price':float(prior.loc[k,'high']),'ref_cvd':float(prior.loc[k,'cvd_proxy'])}
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
            if use_cvd:
                if dirn==1:
                    div=excursion['extreme']<excursion['ref_price'] and excursion['cvd_ext']>excursion['ref_cvd']
                else:
                    div=excursion['extreme']>excursion['ref_price'] and excursion['cvd_ext']<excursion['ref_cvd']
                if not div:
                    excursion=None; continue
            entry_i=i+1; entry=float(d.iloc[entry_i].open)
            stop=(excursion['extreme']-TICK) if dirn==1 else (excursion['extreme']+TICK)
            target=float(row.vwap)
            if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                excursion=None; continue
            out=simulate(d,entry_i,dirn,stop,target)
            if out is None:
                excursion=None;continue
            rr,j,why,mfe,mae=out
            trades.append({'session':pd.Timestamp(sess),'year':pd.Timestamp(sess).year,'signal_time':d.index[i],'direction':'long' if dirn==1 else 'short','entry_hour':d.index[i].hour,'R':rr,'MFE_R':mfe,'MAE_R':mae,'exit_reason':why,'risk_pts':abs(entry-stop),'symbol':row.symbol})
            busy=j; excursion=None
    return pd.DataFrame(trades)


def stats(t):
    if len(t)==0:return {'n':0}
    wins=t[t.R>0].R; losses=t[t.R<=0].R
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum())>0 else np.inf
    eq=t.R.cumsum(); dd=eq-eq.cummax()
    return {'n':len(t),'win_pct':100*(t.R>0).mean(),'avgR':t.R.mean(),'PF':pf,'totalR':t.R.sum(),'maxDD_R':dd.min(),'avgWinR':wins.mean() if len(wins) else np.nan,'avgLossR':losses.mean() if len(losses) else np.nan,'medMFE':t.MFE_R.median(),'medMAE':t.MAE_R.median()}


def show(label,t):
    print('\n###',label)
    s=stats(t)
    print(' '.join(f'{k}={v:.4f}' if isinstance(v,(float,np.floating)) else f'{k}={v}' for k,v in s.items()))


def main():
    raw=load_all(); print('ALL RTH rows',len(raw),'sessions',raw.session.nunique(),'start',raw.index.min(),'end',raw.index.max())
    frame=build_frame(raw)
    mtf=generate(frame,use_cvd=False)
    cvd=generate(frame,use_cvd=True)
    print('\nNOTE: CVD is signed 1-minute bar volume, not exchange aggressor-side delta. Source volume provenance still needs independent verification.')
    show('ALL MTF no CVD',mtf); show('ALL MTF + CVD proxy',cvd)
    print('\nYEAR BY YEAR - CVD PROXY')
    for y in YEARS: show(str(y),cvd[cvd.year==y])
    show('DEVELOPMENT 2021-2024',cvd[cvd.year<=2024])
    show('PRIMARY HOLDOUT 2025',cvd[cvd.year==2025])
    show('RECENT CONFIRMATION 2026 (NOT PURE HOLDOUT)',cvd[cvd.year==2026])
    print('\nDIRECTION')
    for k,g in cvd.groupby('direction'): show(k,g)
    print('\nENTRY HOUR ET')
    for k,g in cvd.groupby('entry_hour'): show(str(k),g)
    print('\nMONTHLY CONSISTENCY')
    cvd=cvd.copy();cvd['month']=cvd.session.dt.to_period('M').astype(str)
    months=[]
    for m,g in cvd.groupby('month'):
        s=stats(g); months.append((m,s.get('n',0),s.get('avgR',np.nan),s.get('PF',np.nan),s.get('totalR',np.nan)))
    for row in months: print(row)
    pos=sum(1 for _,_,avg,_,_ in months if avg>0); print('positive_months',pos,'of',len(months),'pct',100*pos/len(months) if months else np.nan)
    cvd.to_csv('multiyear_trades.csv',index=False)

if __name__=='__main__': main()
